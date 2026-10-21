#!/usr/bin/env python3
"""Smoke-check арифметики и сохранения решений в примерах памятки.

Без внешних библиотек. Численная проверка не заменяет математическую и
корректорскую проверку человеком. После редактирования примеров обновить кейсы.
"""
import ast
import json
import re
from fractions import Fraction
from pathlib import Path


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
    ['75 + 274 − 75', '274'],
    ['73 − 283 + 23 − 73 + 15 + 37 − 23', '−283 + 15 + 37'],
    ['73 − 283 + 18 + 2 − 73 + 15 + 37 − 20',
     '−283 + 18 + 2 + 15 + 37 − 20', '−283 + 20 + 15 + 37 − 20', '−283 + 15 + 37'],
    ['12 + 5 + 4 − 3 × 2', '17 + 4 − 6', '21 − 6', '15'],
    ['8 + 5 − 3', '13 − 3', '10'],
    ['14 − 2 + 4', '12 + 4', '16'],
]
identity_pairs = [
    ('x + 7 − 7', 'x'),
    ('x + 7 + 4 − 7', 'x + 4'),
    ('x + 8 − 3 + 2', 'x + 8 + 2 − 3'),
    ('x − (4 + 2)', 'x − 4 − 2'),
    ('3 + 2 + 1', '5 + 1'),
    ('3 + 2 − 1', '5 − 1'),
    ('5 − 2 + 2', '3 + 2'),
    ('5 − 2 − 2', '3 − 2'),
    ('2 + 1 + 3', '3 + 3'),
    ('2 + 1 − 3', '3 − 3'),
    ('8 + 5 − 3', '8 − 3 + 5'),
    ('x − 3 + 5', 'x + 5 − 3'),
    ('x − 3 + 5', '5 + x − 3'),
    ('x − 3 + 5', '−3 + x + 5'),
    ('x − 3 + 2', 'x + 2 − 3'),
    ('x + 4 − 2', 'x − 2 + 4'),
    ('x + (4 − 2)', 'x + 4 − 2'),
    ('9 + (5 − 3)', '9 + 5 − 3'),
    ('x − (4 − 2)', 'x − 4 + 2'),
    ('x − (+4 − 2)', 'x − 4 + 2'),
    ('9 − (5 − 3)', '9 − 5 + 3'),
]
equation_chains = [
    ['x + 2 = 5', 'x + 2 + 1 = 5 + 1', 'x = 3'],
    ['x + 2 = 5', 'x + 2 − 1 = 5 − 1', 'x = 3'],
    ['x − 2 = 3', 'x − 2 + 2 = 3 + 2', 'x = 5'],
    ['x − 2 = 3', 'x − 2 − 2 = 3 − 2', 'x = 5'],
    ['x + 1 = 3', 'x + 1 + 3 = 3 + 3', 'x = 2'],
    ['x + 1 = 3', 'x + 1 − 3 = 3 − 3', 'x = 2'],
    ['x + 12 = 3 + 12', 'x + 12 − 12 = 3 + 12 − 12', 'x = 3'],
    ['x − 4 = 9 − 4', 'x − 4 + 4 = 9 − 4 + 4', 'x = 9'],
    ['13 + x = 13 + 5', 'x = 5'],
    ['x + 2 + 3 = 10', 'x + 5 = 10', 'x = 10 − 5', 'x = 5'],
    ['x + 4 − 2 = 9', 'x − 2 + 4 = 9'],
    ['x − 2 = 6', 'x − 2 + 2 = 6 + 2', 'x = 8'],
    ['x − 2 = 6', 'x = 6 + 2', 'x = 8'],
    ['x + 3 = 8', 'x + 3 − 3 = 8 − 3', 'x = 5'],
    ['x + 3 = 8', 'x = 8 − 3', 'x = 5'],
    ['45 = x', 'x = 45'],
    ['8 = x + 3', 'x + 3 = 8'],
    ['8 − x = 3', '8 − x + x = 3 + x', '8 = 3 + x'],
]

# Проверяем цепочки непосредственно из банка разборов, без второй копии примеров.
worked_examples = Path(__file__).resolve().parent.parent / 'content/07-worked-examples-REVIEW.md'
if worked_examples.exists():
    for block in re.split(r'^## Пример \d+\.', worked_examples.read_text(), flags=re.M)[1:]:
        chain = re.findall(r'^\d+\. `([^`]+)` —', block, flags=re.M)
        if not chain:
            raise ValueError('В разборе нет строк уравнения')
        equation_chains.append(chain)


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
    practice_path = Path(__file__).resolve().parent.parent / 'content/practice-60.json'
    if practice_path.exists():
        practice = json.loads(practice_path.read_text())
        assert len(practice) == 60
        assert [p['number'] for p in practice] == list(range(1, 61))
        assert len({p['equation'] for p in practice}) == 60
        for item in practice:
            left, right = item['equation'].split('=')
            offset = calc(left, 0) - calc(right, 0)
            slope = calc(left, 1) - calc(right, 1) - offset
            assert slope in (-1, 1), item
            root = -offset / slope
            assert root == item['answer'] and valid(item['equation'], root), item
            assert root.denominator == 1 and 1 <= root <= 20, item
            for x in (-10, 0, 10, 20):
                assert calc(left, x) - calc(right, x) == slope*x + offset, item
            tests += 1
    print(f'OK: {tests} наборов примеров проверены; 60 тренировочных ответов проверены точно.')


if __name__ == '__main__':
    main()
