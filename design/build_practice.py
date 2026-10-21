#!/usr/bin/env python3
"""Build 60 exercises and an answer key; optionally rebuild the accepted reference."""
from pathlib import Path
from copy import deepcopy
import json
import re
import subprocess
import tempfile
from lxml import etree as E
from PIL import ImageFont
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
S = 'http://www.w3.org/2000/svg'
I = 'http://www.inkscape.org/namespaces/inkscape'
N = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
NS = {None: S, 'inkscape': I, 'sodipodi': N}
D, B, M, L, F, G, RED = '#1D2F40', '#607D8C', '#62717B', '#D1D8DC', '#FAFBFC', '#98A8B1', '#A23D38'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans'
fonts = {}
serial = 0


def el(g, tag, **attrs):
    global serial
    serial += 1
    attrs = {k.replace('_', '-'): str(v) for k, v in attrs.items()}
    attrs.setdefault('id', f'object-{serial}')
    return E.SubElement(g, f'{{{S}}}{tag}', attrs)


def width(s, size=20, bold=False):
    key = size, bold
    if key not in fonts:
        fonts[key] = ImageFont.truetype(FONT + ('-Bold' if bold else '') + '.ttf', size * 4)
    return fonts[key].getlength(s) / 4


def text(g, x, y, s, size=20, color=D, bold=False, anchor='start'):
    node = el(g, 'text', x=x, y=y, font_family='DejaVu Sans, sans-serif', font_size=size,
              font_weight=700 if bold else 400, fill=color, text_anchor=anchor)
    node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    node.text = s
    return node


def rich(g, x, y, s, marks=(), size=20, anchor='start'):
    node = text(g, x, y, '', size, anchor=anchor)
    points = sorted({0, len(s)} | {p for a, b, c in marks for p in (a, b)})
    for a, b in zip(points, points[1:]):
        color = next((c for start, end, c in marks if start <= a and b <= end), D)
        el(node, 'tspan', fill=color).text = s[a:b]
    return node


def para(g, x, y, s, w=390, size=20):
    lines = ['']
    for word in s.split():
        candidate = (lines[-1] + ' ' + word).strip()
        if lines[-1] and width(candidate, size) > w:
            lines.append(word)
        else:
            lines[-1] = candidate
    for idx, s in enumerate(lines):
        marks = [(m.start(), m.end(), RED) for m in re.finditer('одновременно', s)]
        last = idx == len(lines) - 1
        node = rich(g, x + w / 2 if last else x, y, s, marks, size, 'middle' if last else 'start')
        if not last and s.count(' '):
            node.set('word-spacing', str((w - width(s, size)) / s.count(' ')))
        y += size * 1.3
    return y


def box(g, x, y, w, h, fill=F, stroke=L, dash=False):
    attrs = dict(x=x, y=y, width=w, height=h, rx=10, fill=fill, stroke=stroke, stroke_width=1.2)
    if dash:
        attrs.update(stroke_dasharray='4 4', stroke_width=1, rx=4)
    return el(g, 'rect', **attrs)


def line(g, x1, y1, x2, y2, color=G, arrow=False):
    attrs = dict(x1=x1, y1=y1, x2=x2, y2=y2, stroke=color, stroke_width=1.1)
    if arrow:
        attrs['marker_end'] = 'url(#arrow)'
    return el(g, 'line', **attrs)


def curve(g, x1, y1, x2, y2, high=20):
    return el(g, 'path', d=f'M {x1},{y1} C {x1},{y1-high} {x2},{y2-high} {x2},{y2}',
              fill='none', stroke=G, stroke_width=1.1, marker_end='url(#arrow)')


def mark(g, s, start, end, x, y, size=20, strike=False):
    left = x + width(s[:start], size)
    right = x + width(s[:end], size)
    box(g, left - 3, y - size + 2, right - left + 6, size + 6, 'none', G, True)
    if strike:
        node = line(g, left, y - 2, right, y - size + 4, M)
        node.set('data-role', 'strike')
    return (left + right) / 2


def centered(g, x, y, s, size=20, selections=(), strike=False, accent=B):
    left = x - width(s, size) / 2
    rich(g, left, y, s, [(a, b, accent) for a, b in selections], size)
    for a, b in selections:
        mark(g, s, a, b, left, y, size, strike)
    return left


def equation(g, cx, y, s, size=20, selections=(), strike=False, accent=B):
    # Align every equality sign within a card to one column.
    left, right = (p.strip() for p in s.split('='))
    lx, rx = cx - 16 - width(left, size), cx + 16
    for side, value, x in [('L', left, lx), ('R', right, rx)]:
        parts = [(a, b) for k, a, b in selections if k == side]
        rich(g, x, y, value, [(a, b, accent) for a, b in parts], size)
        for a, b in parts:
            mark(g, value, a, b, x, y, size, strike)
    text(g, cx, y, '=', size, B, True, 'middle')
    return lx, rx


def base(title, label, number=None, subtitle=None):
    r = E.Element(f'{{{S}}}svg', nsmap=NS, width='210mm', height='297mm', viewBox='0 0 1000 1414', version='1.1')
    el(r, 'title').text = title
    el(r, 'desc').text = 'EasyMath. Редактируемые текст, рамки и стрелки. Формат А4.'
    defs = el(r, 'defs')
    marker = el(defs, 'marker', id='arrow', markerWidth=7, markerHeight=7, refX=6, refY=3.5,
                orient='auto', markerUnits='userSpaceOnUse')
    el(marker, 'path', d='M 0,0 L 7,3.5 L 0,7 Z', fill=G)
    box(r, 0, 0, 1000, 1414, '#FFFFFF', 'none')
    text(r, 500, 52, label, 16, B, True, 'middle')
    text(r, 500, 100, title, 34, D, True, 'middle')
    if subtitle:
        text(r, 500, 136, subtitle, 17, M, anchor='middle')
    if number:
        text(r, 500, 1382, number, 17, M, anchor='middle')
    return r


def card(r, col, row, title):
    x, y = 55 + col * 460, 175 + row * 290
    g = el(r, 'g')
    g.set(f'{{{I}}}groupmode', 'layer')
    g.set(f'{{{I}}}label', title)
    box(g, x, y, 430, 280)
    text(g, x + 215, y + 35, title, 20, D, True, 'middle')
    return g, x, y


def reference():
    r = base('Уравнения: правила', 'КОРОТКАЯ СПРАВКА',
             subtitle='Сначала раскрываем скобки. Затем упрощаем и решаем.')
    g, x, y = card(r, 0, 0, 'Скобки')
    para(g, x + 20, y + 69, 'Перед скобками плюс — знаки внутри сохраняем. Перед скобками минус — каждый знак внутри меняем.')
    for offset, s, dest in [(190, 'x + (4 − 2)', 'x + 4 − 2'), (242, 'x − (4 − 2)', 'x − 4 + 2')]:
        a = centered(g, x + 102, y + offset, s, selections=[(2, 3), (7, 8)])
        centered(g, x + 326, y + offset, dest, selections=[(2, 3), (6, 7)])
        line(g, x + 185, y + offset - 7, x + 235, y + offset - 7, arrow=True)
    g, x, y = card(r, 1, 0, 'Пары внутри одной части')
    para(g, x + 20, y + 69, 'Одинаковые числа с разными знаками дают ноль. Убираем пару вместе со знаками.')
    centered(g, x + 215, y + 177, 'x + 7 + 4 − 7', selections=[(2, 5), (10, 13)], strike=True)
    line(g, x + 215, y + 193, x + 215, y + 218, arrow=True)
    centered(g, x + 215, y + 249, 'x + 4')
    g, x, y = card(r, 0, 1, 'Одинаковые числа с обеих сторон')
    para(g, x + 20, y + 69, 'Одинаковые числа с одинаковыми знаками убираем одновременно из обеих частей.')
    equation(g, x + 215, y + 169, 'x + 12 = 3 + 12', selections=[('L', 2, 6), ('R', 2, 6)], strike=True)
    equation(g, x + 215, y + 199, 'x = 3')
    equation(g, x + 215, y + 235, 'x − 4 = 9 − 4', selections=[('L', 2, 5), ('R', 2, 5)], strike=True)
    equation(g, x + 215, y + 265, 'x = 9')
    g, x, y = card(r, 1, 1, 'Одинаковое действие')
    para(g, x + 20, y + 69, 'Прибавляем или вычитаем одно и то же одновременно в обеих частях. Это может быть и x.')
    equation(g, x + 215, y + 173, '8 − x = 3')
    equation(g, x + 215, y + 215, '8 − x + x = 3 + x', selections=[('L', 6, 9), ('R', 2, 5)], accent=RED)
    equation(g, x + 215, y + 257, '8 = 3 + x')
    g, x, y = card(r, 0, 2, 'Перенос через знак равенства')
    para(g, x + 20, y + 69, 'Переносим число через «=» — меняем его знак.')
    for baseline, a, b, sign in [(139, 'x + 3 = 8', 'x = 8 − 3', '+'), (224, 'x − 2 = 6', 'x = 6 + 2', '−')]:
        lx, rx = equation(g, x + 215, y + baseline, a, selections=[('L', 2, 5)])
        dx, dr = equation(g, x + 215, y + baseline + 36, b, selections=[('R', 2, 5)])
        el(g, 'path', d=f'M {lx+width(a.split("=")[0].strip())-9},{y+baseline+9} C {x+160},{y+baseline+24} {x+267},{y+baseline+6} {dr+width(b.split("=")[1].strip())-9},{y+baseline+17}',
           fill='none', stroke=G, stroke_width=1.1, marker_end='url(#arrow)')
    g, x, y = card(r, 1, 2, 'Перестановка внутри одной части')
    para(g, x + 20, y + 69, 'В левой или правой части переставляем число вместе с его знаком.')
    s = 'x + 8 − 3 + 2'
    a = centered(g, x + 215, y + 164, s, selections=[(10, 13)])
    b = centered(g, x + 215, y + 209, 'x + 8 + 2 − 3', selections=[(6, 9)])
    el(g, 'path', d=f'M {a+width(s[:10])+14},{y+173} C {x+322},{y+198} {x+290},{y+190} {b+width(s[:6])+14},{y+190}',
       fill='none', stroke=G, stroke_width=1.1, marker_end='url(#arrow)')
    para(g, x + 20, y + 244, 'Перед первым положительным числом плюс обычно не пишут.', size=17)
    g, x, y = card(r, 0, 3, 'Обмен частей')
    para(g, x + 20, y + 69, 'Меняем левую и правую части местами целиком. Знаки сохраняем.')
    lx, rx = equation(g, x + 215, y + 164, '8 = x + 3', selections=[('L', 0, 1), ('R', 0, 5)])
    dx, dr = equation(g, x + 215, y + 244, 'x + 3 = 8', selections=[('L', 0, 5), ('R', 0, 1)])
    el(g, 'path', d=f'M {lx+6},{y+175} C {lx+6},{y+207} {dr+6},{y+196} {dr+6},{y+222}',
       fill='none', stroke=G, stroke_width=1.1, marker_end='url(#arrow)')
    el(g, 'path', d=f'M {rx+width("x + 3")/2},{y+175} C {rx+width("x + 3")/2},{y+205} {dx+width("x + 3")/2},{y+197} {dx+width("x + 3")/2},{y+222}',
       fill='none', stroke=G, stroke_width=1.1, marker_end='url(#arrow)')
    g, x, y = card(r, 1, 3, 'Проверка')
    para(g, x + 20, y + 69, 'Подставляем найденное число вместо x в исходное уравнение. Обе части должны быть равны.')
    equation(g, x + 215, y + 173, 'x + 3 = 8', selections=[('L', 0, 1)])
    text(g, x + 315, y + 173, 'x = 5', 17, M)
    equation(g, x + 215, y + 215, '5 + 3 = 8', selections=[('L', 0, 1)])
    equation(g, x + 215, y + 257, '8 = 8')
    return [r]


def practice(data):
    r = base('Реши уравнения', 'ТРЕНИРОВКА / 60 ЗАДАНИЙ',
             subtitle='Проверь ответ подстановкой в исходное уравнение.')
    # Read down the left column (1–30), then the right (31–60).
    line(r, 500, 166, 500, 1320, L)
    for pos, item in enumerate(data):
        x, y = 45 + (pos // 30)*465, 190 + (pos % 30)*38
        text(r, x, y, f'{item["number"]:02}.', 17, M)
        assert width(item['equation'], 20) <= 400, item
        text(r, x+43, y, item['equation'], 20)
    return [r]


def answers(data):
    r = base('Ответы к 60 уравнениям', 'ПРОВЕРКА РЕЗУЛЬТАТОВ')
    for col in range(4):
        x = 55 + col*225
        box(r, x, 175, 215, 1110)
        text(r, x+107.5, 220, f'{col*15+1}–{col*15+15}', 20, B, True, 'middle')
        for row, item in enumerate(data[col*15:col*15+15]):
            y = 285 + row*66
            text(r, x+20, y, f'{item["number"]:02}.', 20, M)
            text(r, x+72, y, f'x = {item["answer"]}', 26)
    return [r]


def write(name, pages, title):
    master = E.Element(f'{{{S}}}svg', nsmap=NS, width='210mm', height='297mm', viewBox='0 0 1000 1414', version='1.1')
    el(master, 'title').text = title
    view = E.SubElement(master, f'{{{N}}}namedview', {'id': 'view', f'{{{I}}}document-units': 'mm'})
    for idx, page in enumerate(pages):
        ox = idx * 1050
        E.SubElement(view, f'{{{I}}}page', {'x': str(ox), 'y': '0', 'width': '1000', 'height': '1414',
                                         'id': f'page-{idx+1}', f'{{{I}}}label': str(idx+1)})
        g = el(master, 'g', transform=f'translate({ox},0)')
        g.set(f'{{{I}}}groupmode', 'layer')
        g.set(f'{{{I}}}label', f'Страница {idx+1}')
        ids = {n.get('id') for n in page.iter() if n.get('id')}
        prefix = f'p{idx+1}-'
        for child in page:
            if E.QName(child).localname in ('title', 'desc'):
                continue
            node = deepcopy(child)
            for n in node.iter():
                for k, v in list(n.attrib.items()):
                    if k == 'id':
                        n.set(k, prefix + v)
                    else:
                        for old in ids:
                            v = v.replace(f'url(#{old})', f'url(#{prefix}{old})')
                        n.set(k, v)
            g.append(node)
    svg = ROOT / 'design' / f'{name}.svg'
    E.ElementTree(master).write(str(svg), encoding='UTF-8', xml_declaration=True)
    with tempfile.TemporaryDirectory(prefix='easymath-practice-') as folder:
        target = Path(folder) / f'{name}.pdf'
        subprocess.run(['inkscape', str(svg), '--export-page=all', '--export-type=pdf', f'--export-filename={target}'], check=True)
        writer = PdfWriter()
        for n in range(1, len(pages)+1):
            exported = Path(folder) / f'{name}_p{n}.pdf'
            if len(pages) == 1 and not exported.exists():
                exported = target
            page = PdfReader(str(exported)).pages[0]
            page.scale_to(595.2755905512, 841.8897637795)
            writer.add_page(page)
        writer.add_metadata({'/Title': title, '/Author': 'EasyMath'})
        dest = ROOT / 'output/pdf' / f'{name}.pdf'
        writer.write(str(dest))
        print(f'{dest}: {len(pages)} pages')


if __name__ == '__main__':
    data = json.loads((ROOT / 'content/practice-60.json').read_text())
    assert len(data) == 60 and [d['number'] for d in data] == list(range(1, 61))
    if '--with-reference' in __import__('sys').argv:
        write('справка', reference(), 'Уравнения: короткая справка')
    write('задачи', practice(data), '60 тренировочных уравнений')
    write('ответы к задачам', answers(data), 'Ответы к 60 уравнениям')
