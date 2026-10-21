"""Strict rational input; decimal/float and executable strings are rejected."""

import re
from sympy import Rational


def rational(value):
    if type(value) is int and abs(value) <= 10**12:
        return Rational(value)
    if isinstance(value, str) and len(value) <= 64 and re.fullmatch(r"[+-]?\d+(?:/[1-9]\d*)?", value):
        return Rational(value)
    raise ValueError("q must contain integers or rational strings such as '1/2'")


def vector_json(vector):
    return [str(x) for x in vector]
