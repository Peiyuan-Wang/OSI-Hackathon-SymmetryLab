from copy import deepcopy
from time import monotonic
import pytest
from symmetrylab.verifier.orientation import orientation_scan, check_orientation, axis_constraints, check_axis
from symmetrylab.tools.sources import hill_formula, search_public
from symmetrylab.tools.discovery import DiscoveryTools
from symmetrylab.agent_core.profile import research_profile


N=[[0,0,1],[1,0,0],[0,1,0],[1,1,0],[0,0,-1]]
Q=[[1,0,0],[0,1,0],[1,1,0],[0,0,1]]


def test_exact_factors_and_counterexample_certificates():
    result=orientation_scan(N,Q,[[0,'1/2','1/2',0,0]])
    assert result['factors'][0]==['1','1','1','0']
    assert result['factors'][3]==['1/2','1/2','0','1']
    assert result['factors'][5]==['1/2','1/2','1/2','1']
    assert ['n1','n5'] in result['identical_pairs']
    assert ['n4','domain_mix1'] not in result['identical_pairs']
    assert check_orientation(result)
    changed=deepcopy(result);changed['factors'][0][0]='0'
    assert not check_orientation(changed)
    changed=deepcopy(result);changed['identical_pairs']=[]
    assert not check_orientation(changed)


def test_nuisance_scale_and_geometry_degeneracy():
    r=orientation_scan([[0,0,1],[1,0,1]],[[0,0,1]])
    assert r['factors']==[['0'],['1/2']]
    assert not r['unknown_common_scale_pairs']
    r=orientation_scan([[1,0,0],[1,0,1]],[[0,0,1]])
    assert not r['identical_pairs']
    assert r['unknown_common_scale_pairs']==[['n1','n2']]
    r=orientation_scan(N,[[0,0,1]])
    assert ['n2','n3'] in r['identical_pairs']


@pytest.mark.parametrize('direction',[[0,0,0],[1.,0,0],['1/0',0,0],['sqrt(2)',0,0],[True,0,0]])
def test_invalid_geometry_is_rejected(direction):
    with pytest.raises(ValueError):orientation_scan([direction,[1,0,0]],Q)


def test_domains_and_axis_constraints_are_not_material_assignments():
    with pytest.raises(ValueError):orientation_scan(N,Q,[[0,1,1,0,0]])
    r=axis_constraints([[[0,-1,0],[1,0,0],[0,0,1]]],N)
    assert [x['compatible'] for x in r['outcomes']]==[True,False,False,False,True]
    assert check_axis(r)
    bad=deepcopy(r);bad['outcomes'][1]['compatible']=True
    assert not check_axis(bad)
    with pytest.raises(ValueError):axis_constraints([[[2,0,0],[0,1,0],[0,0,1]]],N)


def workspace():
    state={k:[] for k in ['sources','retrievals','structure_assessments','calculations','directions','experiment_designs','evidence','lessons']}
    state.update(mode='demo',research_profile=research_profile({'track':'experiment','material':'L10 MnPt','papers':'We develop minimal symmetry models.'}))
    return DiscoveryTools(state,lambda:5),state


def test_sources_and_taste_cannot_forge_references():
    tool,state=workspace()
    assert tool.search_sources('literature','MnPt')['status']=='offline'
    assert not state['sources']
    packet=tool.load_material_context()
    assert len(packet['source_ids'])==5
    assert packet['sample_assignment']=='unresolved'
    with pytest.raises(ValueError):tool.source_ids(['S999'])
    with pytest.raises(ValueError):tool.calculation_ids(['V999'])
    with pytest.raises(ValueError):tool.learn_taste([{'origin':'papers','excerpt':'invented','preference':'Topology'}])
    r=tool.learn_taste([{'origin':'papers','excerpt':'minimal symmetry models','preference':'Mechanism-first modeling'}])
    assert r['status']=='profile_proposed'
    assert 'pending' in r['preferences'][0]['status']


def test_public_metadata_adapters_and_formula_normalization():
    assert hill_formula('PtMn')=='Mn Pt'
    assert hill_formula('H2O')=='H2 O'
    assert hill_formula('CH3COOH')=='C2 H4 O2'
    with pytest.raises(ValueError):hill_formula('L10 MnPt')
    seen=[]
    def fetch(url,timeout):
        seen.append(url)
        return [{'file':'1234567','sg':'P 4/m m m','formula':'Mn Pt','title':'Structure'}]
    r=search_public('structure_formula','MnPt',fetch=fetch)
    assert 'formula=Mn+Pt' in seen[0]
    assert r['records'][0]['fields']['sg']=='P 4/m m m'
    assert 'unresolved' in r['records'][0]['scope']
    r=search_public('literature','MnPt',fetch=lambda *args:{'message':{'items':[{'DOI':'10.1234/a','title':['Example'],'abstract':'Metadata only'}]}})
    assert len(r['records'])==1 and 'full text not retrieved' in r['records'][0]['scope']
    with pytest.raises(ValueError):search_public('doi','https://localhost/secret',fetch=fetch)
    with pytest.raises(ValueError):search_public('url','file:///etc/passwd',fetch=fetch)


def test_profile_fields_and_limits():
    with pytest.raises(ValueError):research_profile({'track':'experiment'})
    with pytest.raises(ValueError):research_profile({'track':'theory','papers':'x'*8001})
    with pytest.raises(ValueError):research_profile({'track':'theory','shell':'ls'})
    assert research_profile()['track']=='legacy'


def test_concatenated_actions_execute_only_first_and_reject_malformed_tail():
    from symmetrylab.model.actions import first_action
    action,count=first_action('{"action":"plan","steps":["test"]}{"action":"tool","name":"exec","arguments":{}}')
    assert action['action']=='plan' and count==1
    with pytest.raises(ValueError):first_action('{"action":"plan"} trailing instructions')
    with pytest.raises(ValueError):first_action('{"action":"plan"}{"action":"override_policy"}')


def test_malformed_source_query_can_be_repaired_without_claiming_network_failure(monkeypatch):
    tool,state=workspace(); state['mode']='live'
    calls=[]
    def fetch(kind,query,timeout,material=''):
        calls.append(query)
        raise OSError('offline')
    monkeypatch.setattr('symmetrylab.tools.discovery.search_public',fetch)
    result=tool.search_sources('structure_formula','MnPt L10 tetragonal structure')
    assert result['status']=='invalid_query' and 'formula' in result['message']
    assert not calls
    result=tool.search_sources('structure_formula','MnPt')
    assert result['status']=='unavailable' and calls==['MnPt']


ATOM_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2510.04184v1</id><published>2025-10-05T12:55:48Z</published>
<title>Longitudinal transport spin polarization of spin degenerate antiferromagnets</title>
<summary>We calculate the longitudinal spin conductivity of representative PT-AFMs, L10-MnPt and Mn2Au.</summary>
<author><name>Meng Zhu</name></author></entry>
<entry><id>http://arxiv.org/abs/2401.00001v2</id><title>Unrelated tunnel junction</title><summary>VSe2 barrier.</summary></entry></feed>"""


def test_arxiv_search_and_arxiv_doi_routing():
    from symmetrylab.tools.sources import source_url
    seen=[]
    def fetch(url,timeout):
        seen.append(url); return {'atom':ATOM_SAMPLE}
    r=search_public('arxiv','MnPt "spin polarization"',fetch=fetch,material='L10 MnPt')
    assert 'export.arxiv.org' in seen[0] and 'all%3AMnPt+AND+all%3A%22spin+polarization%22' in seen[0]
    assert r['records'][0]['record_id']=='arXiv:2510.04184' and r['records'][0]['url']=='https://arxiv.org/abs/2510.04184'
    assert [x['mentions_material'] for x in r['records']]==[True,False] and r['relevant_records']==1
    # arXiv DOIs are DataCite DOIs; Crossref returns 404 for them.
    assert 'id_list=2510.04184' in source_url('doi','https://doi.org/10.48550/arXiv.2510.04184')
    assert 'api.crossref.org' in source_url('doi','10.1103/PhysRevB.104.144403')


def test_supporting_information_records_are_not_counted_as_papers():
    rows=[{'DOI':'10.1021/acsami.9b02493.s001','type':'component','title':['SI']},{'DOI':'10.1103/x','title':['MnPt paper']}]
    r=search_public('literature','MnPt TMR',fetch=lambda *a:{'message':{'items':rows}},material='L10 MnPt')
    assert [x['record_id'] for x in r['records']]==['10.1103/x'] and r['records'][0]['mentions_material']
