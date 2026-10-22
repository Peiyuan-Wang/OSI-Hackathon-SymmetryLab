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
    assert len(result['calculations'])==4
    assert all(c['certificate_verified'] for c in result['calculations'])
    c4,c2=(sum(x['compatible'] for x in c['result']['outcomes']) for c in result['calculations'][:2])
    assert (c4,c2)==(2,6)  # the assumed domain symmetry, not the calculation, decides the axis
    assert result['calculations'][2]['result']['identical_pairs']
    assert len(result['calculations'][3]['result']['identical_pairs'])<len(result['calculations'][2]['result']['identical_pairs'])
    assert not result['structure_assessments'][0]['sample_verified']
    assert result['experiment_designs'][0]['physical_feasibility']=='requires_sample_and_instrument_validation'
    for audience in ('researcher','student','general'):
        report=render_agent_report(result,audience)
        assert 'Scripted offline' in report and 'V003' in report
        assert 'No calibrated intensity' in report and '## Key findings' in report
        assert 'symmetry alone does not decide the axis' in report
        assert '"rotations": [' not in report  # no exploded JSON inputs
    reports={a:render_agent_report(result,a) for a in ('researcher','student','general')}
    assert len(reports['general'])<len(reports['student'])<len(reports['researcher'])
    assert 'Concepts used' in reports['student'] and 'What this means' in reports['general']
    assert 'Controls' in reports['researcher'] and 'Controls' not in reports['general']
    second=run_agent('Determine the MnPt Neel axis',tmp_path/'second',config={'research_profile':{'track':'experiment','material':'L10 MnPt'}})
    assert second['status']=='completed' and second['recalled_lessons']
    assert len(second['calculations'])==3 and second['metrics']['tool_calls']<result['metrics']['tool_calls']
    assert all(len(c['result']['inputs'].get('probes',[1,2]))>1 for c in second['calculations'])
    lessons=recall_lessons(tmp_path,'experiment','demo')
    assert lessons and all(x['status']=='rechecked_conditional_counterexample' for x in lessons)
    assert recall_lessons(tmp_path,'experiment','live')==[]
    for run in ('first','second'):
        data=json.loads((tmp_path/run/'result.json').read_text())
        for c in data['calculations']:
            if 'factors' in c['result']:c['result']['factors'][0][0]='999'
        (tmp_path/run/'result.json').write_text(json.dumps(data))
    assert recall_lessons(tmp_path,'experiment','demo')==[]


def test_theory_taste_and_gauge_memory(tmp_path):
    profile={'track':'theory','papers':'We study minimal symmetry mechanisms.','keywords':'gauge equivalence'}
    r=run_agent('Explore mechanisms',tmp_path/'a',config={'research_profile':profile})
    assert r['status']=='completed' and len(r['directions'])==2
    assert r['taste_profile'] and r['directions'][0]['novelty']=='not_established'
    r2=run_agent('Refine mechanisms',tmp_path/'b',config={'research_profile':profile})
    assert r2['recalled_lessons'][0]['scope']=='public_torus_affine_v1'
    assert [e['result']['status'] for e in r['evidence']]==['gauge_trivial','gauge_nontrivial']
    assert 'Every nonzero momentum shift' in r['hypotheses'][0]['statement']
    assert r2['hypotheses'][0]['statement'].startswith('Recalled lesson')  # refuted claim not re-proposed
    assert len(r2['hypotheses'])<len(r['hypotheses'])
    report=render_agent_report(r,'researcher')
    assert 'Exact toy-model evidence' not in report and report.count('# SymmetryLab')==1
    assert 'Refuted claim' in report and 'genuine obstruction' in report
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


def test_lessons_do_not_cross_into_unrelated_questions(tmp_path):
    run_agent('Determine the Neel-axis orientation of L10 MnPt',tmp_path/'axis',config={'research_profile':{'track':'experiment','material':'L10 MnPt'}})
    assert recall_lessons(tmp_path,'experiment','demo',goal='Determine the Neel-axis orientation of L10 MnPt',material='L10 MnPt')
    assert recall_lessons(tmp_path,'experiment','demo',goal='对于L10 MnPt的磁隧道结有TMR效应吗',material='L10 MnPt')==[]
    assert recall_lessons(tmp_path,'experiment','demo',goal='Does an L10 MnPt tunnel junction show TMR?',material='L10 MnPt')==[]
    assert recall_lessons(tmp_path,'experiment','demo',goal='Determine the Neel-axis orientation of L10 MnPt',material='Mn2Au')==[]


def test_design_without_applicable_kernel_completes_honestly(tmp_path):
    class Transport:
        def complete(self,messages,max_tokens):
            s=json.loads(messages[-1]['content'])
            if not s['plan']: a={'action':'plan','steps':['load','assess','design']}
            elif not s['sources']: a={'action':'tool','name':'load_material_context','arguments':{}}
            elif not s['structure_assessments']: a={'action':'tool','name':'record_structure_assessment','arguments':{'source_ids':['S001'],'phase':'L10','chemical_group':'P4/mmm','magnetic_order':'AFM','conditions':['unspecified'],'unresolved':['junction']}}
            elif not s['experiment_designs']: a={'action':'tool','name':'design_experiment','arguments':{'hypothesis':'h','method':'transport','source_ids':['S001'],'calculation_ids':[],'steps':['s'],'controls':['c'],'predictions':['p'],'falsifier':'f','requirements':['r']}}
            else: a={'action':'finish','summary':'Answer: possible but unproven.','limitations':['source-based only']}
            return {'content':json.dumps(a),'usage':{}}
    r=run_agent('Does an L10 MnPt tunnel junction show TMR?',tmp_path/'tmr',mode='live',client=Transport(),config={'research_profile':{'track':'experiment','material':'L10 MnPt'}})
    assert r['status']=='completed' and not r['calculations'] and r['exact_kernel_applicable'] is False
    report=render_agent_report(r,'researcher')
    assert 'No implemented exact kernel addresses this question' in report
    assert 'neutron' not in report.split('## Research brief')[0].lower()
    assert report.index('Answer: possible') < report.index('## Key findings')


def test_voice_profile_only_applies_after_research_and_preserves_evidence(tmp_path):
    seen = []
    class Capture(DiscoveryDemo):
        def complete(self, messages, max_tokens):
            seen.append(messages)
            packet = json.loads(messages[-1]['content'])
            if 'claim_ledger' in packet:
                return {'content': json.dumps({'summary': packet['original_summary'],
                                               'claim_ids': [c['id'] for c in packet['claim_ledger']]}), 'usage': {'total_tokens': 15}}
            return super().complete(messages, max_tokens)
    style = 'RESEARCHER VOICE PROFILE — governs wording and emphasis only.\nPreferred terminology: spin space group.'
    r = run_agent('Explore gauge mechanisms', tmp_path / 'voice', mode='live', client=Capture(),
                  config={'style_prompt': style, 'style_hash': 'abc123', 'research_profile': {'track': 'theory', 'keywords': 'spin groups'}})
    assert all(len([m for m in messages if m['role'] == 'system']) == 1 for messages in seen)
    assert all(style not in str(messages) for messages in seen[:-1])
    assert json.loads(seen[-1][-1]['content'])['wording_profile'] == style
    assert r['writing_audit']['status'] == 'applied'
    assert r['original_model_summary'] == r['summary']
    assert r['style_profile'] == {'hash': 'abc123', 'applied': True}
    assert 'Researcher voice profile `abc123` applied' in render_agent_report(r, 'researcher')
    plain = run_agent('Explore gauge mechanisms', tmp_path / 'plain', mode='live', client=DiscoveryDemo(), config={'research_profile': {'track': 'theory'}})
    assert plain['style_profile'] is None
    ledger = json.loads(seen[-1][-1]['content'])['claim_ledger']
    assert [c['result'] for c in ledger] == [e['result'] for e in r['evidence'] if e['certificate_verified']]
    assert [e['result']['certificate'] for e in r['evidence']] == [e['result']['certificate'] for e in plain['evidence']]
