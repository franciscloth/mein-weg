"""Einmalig: Korrekturen aus den geprüften App-Daten (Loop 1–3) ableiten."""
import json,difflib,sys,os
H=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,H)
from parse_kalender import parse,zeit
from update import key
ev,_=parse(open(sys.argv[1]).read())
ev=[e for e in ev if (e['n'] or '').upper()!='KADETTEN']
B=json.load(open(sys.argv[2]))
from collections import defaultdict
P=defaultdict(list)
for i,e in enumerate(ev): P[(e['d'],e['v'])].append(i)
used={};static=[];ov={}
for b in B:
    cands=[i for i in P[(b['d'],zeit(b.get('v') or ''))] if i not in used]
    if not cands:
        if b['t'].strip(): static.append({k:v for k,v in b.items() if k not in('ms','sq','gp')})
        continue
    i=max(cands,key=lambda i:difflib.SequenceMatcher(None,ev[i]['t'],b['t']).ratio()+(ev[i]['o']==b.get('o'))+(ev[i]['c']==b['c']))
    used[i]=b;e=ev[i];d={}
    for f in ('t','o','c','k','x','md'):
        if f=='md' and b['c']!='L': continue
        bv=b.get(f);ev_v=e.get(f)
        if bv!=ev_v and not (f in('o','k') and (bv or '')==(ev_v or '')): d[f]=bv
    if b['c']=='L' and (b.get('n') or '')=='' and e['n']: d['n']=''
    for f in ('v','b'):
        if zeit(b.get(f) or '')!=e[f]: d[f]=zeit(b.get(f) or '')
    if d: ov[key(e['d'],e['v'],e['t'])]=d
json.dump(ov,open(os.path.join(H,'korrekturen.json'),'w'),ensure_ascii=False,indent=1)
json.dump(static,open(os.path.join(H,'feste_termine.json'),'w'),ensure_ascii=False,indent=1)
print(len(ov),'Korrekturen;',len(static),'feste Termine')
