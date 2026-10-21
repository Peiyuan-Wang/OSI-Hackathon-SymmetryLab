"""Search a finite supplied domain with executable, whitelisted predicates."""

from time import monotonic
from symmetrylab.schemas import SolverBudget
from .gauge_solver import solve_gauge_equivalence
from .certificate import verify_certificate
from .group_relations import gauge_system, presentation

PREDICATES = {
    "nonzero_q_implies_nontrivial": "Every valid nonzero shift is gauge-nontrivial under a common change of origin.",
    "individual_implies_joint": "If each generator's shift can be removed individually, a common change of origin exists.",
}


def is_counterexample(predicate, case, result, seconds=10):
    if result["status"] not in {"gauge_trivial", "gauge_nontrivial"}:
        return False
    if not verify_certificate(case, result):
        return False
    if predicate == "nonzero_q_implies_nontrivial":
        return any(gauge_system(case)[1]) and result["status"] == "gauge_trivial"
    if predicate == "individual_implies_joint" and result["status"] == "gauge_nontrivial":
        from copy import deepcopy
        from math import isfinite
        if not isfinite(seconds) or seconds <= 0:
            return False
        if case["group"]["name"] != "C2xC2":
            return False
        for op in case["operations"]:
            single = deepcopy(case)
            single["operations"] = [op]
            single["group"] = {"name": "C2", "generators": [op["name"]],
                               "relators": presentation("C2", [op["name"]])}
            one = solve_gauge_equivalence(single, budget=SolverBudget(seconds=seconds / 2))
            if one["status"] != "gauge_trivial" or not verify_certificate(single, one):
                return False
        return True
    return False


def find_counterexample(predicate, cases, max_cases=30, seconds=180):
    if predicate not in PREDICATES:
        raise ValueError("unsupported executable hypothesis")
    start = monotonic()
    evidence = []
    for case in cases:
        remaining = seconds - (monotonic() - start)
        if len(evidence) >= max_cases or remaining <= 0:
            return {"status": "budget_exceeded", "evidence": evidence, "counterexample": None}
        result = solve_gauge_equivalence(case, budget=SolverBudget(seconds=min(10, remaining)))
        evidence.append({"case": case, "result": result})
        remaining = seconds - (monotonic() - start)
        if remaining > 0 and is_counterexample(predicate, case, result, remaining):
            return {"status": "Counterexample found", "evidence": evidence,
                    "counterexample": case["case_id"]}
    completed = all(e["result"]["status"] in {"gauge_trivial", "gauge_nontrivial", "relation_inconsistent", "invalid_input"}
                    for e in evidence)
    return {"status": "No counterexample in supplied finite domain" if completed else "incomplete",
            "evidence": evidence, "counterexample": None}
