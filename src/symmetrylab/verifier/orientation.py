"""Exact, conditional collinear neutron orientation factors and finite identifiability.

Inputs are Cartesian vectors, never Miller indices. This kernel does not supply
magnetic structure factors, accessible reflections, energy minima or a material MSG.
"""
from fractions import Fraction
from itertools import combinations
import re


def rational(value):
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r'-?\d{1,6}(?:/\d{1,6})?', value):
        raise ValueError('Use bounded integer or rational strings; floating point is unsupported')
    try:
        return Fraction(value)
    except ZeroDivisionError as exc:
        raise ValueError('Zero denominator') from exc


def vector(values):
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError('Expected three Cartesian components')
    result = [rational(v) for v in values]
    if not any(result):
        raise ValueError('Zero direction is undefined')
    return result


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def factor(moment, q):
    return 1 - dot(moment, q)**2 / (dot(moment, moment)*dot(q, q))


def orientation_scan(directions, probes, domains=None):
    if not isinstance(directions, list) or not 2 <= len(directions) <= 12:
        raise ValueError('Supply 2–12 candidate moment directions')
    if not isinstance(probes, list) or not 1 <= len(probes) <= 12:
        raise ValueError('Supply 1–12 Cartesian scattering directions')
    ns, qs = [vector(n) for n in directions], [vector(q) for q in probes]
    rows = [[factor(n, q) for q in qs] for n in ns]
    labels = [f'n{i+1}' for i in range(len(ns))]
    # Fractions in each mixture describe incoherent domain populations.
    domains = [] if domains is None else domains
    if not isinstance(domains, list) or len(domains) > 8:
        raise ValueError('At most eight domain mixtures')
    weights = []
    for mixture in domains:
        if not isinstance(mixture, list) or len(mixture) != len(ns):
            raise ValueError('One population per candidate direction is required')
        w = [rational(x) for x in mixture]
        if any(x < 0 for x in w) or sum(w) != 1:
            raise ValueError('Domain populations must be nonnegative and sum to one')
        weights.append(w)
        rows.append([sum(w[i]*rows[i][j] for i in range(len(ns))) for j in range(len(qs))])
        labels.append(f'domain_mix{len(weights)}')
    identical, scale_degenerate = [], []
    for i, j in combinations(range(len(rows)), 2):
        a, b = rows[i], rows[j]
        if a == b:
            identical.append([labels[i], labels[j]])
        # Unknown *common* positive intensity scale; zero/nonzero remains distinct.
        same_ray = bool(any(a)) == bool(any(b)) and all(a[x]*b[y] == a[y]*b[x] for x,y in combinations(range(len(qs)),2))
        if same_ray:
            scale_degenerate.append([labels[i], labels[j]])
    return {
        'status': 'conditional_exact', 'kernel': 'collinear_neutron_orientation_v1',
        'formula': 'P(n,Q) = 1 - (n·Q)^2 / ((n·n)(Q·Q))',
        'inputs': {'directions': directions, 'probes': probes, 'domains': domains},
        'labels': labels, 'factors': [[str(x) for x in row] for row in rows],
        'identical_pairs': identical, 'unknown_common_scale_pairs': scale_degenerate,
        'assumptions': ['Collinear single-axis magnetic structure; incoherent populations for listed domains',
                        'Cartesian vectors; a reciprocal basis is needed to convert actual hkl',
                        'Magnetic peaks have nonzero structure factors; form-factor and reflection corrections are known',
                        'No unknown independent intensity scale or background for each reflection'],
        'limitations': ['Orientation factor only; no absolute intensity or accessible-reflection prediction',
                       'n and -n are indistinguishable in this unpolarized intensity model',
                       'Finite candidate comparison does not reconstruct an arbitrary continuous orientation',
                       'Unknown domain populations can create additional degeneracies']}


def check_orientation(result):
    """Check using the independent cross-product form, then check pair claims."""
    try:
        inp = result['inputs']
        expected = orientation_scan(**inp)
        ns, qs = [vector(n) for n in inp['directions']], [vector(q) for q in inp['probes']]
        rows = []
        for n in ns:
            row = []
            for q in qs:
                cross = [n[1]*q[2]-n[2]*q[1], n[2]*q[0]-n[0]*q[2], n[0]*q[1]-n[1]*q[0]]
                row.append(dot(cross, cross)/(dot(n,n)*dot(q,q)))
            rows.append(row)
        for mixture in inp['domains']:
            w = [rational(x) for x in mixture]
            rows.append([sum(w[i]*rows[i][j] for i in range(len(ns))) for j in range(len(qs))])
        if result['factors'] != [[str(x) for x in row] for row in rows]:
            return False
        return all(result[k] == expected[k] for k in expected)
    except (ValueError, TypeError, KeyError, ZeroDivisionError):
        return False


def axis_constraints(rotations, directions):
    """Necessary director invariance under supplied Cartesian domain operations.

D = n n^T is even under time reversal and sublattice exchange. This is a
single-domain director constraint, not a magnetic-space-group assignment.
"""
    from sympy import Matrix, Rational, eye
    if not isinstance(rotations, list) or not 1 <= len(rotations) <= 8:
        raise ValueError('Supply 1–8 rational orthogonal Cartesian rotations')
    if not isinstance(directions, list) or not 1 <= len(directions) <= 12:
        raise ValueError('Supply 1–12 directions')
    matrices = []
    for rotation in rotations:
        if not isinstance(rotation, list) or len(rotation) != 3 or any(not isinstance(row,list) or len(row)!=3 for row in rotation):
            raise ValueError('Expected 3x3 rotations')
        r = Matrix([[Rational(str(rational(x))) for x in row] for row in rotation])
        if r.T*r != eye(3):
            raise ValueError('Rotations must be orthogonal in a Cartesian basis')
        matrices.append(r)
    outcomes = []
    for direction in directions:
        n = Matrix([Rational(str(x)) for x in vector(direction)])
        dyad = n*n.T/(n.dot(n))
        residuals = [r*dyad*r.T-dyad for r in matrices]
        outcomes.append({'direction':direction, 'compatible':all(x.is_zero_matrix for x in residuals),
                         'residuals':[[[str(x) for x in row] for row in m.tolist()] for m in residuals]})
    return {'status':'conditional_exact', 'kernel':'single_domain_director_v1',
            'inputs':{'rotations':rotations,'directions':directions}, 'outcomes':outcomes,
            'scope':'Necessary invariance of the director D=n n^T under the assumed domain operations.',
            'limitations':['Use the ordered single-domain symmetry, not automatically the parent chemical point group.',
                           'This does not establish site permutations, propagation vector, MSG/SSG, energy stability or material realization.',
                           'A rejected axis can describe a different lower-symmetry magnetic domain.']}


def check_axis(result):
    try:
        # Independently check Rn = ±n for each accepted director.
        inp = result['inputs']
        expected = axis_constraints(**inp)
        if result != expected:
            return False
        for row in result['outcomes']:
            n = vector(row['direction'])
            matches = []
            for r in inp['rotations']:
                transformed = [sum(rational(x)*v for x,v in zip(rr,n)) for rr in r]
                matches.append(transformed == n or transformed == [-x for x in n])
            if row['compatible'] != all(matches):
                return False
        return True
    except (ValueError, TypeError, KeyError):
        return False
