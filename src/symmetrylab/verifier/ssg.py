"""Exact arithmetic on the catalog's graded reciprocal affine operations."""
from fractions import Fraction
import re


def rational(value):
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, str) and len(value) <= 80 and re.fullmatch(r'[+-]?\d+(?:/\d+)?', value):
        return Fraction(value)
    raise ValueError('Use exact integers or rational strings')


def operation(row):
    matrix, shift = row['MomentumAffineAction']
    if len(matrix) != 3 or any(len(r) != 3 for r in matrix) or len(shift) != 3:
        raise ValueError('Expected a three-dimensional affine operation')
    a = tuple(tuple(rational(x) for x in r) for r in matrix)
    b = tuple(rational(x) % 1 for x in shift)
    grade = row['Grading']
    if type(grade) is not int or grade not in (0, 1) or row['Antiunitary'] != bool(grade):
        raise ValueError('Inconsistent antiunitary grading')
    if any(x.denominator != 1 for r in a for x in r):
        raise ValueError('Torus action requires integral matrices')
    determinant = sum(a[0][j]*(a[1][(j+1)%3]*a[2][(j+2)%3]-a[1][(j+2)%3]*a[2][(j+1)%3]) for j in range(3))
    if abs(determinant) != 1:
        raise ValueError('Torus action requires unimodular matrices')
    return a, b, grade


def compose(left, right):
    a, b, g = left; c, d, h = right
    return (tuple(tuple(sum(a[i][k]*c[k][j] for k in range(3)) for j in range(3)) for i in range(3)),
            tuple((b[i]+sum(a[i][k]*d[k] for k in range(3))) % 1 for i in range(3)), g ^ h)


def calculate(record, operation_name, arguments, remaining):
    rows = record.get('GradedReciprocalGroupElements', [])
    if not rows or len(rows) > 384:
        raise ValueError('Supported finite reciprocal quotient size is 1..384')
    operations = [operation(r) for r in rows]
    scope = 'Stored graded reciprocal quotient in its supplied basis and parameter specialization; not the full continuous spin group or a material assignment.'
    if operation_name == 'momentum_orbit':
        if set(arguments) != {'record_id', 'k'} or not isinstance(arguments['k'], list) or len(arguments['k']) != 3:
            raise ValueError('momentum_orbit requires record_id and k: three exact fractions')
        point = tuple(rational(x) for x in arguments['k'])
        images, stabilizers = set(), []
        for index, (a, b, grade) in enumerate(operations):
            remaining()
            image = tuple((sum(a[i][j]*point[j] for j in range(3))+b[i]) % 1 for i in range(3))
            images.add(image)
            if image == tuple(x % 1 for x in point):
                stabilizers.append({'element_index': index, 'grading': grade})
        return {'status': 'computed', 'scope': scope, 'k': [str(x) for x in point],
                'orbit': [[str(x) for x in row] for row in sorted(images)], 'orbit_size': len(images),
                'stabilizers': stabilizers, 'arithmetic': 'exact rational; modulo integer reciprocal translations'}
    if operation_name != 'verify_group' or set(arguments) != {'record_id'}:
        raise ValueError('Unsupported computation or arguments')
    identity = (tuple(tuple(Fraction(int(i == j)) for j in range(3)) for i in range(3)), (Fraction(0),)*3, 0)
    members = set(operations)
    if len(members) != len(operations) or identity not in members:
        return {'status': 'failed', 'scope': scope, 'reason': 'Duplicate operations or missing unitary identity'}
    generators = [operation(r) for r in record.get('ReciprocalGenerators', [])]
    if not generators or any(g not in members for g in generators):
        return {'status': 'failed', 'scope': scope, 'reason': 'Missing or inconsistent generators'}
    # Equality with generator closure proves closure without a quadratic product table.
    reached, queue, products = {identity}, [identity], 0
    while queue:
        current = queue.pop()
        for g in generators:
            remaining(); products += 1
            item = compose(current, g)
            if item not in members:
                return {'status': 'failed', 'scope': scope, 'reason': 'Generator product absent from stored elements'}
            if item not in reached:
                reached.add(item); queue.append(item)
    passed = reached == members and record.get('GradedReciprocalGroupOrder') == len(members)
    return {'status': 'verified' if passed else 'failed', 'scope': scope,
            'checks': ['integral unimodular matrices', 'grading consistency', 'unitary identity',
                       'unique operations', 'exact generator closure equals stored set', 'stored order matches'],
            'order': len(members), 'generated_order': len(reached), 'products_checked': products,
            'arithmetic': 'exact rational affine composition with XOR grading'}
