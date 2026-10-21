#!/usr/bin/env python3
"""Build editable Inkscape pages from the agreed example text; PDF export is separate."""
from pathlib import Path
from copy import deepcopy
import re
from lxml import etree as E
from PIL import ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'design/explanation'
OUT.mkdir(exist_ok=True)
S = 'http://www.w3.org/2000/svg'
I = 'http://www.inkscape.org/namespaces/inkscape'
N = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
NS = {None:S, 'inkscape':I, 'sodipodi':N}
D, B, M, L, F = '#1D2F40','#607D8C','#62717B','#D1D8DC','#FAFBFC'
G, RED = '#98A8B1', '#A23D38'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans'
fonts = {}
serial = 0

def el(g, tag, **a):
    global serial
    serial += 1
    a = {k.replace('_','-'):str(v) for k,v in a.items()}
    a.setdefault('id',f'object-{serial}')
    return E.SubElement(g, f'{{{S}}}{tag}', a)

def width(s,size=20,bold=False):
    k = (size,bold)
    if k not in fonts: fonts[k] = ImageFont.truetype(FONT+('-Bold' if bold else '')+'.ttf',size*4)
    return fonts[k].getlength(s)/4

def wrap(s,w,size=20,bold=False):
    lines=['']
    for word in re.findall(r'[+−]\d+\s+→\s+[+−]\d+|\S+',s):
        candidate=(lines[-1]+' '+word).strip()
        if lines[-1] and width(candidate,size,bold)>w: lines.append(word)
        else: lines[-1]=candidate
    return lines

def text(g,x,y,s,size=20,color=D,bold=False,anchor=None):
    a=dict(x=x,y=y,font_family='DejaVu Sans, sans-serif',font_size=size,
           font_weight=700 if bold else 400,fill=color)
    if anchor: a['text_anchor']=anchor
    t=el(g,'text',**a);t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=s
    return t

def para(g,x,y,s,w=840,size=20,bold=False,color=D,leading=None):
    # Full-width paragraph blocks are centered; completed lines are justified.
    leading = leading or size*1.3
    lines=wrap(s,w,size,bold)
    for i,line_text in enumerate(lines):
        last=i==len(lines)-1
        centered=(last or bold) and w>=800
        t=text(g,x+w/2 if centered else x,y,line_text,size,color,bold,'middle' if centered else None)
        t.set('data-role','paragraph')
        if 'одновременно' in line_text:
            t.text=None
            for part in re.split('(одновременно)',line_text):
                el(t,'tspan',fill=RED if part=='одновременно' else color).text=part
        if not last and not bold and line_text.count(' '):
            t.set('word-spacing',str((w-width(line_text,size,bold))/line_text.count(' ')))
        y+=leading
    return y

def box(g,x,y,w,h,fill=F,stroke=L,dash=False,rx=10):
    a=dict(x=x,y=y,width=w,height=h,rx=rx,fill=fill,stroke=stroke,stroke_width=1.2)
    if dash:a.update(stroke_dasharray='4 4',stroke_width='1')
    return el(g,'rect',**a)

def line(g,x1,y1,x2,y2,color=G,arrow=False):
    a=dict(x1=x1,y1=y1,x2=x2,y2=y2,stroke=color,stroke_width=1.1)
    if arrow:a['marker_end']='url(#arrow-blue)'
    return el(g,'line',**a)

def strike(g,x1,baseline,x2,color=M,size=26):
    mark=line(g,x1,baseline-3,x2,baseline-size+4,color=color)
    mark.set('data-role','strike')
    return mark

def curve(g,x1,y1,x2,y2):
    mid=(y1+y2)/2
    return el(g,'path',d=f'M {x1},{y1} C {x1},{mid} {x2},{mid} {x2},{y2}',
              fill='none',stroke=G,stroke_width=1.0,marker_end='url(#arrow-blue)')

def base(n,title):
    r=E.Element(f'{{{S}}}svg',nsmap=NS,width='210mm',height='297mm',viewBox='0 0 1000 1414',version='1.1')
    el(r,'title').text=title
    el(r,'desc').text='Редактируемый разбор. Текст, рамки, стрелки и цветовые выделения — отдельные объекты.'
    defs=el(r,'defs')
    marker=el(defs,'marker',id='arrow-blue',markerWidth=7,markerHeight=7,refX=6,refY=3.5,orient='auto',markerUnits='userSpaceOnUse')
    el(marker,'path',d='M 0,0 L 7,3.5 L 0,7 Z',fill=G)
    red_marker=el(defs,'marker',id='arrow-red',markerWidth=7,markerHeight=7,refX=6,refY=3.5,orient='auto',markerUnits='userSpaceOnUse')
    el(red_marker,'path',d='M 0,0 L 7,3.5 L 0,7 Z',fill=RED)
    box(r,0,0,1000,1414,'#FFFFFF','none',rx=0)
    text(r,500,52,f'РАЗБОР УРАВНЕНИЙ / {n:02}',16,B,True,'middle')
    text(r,500,100,title,34,D,True,'middle')
    line(r,55,129,945,129,L)
    text(r,500,1382,str(n),17,M,anchor='middle')
    return r

def card(r,y,h,title):
    g=el(r,'g');g.set(f'{{{I}}}groupmode','layer');g.set(f'{{{I}}}label',title)
    box(g,55,y,890,h)
    text(g,500,y+37,title,26,D,True,'middle')
    return g

def equation(g,eq,y,cx=330,size=26,final=False):
    a,b=[s.strip() for s in eq.split('=',1)]
    ax=cx-24-width(a,size,final);bx=cx+24
    if final:box(g,ax-12,y-size-7,bx+width(b,size,final)-ax+24,size+20,'#EDF8F4','none',rx=6)
    left=text(g,ax,y,a,size,D,final);text(g,cx,y,'=',size,B,True,'middle');right=text(g,bx,y,b,size,D,final)
    return dict(L=(a,ax),R=(b,bx),y=y,size=size,cx=cx,bold=final,nodes={'L':left,'R':right},highlights={'L':[],'R':[]},frames={'L':[],'R':[]})

def span(g,row,side,start,end,stroke=True):
    s,x=row[side];size=row['size'];y=row['y']
    x+=width(s[:start],size,row['bold']);w=width(s[start:end],size,row['bold'])
    if stroke:
        fs,fe=start,end
        for prior in list(row['frames'][side]):
            u,v,rect=prior
            if not (fe<u or fs>v):
                fs,fe=min(fs,u),max(fe,v)
                g.remove(rect);row['frames'][side].remove(prior)
        sx=row[side][1]+width(s[:fs],size,row['bold'])
        sw=width(s[fs:fe],size,row['bold'])
        rect=box(g,sx-4,y-size+2,sw+8,size+8,'none',row.get('stroke_color',G),True,4)
        row['frames'][side].append((fs,fe,rect))
    row['highlights'][side].append((start,end))
    n=row['nodes'][side]
    n.text=None
    for child in list(n):n.remove(child)
    marks={0,len(s)}
    for a,b in row['highlights'][side]:marks.update((a,b))
    marks=sorted(marks)
    for a,b in zip(marks,marks[1:]):
        selected=any(a>=u and b<=v for u,v in row['highlights'][side])
        t=el(n,'tspan',fill=row.get('accent',D) if selected else D);t.text=s[a:b]
    return (x+w/2,y+8,x,y-size+2,w)

def whole(g,row,side):
    return span(g,row,side,0,len(row[side][0]))

def signed(expr):
    result=[]
    for m in re.finditer(r'([+−]?)\s*(\d+|x)',expr):
        start=m.start(1) if m[1] else m.start(2)
        result.append((m[1] or '+',m[2],start,m.end(2)))
    return result

def term(g,row,side,sgn,val,last=False):
    matches=[t for t in signed(row[side][0]) if t[:2]==(sgn,val)]
    if not matches:return None
    t=matches[-1] if last else matches[0]
    return span(g,row,side,t[2],t[3])

def join(g,a,b):
    if a and b:curve(g,a[0],a[1]+2,b[0],b[3]-3)

def transition(g,old,new,action):
    if 'Меняем' in action and ('части местами' in action or 'левую и правую' in action):
        a=whole(g,old,'L');b=whole(g,old,'R');c=whole(g,new,'L');d=whole(g,new,'R')
        join(g,a,d);join(g,b,c);return
    moved=re.search(r'Переносим ([+−])(\d+)',action)
    if moved:
        sg,val=moved.groups();src='R' if ('справа налево' in action or 'справа' in action or 'влево' in action) else 'L'
        dst='L' if src=='R' else 'R'
        a=term(g,old,src,sg,val);b=term(g,new,dst,'−' if sg=='+' else '+',val,True)
        join(g,a,b);return
    moved=re.search(r'Переставляем ([+−])(\d+)',action,re.I)
    if moved:
        sg,val=moved.groups();join(g,term(g,old,'L',sg,val),term(g,new,'L',sg,val));return
    if any('(' in old[k][0] and '(' not in new[k][0] for k in ('L','R')):
        side='L' if '(' in old['L'][0] else 'R';s=old[side][0]
        start=s.index('(');end=s.index(')')+1
        a=span(g,old,side,start,end)
        # The affected group expands in the same side, with no crossing of equality.
        dest=new[side][0]
        prefix=s[:start].rstrip()
        if prefix.endswith(('+','−')):prefix=prefix[:-1].rstrip()
        start2=len(prefix)
        while start2<len(dest) and dest[start2]==' ':start2+=1
        b=span(g,new,side,start2,len(dest),stroke=False);join(g,a,b);return
    if 'Прибавляем x' in action:
        for side in ('L','R'):
            b=term(g,new,side,'+','x',True)
            if b:curve(g,b[0],old['y']+17,b[0],b[3]-3)
        return
    if 'дают ноль' in action:
        s=old['L'][0];m=re.search(r'−\s*x\s*\+\s*x',s)
        if m:
            a=span(g,old,'L',m.start(),m.end());strike(g,a[2],old['y'],a[2]+a[4])
            text(g,a[0],old['y']+27,'0',16,B,anchor='middle')
        return
    if action.startswith('Считаем'):
        described=re.search(r':\s*([0-9 +−]+)\s*=\s*(\d+)',action)
        for side in ('L','R'):
            src=old[side][0];dst=new[side][0]
            if src==dst:continue
            m=None
            if described:
                phrase=described[1].strip()
                pos=src.find(phrase)
                if pos>=0:
                    begin,end=pos,pos+len(phrase)
                    matches=[t for t in signed(dst) if t[1]==described[2]]
                else:continue
            else:
                m=re.search(r'\d+(?:\s*[+−]\s*\d+)+',src)
                if not m:continue
                begin,end=m.start(),m.end()
                matches=[t for t in signed(dst) if t[1]!='x']
            a=span(g,old,side,begin,end)
            if matches:
                t=matches[-1];b=span(g,new,side,t[2],t[3]);join(g,a,b)
            return

def note_rule(g,x,y,s,w=840):return para(g,x,y,s,w,20,True)

def simple_runs(g,x,y,parts,size=26):
    for s,selected in parts:
        w=width(s,size)
        if selected:
            box(g,x-4,y-size+2,w+8,size+8,'none',G,True,4)
        text(g,x,y,s,size,D)
        x+=w
    return x

def simultaneous(g,x,y,before,word,after,size=20):
    t=text(g,500,y,'',size,D,True,'middle')
    for fragment,color in [(before,D),(word,RED),(after,D)]:
        el(t,'tspan',fill=color).text=fragment

def red_arrow(g,x1,y1,x2,y2):
    mid=(y1+y2)/2
    el(g,'path',d=f'M {x1},{y1} C {x1},{mid} {x2},{mid} {x2},{y2}',fill='none',stroke=RED,stroke_width=1.4,marker_end='url(#arrow-red)')

def balance(g,y,left,right,with_addition=False):
    # A level beam and pans show equality; both additions appear on the same level.
    line(g,300,y,700,y,color=M)
    el(g,'path',d=f'M 500,{y} L 475,{y+42} L 525,{y+42} Z',fill='none',stroke=M,stroke_width=1.2)
    for cx,expr in [(300,left),(700,right)]:
        line(g,cx,y,cx-100,y+86,color=G);line(g,cx,y,cx+100,y+86,color=G)
        el(g,'path',d=f'M {cx-100},{y+86} Q {cx},{y+110} {cx+100},{y+86}',fill='none',stroke=M,stroke_width=1.2)
        x=cx-width(expr,26)/2
        if with_addition:
            split=expr.rfind('+ 1')
            text(g,x,y+67,expr[:split],26)
            text(g,x+width(expr[:split],26),y+67,expr[split:],26,RED,True)
        else:text(g,x,y+67,expr,26)

pages=[]
# The preservation principle comes before using it to find x.
r=base(2,'Равенство и равновесие')
g=card(r,154,610,'Как на весах: сохраняем равновесие')
simultaneous(g,80,224,'Прибавляем одно и то же число ','одновременно',' к обеим частям.')
simultaneous(g,80,255,'Вычитаем одно и то же число ','одновременно',' из обеих частей.')
text(g,500,292,'Одно действие — сразу слева и справа.',20,RED,True,'middle')
text(g,300,324,'ЛЕВАЯ ЧАСТЬ',16,B,True,'middle');text(g,700,324,'ПРАВАЯ ЧАСТЬ',16,M,True,'middle')
balance(g,344,'x + 2','5')
text(g,500,480,'ОДНОВРЕМЕННО +1',20,RED,True,'middle')
for cx in (300,700):
    red_arrow(g,450 if cx==300 else 550,487,cx,499)
    text(g,cx,520,'+1',20,RED,True,'middle')
balance(g,540,'x + 2 + 1','5 + 1',True)
para(g,80,686,'При одинаковом действии равновесие сохраняется.',840,20,False,D)
para(g,80,722,'Корень уравнения при этом не изменится.',840,20,True,D)
proofs=[('x + 2 = 5',3,1,'3 + 2 + 1 = 5 + 1','6 = 6','3 + 2 − 1 = 5 − 1','4 = 4'),
        ('x − 2 = 3',5,2,'5 − 2 + 2 = 3 + 2','5 = 5','5 − 2 − 2 = 3 − 2','1 = 1'),
        ('x + 1 = 3',2,3,'2 + 1 + 3 = 3 + 3','6 = 6','2 + 1 − 3 = 3 − 3','0 = 0')]
for y,(original,root,amount,plus,plus_result,minus,minus_result) in zip([784,969,1154],proofs):
    g=card(r,y,170 if y<1154 else 182,f'{original}. Корень — {root}.')
    for cx,eq,result,sgn in [(310,plus,plus_result,'+'),(755,minus,minus_result,'−')]:
        text(g,cx-5,y+65,f'Одновременно {sgn}{amount}',17,RED,True,'middle')
        row=equation(g,eq,y+108,cx);row['accent']=RED;row['stroke_color']='#BE8C87'
        for side in ('L','R'):term(g,row,side,sgn,str(amount),True)
        equation(g,result,y+150,cx)
pages.append((2,r))

# Cancellation is the immediate inverse of the equal-action rule.
r=base(3,'Сначала ищем, что можно убрать')
g=card(r,154,600,'Внутри одной части: противоположные знаки')
para(g,80,224,'Одно и то же число прибавляется и вычитается — пара даёт ноль.',840,20,True,D)
para(g,80,254,'Числа взаимно уничтожаются.',840,20,False,D)
para(g,80,286,'Сначала раскрываем скобки.',840,20,True,D)
para(g,80,314,'Затем смотрим на знаки чисел и убираем пары, которые дают ноль.',840,20,False,D)

def expression(g,s,y,final=False):
    x=500-width(s,26,final)/2
    n=text(g,x,y,s,26,D,final)
    return dict(L=(s,x),R=('',0),y=y,size=26,cx=500,bold=final,
                nodes={'L':n},highlights={'L':[]},frames={'L':[]})

def cancel(g,row,value):
    for sign in ('+','−'):
        a=term(g,row,'L',sign,str(value))
        assert a is not None,(row['L'][0],sign,value)
        strike(g,a[2],row['y'],a[2]+a[4],color=M)

# The child's original case stays as the introduction.
row=expression(g,'75 + 274 − 75',358);cancel(g,row,75)
# Put the short result on the right while keeping the 75 pair clearly visible.
# This equation fragment is deliberately left uncomputed except for the cancelling pair.
line(g,715,350,775,350,arrow=True);text(g,820,358,'274',26,D,True)
text(g,500,394,'75 − 75 = 0',17,M,anchor='middle')
text(g,500,420,'Нам не нужно сначала складывать 75 и 274, а потом вычитать из результата 75.',17,M,anchor='middle')

# Two separated pairs: 73 / −73 and +23 / −23.
row=expression(g,'73 − 283 + 23 − 73 + 15 + 37 − 23',474)
cancel(g,row,73);cancel(g,row,23)
line(g,500,486,500,499,arrow=True)
expression(g,'−283 + 15 + 37',529,True)

# A pair that only appears after the small calculation 18 + 2 = 20.
original=expression(g,'73 − 283 + 18 + 2 − 73 + 15 + 37 − 20',569)
cancel(g,original,73)
line(g,500,581,500,594,arrow=True)
nextrow=expression(g,'−283 + 18 + 2 + 15 + 37 − 20',624)
match=re.search(r'\+ 18 \+ 2',nextrow['L'][0]);a=span(g,nextrow,'L',match.start(),match.end())
reduced=expression(g,'−283 + 20 + 15 + 37 − 20',679)
b=term(g,reduced,'L','+','20');join(g,a,b)
cancel(g,reduced,20)
text(g,90,658,'18 + 2 = 20',17,M)
line(g,500,691,500,704,arrow=True)
expression(g,'−283 + 15 + 37',734,True)
g=card(r,776,560,'Одинаковое число в обеих частях')
para(g,80,847,'Одинаковые числа с одинаковыми знаками можно убрать одновременно из левой и правой частей.',840,20,True,leading=29)
text(g,310,908,'Почему это работает',17,M,anchor='middle')
text(g,755,908,'Короткая запись',17,M,anchor='middle')
long=[equation(g,eq,yy,310) for eq,yy in zip(
    ['x + 12 = 3 + 12','x + 12 − 12 = 3 + 12 − 12','x = 3'],[951,1002,1053])]
for side in ('L','R'):
    long[1]['accent']=RED;long[1]['stroke_color']='#BE8C87'
    term(g,long[1],side,'−','12',True)
    a,b=long[1][side];m=re.search(r'\+ 12 − 12',a)
    span(g,long[1],side,m.start(),m.end(),stroke=False)
    x=b+width(a[:m.start()],26);w=width(a[m.start():m.end()],26)
    strike(g,x,1002,x+w,color=M)
short=equation(g,'x + 12 = 3 + 12',951,755)
short['accent']=RED;short['stroke_color']='#BE8C87'
for side in ('L','R'):
    a=term(g,short,side,'+','12');strike(g,a[2],951,a[2]+a[4],color=RED)
line(g,755,974,755,1010,arrow=True)
equation(g,'x = 3',1053,755,final=True)
para(g,80,1101,'Одновременно вычли 12 из обеих частей.',840,20,True,RED)
line(g,80,1129,920,1129,L)
for yy,eq,result,sg,value,note in [
    (1176,'x − 4 = 9 − 4','x = 9','−','4','К обеим частям одновременно прибавили 4.'),
    (1270,'13 + x = 13 + 5','x = 5','+','13','Из обеих частей одновременно вычли 13.')]:
    row=equation(g,eq,yy,310);row['accent']=RED;row['stroke_color']='#BE8C87'
    for side in ('L','R'):
        a=term(g,row,side,sg,value);strike(g,a[2],yy,a[2]+a[4],color=RED)
    line(g,470,yy-8,535,yy-8,arrow=True)
    equation(g,result,yy,755)
    text(g,500,yy+41,note,17,RED,anchor='middle')
pages.append((3,r))

# Page 4 — the agreed bridge between equal actions and transfer.
r=base(4,'Действия с частями уравнения')
g=card(r,154,350,'Прибавляем или вычитаем одно и то же число')
simultaneous(g,80,222,'К обеим частям ','одновременно',' прибавляем одно и то же число.')
simultaneous(g,80,255,'Из обеих частей ','одновременно',' вычитаем одно и то же число.')
para(g,80,290,'Корень уравнения при этом не изменится.',840,20,False,D)
for cx,eqs,label in [(310,['x − 2 = 6','x − 2 + 2 = 6 + 2','x = 8'],'Прибавим 2 к обеим частям'),(755,['x + 3 = 8','x + 3 − 3 = 8 − 3','x = 5'],'Вычтем 3 из обеих частей')]:
    text(g,cx-15,326,label,17,RED,True,anchor='middle')
    rows=[equation(g,eq,y,cx,26,i==2) for i,(eq,y) in enumerate(zip(eqs,[363,415,469]))]
    for side in ('L','R'):
        p=term(g,rows[1],side,'+' if cx==310 else '−','2' if cx==310 else '3',True)
        if p:curve(g,p[0],rows[0]['y']+12,p[0],p[3]-3)
    pair='− 2 + 2' if cx==310 else '+ 3 − 3';s=rows[1]['L'][0];start=s.index(pair)
    a=span(g,rows[1],'L',start,start+len(pair),stroke=False);strike(g,a[2],rows[1]['y'],a[2]+a[4])
g=card(r,526,490,'Переносим число в другую часть уравнения')
para(g,80,593,'Предыдущее действие можно записать короче.',840,20,False,D)
para(g,80,622,'Слева +3 − 3 дают ноль. Справа появляется −3.',840,20,False,D)
text(g,300,656,'Действие с обеими частями',17,M,anchor='middle');text(g,755,656,'Короткая запись',17,M,anchor='middle')
long=[equation(g,eq,y,310) for eq,y in zip(['x + 3 = 8','x + 3 − 3 = 8 − 3','x = 8 − 3','x = 5'],[700,751,802,853])]
short=[equation(g,eq,y,755) for eq,y in zip(['x + 3 = 8','x = 8 − 3','x = 5'],[700,802,853])]
transition(g,short[0],short[1],'Переносим +3 вправо, меняем знак.')
a=span(g,long[1],'L',2,len(long[1]['L'][0]),stroke=False);strike(g,a[2],751,a[2]+a[4])
para(g,80,905,'Переносим число через знак равенства — меняем его знак.',840,20,True,D)
old=equation(g,'x − 2 = 6',963,310);new=equation(g,'x = 6 + 2',963,755)
a=term(g,old,'L','−','2');b=term(g,new,'R','+','2');line(g,470,953,535,953,arrow=True)
equation(g,'x = 8',999,755)
g=card(r,1038,298,'Меняем левую и правую части местами')
para(g,80,1105,'Левую и правую части уравнения можно поменять местами целиком.',840,20,False,D)
para(g,80,1133,'Знаки внутри них сохраняются.',840,20,False,D)
for yy,a,b in [(1190,'45 = x','x = 45'),(1260,'8 = x + 3','x + 3 = 8')]:
    first=equation(g,a,yy,310);second=equation(g,b,yy,755)
    for row in (first,second):whole(g,row,'L');whole(g,row,'R')
    line(g,470,yy-8,535,yy-8,arrow=True)
pages.append((4,r))
# Page 5 — parentheses and the parent's exact text alongside them.
r=base(5,'Скобки и знаки')
g=card(r,154,513,'Раскрываем скобки')
para(g,80,224,'Перед скобками плюс — убираем скобки, знаки внутри оставляем.',840,20,True,D)
for yy,src,dst in [(277,'x + (4 − 2)','x + 4 − 2'),(328,'9 + (5 − 3)','9 + 5 − 3')]:
    simple_runs(g,150,yy,[(src,False)]);line(g,465,yy-8,535,yy-8,arrow=True);simple_runs(g,600,yy,[(dst,False)])
para(g,55,388,'Перед скобками минус — убираем скобки, каждый знак внутри меняем.',890,20,True,D)
para(g,80,423,'Если перед первым числом внутри скобок знак не написан, это +. При раскрытии скобок он тоже меняется на −.',840,20)
# The two cases differ by the sign inside; the first positive number has no written plus.
for yy,inside,label in [(540,'+','Плюс внутри'),(630,'−','Минус внутри')]:
    text(g,80,yy-42,label,17,M)
    x=145;text(g,x,yy,'x − (',26);x+=width('x − (',26)
    first=x
    simple_runs(g,x,yy,[('4',True),(' ',False),(inside,True),(' 2)',False)])
    second=first+width('4 ',26)
    x2=600;text(g,x2,yy,'x ',26);x2+=width('x ',26)
    dest1=x2;out='−' if inside=='+' else '+'
    simple_runs(g,x2,yy,[('−',True),(' 4 ',False),(out,True),(' 2',False)])
    dest2=dest1+width('− 4 ',26)
    for a,b,h in [(first,dest1,90),(second,dest2,65)]:
        el(g,'path',d=f'M {a+9},{yy-29} C {a+75},{yy-h} {b-65},{yy-h} {b+9},{yy-29}',fill='none',stroke=G,stroke_width=1,marker_end='url(#arrow-blue)')
g=card(r,690,646,'Знак перемещается вместе с числом')
para(g,80,758,'Работаем внутри одной части уравнения — левой или правой.',840,20,True,D)
author=(ROOT/'content/02-signs-DRAFT.md').read_text().split('## Авторский текст\n\n',1)[1].split('\n\n##',1)[0]
y=para(g,80,803,author,840,20,leading=27)
text(g,500,1084,'Одна часть уравнения',17,M,anchor='middle')
for yy,left,right in [
    (1136,[('x ',False),('−3',True),(' + 5',False)],[('x + 5 ',False),('−3',True)]),
    (1203,[('x − 3 ',False),('+5',True)],[('5',True),(' + x − 3',False)]),
    (1270,[('x ',False),('−3',True),(' + 5',False)],[('−3',True),(' + x + 5',False)])]:
    simple_runs(g,220,yy,left);line(g,450,yy-8,520,yy-8,arrow=True);simple_runs(g,570,yy,right)
assert y<1065,('author overflow',y)
pages.append((5,r))

source=(ROOT/'content/07-worked-examples-REVIEW.md').read_text()
heads=list(re.finditer(r'^## Пример (\d+)\. (.+)\n',source,re.M))
examples={}
for i,m in enumerate(heads):
    end=heads[i+1].start() if i+1<len(heads) else source.index('## Статус согласования')
    block=source[m.end():end]
    steps=re.findall(r'^\d+\. `([^`]+)` — (.+)$',block,re.M)
    checks=re.findall(r'^`([^`]+)`$',block,re.M)
    examples[int(m[1])]=(m[2],steps,checks)

def example_height(ex,roomy=False):
    title,steps,checks=ex
    header=len(wrap(title,800,26,True))*32+25
    rows=[max(82 if roomy else 62,len(wrap(a,420,20))*24+18) for eq,a in steps]
    return header+sum(rows)+100,header,rows

def worked(r,num,y,roomy=False):
    ex=examples[num];title,steps,checks=ex;h,header,heights=example_height(ex,roomy)
    g=el(r,'g',id=f'example-{num}');g.set(f'{{{I}}}groupmode','layer');g.set(f'{{{I}}}label',f'Пример {num}')
    box(g,55,y,890,h)
    # Keep every approved title; wrapping changes only line placement.
    for i,s in enumerate(wrap(title,800,26,True)):
        text(g,500,y+35+i*32,s,26,D,True,'middle')
    yy=y+header+24;rows=[]
    for j,((eq,action),rowheight) in enumerate(zip(steps,heights),1):
        text(g,82,yy,str(j),16,B,True,anchor='middle')
        row=equation(g,eq,yy,330,26,j==len(steps));rows.append(row)
        para(g,510,yy-3,action,420,20,leading=24)
        yy+=rowheight
    for j in range(1,len(rows)):
        transition(g,rows[j-1],rows[j],steps[j][1])
    yy=y+h-76
    line(g,80,yy-18,920,yy-18,L)
    text(g,310,yy+8,'Проверка',20,D,True,'middle')
    text(g,720,yy+8,'Подставляем ответ в исходное уравнение.',17,M,anchor='middle')
    checkrow=equation(g,checks[0],yy+45,330,26)
    result=equation(g,checks[1],yy+45,800,26)
    line(g,570,yy+37,645,yy+37,arrow=True)
    # Show x -> found number in the original/check correspondence.
    original=rows[0]
    for side in ('L','R'):
        s=original[side][0]
        if 'x' in s:
            pos=s.index('x');span(g,original,side,pos,pos+1)
            root=steps[-1][0].split('=')[1].strip()
            c=checkrow[side][0]
            # Replacement is at the same character position, including bracket contexts.
            span(g,checkrow,side,pos,pos+len(root))
            break
    return h

pairs=[(1,2),(3,4),(5,6),(7,8),(11,12)]
page=6
for a,b in pairs:
    r=base(page,f'Решаем по шагам · {a} и {b}')
    ha=worked(r,a,151);hb=worked(r,b,151+ha+20)
    assert 151+ha+20+hb<=1346,(a,b,ha,hb)
    pages.append((page,r));page+=1
for num in (9,10):
    r=base(page,f'Если перед x появился минус · {num}')
    h=worked(r,num,151,True);assert h+151<=1346
    pages.append((page,r));page+=1

for n,r in pages:
    E.ElementTree(r).write(str(OUT/f'{n:02}.svg'),xml_declaration=True,encoding='UTF-8')

# A native multipage Inkscape SVG keeps the accepted first-page content; palette changes affect the copy only.
master=E.Element(f'{{{S}}}svg',nsmap=NS,width='210mm',height='297mm',viewBox='0 0 1000 1414',version='1.1')
view=E.SubElement(master,f'{{{N}}}namedview',{'id':'view',f'{{{I}}}document-units':'mm'})
allroots=[E.parse(str(ROOT/'design/01-intro-working.svg')).getroot()]+[r for _,r in pages]
for idx,pr in enumerate(allroots):
    ox=idx*1050
    E.SubElement(view,f'{{{I}}}page',{'x':str(ox),'y':'0','width':'1000','height':'1414','id':f'page-{idx+1}',f'{{{I}}}label':str(idx+1)})
    group=el(master,'g',id=f'page-content-{idx+1}',transform=f'translate({ox},0)')
    group.set(f'{{{I}}}groupmode','layer');group.set(f'{{{I}}}label',f'Страница {idx+1}')
    # Prefix every copied ID and its references to avoid cross-page collisions.
    prefix=f'p{idx+1}-';ids={e.get('id') for e in pr.iter() if e.get('id')}
    for child in pr:
        if E.QName(child).localname in ('namedview','title','desc'):continue
        c=deepcopy(child)
        for e in c.iter():
            for k,v in list(e.attrib.items()):
                if k=='id':e.set(k,prefix+v)
                elif k in ('fill','stroke') and v.lower()=='#177ab0':
                    e.set(k,G if k=='stroke' or E.QName(e).localname=='path' else B)
                elif k in ('fill','stroke') and v.lower()=='#c7d7e1':e.set(k,L)
                elif k=='fill' and v.lower() in ('#f5f8fa','#eff7fc'):e.set(k,F)
                else:
                    for old in ids:
                        v=v.replace(f'url(#{old})',f'url(#{prefix}{old})')
                        if v=='#'+old:v='#'+prefix+old
                    e.set(k,v)
        group.append(c)
E.ElementTree(master).write(str(ROOT/'design/разбор уравнений.svg'),xml_declaration=True,encoding='UTF-8')
print(f'Built {len(allroots)} pages, 12 examples. Accepted first SVG was read only.')

if '--pdf' in __import__('sys').argv:
    import subprocess
    import tempfile
    from pypdf import PdfReader, PdfWriter
    with tempfile.TemporaryDirectory(prefix='easymath-export-') as tmp:
        dest=Path(tmp)/'explanation.pdf'
        subprocess.run(['inkscape',str(ROOT/'design/разбор уравнений.svg'),'--export-page=all','--export-type=pdf',f'--export-filename={dest}'],check=True)
        writer=PdfWriter()
        for n in range(1,len(allroots)+1):
            page=PdfReader(str(Path(tmp)/f'explanation_p{n}.pdf')).pages[0]
            # Cairo rounds exported page bounds; restore exact physical A4 dimensions.
            page.scale_to(595.2755905512,841.8897637795)
            writer.add_page(page)
        writer.add_metadata({'/Title':'Разбор уравнений: правила и 12 пошаговых примеров','/Author':'EasyMath'})
        dest=ROOT/'output/pdf/разбор уравнений.pdf'
        dest.parent.mkdir(parents=True,exist_ok=True)
        writer.write(str(dest))
        print(f'PDF: {dest}')
