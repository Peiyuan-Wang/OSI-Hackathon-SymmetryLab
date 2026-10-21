"""Finite toy presentations, exact affine composition and input validation."""

from sympy import Matrix, eye, zeros
from symmetrylab.schemas import CONVENTION
from .rational import rational, vector_json


def presentation(name, generators):
    if name in {"C2", "C4"} and len(generators) == 1:
        return [generators * (2 if name == "C2" else 4)]
    if name == "C2xC2" and len(generators) == 2:
        a, b = generators
        return [[a, a], [b, b], [a, b, a + "^-1", b + "^-1"]]
    raise NotImplementedError("supported groups: C2, C4, C2xC2 with canonical presentations")


def validate_case(case):
    try:
        if not isinstance(case, dict):
            raise ValueError("case must be an object")
        if case.get("schema_version") != "1.0" or case.get("convention") != CONVENTION:
            raise ValueError("schema_version or convention mismatch")
        d = case["dimension"]
        if type(d) is not int or d not in (1, 2):
            raise NotImplementedError("supported dimensions: 1 and 2")
        if case.get("physical_scope") != "toy_only":
            raise NotImplementedError("v0.1 verifies toy_only cases")
        if case.get("privacy") != "public_toy":
            raise NotImplementedError("v0.1 accepts public_toy only")
        group = case["group"]
        names = group["generators"]
        if not isinstance(names, list) or not 1 <= len(names) <= 2:
            raise NotImplementedError("one or two generators required")
        if any(not isinstance(n, str) or not n.isidentifier() or len(n) > 32 for n in names):
            raise ValueError("invalid generator name")
        if len(set(names)) != len(names):
            raise ValueError("duplicate generator name")
        expected = presentation(group["name"], names)
        if sorted(group["relators"]) != sorted(expected):
            raise ValueError("incomplete or noncanonical presentation")
        operations = case["operations"]
        if not isinstance(operations, list) or len(operations) != len(names):
            raise ValueError("operation count mismatch")
        parsed = {}
        for op in operations:
            name, rows, s = op["name"], op["R"], op["s"]
            if name not in names or name in parsed:
                raise ValueError("unknown or duplicate operation")
            if type(s) is not int or s not in (-1, 1):
                raise ValueError("s must be +1 or -1")
            if not isinstance(rows, list) or len(rows) != d or any(not isinstance(row, list) or len(row) != d for row in rows):
                raise ValueError("matrix dimensions mismatch")
            if any(type(x) is not int for row in rows for x in row):
                raise ValueError("R must contain integers")
            if any(abs(x) > 2 for row in rows for x in row):
                raise NotImplementedError("matrix entries must have absolute value <= 2")
            R = Matrix(rows)
            if abs(R.det()) != 1:
                raise ValueError("R must be unimodular")
            if not isinstance(op["q"], list) or len(op["q"]) != d:
                raise ValueError("q dimensions mismatch")
            q = Matrix([rational(x) % 1 for x in op["q"]])
            if any(x.q > 8 for x in q):
                raise NotImplementedError("q denominators must be <= 8")
            parsed[name] = {"R": R, "s": s, "q": q}
        return {"status": "valid", "dimension": d, "operations": parsed}
    except NotImplementedError as exc:
        return {"status": "unsupported", "message": str(exc)}
    except (KeyError, TypeError, ValueError, ZeroDivisionError, AttributeError) as exc:
        return {"status": "invalid_input", "message": str(exc)}


def compose(left, right):
    A, b = left
    C, c = right
    return A * C, (b + A * c).applyfunc(lambda x: x % 1)


def inverse(affine):
    A, b = affine
    inv = A.inv()
    return inv, (-inv * b).applyfunc(lambda x: x % 1)


def check_group_relations(case):
    parsed = validate_case(case)
    if parsed["status"] != "valid":
        return parsed
    d, ops = parsed["dimension"], parsed["operations"]
    for word in case["group"]["relators"]:
        R, sign = eye(d), 1
        affine = (eye(d), zeros(d, 1))
        for token in word:
            inv = token.endswith("^-1")
            op = ops[token[:-3] if inv else token]
            op_affine = (op["s"] * op["R"], op["s"] * op["q"])
            R = R * (op["R"].inv() if inv else op["R"])
            sign *= op["s"]
            affine = compose(affine, inverse(op_affine) if inv else op_affine)
        if R != eye(d) or sign != 1 or affine != (eye(d), zeros(d, 1)):
            return {"status": "relation_inconsistent", "word": word,
                    "R_residual": [[int(x) for x in row] for row in R.tolist()],
                    "s_residual": sign, "A_residual": [[int(x) for x in row] for row in affine[0].tolist()],
                    "b_residual": vector_json(affine[1])}
    return {"status": "valid", "relations_checked": len(case["group"]["relators"])}


def gauge_system(case):
    parsed = validate_case(case)
    if parsed["status"] != "valid":
        raise ValueError(parsed.get("message", parsed["status"]))
    ops = [parsed["operations"][n] for n in case["group"]["generators"]]
    d = parsed["dimension"]
    return Matrix.vstack(*(o["R"] - o["s"] * eye(d) for o in ops)), Matrix.vstack(*(o["q"] for o in ops))
