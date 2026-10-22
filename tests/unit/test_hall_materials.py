import pytest
from sympy import Matrix, Rational
from symmetrylab.verifier.hall import PRESETS, check_linear_ahe
from symmetrylab.tools.materials import explore_material, catalog


@pytest.mark.parametrize("preset,axis,allowed,dimension", [
    ("identity", "z", True, 3), ("time_reversal", "z", False, 0),
    ("inversion", "x", True, 3), ("mirror_z", "z", True, 1),
    ("mirror_z", "x", False, 1), ("c2z_time_reversal", "z", False, 2),
    ("c2z_time_reversal", "x", True, 2),
])
def test_known_axial_vector_constraints_and_independent_certificates(preset, axis, allowed, dimension):
    result = check_linear_ahe(PRESETS[preset]["generators"], axis)
    assert result["status"] == ("symmetry_allowed" if allowed else "symmetry_forbidden")
    assert result["dimension"] == dimension and result["certificate_verified"]
    constraints = Matrix([[Rational(x) for x in row] for row in result["constraint_matrix"]])
    certificate = result["certificate"]
    if allowed:
        witness = Matrix([Rational(x) for x in certificate["hall_vector"]])
        assert constraints * witness == Matrix.zeros(constraints.rows, 1)
        assert witness[("x", "y", "z").index(axis)] != 0
    else:
        weights = Matrix([Rational(x) for x in certificate["row_combination"]])
        assert weights.T * constraints == Matrix([[int(j == ("x", "y", "z").index(axis)) for j in range(3)]])


def test_combined_generators_reduce_solution_space():
    operations = PRESETS["mirror_z"]["generators"] + PRESETS["c2z_time_reversal"]["generators"]
    result = check_linear_ahe(operations)
    assert result["dimension"] == 0 and result["group_order"] == 4


@pytest.mark.parametrize("operations", [
    [{"rotation": [[1, 1, 0], [0, 1, 0], [0, 0, 1]], "time_reversal": False}],
    [{"rotation": [[1.0, 0, 0], [0, 1, 0], [0, 0, 1]], "time_reversal": False}],
    [{"rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "time_reversal": 1}],
    [{"rotation": [["1e999999", 0, 0], [0, 1, 0], [0, 0, 1]], "time_reversal": False}],
    [{"rotation": [["3/5", "-4/5", 0], ["4/5", "3/5", 0], [0, 0, 1]], "time_reversal": False}],
])
def test_invalid_or_unsupported_operations_rejected(operations):
    with pytest.raises(ValueError):
        check_linear_ahe(operations)


def test_unknown_material_does_not_infer_symmetry_or_papers():
    result = explore_material({"material": "Unknown-X", "msg": "some label"})
    assert result["hall"] is None
    assert result["counts"] == {"directions": 50, "computed": 0, "literature_verified": 0}
    assert result["groups"]["msg"]["status"] == "user_supplied_unverified"
    assert all(not card["literature"]["papers"] and card["evidence"] is None for card in result["cards"])
    assert len(catalog()["families"]) == 9


def test_revision_compares_assumptions_not_material_discoveries():
    forbidden = explore_material({"material": "Illustrative", "preset": "c2z_time_reversal"})
    revised = explore_material({"material": "Illustrative", "preset": "identity"})
    assert forbidden["hall"]["status"] == "symmetry_forbidden"
    assert revised["hall"]["status"] == "symmetry_allowed"
    assert forbidden["hall"]["input_origin"].startswith("illustrative")
    assert all(card["status"] == "not_evaluated" for card in forbidden["cards"][1:])


@pytest.mark.parametrize("payload", [{"material": ""}, {"material": "x", "preset": "typo"}, {"material": "x", "component": "a"}, {"material": "x", "conditions": []}] )
def test_invalid_material_request(payload):
    with pytest.raises(ValueError):
        explore_material(payload)
