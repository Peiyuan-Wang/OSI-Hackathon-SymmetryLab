import json
from threading import Thread
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
import pytest
from symmetrylab.web.server import make_server


@pytest.fixture
def material_server(tmp_path):
    server = make_server(0, tmp_path / "runs")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    opener = build_opener(ProxyHandler({}))
    def request(path, body=None, token=True):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-SymmetryLab-Token"] = server.app.token
        req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with opener.open(req, timeout=8) as response:
            return response.read()
    yield request, server.app
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_new_routes_and_legacy_page(material_server):
    request, _ = material_server
    assert b"Original mathematics workbench" in request("/materials")
    assert b"/materials" in request("/")
    assert b"function renderCards" in request("/materials.js")
    assert len(json.loads(request("/api/materials/catalog"))["families"]) == 9
    result = json.loads(request("/api/materials/explore", {"material": "Example", "preset": "time_reversal"}))
    assert result["hall"]["status"] == "symmetry_forbidden"
    with pytest.raises(HTTPError) as error:
        request("/api/materials/explore", {"material": "Example"}, token=False)
    assert error.value.code == 403


def test_optional_api_connection_and_plan_keep_evidence_frozen(material_server, monkeypatch):
    request, app = material_server
    class Model:
        def __init__(self, config, timeout=30):
            assert config["auth_mode"] == "cc_switch" and config["model"] == "relay-model"
        def complete(self, messages, max_tokens):
            return {"content": "Unverified conditional proposal; no papers retrieved.", "model": "relay-model", "usage": {"total_tokens": 20}}
    monkeypatch.setattr("symmetrylab.web.server.OpenAICompatibleClient", Model)
    connection = {"base_url": "http://127.0.0.1:15721/v1", "model": "relay-model", "protocol": "responses", "auth_mode": "cc_switch", "api_key_env": "SYMMETRYLAB_API_KEY"}
    probe = json.loads(request("/api/connection/test", connection))
    assert probe["status"] == "connected"
    result = json.loads(request("/api/materials/plan", {"material": "Example", "preset": "time_reversal", "connection": connection}))
    assert result["model_plan"]["status"] == "unverified_model_proposal"
    assert result["mode"] == "model_assisted_framework"
    assert result["hall"]["status"] == "symmetry_forbidden" and result["hall"]["certificate_verified"]
    assert not app.probing


def test_invalid_material_returns_safe_error(material_server):
    request, _ = material_server
    with pytest.raises(HTTPError) as error:
        request("/api/materials/explore", {"material": ""})
    assert error.value.code == 400
