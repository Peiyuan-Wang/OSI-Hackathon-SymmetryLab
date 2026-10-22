"""Synthetic MCP fixtures, not captured or authenticated Bond responses."""
import io
import json
from urllib.error import HTTPError

import pytest

from symmetrylab.mcp.bond import BondError, BondMCP, ENDPOINT, http_post, tool_data
from symmetrylab.literature.bond import BondClient, identities, normalize
from symmetrylab.literature.encoders import LexiconEncoder
from symmetrylab.literature.service import Literature
from test_literature import FakeArxiv, row


class ProtocolFixture:
    def __init__(self):
        self.calls = []
        self.schema = {'properties': {'query': {'type': 'string'}, 'limit': {'type': 'integer', 'maximum': 10}},
                       'required': ['query']}
        self.papers = [{'id': '2510.04184v2', 'title': 'Spin space symmetry', 'abstract': 'Exact symmetry calculation.',
                        'categories': ['cond-mat.mtrl-sci'], 'authors': [{'name': 'A. Author'}]},
                       {'doi': '10.1000/example', 'title': 'Quantum physics example', 'categories': ['quant-ph']},
                       {'id': 'unclassified', 'title': 'Unclassified physics paper'}]

    def __call__(self, payload, headers):
        self.calls.append((payload, headers))
        method = payload['method']
        if method == 'initialize':
            result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'fixture'}}
        elif method == 'notifications/initialized':
            return None, {}
        elif method == 'tools/list':
            if 'cursor' not in payload['params']:
                result = {'tools': [{'name': 'list_sources', 'inputSchema': {}}], 'nextCursor': 'second'}
            else:
                result = {'tools': [{'name': 'semantic_search_papers', 'inputSchema': self.schema}]}
        else:
            name = payload['params']['name']
            result = {'structuredContent': {'sources': ['arxiv']}} if name == 'list_sources' else {
                'content': [{'type': 'text', 'text': json.dumps({'papers': self.papers})}]}
        return {'jsonrpc': '2.0', 'id': payload['id'], 'result': result}, {'mcp-session-id': 'fixture-session'}


def test_protocol_lifecycle_discovery_search_and_normalization():
    fixture = ProtocolFixture()
    client = BondClient('fixture-token', mcp=BondMCP('fixture-token', post=fixture))
    client.test()
    papers = client.search('spin space groups')
    assert [p['id'] for p in papers] == ['arXiv:2510.04184', 'doi:10.1000/example']
    assert papers[0]['authors'] == ['A. Author']
    assert papers[0]['retrieved_via'] == ['bond']
    assert fixture.calls[-1][0]['params']['arguments'] == {'query': 'spin space groups', 'limit': 10}
    assert len(client.search('spin space groups', physics_only=False)) == 3
    assert [p['method'] for p, _ in fixture.calls].count('initialize') == 1
    assert [p['method'] for p, _ in fixture.calls].count('tools/list') == 2
    assert 'id' not in fixture.calls[1][0]
    for _, headers in fixture.calls[1:]:
        assert headers['MCP-Protocol-Version'] == '2025-06-18'
        assert headers['Mcp-Session-Id'] == 'fixture-session'
        assert headers['Authorization'] == 'Bearer fixture-token'


def test_runtime_schema_required_fields_and_nullable_limit():
    fixture = ProtocolFixture()
    fixture.schema['required'].append('unknown_parameter')
    client = BondClient('fixture', mcp=BondMCP('fixture', post=fixture))
    with pytest.raises(BondError, match='unsupported search parameters'):
        client.search('spin')
    assert not any(p['method'] == 'tools/call' for p, _ in fixture.calls)
    fixture.schema['required'].remove('unknown_parameter')
    fixture.schema['properties']['limit'] = {'anyOf': [{'type': 'integer'}, {'type': 'null'}]}
    client.search('spin')
    assert fixture.calls[-1][0]['params']['arguments']['limit'] == 25


@pytest.mark.parametrize('message', [
    {'jsonrpc': '2.0', 'id': 999, 'result': {}},
    {'jsonrpc': '2.0', 'id': 1, 'error': {'message': 'SECRET'}},
    {'jsonrpc': '2.0', 'id': 1, 'result': {'protocolVersion': 'unknown'}},
])
def test_protocol_errors_do_not_leak_remote_text(message):
    with pytest.raises(BondError) as error:
        BondMCP('SECRET', post=lambda *args: (message, {})).connect()
    assert 'SECRET' not in str(error.value)


def test_tool_errors_and_unsupported_output_are_not_empty_success():
    fixture = ProtocolFixture()
    mcp = BondMCP('fixture', post=fixture)
    mcp.connect()
    mcp.post = lambda p, h: ({'jsonrpc': '2.0', 'id': p['id'], 'result': {
        'isError': True, 'content': [{'type': 'text', 'text': 'SECRET'}]}}, {})
    with pytest.raises(BondError) as error:
        mcp.call('list_sources', {})
    assert 'SECRET' not in str(error.value)
    with pytest.raises(BondError, match='unsupported data format'):
        tool_data({'content': [{'type': 'text', 'text': 'SECRET'}]})
    fixture = ProtocolFixture()
    fixture.papers = [{'unknown_title_field': 'Example'}]
    with pytest.raises(BondError, match='fields are not recognized'):
        BondClient('fixture', mcp=BondMCP('fixture', post=fixture)).search('spin')


class FakeResponse(io.BytesIO):
    status = 200
    def __init__(self, body, content_type):
        super().__init__(body)
        self.headers = {'Content-Type': content_type, 'Mcp-Session-Id': 'session'}


@pytest.mark.parametrize('sse', [False, True])
def test_http_json_and_sse_complete_without_waiting_for_stream_close(monkeypatch, sse):
    message = {'jsonrpc': '2.0', 'id': 3, 'result': {'tools': []}}
    body = json.dumps(message).encode()
    if sse:
        body = b': keepalive\r\n\r\ndata: ' + body + b'\r\n\r\nremaining stream'
    response = FakeResponse(body, 'text/event-stream' if sse else 'application/json')
    class Opener:
        def open(self, request, timeout):
            assert request.full_url == ENDPOINT and timeout == 20
            return response
    monkeypatch.setattr('symmetrylab.mcp.bond.build_opener', lambda *args: Opener())
    result, headers = http_post({'id': 3}, {})
    assert result == message and headers['mcp-session-id'] == 'session'


@pytest.mark.parametrize('status,expected', [(401, 'rejected'), (403, 'rejected'), (429, 'rate limit'), (302, '302')])
def test_http_failure_diagnostics_redact_body(monkeypatch, status, expected):
    class Opener:
        def open(self, *args, **kwargs):
            raise HTTPError(ENDPOINT, status, 'SECRET', {}, io.BytesIO(b'SECRET'))
    monkeypatch.setattr('symmetrylab.mcp.bond.build_opener', lambda *args: Opener())
    with pytest.raises(BondError, match=expected) as error:
        http_post({'id': 1}, {'Authorization': 'Bearer SECRET'})
    assert 'SECRET' not in str(error.value)


def test_normalize_urls_and_strong_identifiers():
    paper = normalize({'title': 'Spin symmetry example', 'url': 'javascript:alert(1)', 'doi': 'https://doi.org/10.1000/ABC'})
    assert paper['url'] == 'https://doi.org/10.1000/abc'
    assert identities(paper) == {'doi:10.1000/abc'}
    assert normalize({'name': 'Example', '@id': 'javascript:alert(1)'})['url'] == ''
    assert normalize({'title': 'Example', 'doi': '10.48550/arXiv.2510.04184v2'})['id'] == 'arXiv:2510.04184'


class FakeBond:
    def __init__(self, token):
        if not token:
            raise BondError('Enter a Bond bearer token in Paper survey first.')
    def search(self, *args):
        return [dict(row('arXiv:0001.00001'), retrieved_via=['bond']),
                normalize({'title': 'Journal quantum transport paper', 'doi': '10.1000/transport'})]
    def test(self):
        pass


def test_combined_deduplication_preserves_votes_and_tokens_never_persist(tmp_path, monkeypatch):
    monkeypatch.delenv('SYMMETRYLAB_BOND_TOKEN', raising=False)
    lit = Literature(tmp_path / 'lit', client=FakeArxiv(), encoder=LexiconEncoder(), bond_factory=FakeBond)
    lit.set_profile(['spin'], [])
    assert lit.state()['search_sources'] == ['arxiv']
    lit.search()
    lit.vote('arXiv:0001.00001', 'up')
    lit.configure_sources(['bond', 'arxiv'], 'SECRET')
    lit.test_bond()
    state = lit.search()
    assert state['candidate_count'] == 6 and state['last_search']['new'] == 1
    both = next(p for p in state['ranked'] if p['id'] == 'arXiv:0001.00001')
    assert both['retrieved_via'] == ['arxiv', 'bond'] and both['vote'] == 'up'
    assert 'SECRET' not in json.dumps(state)
    assert all('SECRET' not in p.read_text() for p in (tmp_path / 'lit').glob('*.json'))
    restarted = Literature(lit.root, encoder=LexiconEncoder())
    assert not restarted.state()['bond']['configured']
    assert restarted.state()['search_sources'] == ['arxiv', 'bond']
    lit.clear()
    assert not lit.state()['bond']['configured']


def test_missing_token_and_partial_failure_keep_arxiv_results(tmp_path, monkeypatch):
    monkeypatch.delenv('SYMMETRYLAB_BOND_TOKEN', raising=False)
    lit = Literature(tmp_path / 'lit', client=FakeArxiv(), encoder=LexiconEncoder(), bond_factory=FakeBond)
    lit.set_profile(['spin', 'magnetic symmetry'], [])
    lit.configure_sources(['arxiv', 'bond'])
    state = lit.search()
    assert state['candidate_count'] == 5 and state['last_search']['problems']
    class Broken(FakeBond):
        calls = 0
        def search(self, *args):
            self.calls += 1
            raise BondError('Bond rate limit reached. Try again later.')
    client = Broken('fixture')
    lit.bond_factory = lambda token: client
    state = lit.search()
    assert state['candidate_count'] == 5 and client.calls == 1
    assert state['last_search']['problems'] == ['Bond rate limit reached. Try again later.']


def test_bond_only_and_environment_token(tmp_path, monkeypatch):
    monkeypatch.setenv('SYMMETRYLAB_BOND_TOKEN', 'environment-fixture')
    lit = Literature(tmp_path / 'lit', client=FakeArxiv(), encoder=LexiconEncoder(), bond_factory=FakeBond)
    lit.set_profile(['spin'], [])
    lit.configure_sources(['bond'])
    state = lit.search()
    assert not lit.client.queries
    assert state['candidate_count'] == 2 and state['bond']['token_source'] == 'environment'
    lit.configure_sources(['bond'], 'session-fixture')
    lit.configure_sources(['bond'], forget_token=True)
    assert lit.bond_token() == 'environment-fixture'
    with pytest.raises(ValueError):
        lit.configure_sources([])
    with pytest.raises(ValueError):
        lit.configure_sources(['bond'], 'bad\ntoken')
