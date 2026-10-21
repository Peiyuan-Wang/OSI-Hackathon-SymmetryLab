from time import monotonic
import pytest
from symmetrylab.tools.research import ResearchTools


def workspace(max_candidates=40):
    state={k:[] for k in ['candidates','evidence','claim_checks','lessons']}
    return ResearchTools(state,monotonic()+10,lambda:False,max_candidates),state


def test_scan_records_finite_domain_and_comparison():
    tools,state=workspace()
    first=tools.register_candidate('Inversion',1,'C2',[{'R':[[-1]],'s':1,'q':[0]}])['candidate_id']
    scan=tools.scan_shifts(first,denominator=2,max_cases=1)
    assert scan['truncated'] is True and scan['domain_size']==2
    other=tools.register_candidate('Shifted inversion',1,'C2',[{'R':[[-1]],'s':1,'q':['1/2']}])['candidate_id']
    result=tools.compare_gauge(first,other)
    assert result['certificate_verified'] and result['result']['status']=='gauge_trivial'
    assert result['target_id']==other


def test_inconsistent_relations_do_not_become_evidence():
    tools,state=workspace()
    cid=tools.register_candidate('Invalid translation order',1,'C2',[{'R':[[1]],'s':1,'q':['1/3']}])['candidate_id']
    result=tools.solve_gauge(cid)
    assert result['result']['status']=='relation_inconsistent'
    assert not result['certificate_verified']
    checked=tools.test_claim('nonzero_q_implies_nontrivial',[cid])
    assert checked['excluded_invalid']==[cid] and checked['counterexamples']==[]


def test_tool_budgets_and_mismatched_actions():
    tools,state=workspace(2)
    a=tools.register_candidate('Inversion',1,'C2',[{'R':[[-1]],'s':1,'q':[0]}])['candidate_id']
    b=tools.register_candidate('Identity',1,'C2',[{'R':[[1]],'s':1,'q':[0]}])['candidate_id']
    with pytest.raises(ValueError,match='same ordered'): tools.compare_gauge(a,b)
    with pytest.raises(ValueError,match='candidate budget'): tools.register_candidate('More',1,'C2',[{'R':[[1]],'s':1,'q':[0]}])
    with pytest.raises(ValueError): tools.scan_shifts(a,denominator=999,max_cases=1)
    tools.cancelled=lambda:True
    with pytest.raises(InterruptedError): tools.call('solve_gauge',{'candidate_id':a})
