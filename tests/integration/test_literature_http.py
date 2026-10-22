import json
from threading import Thread
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
import pytest
from symmetrylab.web.server import make_server
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "unit"))
from test_literature import FakeArxiv


def test_paper_survey_page_api_and_style_gate(tmp_path):
    server = make_server(0, tmp_path / 'runs'); server.app.literature.client = FakeArxiv()
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    opener = build_opener(ProxyHandler({})); base = f'http://127.0.0.1:{server.server_port}'
    def request(path, data=None, headers=None):
        return opener.open(Request(base + path, data=None if data is None else json.dumps(data).encode(), headers=headers or {}), timeout=20)
    try:
        with request('/papers') as r: assert b'id="ranked"' in r.read()
        with request('/papers.js') as r: assert r.status == 200
        token = json.load(request('/api/bootstrap'))['token']
        h = {'Content-Type': 'application/json', 'X-SymmetryLab-Token': token}
        with pytest.raises(HTTPError): request('/api/literature/search', {}, dict(h, **{'X-SymmetryLab-Token': 'x'}))
        v = json.load(request('/api/literature/profile', {'keywords': ['altermagnetism'], 'papers': ['2510.04184']}, h))
        assert v['papers'][0]['id'] == 'arXiv:2510.04184' and v['encoder']['kind'] == 'lexicon'
        v = json.load(request('/api/literature/search', {}, h))
        assert v['candidate_count'] == 5 and v['ranked']
        v = json.load(request('/api/literature/vote', {'paper_id': v['ranked'][0]['id'], 'vote': 'up'}, h))
        assert v['votes']['up'] == 1
        chosen = v['ranked'][0]['id']
        v = json.load(request('/api/literature/style-vote', {'paper_id': chosen, 'selected': True}, h))
        assert next(p for p in v['ranked'] if p['id'] == chosen)['style_selected']
        v = json.load(request('/api/literature/writing', {'section':'derivation', 'audience':'student'}, h))
        assert v['writing']['section'] == 'derivation'
        # A live run that asks for the voice profile is refused until one is built and enabled.
        with pytest.raises(HTTPError) as e:
            request('/api/runs', {'goal': 'x', 'mode': 'demo', 'use_style': True, 'research_profile': {'track': 'theory'}}, h)
        assert 'voice profile' in json.loads(e.value.read())['error']
        v = json.load(request('/api/literature/style', {'enabled': True}, h))
        assert v['style_enabled'] and v['style']['hash']
        v = json.load(request('/api/literature/writing', {'section':'discussion'}, h))
        assert v['style_stale']
        with pytest.raises(HTTPError) as e:
            request('/api/runs', {'goal':'x','mode':'demo','use_style':True,'research_profile':{'track':'theory'}}, h)
        assert 'out of date' in json.loads(e.value.read())['error']
        assert (tmp_path / 'literature' / 'profile.json').exists() and not (tmp_path / 'runs' / 'profile.json').exists()
        v = json.load(request('/api/literature/clear', {}, h))
        assert v['candidate_count'] == 0 and not v['style']
    finally:
        server.shutdown(); server.server_close(); thread.join()
