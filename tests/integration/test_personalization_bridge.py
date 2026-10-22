from threading import Event
from symmetrylab.web import server
from symmetrylab.literature.service import Literature
from symmetrylab.literature.encoders import LexiconEncoder


def test_shared_profile_reaches_run_independently_of_style(tmp_path, monkeypatch):
    app = server.Workbench(tmp_path/'runs')
    app.literature = Literature(tmp_path/'lit', encoder=LexiconEncoder())
    app.literature.set_profile(['spin groups'], [], research_preferences={
        'methods':'Exact classification', 'share_with_agent':True})
    received, finished = {}, Event()
    def capture(goal, output, mode, config, *args):
        received.update(config); finished.set()
    monkeypatch.setattr(server, 'run_agent', capture)
    app.start({'goal':'Find a mechanism', 'mode':'demo', 'research_profile':{'track':'theory'}})
    assert finished.wait(3)
    assert received['interest_context']['explicit_preferences']['methods'] == 'Exact classification'
    assert 'style_prompt' not in received


def test_shared_profile_can_support_traceable_taste(tmp_path):
    from symmetrylab.tools.discovery import DiscoveryTools
    state = {'research_profile': {'papers':'', 'keywords':'', 'taste_notes':''},
             'interest_context':{'explicit_preferences': {'methods':'Exact classification'}}, 'sources':[]}
    tool = DiscoveryTools(state, lambda:10)
    result = tool.learn_taste([{'preference':'Prefer exact classification', 'origin':'interest_profile', 'excerpt':'Exact classification'}])
    assert result['preferences'][0]['origin'] == 'interest_profile'


def test_preference_memory_does_not_cross_interest_versions(tmp_path):
    import json
    from symmetrylab.memory.discovery import recall_preferences
    folder = tmp_path/'run'; folder.mkdir()
    profile = {'track':'theory', 'papers':'', 'keywords':''}
    (folder/'result.json').write_text(json.dumps({'research_profile':profile, 'interest_context':{'hash':'v1'}}))
    (folder/'preference_feedback.jsonl').write_text(json.dumps({'origin':'researcher_feedback', 'reason':'Prefer exactness'})+'\n')
    assert recall_preferences(tmp_path, profile, interest_hash='v1')
    assert not recall_preferences(tmp_path, profile, interest_hash='v2')
    assert not recall_preferences(tmp_path, profile)
