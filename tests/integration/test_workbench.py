import json
from threading import Event, Thread
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
import pytest
from symmetrylab.agent_core.workbench import run_agent
from symmetrylab.communication.workbench import render_agent_report
from symmetrylab.web.server import make_server


def test_simulated_full_loop_and_report(tmp_path):
    result = run_agent('Investigate shifts', tmp_path / 'run')
    assert result['status'] == 'completed'
    assert result['metrics']['model_calls'] == 0
    assert result['metrics']['tool_calls'] == 4
    assert len(result['lessons']) == 1
    assert len(result['hypotheses']) == 2
    assert [e['result']['status'] for e in result['evidence']] == ['gauge_trivial', 'gauge_nontrivial']
    assert all(e['certificate_verified'] for e in result['evidence'])
    assert (tmp_path / 'run' / 'report_researcher_en.md').exists()
    for audience in ['researcher','student','general']:
        report = render_agent_report(result, audience)
        assert result['evidence_hash'] in report
        assert 'unverified model text' in report
        assert 'simulated offline policy' in report


class AdaptiveModel:
    def __init__(self): self.observations = []
    def complete(self, messages, max_tokens):
        state = json.loads(messages[-1]['content'])
        self.observations.append(state['last_observation'])
        if state['metrics']['policy_turns'] == 0:
            action = {'action':'tool','name':'register_candidate','arguments':{'label':'Invalid sign','dimension':1,'group':'C2','operations':[{'R':[[-1]],'s':0,'q':['1/2']}]}}
        elif not state['candidates']:
            assert state['last_observation']['status'] == 'invalid_input'
            action = {'action':'tool','name':'register_candidate','arguments':{'label':'Repaired sign','dimension':1,'group':'C2','operations':[{'R':[[-1]],'s':1,'q':['1/2']}]}}
        elif not state['evidence']:
            action = {'action':'tool','name':'solve_gauge','arguments':{'candidate_id':state['candidates'][0]['case_id']}}
        else:
            assert state['last_observation']['certificate_verified']
            action = {'action':'finish','summary':'One instance was checked.','limitations':['No universal theorem.']}
        return {'content':json.dumps(action),'usage':{'total_tokens':100}}


def test_live_controller_repairs_from_actual_feedback(tmp_path):
    model = AdaptiveModel()
    result = run_agent('Repair invalid input',tmp_path/'adaptive',mode='live',client=model)
    assert result['status'] == 'completed'
    assert result['metrics']['model_calls'] == 4
    assert result['metrics']['reported_tokens'] == 400
    assert len(model.observations) == 4
    assert result['candidates'][0]['operations'][0]['s'] == 1


def test_budget_cancellation_and_unverified_finish(tmp_path):
    small = run_agent('test',tmp_path/'small',config={'limits':{'max_model_calls':1}})
    assert small['status'] == 'budget_exceeded'
    token = run_agent('test',tmp_path/'token',config={'limits':{'max_total_tokens':1}})
    assert token['metrics']['policy_turns'] == 0
    cancelled = run_agent('test',tmp_path/'cancel',cancelled=lambda:True)
    assert cancelled['status'] == 'cancelled'
    class Finish:
        def complete(self,*args): return {'content':json.dumps({'action':'finish','summary':'A theorem is proved','limitations':[]})}
    empty = run_agent('test',tmp_path/'empty',mode='live',client=Finish())
    assert empty['status'] == 'incomplete'
    assert 'unverified model text' in render_agent_report(empty)


def test_unknown_tool_and_bad_json_never_execute(tmp_path):
    class Bad:
        def complete(self,*args): return {'content':'{"action":"tool","name":"exec","arguments":{"cmd":"touch forbidden"}}'}
    result = run_agent('test',tmp_path/'bad',mode='live',client=Bad())
    assert result['status'] == 'failed'
    assert result['metrics']['model_calls'] == 3
    assert len([e for e in result['events'] if e['kind']=='action_error']) == 3


def test_http_security_and_demo(tmp_path):
    server = make_server(0,tmp_path/'runs')
    thread = Thread(target=server.serve_forever,daemon=True); thread.start()
    opener = build_opener(ProxyHandler({}))
    base = f'http://127.0.0.1:{server.server_port}'
    def request(path,data=None,headers=None):
        req = Request(base+path,data=None if data is None else json.dumps(data).encode(),headers=headers or {})
        return opener.open(req,timeout=10)
    try:
        with request('/') as response:
            html = response.read().decode()
            assert 'CC Switch local routing' in html and 'lang="en"' in html
            assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
        with request('/api/bootstrap') as response:
            boot = json.load(response)
        with pytest.raises(HTTPError) as error:
            request('/api/runs',{})
        assert error.value.code == 403
        headers = {'Content-Type':'application/json','X-SymmetryLab-Token':boot['token']}
        with pytest.raises(HTTPError) as error:
            request('/api/runs',{},dict(headers,Origin='https://attacker.example'))
        assert error.value.code == 403
        with pytest.raises(HTTPError) as error:
            request('/api/bootstrap',headers={'Host':'attacker.example'})
        assert error.value.code == 403
        with request('/api/runs',{'mode':'demo','goal':'Investigate toy actions'},headers) as response:
            run_id = json.load(response)['run_id']
        # Wait on the worker's terminal state without arbitrary long sleeps.
        import time
        deadline = time.monotonic()+10
        while time.monotonic()<deadline:
            with request('/api/runs/'+run_id) as response: state = json.load(response)
            if state['status'] != 'running': break
            Event().wait(.05)
        assert state['status']=='completed'
        with request('/api/runs/'+run_id+'/report?audience=student&download=1') as response:
            assert '.md' in response.headers['Content-Disposition']
            assert 'simulated offline policy' in response.read().decode()
        with pytest.raises(HTTPError): request('/api/runs/../../secret')
        # Restart recovery must identify unfinished persisted runs.
        state['status']='running'
        (tmp_path/'runs'/run_id/'state.json').write_text(json.dumps(state))
        server.app.snapshots.clear()
        assert server.app.snapshot(run_id)['status']=='interrupted'
    finally:
        server.shutdown(); server.server_close(); thread.join()
