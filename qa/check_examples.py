#!/usr/bin/env python3
"""Smoke-check арифметики и сохранения решений в примерах памятки.

Без внешних библиотек. Численная проверка не заменяет математическую и
корректорскую проверку человеком. После редактирования примеров обновить кейсы.
"""
import ast
from fractions import Fraction


def calc(s, x=0):
    s = s.replace('−', '-').replace('×', '*').replace(' ', '')
    node = ast.parse(s, mode='eval').body

    def walk(n):
        if isinstance(n, ast.Constant) and type(n.value) is int:
            return Fraction(n.value)
        if isinstance(n, ast.Name) and n.id == 'x':
            return Fraction(x)
        if isinstance(n, ast.UnaryOp):
            a = walk(n.operand)
            if isinstance(n.op, ast.USub): return -a
            if isinstance(n.op, ast.UAdd): return a
        if isinstance(n, ast.BinOp):
            a, b = walk(n.left), walk(n.right)
            if isinstance(n.op, ast.Add): return a + b
            if isinstance(n.op, ast.Sub): return a - b
            if isinstance(n.op, ast.Mult): return a * b
            if isinstance(n.op, ast.Div): return a / b
        raise ValueError(f'Недопустимое выражение: {s}')
    return walk(node)


def valid(eq, x):
    a, b = eq.split('=', 1)
    return calc(a, x) == calc(b, x)


arithmetic_chains = [
    ['12 + 5 + 4 − 3 × 2', '17 + 4 − 6', '21 − 6', '15'],
    ['8 + 5 − 3', '13 − 3', '10'],
    ['14 − 2 + 4', '12 + 4', '16'],
]
identity_pairs = [
    ('8 + 5 − 3', '8 − 3 + 5'),
    ('x − 3 + 2', 'x + 2 − 3'),
    ('x + 4 − 2', 'x − 2 + 4'),
    ('x + (4 − 2)', 'x + 4 − 2'),
    ('9 + (5 − 3)', '9 + 5 − 3'),
    ('x − (4 − 2)', 'x − 4 + 2'),
    ('9 − (5 − 3)', '9 − 5 + 3'),
]
equation_chains = [
    ['x + 2 + 3 = 10', 'x + 5 = 10', 'x = 10 − 5', 'x = 5'],
    ['x + 4 − 2 = 9', 'x − 2 + 4 = 9'],
    ['x − 2 = 6', 'x − 2 + 2 = 6 + 2', 'x = 8'],
    ['x − 2 = 6', 'x = 6 + 2', 'x = 8'],
    ['x + 3 = 8', 'x + 3 − 3 = 8 − 3', 'x = 5'],
    ['x + 3 = 8', 'x = 8 − 3', 'x = 5'],
    ['45 = x', 'x = 45'],
    ['8 = x + 3', 'x + 3 = 8'],
]


def main():
    tests = 0
    for chain in arithmetic_chains:
        vals = [calc(s) for s in chain]
        assert len(set(vals)) == 1, f'Ошибка вычисления: {chain!r}: {vals!r}'
        tests += 1
    for a, b in identity_pairs:
        for x in range(-100, 101):
            assert calc(a, x) == calc(b, x), f'Ошибка тождества: {a!r} == {b!r} при x={x}'
        tests += 1
    for chain in equation_chains:
        solutions = [tuple(x for x in range(-100, 101) if valid(eq, x)) for eq in chain]
        assert len(set(solutions)) == 1, f'Неравносильные уравнения: {chain!r}: {solutions!r}'
        tests += 1
    print(f'OK: {tests} наборов примеров проверены (численный smoke-check).')


if __name__ == '__main__':
    main()
