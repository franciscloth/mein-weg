#!/usr/bin/env python3
"""Erzeugt termine.json für „Mein Weg“ aus dem Text-Export des Kalenders.

Aufruf:
  python3 tools/update.py ROHTEXT.txt            → schreibt termine.json + tools/bericht.md, Exit 0 = veröffentlichen
  python3 tools/update.py ROHTEXT.txt --dry-run  → nur Bericht
Exit-Codes: 0 = Änderungen, gültig | 3 = keine Änderungen | 2 = Prüfung fehlgeschlagen (nicht veröffentlichen)
"""
import json, re, sys, os, datetime, difflib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from parse_kalender import parse, zeit

AUSSCHLUSS_CODES = {'KADETTEN'}          # Jugend/Kadetten gehören nicht in die App
BEKANNTE_ORTE = {'Amel','Büllingen','Burg-Reuland','Eupen','Kelmis','Lontzen','Sankt Vith','Amay','Seraing','Juribise',
                 'Francochamps','Aywaille','Raeren','Sektor Nord','Sektor Süd','Operationeller','Sonderteam','Waremme','Andere'}

def key(d, v, t):
    return f"{d}|{zeit(v or '')}|{re.sub(r'[^a-z0-9]', '', (t or '').lower())[:40]}"

def ableiten(e):
    if e['c'] != 'L':
        for f in ('md', 'sq', 'gp', 'ms'): e.pop(f, None)
        return e
    s = re.search(r'Sequenz\s+(\d+)', e['t']); e['sq'] = f'Sequenz {s.group(1)}' if s else ''
    g = re.search(r'Gruppe\s*(\d+)', e['t'], re.I); e['gp'] = f'Gruppe {g.group(1)}' if g else ''
    e.setdefault('md', [])
    return e

def build(raw):
    ev, seen = parse(raw)
    ev = [e for e in ev if not (e['n'] or '').upper().replace(' ', '') in AUSSCHLUSS_CODES]
    # Rohtitel merken (für Korrekturen)
    for e in ev: e['_k'] = key(e['d'], e['v'], e['t'])
    ov = json.load(open(os.path.join(HERE, 'korrekturen.json'), encoding='utf-8'))
    for e in ev:
        if e['_k'] in ov: e.update(ov[e['_k']])
    static = json.load(open(os.path.join(HERE, 'feste_termine.json'), encoding='utf-8'))
    out = []
    for e in ev + static:
        e = {k: v for k, v in e.items() if not k.startswith('_') and k != 'src'}
        if e.get('h') is None: e.pop('h', None)
        out.append(ableiten(e))
    out.sort(key=lambda e: (e['d'], zeit(e.get('v') or ''), e['t']))
    return out, seen

def pruefen(ev, alt):
    fehler, hinweise = [], []
    for e in ev:
        try: datetime.date.fromisoformat(e['d'])
        except Exception: fehler.append(f"Ungültiges Datum: {e}")
        if not e['t'].strip(): fehler.append(f"Termin ohne Titel am {e['d']}")
        if e['c'] == 'L' and not e.get('md'): hinweise.append(f"Laufbahntermin ohne Modul: {e['d']} {e['t']} → in der App „Modul noch nicht zugeordnet“")
        if e.get('o') and e['o'] not in BEKANNTE_ORTE: hinweise.append(f"Unbekannter Ort „{e['o']}“: {e['d']} {e['t']}")
    if alt:
        weg = len(alt) - len(ev)
        if weg > max(25, len(alt) * 0.15):
            fehler.append(f"Es fehlen plötzlich {weg} von {len(alt)} Terminen – möglicherweise falsch eingelesen. Nicht veröffentlicht.")
    return fehler, hinweise

def diff(alt, neu):
    k = lambda e: (e['d'], zeit(e.get('v') or ''), e['t'], e.get('o', ''))
    A, N = {k(e): e for e in alt}, {k(e): e for e in neu}
    return [N[x] for x in N if x not in A], [A[x] for x in A if x not in N]

def main():
    raw = open(sys.argv[1], encoding='utf-8').read()
    dry = '--dry-run' in sys.argv
    ev, seen = build(raw)
    pfad = os.path.join(ROOT, 'termine.json')
    alt = json.load(open(pfad, encoding='utf-8'))['termine'] if os.path.exists(pfad) else []
    fehler, hinweise = pruefen(ev, alt)
    neu, weg = diff(alt, ev)
    heute = datetime.date.today().isoformat()
    b = [f"# Abgleich Mein Weg – {heute}", f"Gelesene Blätter: {', '.join(seen)}", f"Termine: {len(ev)} (vorher {len(alt)})",
         f"Neu oder geändert: {len(neu)}", f"Entfallen oder geändert: {len(weg)}", '']
    if fehler: b += ['## FEHLER – nicht veröffentlicht'] + [f'- {x}' for x in fehler] + ['']
    if neu: b += ['## Neu / geändert'] + [f"- {e['d']} {e.get('v','')} {e['t']} ({e.get('o','')})" for e in neu[:60]] + ['']
    if weg: b += ['## Entfallen / vorher'] + [f"- {e['d']} {e.get('v','')} {e['t']} ({e.get('o','')})" for e in weg[:60]] + ['']
    if hinweise: b += ['## Hinweise zur Prüfung'] + [f'- {x}' for x in sorted(set(hinweise))] + ['']
    open(os.path.join(HERE, 'bericht.md'), 'w', encoding='utf-8').write('\n'.join(b))
    print('\n'.join(b))
    if fehler: sys.exit(2)
    if not neu and not weg: sys.exit(3)
    if not dry:
        json.dump({'stand': heute, 'quelle': 'Übungs-Weiterbildungskalender.xlsx (SharePoint HLZ DG), Stundenpläne NB01 und NM-02',
                   'termine': ev}, open(pfad, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    sys.exit(0)

if __name__ == '__main__':
    main()
