from copy import deepcopy
from fractions import Fraction
from itertools import product
from pathlib import Path
import pytest
from sympy import Matrix, Rational, eye
from symmetrylab.schemas import SolverBudget, CONVENTION, read_json
from symmetrylab.evaluation.benchmark import load_suite
from symmetrylab.verifier.gauge_solver import solve_gauge_equivalence
from symmetrylab.verifier.certificate import verify_certificate
from symmetrylab.verifier.exact_fallback import solve_linear_torus
from symmetrylab.verifier.group_relations import check_group_relations, compose, inverse

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = [(case, spec) for case, spec in load_suite(ROOT / "benchmarks/manifest.json") if spec["split"] == "golden"]


@pytest.mark.parametrize("case,spec", GOLDEN, ids=[c["case_id"] for c, _ in GOLDEN])
def test_golden(case, spec):
    answer = solve_gauge_equivalence(case)
    assert answer["status"] == spec["expected"]
    if answer["status"] in {"gauge_trivial", "gauge_nontrivial"}:
        assert verify_certificate(case, answer)


def test_quarter_denominator_and_joint_obstruction(case_factory):
    answer = solve_gauge_equivalence(case_factory())
    assert Fraction(answer["theta"][0]) in {Fraction(1, 4), Fraction(3, 4)}
    joint = solve_gauge_equivalence(case_factory("T05"))
    assert joint["status"] == "gauge_nontrivial"
    assert joint["certificate"]["kind"] == "integer_annihilator"


@pytest.mark.parametrize("mutation", [
    lambda c: c.update(convention="wrong"),
    lambda c: c["operations"][0].update(q=[0.5, 0]),
    lambda c: c["operations"][0].update(q=["0.1", "0"]),
    lambda c: c["operations"][0].update(q=["__import__('os')", "0"]),
    lambda c: c["operations"][0].update(q=["1/0", "0"]),
    lambda c: c["operations"][0].update(R=[[1, 0]]),
    lambda c: c["operations"][0].update(R=[[True, 0], [0, 1]]),
    lambda c: c["operations"][0].update(R=[[2, 0], [0, 1]]),
    lambda c: c["operations"][0].update(s=True),
    lambda c: c["group"].update(relators=[]),
])
def test_invalid_input(case_factory, mutation):
    case = case_factory()
    mutation(case)
    assert solve_gauge_equivalence(case)["status"] == "invalid_input"


@pytest.mark.parametrize("mutation", [
    lambda c: c.update(dimension=3),
    lambda c: c.update(privacy="private_research"),
    lambda c: c.update(physical_scope="physically_checked"),
    lambda c: c["group"].update(name="arbitrary_group"),
    lambda c: c["operations"][0].update(q=["1/9", "0"]),
])
def test_unsupported(case_factory, mutation):
    case = case_factory()
    mutation(case)
    assert solve_gauge_equivalence(case)["status"] == "unsupported"


def test_relation_residual_is_serializable(case_factory):
    import json
    result = check_group_relations(case_factory("T09"))
    assert result["status"] == "relation_inconsistent"
    json.dumps(result)


def test_affine_inverse_and_composition_direction():
    A = Matrix([[0, -1], [1, 0]])
    b = Matrix([Rational(1, 2), Rational(1, 3)])
    C = Matrix([[1, 0], [0, -1]])
    c = Matrix([0, Rational(1, 4)])
    k = Matrix([Rational(1, 5), Rational(2, 7)])
    composed = compose((A, b), (C, c))
    assert (composed[0] * k + composed[1] - (A * (C * k + c) + b)).applyfunc(lambda x: x % 1) == Matrix([0, 0])
    assert compose((A, b), inverse((A, b))) == (eye(2), Matrix([0, 0]))


def test_c4_and_linear_relation_failure(case_factory):
    case = case_factory()
    case["group"].update(name="C4", relators=[["g"] * 4])
    case["operations"][0]["R"] = [[0, -1], [1, 0]]
    assert solve_gauge_equivalence(case)["status"] == "gauge_trivial"
    case["group"].update(name="C2", relators=[["g", "g"]])
    assert solve_gauge_equivalence(case)["status"] == "relation_inconsistent"


def test_budget_is_not_unsolvable(case_factory):
    for budget in [SolverBudget(seconds=0), SolverBudget(max_combinations=0), SolverBudget(max_combinations=1)]:
        assert solve_gauge_equivalence(case_factory(), budget=budget)["status"] == "budget_exceeded"


def test_rank_zero_and_rank_deficient_vertices():
    for B, q, expected in [([[0, 0]], [0], "gauge_trivial"),
                           ([[0, 0]], [Rational(1, 2)], "gauge_nontrivial"),
                           ([[-2, 0], [0, 0]], [Rational(1, 2), 0], "gauge_trivial")]:
        assert solve_linear_torus(B, q)["status"] == expected


def test_fallback_when_primitive_nullspace_basis_misses_obstruction():
    # Primitive rational nullspace vectors need not span the saturated integer
    # lattice. Each candidate annihilator passes, but the full system is impossible.
    result = solve_linear_torus([[2], [1], [1]], [0, Rational(1, 2), 0])
    assert result["status"] == "gauge_nontrivial"
    assert result["certificate"]["kind"] == "exhaustive_integer_residuals"
    assert result["certificate"]["complete"]


def test_solver_matches_complete_small_1d_oracle():
    # lcm of all possible nonzero minors 1,2 is 2; q denominator 4 -> grid 8
    for a, b in product(range(-2, 3), repeat=2):
        for p, t in product(range(4), repeat=2):
            qs = [Fraction(p, 4), Fraction(t, 4)]
            exists = any(all((coef * Fraction(x, 8) - q) % 1 == 0 for coef, q in zip([a, b], qs)) for x in range(8))
            result = solve_linear_torus([[a], [b]], [Rational(p, 4), Rational(t, 4)])
            assert (result["status"] == "gauge_trivial") == exists


def test_target_shift_validation_and_certificate(case_factory):
    case = case_factory()
    answer = solve_gauge_equivalence(case, target_q=[["0", "0"]])
    assert answer["status"] == "gauge_trivial" and verify_certificate(case, answer)
    invalid = solve_gauge_equivalence(case_factory("T02"), target_q=[["1/3", "0"]])
    assert invalid["status"] == "relation_inconsistent"


def test_certificate_tampering(case_factory):
    case = case_factory()
    result = solve_gauge_equivalence(case)
    bad = deepcopy(result)
    bad["theta"] = ["0", "0"]
    assert not verify_certificate(case, bad)
    bad = deepcopy(result)
    bad["certificate"]["theta"] = ["0", "0"]
    assert not verify_certificate(case, bad)
    other = case_factory("T05")
    bad = solve_gauge_equivalence(other)
    bad["certificate"]["w"] = [0, 0, 0, 0]
    assert not verify_certificate(other, bad)


@pytest.mark.parametrize("name", ["T01", "T02", "T05", "T06", "T07", "T08"])
def test_integer_representatives_and_gauge_metamorphisms(case_factory, name):
    case = case_factory(name)
    expected = solve_gauge_equivalence(case)["status"]
    for op in case["operations"]:
        op["q"] = [str(Fraction(x) + 2) for x in op["q"]]
    assert solve_gauge_equivalence(case)["status"] == expected
    eta = Matrix([Rational(1, 8), Rational(3, 8)])
    for op in case["operations"]:
        q = Matrix([Rational(x) for x in op["q"]])
        q = q - (Matrix(op["R"]) - op["s"] * eye(2)) * eta
        op["q"] = [str(x % 1) for x in q]
    answer = solve_gauge_equivalence(case)
    assert answer["status"] == expected and verify_certificate(case, answer)


def test_basis_and_generator_order(case_factory):
    for name in ["T01", "T05", "T07", "T08"]:
        case = case_factory(name)
        expected = solve_gauge_equivalence(case)["status"]
        P = Matrix([[0, 1], [1, 0]])
        for op in case["operations"]:
            op["R"] = [[int(x) for x in row] for row in (P * Matrix(op["R"]) * P.inv()).tolist()]
            op["q"] = [str(x % 1) for x in P * Matrix([Rational(x) for x in op["q"]])]
        case["group"]["generators"].reverse()
        case["operations"].reverse()
        # group relators are the same defining words, reordered generators allowed
        from symmetrylab.verifier.group_relations import presentation
        case["group"]["relators"] = presentation(case["group"]["name"], case["group"]["generators"])
        assert solve_gauge_equivalence(case)["status"] == expected
