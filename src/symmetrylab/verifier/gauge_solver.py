"""Public solver: validation always precedes mathematical classification."""

from copy import deepcopy
from symmetrylab.schemas import digest
from .group_relations import check_group_relations, gauge_system
from .exact_fallback import solve_linear_torus


def solve_gauge_equivalence(case, target_q=None, budget=None):
    relation = check_group_relations(case)
    base = {"input_hash": digest(case), "solver_version": "0.1.0", "relations": relation}
    if relation["status"] != "valid":
        return dict(base, status=relation["status"], message=relation.get("message"),
                    theta=None, certificate=None)
    B, q = gauge_system(case)
    if target_q is not None:
        # A full list of generator q-vectors is required; validate its group action too.
        target = deepcopy(case)
        if not isinstance(target_q, list) or len(target_q) != len(target["operations"]):
            return dict(base, status="invalid_input", message="target_q shape mismatch")
        for op, vector in zip(target["operations"], target_q):
            op["q"] = vector
        checked = check_group_relations(target)
        if checked["status"] != "valid":
            return dict(base, status=checked["status"], message="target shift is not valid",
                        target_relations=checked)
        _, other = gauge_system(target)
        q = (q - other).applyfunc(lambda x: x % 1)
        base["target_q"] = target_q
        base["target_hash"] = digest(target)
    return dict(base, **solve_linear_torus(B, q, budget))
