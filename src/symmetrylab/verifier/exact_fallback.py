"""Complete bounded integer-residual enumeration, never a theta-grid heuristic."""

from itertools import combinations, product
from math import ceil, floor, gcd, lcm, prod
from time import monotonic
from sympy import Matrix, eye
from symmetrylab.schemas import SolverBudget
from .rational import vector_json


def obstruction(B, q):
    # Any returned integer annihilator is a certificate. Missing one proves nothing.
    for row in B.T.nullspace():
        scale = lcm(*(int(x.q) for x in row))
        w = [int(x * scale) for x in row]
        common = gcd(*w)
        w = [x // common for x in w]
        if (Matrix([w]) * q)[0] % 1:
            return {"kind": "integer_annihilator", "w": w,
                    "wq": str((Matrix([w]) * q)[0] % 1)}
    return None


def solve_linear_torus(B, q, budget=None):
    budget = budget or SolverBudget()
    start = monotonic()
    B, q = Matrix(B), Matrix(q).applyfunc(lambda x: x % 1)
    m, d = B.shape
    if d not in (1, 2) or m < 1 or q.shape != (m, 1) or any(not x.is_Integer for x in B):
        raise ValueError("integer B with 1/2 columns and compatible rational q required")
    if any(x.is_Rational is not True for x in q):
        raise ValueError("q must be exact rational")
    rank = B.rank()
    base = {"rank": rank, "method": "exact_integer_residual_vertices", "theta": None,
            "obstruction": None, "certificate": None, "exact_residual": None}
    if budget.seconds == 0 or budget.max_combinations == 0:
        return dict(base, status="budget_exceeded", elapsed_ms=0)
    witness = obstruction(B, q)
    if witness:
        return dict(base, status="gauge_nontrivial", obstruction=witness, certificate=witness,
                    elapsed_ms=(monotonic() - start) * 1000)
    ranges = [(ceil(sum(min(x, 0) for x in B.row(i)) - q[i]),
               floor(sum(max(x, 0) for x in B.row(i)) - q[i])) for i in range(m)]
    estimated = prod(max(0, hi - lo + 1) for lo, hi in ranges)
    if estimated > budget.max_combinations:
        return dict(base, status="budget_exceeded", estimated_combinations=estimated,
                    elapsed_ms=(monotonic() - start) * 1000)
    # Enumerate all possible independent coordinate boundaries at a cube vertex.
    systems = []
    for fixed in combinations(range(d), d - rank):
        E = Matrix([list(eye(d).row(j)) for j in fixed]) if fixed else Matrix.zeros(0, d)
        C = B.col_join(E)
        if C.rank() == d:
            pivots = C.T.rref()[1]
            rows = list(pivots)
            systems.append((fixed, C, rows, C[rows, :].inv()))
    count = 0
    for z in product(*(range(lo, hi + 1) for lo, hi in ranges)):
        if monotonic() - start >= budget.seconds:
            return dict(base, status="budget_exceeded", combinations_checked=count,
                        elapsed_ms=(monotonic() - start) * 1000)
        count += 1
        rhs = q + Matrix(z)
        for fixed, C, rows, inv in systems:
            for values in product((0, 1), repeat=len(fixed)):
                b = rhs.col_join(Matrix(len(values), 1, list(values)))
                theta = inv * b[rows, :]
                if C * theta == b and all(0 <= x <= 1 for x in theta):
                    theta = theta.applyfunc(lambda x: x % 1)
                    residual = (B * theta - q).applyfunc(lambda x: x % 1)
                    assert not any(residual)
                    certificate = {"kind": "solution", "theta": vector_json(theta)}
                    return dict(base, status="gauge_trivial", theta=vector_json(theta),
                                certificate=certificate, exact_residual=vector_json(residual),
                                combinations_checked=count, elapsed_ms=(monotonic() - start) * 1000)
    certificate = {"kind": "exhaustive_integer_residuals", "ranges": ranges,
                   "combinations_checked": count, "complete": True}
    return dict(base, status="gauge_nontrivial", certificate=certificate,
                elapsed_ms=(monotonic() - start) * 1000)
