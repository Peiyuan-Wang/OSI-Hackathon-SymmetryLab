"""Independent certificate arithmetic, with a complete-grid cross-check fallback.

The fallback's grid bound follows from cube vertices and integer maximal minors;
it does not call the solver or assume the input denominator suffices.
"""

from itertools import combinations, product
from math import lcm
from sympy import Matrix
from symmetrylab.schemas import digest
from .rational import rational
from .group_relations import check_group_relations, gauge_system


def verify_certificate(case, result):
    try:
        if digest(case) != result["input_hash"] or check_group_relations(case)["status"] != "valid":
            return False
        B, q = gauge_system(case)
        if "target_q" in result:
            from copy import deepcopy
            other = deepcopy(case)
            for op, vector in zip(other["operations"], result["target_q"], strict=True):
                op["q"] = vector
            if check_group_relations(other)["status"] != "valid" or digest(other) != result["target_hash"]:
                return False
            q = (q - gauge_system(other)[1]).applyfunc(lambda x: x % 1)
        cert = result["certificate"]
        if result["status"] == "gauge_trivial" and cert["kind"] == "solution":
            theta = Matrix([rational(x) for x in cert["theta"]])
            return (result["theta"] == cert["theta"] and theta.shape == (B.cols, 1)
                    and all((x % 1) == 0 for x in B * theta - q))
        if result["status"] != "gauge_nontrivial":
            return False
        if cert["kind"] == "integer_annihilator":
            w = cert["w"]
            return (len(w) == B.rows and all(type(x) is int for x in w)
                    and not any(Matrix([w]) * B) and (Matrix([w]) * q)[0] % 1 != 0
                    and str((Matrix([w]) * q)[0] % 1) == cert["wq"])
        if cert["kind"] == "exhaustive_integer_residuals" and cert["complete"]:
            # Every nonempty rational cube slice has a vertex. Its denominator
            # divides input denominator * some nonzero rank-sized minor.
            r = B.rank()
            determinants = [1]
            for rows in combinations(range(B.rows), r):
                for cols in combinations(range(B.cols), r):
                    det = abs(int(B[list(rows), list(cols)].det()))
                    if det:
                        determinants.append(det)
            bound = lcm(*(int(x.q) for x in q)) * lcm(*determinants)
            if bound ** B.cols > 250_000:
                return False  # verification budget, never an assertion of unsolvability
            for point in product(range(bound), repeat=B.cols):
                theta = Matrix([rational(f"{x}/{bound}") for x in point])
                if all(x % 1 == 0 for x in B * theta - q):
                    return False
            return True
        return False
    except (KeyError, ValueError, TypeError, IndexError, AttributeError, ZeroDivisionError):
        return False
