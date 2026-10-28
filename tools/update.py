#!/usr/bin/env python3
"""Erzeugt termine.json für „Mein Weg“ aus dem Text-Export des Kalenders.

Aufruf:
  python3 tools/update.py ROHTEXT.txt            → schreibt termine.json + tools/bericht.md, Exit 0 = veröffentlichen
  python3 tools/update.py ROHTEXT.txt --dry-run  → nur Bericht
Exit-Codes: 0 = Änderungen, gültig | 3 = keine Änderungen | 2 = Prüfung fehlgeschlagen (nicht veröffentlichen)
"""
import json, re, sys, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from parse_kalender import parse, zeit

AUSSCHLUSS_CODES = {'KADETTEN'}          # Jugend/Kadetten gehören nicht in die App
BEKANNTE_ORTE = {'Amel','Büllingen','Burg-Reuland','Eupen','Kelmis','Lontzen','Sankt Vith','Amay','Seraing','Juribise',
                 'Francochamps','Aywaille','Raeren','Sektor Nord','Sektor Süd','Operationeller','Sonderteam','Waremme','Andere',
                 'Multidisziplinär','HEMECO','Walhorn auf L3','FW-Schleiden','Hydro','Goldener Morgen'}

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

# Felder, die in der App sichtbar sind oder die Zuordnung bestimmen
FELDER = ['d', 'v', 'b', 't', 'o', 'c', 'k', 'md', 'sq', 'gp', 'n', 'x', 'h', 'a', 'ag']
FELDNAMEN = {'d': 'Datum', 'v': 'Beginn', 'b': 'Ende', 't': 'Titel', 'o': 'Ort', 'c': 'Kategorie', 'k': 'Brevet',
             'md': 'Modul', 'sq': 'Sequenz', 'gp': 'Gruppe', 'n': 'Kursnummer', 'x': 'Status (unbestätigt)', 'h': 'Stunden',
             'a': 'Annulliert', 'ag': 'Grund der Annullierung'}
MIN_TERMINE = 50

def norm(v):
    if v is None or v == '' or v == []: return None
    if isinstance(v, str): return v.strip()
    return v

def inhalt(e):
    return tuple(json.dumps(norm(e.get(f)), ensure_ascii=False, sort_keys=True) for f in FELDER)

def titel_norm(t):
    return re.sub(r'[^a-z0-9äöüß]', '', (t or '').lower())

def unterschiede(a, n):
    return [f for f in FELDER if norm(a.get(f)) != norm(n.get(f))]

def vergleiche(alt, neu):
    """Ordnet alte und neue Termine einander zu.
    1. Identischer Inhalt (alle Felder) → unverändert; Reihenfolge und doppelte Zeilen spielen keine Rolle.
    2. Übrige Termine werden in mehreren Stufen als „derselbe Termin“ erkannt (siehe STUFEN) → geändert.
    3. Was übrig bleibt → neu bzw. entfallen. Mehrere gleich gute Kandidaten → im Bericht als mehrdeutig."""
    from collections import defaultdict
    A = list(range(len(alt))); N = list(range(len(neu)))
    pool = defaultdict(list)
    for j in N: pool[inhalt(neu[j])].append(j)
    rest_a, used_n = [], set()
    for i in A:
        lst = pool.get(inhalt(alt[i]))
        if lst: used_n.add(lst.pop())
        else: rest_a.append(i)
    rest_n = [j for j in N if j not in used_n]
    STUFEN = [
        ('gleicher Tag, gleiche Art, gleicher Titel', lambda e: (e['d'], e['c'], titel_norm(e['t']))),
        ('gleicher Tag, Beginn und Ort', lambda e: (e['d'], zeit(e.get('v') or ''), e.get('o') or '', e['c'])),
        ('gleicher Titel, Beginn und Ort, anderer Tag', lambda e: (titel_norm(e['t']), zeit(e.get('v') or ''), e.get('o') or '', e['c'])),
    ]
    geaendert, mehrdeutig = [], []
    for name, kf in STUFEN:
        idx = defaultdict(list)
        for j in rest_n: idx[kf(neu[j])].append(j)
        noch_a = []
        for i in rest_a:
            kand = [j for j in idx.get(kf(alt[i]), []) if j in rest_n]
            if not kand: noch_a.append(i); continue
            kand.sort(key=lambda j: len(unterschiede(alt[i], neu[j])))
            if len(kand) > 1 and len(unterschiede(alt[i], neu[kand[0]])) == len(unterschiede(alt[i], neu[kand[1]])):
                mehrdeutig.append((alt[i], [neu[j] for j in kand]))
            j = kand[0]; rest_n.remove(j)
            geaendert.append((alt[i], neu[j], unterschiede(alt[i], neu[j]), name))
        rest_a = noch_a
    return {'neu': [neu[j] for j in rest_n], 'entfallen': [alt[i] for i in rest_a], 'geaendert': geaendert,
            'mehrdeutig': mehrdeutig, 'unveraendert': len(used_n)}

def lade_absagen(pfad):
    """Absagen aus Mails der Ausbildungszelle (tools/absagen.json). Liste von Einträgen:
    {"d": "JJJJ-MM-TT", "v": "HH:MM" (optional), "n": Kursnummer (optional), "t": Titelstück (optional),
     "o": Ort (optional), "grund": "mangels Teilnehmer" (optional), "gemeldet": "JJJJ-MM-TT"}
    Rückgabe: (gültige Einträge, Fehler, Hinweise). Kaputte Datei = Fehler; einzelne ungültige Einträge werden übersprungen."""
    if not os.path.exists(pfad): return [], [], []
    try: liste = json.load(open(pfad, encoding='utf-8'))
    except Exception as ex: return [], [f'tools/absagen.json ist kein gültiges JSON: {ex}'], []
    if not isinstance(liste, list): return [], ['tools/absagen.json muss eine Liste sein.'], []
    ok, hinweise = [], []
    for a in liste:
        if not isinstance(a, dict): hinweise.append(f'Ungültige Absage übersprungen: {a!r}'); continue
        try: datetime.date.fromisoformat(a.get('d', ''))
        except Exception: hinweise.append(f"Absage mit ungültigem Datum übersprungen: {a!r}"); continue
        if not (a.get('v') or a.get('n') or a.get('t')):
            hinweise.append(f"Absage am {a['d']} ohne Uhrzeit, Kursnummer oder Titel übersprungen."); continue
        g = a.get('grund') or ''
        if not isinstance(g, str) or len(g) > 120 or re.search(r'@|\d{3}[\s/.]?\d{2}[\s/.]?\d{2}', g):
            hinweise.append(f"Absage am {a['d']} übersprungen: Grund zu lang oder mit Mailadresse/Telefonnummer."); continue
        ok.append(a)
    return ok, [], hinweise

def passt(a, e):
    if e['d'] != a['d']: return False
    if a.get('v') and zeit(e.get('v') or '') != zeit(a['v']): return False
    if a.get('n') and (e.get('n') or '').upper().replace(' ', '') != a['n'].upper().replace(' ', ''): return False
    if a.get('t') and titel_norm(a['t']) not in titel_norm(e['t']): return False
    if a.get('o') and (e.get('o') or '') != a['o']: return False
    return True

def wende_absagen_an(ev, absagen, heute):
    """Markiert abgesagte Termine (a = True, ag = Grund). Nur eindeutige Zuordnungen werden übernommen."""
    angewandt, hinweise = [], []
    for a in absagen:
        kand = [e for e in ev if passt(a, e)]
        beschr = f"{a['d']} {a.get('v', '')} {a.get('t') or a.get('n') or ''}".replace('  ', ' ').strip()
        if len(kand) == 1:
            e = kand[0]; e['a'] = True
            if (a.get('grund') or '').strip(): e['ag'] = a['grund'].strip()
            angewandt.append(e)
        elif not kand:
            if a['d'] >= heute: hinweise.append(f"Absage aus Mail ohne passenden Termin in der Tabelle: {beschr}")
        else:
            hinweise.append(f"Absage aus Mail passt auf {len(kand)} Termine, nicht übernommen: {beschr} → " + ' | '.join(zeile(x) for x in kand))
    return angewandt, hinweise

def pruefen(ev, alt, seen, erg, alt_blaetter=None):
    """Fehler verhindern die Veröffentlichung. Hinweise gelten nur für neue oder geänderte Termine."""
    fehler, hinweise = [], []
    if not any(re.fullmatch(r'\d{4}', s) for s in seen):
        fehler.append('Kein Jahresblatt (z. B. „2026“) gefunden – Quelldatei leer, beschädigt oder unvollständig gelesen.')
    if len([e for e in ev if e['c'] in ('W', 'U')]) == 0:
        fehler.append('Keine Übungen und Weiterbildungen eingelesen – Quelldatei leer oder beschädigt.')
    if len(ev) < MIN_TERMINE:
        fehler.append(f'Nur {len(ev)} Termine eingelesen (Minimum {MIN_TERMINE}) – Quelldatei vermutlich unvollständig.')
    for e in ev:
        try: datetime.date.fromisoformat(e['d'])
        except Exception: fehler.append(f"Ungültiges Datum: {e.get('d')} {e.get('t')}")
        if not (e.get('t') or '').strip(): fehler.append(f"Termin ohne Titel am {e['d']}")
        if e['c'] not in ('L', 'W', 'U'): fehler.append(f"Unbekannte Kategorie „{e['c']}“: {e['d']} {e['t']}")
    if alt_blaetter:
        fehlt = [b for b in alt_blaetter if b not in seen]
        if fehlt: fehler.append(f"Diese Blätter wurden beim letzten Mal gelesen und fehlen jetzt: {', '.join(fehlt)}. Nicht veröffentlicht.")
    if alt:
        weg = len(alt) - len(ev)
        if weg > max(20, len(alt) * 0.10):
            fehler.append(f"Es fehlen plötzlich {weg} von {len(alt)} Terminen – möglicherweise falsch eingelesen. Nicht veröffentlicht.")
        for c, name in (('L', 'Laufbahn'), ('W', 'Weiterbildung'), ('U', 'Übungen')):
            a = sum(1 for e in alt if e['c'] == c); n = sum(1 for e in ev if e['c'] == c)
            if a - n > max(10, a * 0.25):
                fehler.append(f"Bei „{name}“ fehlen plötzlich {a - n} von {a} Terminen. Nicht veröffentlicht.")
        if len(ev) - len(alt) > max(25, len(alt) * 0.3):
            hinweise.append(f"Ungewöhnlich viele neue Termine: {len(ev) - len(alt)} (vorher {len(alt)}). Bitte prüfen.")
    betroffen = erg['neu'] + [g[1] for g in erg['geaendert']]
    zaehl = {}
    for e in ev: zaehl[inhalt(e)] = zaehl.get(inhalt(e), 0) + 1
    for e in betroffen:
        if e['c'] == 'L' and not e.get('md'): hinweise.append(f"Laufbahntermin ohne Modul: {e['d']} {e['t']} → in der App „Modul noch nicht zugeordnet“")
        if e.get('o') and e['o'] not in BEKANNTE_ORTE: hinweise.append(f"Unbekannter Ort „{e['o']}“: {e['d']} {e['t']}")
        if zaehl.get(inhalt(e), 0) > 1: hinweise.append(f"Mögliche Dublette (Zeile steht mehrfach in der Quelle): {e['d']} {e.get('v','')} {e['t']} ({e.get('o','')})")
    return fehler, hinweise

def zeile(e):
    return f"{e['d']} {e.get('v','') or ''} {e['t']} ({e.get('o','') or ''})".replace('  ', ' ')

def bericht(ev, alt, seen, erg, fehler, hinweise, heute, annulliert=()):
    dub = sum(c - 1 for c in __import__('collections').Counter(inhalt(e) for e in ev).values() if c > 1)
    b = [f"# Abgleich Mein Weg – {heute}", f"Gelesene Blätter: {', '.join(seen) or '–'}",
         f"Termine: {len(ev)} (vorher {len(alt)}) · unverändert {erg['unveraendert']} · neu {len(erg['neu'])} · geändert {len(erg['geaendert'])} · entfallen {len(erg['entfallen'])} · mehrfach vorhandene Zeilen {dub}", '']
    if fehler: b += ['## FEHLER – nicht veröffentlicht'] + [f'- {x}' for x in fehler] + ['']
    if erg['neu']: b += ['## Neu'] + [f'- {zeile(e)}' for e in erg['neu'][:80]] + ['']
    if erg['geaendert']:
        b += ['## Geändert']
        for a, n, fs, wie in erg['geaendert'][:80]:
            det = '; '.join(f"{FELDNAMEN[f]}: {norm(a.get(f))!s} → {norm(n.get(f))!s}" for f in fs)
            b.append(f'- {zeile(n)}: {det}')
        b.append('')
    if erg['entfallen']: b += ['## Entfallen'] + [f'- {zeile(e)}' for e in erg['entfallen'][:80]] + ['']
    if erg['mehrdeutig']:
        b += ['## Mehrdeutige Zuordnung (bitte prüfen)'] + [f"- {zeile(a)} → {len(k)} mögliche Termine: " + ' | '.join(zeile(x) for x in k) for a, k in erg['mehrdeutig']] + ['']
    if annulliert: b += ['## Als annulliert gekennzeichnet (aus Mails)'] + [f"- {zeile(e)}" + (f" – {e['ag']}" if e.get('ag') else '') for e in annulliert] + ['']
    if hinweise: b += ['## Hinweise zur Prüfung'] + [f'- {x}' for x in sorted(set(hinweise))] + ['']
    return '\n'.join(b)

def schreibe_atomar(pfad, text):
    tmp = pfad + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: f.write(text)
    os.replace(tmp, pfad)

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    dry = '--dry-run' in argv
    ziel = ROOT
    if '--ziel' in argv: ziel = argv[argv.index('--ziel') + 1]
    rohpfad = [a for a in argv if not a.startswith('--') and a != ziel][0]
    heute = os.environ.get('MEINWEG_HEUTE') or datetime.date.today().isoformat()
    pfad = os.path.join(ziel, 'termine.json')
    altj = json.load(open(pfad, encoding='utf-8')) if os.path.exists(pfad) else {}
    alt = altj.get('termine', []); alt_blaetter = altj.get('blaetter')
    try:
        raw = open(rohpfad, encoding='utf-8').read()
        ev, seen = build(raw)
    except Exception as ex:
        ev, seen = [], []
        fehler0 = [f'Quelldatei konnte nicht gelesen werden: {ex}']
    else:
        fehler0 = []
    absagen, fehler_abs, hinweise_abs = lade_absagen(os.path.join(ziel, 'tools', 'absagen.json'))
    annulliert, h2 = wende_absagen_an(ev, absagen, heute)
    hinweise_abs += h2
    erg = vergleiche(alt, ev)
    fehler, hinweise = pruefen(ev, alt, seen, erg, alt_blaetter)
    fehler = fehler0 + fehler_abs + fehler
    hinweise += hinweise_abs
    text = bericht(ev, alt, seen, erg, fehler, hinweise, heute, [e for e in annulliert if e['d'] >= heute])
    schreibe_atomar(os.path.join(ziel, 'tools', 'bericht.md') if os.path.isdir(os.path.join(ziel, 'tools')) else os.path.join(ziel, 'bericht.md'), text)
    print(text)
    if fehler: return 2
    if not erg['neu'] and not erg['geaendert'] and not erg['entfallen'] and (alt_blaetter is not None or not alt): return 3
    if not dry:
        schreibe_atomar(pfad, json.dumps({'stand': heute, 'quelle': 'Übungs-Weiterbildungskalender.xlsx (SharePoint HLZ DG), Stundenpläne NB01 und NM-02',
                                          'blaetter': seen, 'termine': ev}, ensure_ascii=False, separators=(',', ':')))
    return 0

if __name__ == '__main__':
    sys.exit(main())
