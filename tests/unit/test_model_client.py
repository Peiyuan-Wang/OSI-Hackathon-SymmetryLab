import json
from urllib.error import HTTPError
import pytest
from symmetrylab.model import client as module


def test_http_adapter_and_no_secret_in_response(monkeypatch):
    monkeypatch.setenv("SYMMETRYLAB_API_KEY", "test-secret-for-mock-only")
    seen = {}

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return json.dumps({"choices": [{"message": {"content": '{"predicate":"nonzero_q_implies_nontrivial"}'}}],
                               "usage": {"total_tokens": 12}}).encode()

    class Opener:
        def open(self, request, timeout):
            seen["url"] = request.full_url
            seen["payload"] = json.loads(request.data)
            seen["auth_present"] = bool(request.get_header("Authorization"))
            return Response()

    monkeypatch.setattr(module, "build_opener", lambda handler: Opener())
    client = module.OpenAICompatibleClient({"base_url": "https://example.com/v1", "model": "mock"})
    answer = client.complete([{"role": "user", "content": "public toy"}], 100)
    assert seen["url"] == "https://example.com/v1/chat/completions"
    assert seen["payload"]["max_tokens"] == 100 and seen["auth_present"]
    assert answer["usage"]["total_tokens"] == 12
    assert "test-secret" not in json.dumps(answer)
    assert module.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example") is None


def test_remote_error_body_is_not_exposed(monkeypatch):
    monkeypatch.setenv("SYMMETRYLAB_API_KEY", "test-secret-for-mock-only")

    class Broken:
        def open(self, *args, **kwargs):
            raise HTTPError("https://example.com", 401, "secret-body", {}, None)

    monkeypatch.setattr(module, "build_opener", lambda handler: Broken())
    client = module.OpenAICompatibleClient({"base_url": "https://example.com/v1", "model": "mock"})
    with pytest.raises(RuntimeError) as error:
        client.complete([], 10)
    assert str(error.value) == "model request failed (HTTP 401)"


def test_cc_switch_responses_uses_placeholder_and_bypasses_proxy(monkeypatch):
    seen = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,size):
            return json.dumps({'status':'completed','output':[{'type':'reasoning'}, {'type':'message','content':[{'type':'output_text','text':'OK'}]}], 'usage':{'total_tokens':5}}).encode()
    class Opener:
        def open(self,request,timeout):
            seen['url']=request.full_url; seen['body']=json.loads(request.data); seen['auth']=request.get_header('Authorization')
            return Response()
    def build(*handlers):
        seen['handlers']=handlers
        return Opener()
    monkeypatch.setattr(module,'build_opener',build)
    client=module.OpenAICompatibleClient({'base_url':'http://127.0.0.1:15721/v1','model':'test','protocol':'responses','auth_mode':'cc_switch'})
    result=client.complete([{'role':'system','content':'Be exact'},{'role':'user','content':'test'}],64)
    assert result['content']=='OK'
    assert seen['url'].endswith('/v1/responses')
    assert seen['body']['instructions']=='Be exact'
    assert seen['body']['max_output_tokens']==64 and seen['body']['store'] is False
    assert seen['auth']=='Bearer PROXY_MANAGED'
    assert any(isinstance(h,module.ProxyHandler) and not h.proxies for h in seen['handlers'])


@pytest.mark.parametrize('url',['http://example.com/v1','https://user:secret@example.com/v1','https://example.com/v1?secret=x'])
def test_unsafe_connection_rejected(url):
    with pytest.raises(ValueError):
        module.OpenAICompatibleClient({'base_url':url,'model':'test','auth_mode':'cc_switch'})


def test_responses_sse_and_incomplete(monkeypatch):
    completed={'type':'response.completed','response':{'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'OK'}]}]}}
    raw=('event: response.completed\ndata: '+json.dumps(completed)+'\n\n').encode()
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,size): return raw
    class Opener:
        def open(self,*args,**kwargs): return Response()
    monkeypatch.setattr(module,'build_opener',lambda *handlers:Opener())
    client=module.OpenAICompatibleClient({'base_url':'http://localhost:15721/v1','model':'test','protocol':'responses','auth_mode':'cc_switch'})
    assert client.complete([],64)['content']=='OK'
    raw=b'event: response.incomplete\ndata: {"type":"response.incomplete"}\n\n'
    with pytest.raises(RuntimeError,match='did not complete'): client.complete([],64)
