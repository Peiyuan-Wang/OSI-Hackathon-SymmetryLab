import json
import time
from threading import Thread, Event
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
import pytest
from symmetrylab.web.server import make_server


def test_two_workspaces_navigation_security_and_human_preference(tmp_path):
    server=make_server(0,tmp_path/'runs'); thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    opener=build_opener(ProxyHandler({}));base=f'http://127.0.0.1:{server.server_port}'
    def request(path,data=None,headers=None):
        return opener.open(Request(base+path,data=None if data is None else json.dumps(data).encode(),headers=headers or {}),timeout=10)
    try:
        nav={'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'navigate','Sec-Fetch-Dest':'document'}
        for path in ('/','/experiment'):
            with request(path,headers=nav) as r: assert r.status==200 and b'id="papers"' in r.read()
        for path in ('/api/bootstrap','/api/runs'):
            with pytest.raises(HTTPError) as e:request(path,headers=nav)
            assert e.value.code==403
        with pytest.raises(HTTPError):request('/',headers=dict(nav,Origin='https://external.test'))
        with pytest.raises(HTTPError):request('/',headers=dict(nav,Host='invalid.test'))
        with pytest.raises(HTTPError):request('/experiment',headers=dict(nav,**{'Sec-Fetch-Dest':'iframe'}))
        with request('/api/bootstrap') as r:boot=json.load(r)
        headers={'Content-Type':'application/json','X-SymmetryLab-Token':boot['token']}
        def run(track):
            with request('/api/runs',{'goal':'Study symmetry','mode':'demo','research_profile':{'track':track,'material':'L10 MnPt','keywords':'mechanisms'}},headers) as r:identifier=json.load(r)['run_id']
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                with request('/api/runs/'+identifier) as r:state=json.load(r)
                if state['status']!='running':return identifier,state
                Event().wait(.02)
            pytest.fail('research timeout')
        identifier,state=run('theory')
        assert state['status']=='completed'
        feedback={'left':'D001','right':'D002','choice':'D001','reason':'I prefer a minimal obstruction mechanism.'}
        with pytest.raises(HTTPError):request('/api/runs/'+identifier+'/preference',feedback,dict(headers,**nav))
        with request('/api/runs/'+identifier+'/preference',feedback,headers) as r:assert json.load(r)['status']=='recorded'
        with pytest.raises(HTTPError):request('/api/runs/'+identifier+'/preference',dict(feedback,right='D999'),headers)
        server.app.snapshots[identifier]['status']='interrupted'
        with pytest.raises(HTTPError):request('/api/runs/'+identifier+'/preference',feedback,headers)
        experiment,state=run('experiment')
        assert state['status']=='completed' and len(state['calculations']) in (3,4)
        with request('/api/runs/'+experiment+'/report') as r:
            assert 'Conditional exact' in r.read().decode()
        with request('/api/runs') as r:
            assert {x['track'] for x in json.load(r)}=={'theory','experiment'}
    finally:
        server.shutdown();server.server_close();thread.join()
