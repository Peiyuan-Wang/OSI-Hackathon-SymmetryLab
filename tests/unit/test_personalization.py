import json
from copy import deepcopy
from time import monotonic
import pytest
from symmetrylab.literature.personalization import preferences, writing_preferences, paper_facets, task_examples
from symmetrylab.agent_core.writing import rewrite
from test_literature import survey


def test_query_sources_and_rotation(tmp_path):
    lit, _ = survey(tmp_path)
    data = lit.load(); data['keywords'] = [f'keyword{i}' for i in range(12)]; data['search_round'] = 0
    queries = lit.queries(data)
    assert len(queries) == 6 and any(q not in data['keywords'] for q in queries)
    assert queries[:2] == data['keywords'][:2]
    data['search_round'] = 1
    assert lit.queries(data)[:2] == data['keywords'][2:4]
    data['keywords'] = []; data['papers'] = []
    data['feedback'] = {'arXiv:0001.00003': {'vote': 'up'}}
    assert lit.queries(data), 'Positive feedback must support new retrieval'


def test_content_and_style_feedback_are_independent(tmp_path):
    lit, _ = survey(tmp_path)
    lit.rebuild_style(); original = lit.active_style()['hash']
    liked = lit.vote('arXiv:0001.00003', 'up')
    assert not liked['style_stale']
    assert lit.active_style()['hash'] == original
    scores = [(r['id'], r['score']) for r in liked['ranked']]
    selected = lit.style_vote('arXiv:0001.00004', True)
    assert [(r['id'], r['score']) for r in selected['ranked']] == scores
    assert selected['style_stale']
    with pytest.raises(ValueError, match='out of date'):
        lit.active_style()
    updated = lit.rebuild_style()
    assert updated['style']['sources']['liked'] == ['arXiv:0001.00004']
    assert not updated['style_stale']
    lit.style_vote('arXiv:0001.00004', False)
    assert lit.state()['style_stale']


def test_explicit_intent_and_provenance_gate(tmp_path):
    lit, _ = survey(tmp_path)
    assert lit.planning_context() is None
    v = lit.set_profile(['spin space groups'], ['2510.04184'], research_preferences={
        'problem': 'Classify symmetry constraints', 'methods': 'Representation theory',
        'current_goal': 'Minimal counterexamples', 'share_with_agent': True})
    assert any('current intent' in s['kinds'] for s in v['interests'])
    packet = lit.planning_context('spin current')
    assert packet['explicit_preferences']['methods'] == 'Representation theory'
    assert packet['historical_facets'] and packet['hash']
    paper = lit.load()['papers'][0]
    for f in packet['historical_facets']:
        assert f['excerpt'] in paper['title'] + '. ' + paper['abstract']
        assert 'unconfirmed' in f['status']
    assert paper_facets([{'id':'x', 'title':'Spin space groups', 'abstract':''}])[0]['kind'] == 'symmetry'


def test_writing_samples_require_evidence_and_match_section(tmp_path):
    lit, _ = survey(tmp_path)
    lit.set_profile(['spin groups'], [])
    with pytest.raises(ValueError, match='keywords alone'):
        lit.rebuild_style()
    a = {'section': 'discussion', 'text': 'We discuss spin groups and their consequences for magnetic order.'}
    b = {'section': 'derivation', 'text': 'Assume an orthogonal action. Substitution then fixes the allowed tensor components.'}
    lit.set_writing({'section': 'derivation', 'audience': 'student', 'samples': [a, b]})
    lit.rebuild_style()
    active = lit.active_style('spin groups')
    assert active['task_examples'][0]['section'] == 'derivation'
    assert active['writing']['audience'] == 'student' and 'samples' not in active['writing']
    assert len(active['prompt']) <= 3500
    lit.set_writing({'section':'discussion', 'samples':[a,b]})
    assert lit.state()['style_stale']


@pytest.mark.parametrize('value', [{'share_with_agent':'yes'}, {'methods': 'x'*801}, {'unknown':True}])
def test_invalid_preferences(value):
    with pytest.raises(ValueError): preferences(value)


def test_invalid_writing_sample():
    with pytest.raises(ValueError): writing_preferences({'samples':[{'section':'derivation', 'text':'short'}]})


def writing_state():
    return {'summary':'The result is conditional.', 'goal':'Explain the calculation.', 'limitations':['Unknown domain populations'],
            'evidence':[], 'calculations':[], 'sources':[],
            'limits':{'max_model_calls':3, 'max_total_tokens':100000, 'max_output_tokens':1000},
            'metrics':{'model_calls':1,'estimated_tokens_reserved':0,'reported_tokens':0,'usage_missing_calls':0}}


@pytest.mark.parametrize('response', [
    {'summary':'We predict a signal of 900 tesla.', 'claim_ids':[]},
    {'summary':'A conditional result.', 'claim_ids':['invented']},
    {'action':'tool','name':'execute'},
])
def test_writer_rejects_invalid_rewrites_without_losing_research(response):
    class Client:
        def complete(self, *args): return {'content':json.dumps(response), 'usage':{'total_tokens':10}}
    state = writing_state(); before = deepcopy(state)
    result = rewrite(state, Client(), 'Keep conditions.', {}, monotonic()+10, lambda:False)
    assert result['status'] == 'rejected_or_unavailable'
    assert state['summary'] == before['summary'] and state['evidence'] == before['evidence']
    assert state['metrics']['reported_tokens'] == 10


def test_writer_budget_and_connection_fallback():
    class Client:
        def complete(self, *args): raise RuntimeError('Do not expose provider response')
    state = writing_state()
    assert rewrite(state, Client(), '', {}, monotonic()+10, lambda:False)['status'] == 'rejected_or_unavailable'
    state['metrics']['model_calls'] = 3
    assert rewrite(state, Client(), '', {}, monotonic()+10, lambda:False)['status'] == 'skipped_budget'
    assert state['summary'] == 'The result is conditional.'
