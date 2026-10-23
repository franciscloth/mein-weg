#!/usr/bin/env python3
"""Baut index.html aus tools/app_vorlage.html und termine.json (Termine werden zusätzlich eingebaut, falls termine.json nicht lädt)."""
import json, os
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(H)
t = open(os.path.join(H, 'app_vorlage.html'), encoding='utf-8').read()
j = json.load(open(os.path.join(R, 'termine.json'), encoding='utf-8'))
L = json.load(open(os.path.join(H, 'logo.json')))
out = t.replace('__DATA__', json.dumps(j['termine'], ensure_ascii=False, separators=(',', ':'))).replace('__STAND__', j['stand'])
for k in ['FAV', 'ICON', 'EMB', 'FULL']: out = out.replace(f'__{k}__', L[k.lower()])
assert '__DATA__' not in out and '__STAND__' not in out
tmp = os.path.join(R, 'index.html.tmp')
open(tmp, 'w', encoding='utf-8').write(out)
os.replace(tmp, os.path.join(R, 'index.html'))  # atomar: nie eine halb geschriebene Datei
print('index.html', len(out))
