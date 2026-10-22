import json
import sqlite3
import zlib
from copy import deepcopy
import pytest
from symmetrylab.database.ssg import SSGCatalog
from symmetrylab.skills.registry import SkillRegistry
from symmetrylab.verifier.ssg import calculate


def fixture_record():
    identity = [[1,0,0],[0,1,0],[0,0,1]]
    def row(a,b,g):
        return {'MomentumAffineAction':[a,b], 'Grading':g, 'Antiunitary':bool(g)}
    e=row(identity,[0,0,0],0)
    anti=row([[-1,0,0],[0,-1,0],[0,0,-1]],[0,0,0],1)
    return {'GradedReciprocalGroupElements':[e,anti], 'ReciprocalGenerators':[anti], 'GradedReciprocalGroupOrder':2}


@pytest.fixture
def catalog(tmp_path,monkeypatch):
    path=tmp_path/'fixture.sqlite'
    with sqlite3.connect(path) as c:
        c.execute('create table metadata(key text,value text)')
        c.executemany('insert into metadata values (?,?)',[('schema_version','3'),('database_version','test'),('record_count','1')])
        c.execute('create table ssg_records(label text,parent_space_group int,magnetic_order text,bns_number text,nonsymmorphic int,status text,reciprocal_record_zlib blob,o3_record_zlib blob)')
        blob=zlib.compress(json.dumps(fixture_record()).encode())
        c.execute('insert into ssg_records values (?,?,?,?,?,?,?,?)',('fixture',1,'collinear','1.1',0,'COMPLETE',blob,zlib.compress(b'{}')))
    monkeypatch.setenv('SYMMETRYLAB_SSG_CATALOG',str(path))
    return SSGCatalog(path)


def test_search_parameterization_and_read_only(catalog):
    assert catalog.call('metadata',{})['actual_record_count']==1
    assert catalog.call('search',{'parent_space_group':1})['total']==1
    assert catalog.call('search',{'query':"' OR 1=1 --"})['total']==0
    assert catalog.call('get',{'record_id':'missing'})['status']=='not_found'
    c=catalog.connect()
    try:
        with pytest.raises(sqlite3.OperationalError): c.execute('delete from ssg_records')
    finally: c.close()
    with pytest.raises(ValueError): catalog.call('search',{'bns_number':1.1})
    with pytest.raises(ValueError): catalog.call('search',{'limit':True})
    with pytest.raises(ValueError): catalog.call('get',{'record_id':'fixture','path':'/tmp/other'})


def test_orbit_has_no_double_antiunitary_sign():
    result=calculate(fixture_record(),'momentum_orbit',{'record_id':'fixture','k':['1/3',0,0]},lambda:None)
    assert result['orbit']==[['1/3','0','0'],['2/3','0','0']]
    assert result['stabilizers']==[{'element_index':0,'grading':0}]
    with pytest.raises(ValueError): calculate(fixture_record(),'momentum_orbit',{'record_id':'fixture','k':[0.3,0,0]},lambda:None)


def test_closure_detects_tampering_and_cancellation():
    r=fixture_record()
    assert calculate(r,'verify_group',{'record_id':'fixture'},lambda:None)['status']=='verified'
    broken=deepcopy(r); broken['GradedReciprocalGroupOrder']=3
    assert calculate(broken,'verify_group',{'record_id':'fixture'},lambda:None)['status']=='failed'
    broken=deepcopy(r); broken['ReciprocalGenerators']=[r['GradedReciprocalGroupElements'][0]]
    assert calculate(broken,'verify_group',{'record_id':'fixture'},lambda:None)['status']=='failed'
    def stop(): raise InterruptedError('cancelled')
    with pytest.raises(InterruptedError): calculate(r,'verify_group',{'record_id':'fixture'},stop)


def test_skill_provenance_and_budgeted_dispatch(catalog):
    from symmetrylab.tools.research import ResearchTools
    from time import monotonic
    state={'sources':[]}
    tools=ResearchTools(state,monotonic()+10,lambda:False)
    assert tools.call('list_skills',{})['skills'][0]['configured']
    assert 'Rtilde' in tools.call('read_skill',{'skill':'ssg-database'})['instructions']
    result=tools.call('call_skill',{'skill':'ssg-database','operation':'verify_group','arguments':{'record_id':'fixture'}})
    assert result['status']=='verified' and result['source_ids']==['S001']
    assert state['sources'][0]['record_id']=='fixture'
    assert result['record_hash'] and state['skill_calculations'][0]==result
    with pytest.raises(ValueError): tools.call('call_skill',{'skill':'../../other','operation':'get','arguments':{}})
    with pytest.raises(ValueError): tools.call('call_skill',{'skill':'ssg-database','operation':'sql','arguments':{}})


def test_skill_model_loop_and_report(catalog,tmp_path):
    from symmetrylab.agent_core.workbench import run_agent
    from symmetrylab.communication.workbench import render_agent_report
    actions=iter([
        {'action':'plan','steps':['Inspect and compute stored symmetry'],'reason':'Test'},
        {'action':'tool','name':'list_skills','arguments':{}},
        {'action':'tool','name':'read_skill','arguments':{'skill':'ssg-database'}},
        {'action':'tool','name':'call_skill','arguments':{'skill':'ssg-database','operation':'verify_group','arguments':{'record_id':'fixture'}}},
        {'action':'tool','name':'propose_direction','arguments':{'title':'Compare orbits','mechanism':'Affine symmetry','minimal_model':'Stored quotient','falsifier':'Missing closure','next_test':'Compute a generic orbit','source_ids':['S001'],'calculation_ids':['SSG001'],'taste_alignment':'Exact algebra'}},
        {'action':'finish','summary':'The stored quotient closes. Physical interpretation remains conditional.','limitations':['Synthetic fixture only.']}
    ])
    class Client:
        def complete(self,messages,max_tokens):
            return {'content':json.dumps(next(actions)), 'usage':{'total_tokens':10}}
    result=run_agent('Inspect SSG',tmp_path/'run',client=Client(),config={'research_profile':{'track':'theory'}})
    assert result['status']=='completed'
    assert result['directions'][0]['calculation_ids']==['SSG001']
    for audience in ('researcher','student','general'):
        report=render_agent_report(result,audience)
        assert 'SSG001' in report and 'S001' in report


def test_frozen_catalog_candidates_cover_mac_and_windows(monkeypatch, tmp_path):
    import sys
    from symmetrylab.database import ssg
    exe = tmp_path / 'SymmetryLab.app' / 'Contents' / 'MacOS' / 'SymmetryLab'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(exe))
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path / 'SymmetryLab.app' / 'Contents' / 'Frameworks'), raising=False)
    found = [str(p) for p in ssg.catalog_candidates()]
    assert any('Contents/Frameworks/data/ssg' in p for p in found) and any('Contents/Resources/data/ssg' in p for p in found)
    target = tmp_path / 'SymmetryLab.app' / 'Contents' / 'Resources' / 'data' / 'ssg' / ssg.CATALOG_NAME
    target.parent.mkdir(parents=True); target.write_bytes(b'')
    assert ssg.default_catalog() == target


REAL = __import__('symmetrylab.database.ssg', fromlist=['x']).default_catalog()


@pytest.mark.skipif(not REAL.is_file(), reason='SSG catalog not installed')
def test_offline_ssg_walkthrough_uses_real_catalog(tmp_path, monkeypatch):
    monkeypatch.delenv('SYMMETRYLAB_SSG_CATALOG', raising=False)
    from symmetrylab.agent_core.workbench import run_agent
    from symmetrylab.communication.workbench import render_agent_report
    r = run_agent('Explore a spin space group over P3 using the SSG catalog', tmp_path / 'ssg',
                  config={'research_profile': {'track': 'theory', 'keywords': 'spin space groups'}})
    calcs = {c['calculation_id']: c for c in r['skill_calculations']}
    assert r['status'] == 'completed' and calcs['SSG001']['status'] == 'verified' and calcs['SSG001']['order'] == 6
    assert calcs['SSG002']['orbit_size'] == 6 and calcs['SSG003']['orbit_size'] == 2
    assert 6 == calcs['SSG003']['orbit_size'] * len(calcs['SSG003']['stabilizers'])   # orbit-stabilizer
    assert r['sources'][0]['kind'] == 'ssg_database' and r['directions'][0]['calculation_ids'] == ['SSG001', 'SSG002', 'SSG003']
    report = render_agent_report(r, 'researcher')
    assert '| SSG003 | N143.10.1 | orbit of k = (1/3, 1/3, 0) | orbit 2, stabilizer 3 |' in report and '```json' not in report
    assert 'orbit of 2 momenta' in render_agent_report(r, 'general') and 'SSG catalog calculations' not in render_agent_report(r, 'general')
