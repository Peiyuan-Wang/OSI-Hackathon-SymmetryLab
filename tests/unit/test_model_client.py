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
            seen["timeout"] = timeout
            seen["user_agent"] = request.get_header("User-agent")
            seen["url"] = request.full_url
            seen["payload"] = json.loads(request.data)
            seen["auth_present"] = bool(request.get_header("Authorization"))
            return Response()

    monkeypatch.setattr(module, "build_opener", lambda handler: Opener())
    client = module.OpenAICompatibleClient({"base_url": "https://example.com/v1", "model": "mock"})
    answer = client.complete([{"role": "user", "content": "public toy"}], 100)
    assert seen["url"] == "https://example.com/v1/chat/completions"
    assert seen["payload"]["max_tokens"] == 100 and seen["auth_present"]
    assert seen["timeout"] == 60 and seen["user_agent"] == "SymmetryLab/0.3"
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


def test_loopback_responses_uses_saved_key_and_bypasses_proxy(monkeypatch):
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
    client=module.OpenAICompatibleClient({'base_url':'http://127.0.0.1:8000/v1','model':'test','protocol':'responses','api_key':'saved-key-for-test'})
    result=client.complete([{'role':'system','content':'Be exact'},{'role':'user','content':'test'}],64)
    assert result['content']=='OK'
    assert seen['url'].endswith('/v1/responses')
    assert seen['body']['instructions']=='Be exact'
    assert seen['body']['max_output_tokens']==64 and seen['body']['store'] is False
    assert seen['auth']=='Bearer saved-key-for-test'
    assert any(isinstance(h,module.ProxyHandler) and not h.proxies for h in seen['handlers'])


@pytest.mark.parametrize('url',['http://example.com/v1','https://user:secret@example.com/v1','https://example.com/v1?secret=x'])
def test_unsafe_connection_rejected(url):
    with pytest.raises(ValueError):
        module.OpenAICompatibleClient({'base_url':url,'model':'test','api_key':'k'})


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
    client=module.OpenAICompatibleClient({'base_url':'http://localhost:8000/v1','model':'test','protocol':'responses','api_key':'k'})
    assert client.complete([],64)['content']=='OK'
    raw=b'event: response.incomplete\ndata: {"type":"response.incomplete"}\n\n'
    with pytest.raises(RuntimeError,match='did not complete'): client.complete([],64)


def test_key_pasted_into_variable_field_is_rejected_without_echo():
    import pytest
    from symmetrylab.model.client import OpenAICompatibleClient
    with pytest.raises(ValueError) as e:
        OpenAICompatibleClient({"base_url": "https://api.example.test/v1", "model": "m", "api_key_env": "sk-abc123-def"})
    assert "NAME" in str(e.value) and "sk-abc" not in str(e.value)


def test_server_explains_failures_with_hints():
    from symmetrylab.web.server import explain
    assert "Open Connection" in explain("No API key saved")
    assert "/v1" in explain("model request failed (HTTP 404)")


def test_connection_store_saves_key_privately_and_never_exposes_it(tmp_path, monkeypatch):
    import os, stat
    from symmetrylab.model.connection import ConnectionStore
    monkeypatch.delenv("SYMMETRYLAB_API_KEY", raising=False)
    store = ConnectionStore(tmp_path / "connection.json")
    assert store.public()["ready"] is False and store.public()["key_source"] == "none"
    view = store.save({"base_url": "https://api.example.test/v1", "model": "m1", "protocol": "responses", "api_key": "sk-test-1234567890abcd"})
    assert view == {"base_url": "https://api.example.test/v1", "model": "m1", "protocol": "responses", "key_saved": True,
                    "key_hint": "abcd", "key_source": "saved", "ready": True}
    # Windows uses inherited NTFS ACLs; POSIX mode bits do not encode those rights.
    if os.name != "nt":
        assert stat.S_IMODE(os.stat(tmp_path / "connection.json").st_mode) == 0o600
    assert "sk-test" not in json.dumps(view)
    # An empty key field keeps the saved key; other fields update.
    store.save({"base_url": "https://api.example.test/v1", "model": "m2", "protocol": "responses"})
    assert store.client_config()["api_key"] == "sk-test-1234567890abcd" and store.public()["model"] == "m2"
    assert store.save({}, forget_key=True)["key_saved"] is False
    with pytest.raises(ValueError):
        store.save({"base_url": "http://remote.example/v1", "model": "m"})       # plain HTTP off loopback
    with pytest.raises(ValueError):
        store.save({"base_url": "https://a.test/v1", "model": "m", "api_key": "two words"})
    with pytest.raises(ValueError):
        store.save({"base_url": "https://a.test/v1", "model": "m", "auth_mode": "cc_switch"})


def test_missing_key_message_points_to_connection_page(monkeypatch):
    monkeypatch.delenv("SYMMETRYLAB_API_KEY", raising=False)
    with pytest.raises(ValueError, match="No API key saved"):
        module.OpenAICompatibleClient({"base_url": "https://api.example.test/v1", "model": "m"})
