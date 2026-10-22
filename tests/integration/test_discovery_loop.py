import json
from pathlib import Path
from symmetrylab.agent_core.workbench import run_agent
from symmetrylab.communication.workbench import render_agent_report
from symmetrylab.memory.discovery import recall_lessons, recall_preferences
from symmetrylab.model.discovery_demo import DiscoveryDemo


def test_mnpt_dossier_refines_a_degenerate_measurement(tmp_path):
    result=run_agent('Determine the MnPt Neel axis',tmp_path/'first',config={'research_profile':{'track':'experiment','material':'L10 MnPt'}})
    assert result['status']=='completed'
    assert result['metrics']['model_calls']==0
    assert len(result['calculations'])==3
    assert all(c['certificate_verified'] for c in result['calculations'])
    assert result['calculations'][1]['result']['identical_pairs']
    assert len(result['calculations'][2]['result']['identical_pairs'])<len(result['calculations'][1]['result']['identical_pairs'])
    assert not result['structure_assessments'][0]['sample_verified']
    assert result['experiment_designs'][0]['physical_feasibility']=='requires_sample_and_instrument_validation'
    for audience in ('researcher','student','general'):
        report=render_agent_report(result,audience)
        assert 'Scripted offline' in report and 'V003' in report
        assert 'No calibrated intensity' in report
    lessons=recall_lessons(tmp_path,'experiment','demo')
    assert lessons and all(x['status']=='rechecked_conditional_counterexample' for x in lessons)
    assert recall_lessons(tmp_path,'experiment','live')==[]
    data=json.loads((tmp_path/'first'/'result.json').read_text())
    for c in data['calculations']:
        if 'factors' in c['result']:c['result']['factors'][0][0]='999'
    (tmp_path/'first'/'result.json').write_text(json.dumps(data))
    assert recall_lessons(tmp_path,'experiment','demo')==[]


def test_theory_taste_and_gauge_memory(tmp_path):
    profile={'track':'theory','papers':'We study minimal symmetry mechanisms.','keywords':'gauge equivalence'}
    r=run_agent('Explore mechanisms',tmp_path/'a',config={'research_profile':profile})
    assert r['status']=='completed' and len(r['directions'])==2
    assert r['taste_profile'] and r['directions'][0]['novelty']=='not_established'
    r2=run_agent('Refine mechanisms',tmp_path/'b',config={'research_profile':profile})
    assert r2['recalled_lessons'][0]['scope']=='public_torus_affine_v1'
    feedback={'origin':'researcher_feedback','left':'A','right':'B','choice':'A','reason':'Prefer minimal models.'}
    (tmp_path/'a'/'preference_feedback.jsonl').write_text(json.dumps(feedback)+'\n')
    assert recall_preferences(tmp_path,r['research_profile'])[0]['reason']=='Prefer minimal models.'
    assert not recall_preferences(tmp_path,dict(r['research_profile'],papers='Different researcher context'))


def test_unknown_material_remains_incomplete(tmp_path):
    r=run_agent('Find an axis',tmp_path/'unknown',config={'research_profile':{'track':'experiment','material':'Unknown'}})
    assert r['status']=='incomplete' and not r['calculations'] and not r['sources']


def test_live_policy_double_uses_tools_without_claiming_live_provider(tmp_path):
    # Exercise the live controller, not a real provider. Demo policy never requests a network search.
    r=run_agent('Explore symmetry',tmp_path/'double',mode='live',client=DiscoveryDemo(),config={'research_profile':{'track':'theory','keywords':'Symmetry'}})
    assert r['status']=='completed' and r['metrics']['model_calls']>0
    assert r['directions'] and r['evidence'][0]['certificate_verified']


def test_speculative_second_action_never_executes(tmp_path):
    class Batch:
        def complete(self,messages,max_tokens):
            state=json.loads(messages[-1]['content'])
            if not state['plan']:
                return {'content':'{"action":"plan","steps":["Wait for actual feedback"]}{"action":"tool","name":"register_candidate","arguments":{}}'}
            assert state['last_observation']['status']=='plan_updated'
            assert not state['candidates']
            return {'content':'{"action":"finish","summary":"No calculation yet.","limitations":["Needs evidence"]}'}
    r=run_agent('Batch response',tmp_path/'batch',mode='live',client=Batch())
    assert r['status']=='incomplete' and r['metrics']['tool_calls']==0
    assert r['metrics']['discarded_speculative_actions']==1


def test_replanning_without_tool_progress_is_bounded(tmp_path):
    class Repeat:
        def complete(self,*args):return {'content':'{"action":"plan","steps":["Repeat forever"]}'}
    r=run_agent('No progress',tmp_path/'repeat',mode='live',client=Repeat())
    assert r['status']=='failed' and r['metrics']['model_calls']==4
    assert r['metrics']['tool_calls']==0
    assert any('Execute a registered tool' in e['data'].get('message','') for e in r['events'])


def test_keyword_only_preferences_are_scoped_to_the_supplied_interests(tmp_path):
    profile={'track':'theory','keywords':'gauge equivalence'}
    r=run_agent('Explore mechanisms',tmp_path/'a',config={'research_profile':profile})
    item={'origin':'researcher_feedback','left':'A','right':'B','choice':'A','reason':'Minimal models'}
    (tmp_path/'a'/'preference_feedback.jsonl').write_text(json.dumps(item)+'\n')
    assert recall_preferences(tmp_path,r['research_profile'])
    assert not recall_preferences(tmp_path,dict(r['research_profile'],keywords='unrelated transport theory'))
