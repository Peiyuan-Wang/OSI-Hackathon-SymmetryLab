"""Exact zero-field linear AHE constraints for supplied Cartesian generators.

This checks a time-odd axial Hall vector, not nonlinear or finite-field transport.
It does not infer a magnetic structure from a formula, MSG label, or SSG label.
"""
import re
from sympy import Matrix, Rational, eye


PRESETS = {
    "identity": {"label": "Identity only (illustrative)", "generators": []},
    "time_reversal": {"label": "Time reversal (illustrative)", "generators": [{"rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "time_reversal": True}]},
    "inversion": {"label": "Inversion (illustrative)", "generators": [{"rotation": [[-1, 0, 0], [0, -1, 0], [0, 0, -1]], "time_reversal": False}]},
    "mirror_z": {"label": "Mirror normal to z (illustrative)", "generators": [{"rotation": [[1, 0, 0], [0, 1, 0], [0, 0, -1]], "time_reversal": False}]},
    "c2z_time_reversal": {"label": "Twofold z rotation with time reversal (illustrative)", "generators": [{"rotation": [[-1, 0, 0], [0, -1, 0], [0, 0, 1]], "time_reversal": True}]},
}


def exact_matrix(raw):
    if not isinstance(raw, list) or len(raw) != 3 or any(not isinstance(row, list) or len(row) != 3 for row in raw):
        raise ValueError("Each rotation must be a 3 by 3 Cartesian matrix.")
    entries = []
    for row in raw:
        for value in row:
            if type(value) is not int and not (isinstance(value, str) and re.fullmatch(r"-?\d{1,3}(?:/\d{1,2})?", value)):
                raise ValueError("Use integers or exact fraction strings, not floats.")
            try:
                number = Rational(value)
            except (ValueError, TypeError, ZeroDivisionError):
                raise ValueError("Invalid exact rotation entry.") from None
            if not number.is_finite or abs(number) > 1 or number.q > 24:
                raise ValueError("Rotation entries exceed the supported exact range.")
            entries.append(number)
    rotation = Matrix(3, 3, entries)
    if rotation.T * rotation != eye(3) or rotation.det() not in (-1, 1):
        raise ValueError("Rotations must be orthogonal in a Cartesian basis; convert fractional coordinates first.")
    return rotation


def check_linear_ahe(generators, component="z"):
    if component not in ("x", "y", "z"):
        raise ValueError("Hall-vector component must be x, y, or z.")
    if not isinstance(generators, list) or len(generators) > 8:
        raise ValueError("Supply up to eight magnetic point-group generators.")
    operations = []
    for generator in generators:
        if not isinstance(generator, dict) or set(generator) != {"rotation", "time_reversal"} or type(generator["time_reversal"]) is not bool:
            raise ValueError("Each generator needs rotation and boolean time_reversal fields.")
        operations.append((exact_matrix(generator["rotation"]), generator["time_reversal"]))
    # Reject unsupported noncrystallographic or effectively infinite closures.
    group = [(eye(3), False)]
    known = {(tuple(eye(3)), False)}
    index = 0
    while index < len(group):
        rotation, anti = group[index]
        for other, other_anti in operations:
            product, parity = rotation * other, anti ^ other_anti
            key = (tuple(product), parity)
            if key not in known:
                if len(group) >= 96 or any(abs(x.p) > 1000000 or x.q > 1000000 for x in product):
                    raise ValueError("Generator closure exceeds this prototype's finite-group support.")
                known.add(key)
                group.append((product, parity))
        index += 1
    constraints = [((-1 if anti else 1) * rotation.det() * rotation - eye(3)) for rotation, anti in group]
    stacked = Matrix.vstack(*constraints)
    basis = stacked.nullspace()
    axis = ("x", "y", "z").index(component)
    allowed = any(vector[axis] != 0 for vector in basis)
    witness = next((vector for vector in basis if vector[axis] != 0), None)
    verified = all(stacked * vector == Matrix.zeros(stacked.rows, 1) for vector in basis)
    if not allowed:
        selector = Matrix([[int(j == axis) for j in range(3)]])
        # Independent row-space certificate that the selected coordinate is zero.
        multipliers = stacked.T.gauss_jordan_solve(selector.T)[0]
        free = set().union(*(entry.free_symbols for entry in multipliers))
        multipliers = multipliers.subs({symbol: 0 for symbol in free})
        verified = verified and multipliers.T * stacked == selector
        certificate = {"kind": "zero_component", "row_combination": [str(x) for x in multipliers]}
    else:
        certificate = {"kind": "allowed_witness", "hall_vector": [str(x) for x in witness]}
    return {
        "status": "symmetry_allowed" if allowed else "symmetry_forbidden",
        "component": component, "group_order": len(group), "dimension": len(basis),
        "basis": [[str(x) for x in vector] for vector in basis],
        "constraint_matrix": [[str(stacked[i, j]) for j in range(3)] for i in range(stacked.rows)],
        "certificate": certificate, "certificate_verified": bool(verified),
        "rule": "h = (-1)^time_reversal det(R) R h",
        "scope": "Uniform zero-field linear anomalous Hall response; supplied Cartesian magnetic point-group generators.",
        "limitations": ["Allowed does not establish a finite or measurable signal.", "Association of these operations with the material is not verified.", "SSG spin operations, nonlinear responses, interfaces and finite-field symmetry changes are not evaluated."],
        "reference": "https://arxiv.org/abs/1507.04947",
    }
