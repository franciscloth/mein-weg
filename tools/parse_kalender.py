#!/usr/bin/env python3
"""Liest den Text-Export der Datei „Übungs-Weiterbildungskalender.xlsx“ (Microsoft-365-Connector)
und erzeugt daraus Rohtermine. Ausbildernamen werden nie übernommen.

Verarbeitete Blätter:
  * Jahresblätter („2026“, „2027“ …): Übungen, Weiterbildungen, Laufbahnkurse mit Kursnummer
  * Stundenpläne „NB01 JJJJ-JJJJ“: Grundausbildung mit Spalte „Modul“
Andere Blätter (z. B. „NB02 - Korporal 2026“) werden nicht automatisch gelesen.
"""
import re, sys, json, datetime

MIN_JAHR = 2026
MO = {'janvier':1,'février':2,'fevrier':2,'mars':3,'avril':4,'mai':5,'juin':6,'juillet':7,'août':8,'aout':8,
      'septembre':9,'octobre':10,'novembre':11,'décembre':12,'decembre':12,
      'januar':1,'februar':2,'märz':3,'april':4,'juni':6,'juli':7,'august':8,'september':9,'oktober':10,'november':11,'dezember':12}
ORTE = {'sv':'Sankt Vith','sankt vith':'Sankt Vith','st.vith':'Sankt Vith','st. vith':'Sankt Vith','eupen':'Eupen','kelmis':'Kelmis',
        'büllingen':'Büllingen','amel':'Amel','lontzen':'Lontzen','burg-reuland':'Burg-Reuland','br':'Burg-Reuland','amay':'Amay',
        'seraing':'Seraing','juribise':'Juribise','francochamps':'Francochamps','aywaille':'Aywaille','operationeller':'Sonderteam','/':'','-':''}
POSTEN = ['Amel','Büllingen','Burg-Reuland','Eupen','Kelmis','Lontzen','Sankt Vith','Amay','Seraing','Andere']

def datum(s):
    s = (s or '').strip()
    if not s: return None
    if re.fullmatch(r'\d{5}', s):  # Excel-Seriennummer
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(s))).isoformat()
    m = re.search(r'(\d{1,2})[.\s]+([A-Za-zÀ-ÿ]+)\s+(\d{4})', s)
    if m and m.group(2).lower() in MO:
        return datetime.date(int(m.group(3)), MO[m.group(2).lower()], int(m.group(1))).isoformat()
    return None

def zeit(s):
    s = (s or '').strip().replace('h', ':').replace('.', ':')
    if not s: return ''
    if re.fullmatch(r'0?,\d+|0', s):  # Tagesbruchteil aus Excel
        mins = round(float(s.replace(',', '.')) * 1440)
        return f'{mins//60:02d}:{mins%60:02d}'
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(?::\d{2})?', s)
    return f'{int(m.group(1)):02d}:{m.group(2)}' if m else ''

def stunden(s):
    s = (s or '').strip().replace('h', ':')
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(?::\d{2})?', s)
    if m: return round(int(m.group(1)) + int(m.group(2)) / 60, 2)
    if re.fullmatch(r'0?,\d+', s): return round(float(s.replace(',', '.')) * 24, 2)
    return None

def ort(s):
    s = re.sub(r'\s+', ' ', (s or '').strip())
    return ORTE.get(s.lower(), s)

def blaetter(text):
    out, name, rows = [], None, []
    for line in text.split('\n'):
        m = re.match(r'^## Sheet: (.+?) — ', line)
        if m:
            if name: out.append((name, rows))
            name, rows = m.group(1), []
        elif name is not None:
            if line.startswith('Formulas:'):
                out.append((name, rows)); name = None; continue
            rows.append(line.split('\t'))
    if name: out.append((name, rows))
    return out

def kurs_info(code, name):
    """Laufbahnkurse an der Kursnummer erkennen: NM01xx (Sergeant), NB02 (Korporal), NOFF1 (Leutnant), NM02 (Adjutant)."""
    c = code.upper().replace(' ', '')
    md = []
    if c.startswith('NM01'):
        k = 'NMO1'
        rest = c[4:].lstrip('/')
        md = sorted({int(x) for x in re.findall(r'\d+', rest)})
    elif c.startswith('NM02'): k = 'NMO2'
    elif c.startswith('NB02'): k = 'BO2'
    elif c.startswith('NOFF1'): k = 'NOFF1'
    elif c.startswith('NB01'): k = 'NBO1'
    else: return None, []
    if not md:
        m = re.search(r'Modul(?:e)?\s+(\d+)(?:\s*[-+]\s*(\d+))?', name)
        if m:
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
            md = list(range(a, b + 1)) if b >= a else [a]
    return k, md

def jahresblatt(rows):
    ev, hdr = [], None
    for r in rows:
        if r and r[0].strip() == 'Datum': hdr = [h.strip() for h in r]; continue
        if not hdr: continue
        d = datum(r[0] if r else '')
        if not d: continue
        g = lambda i: r[i].strip() if i < len(r) else ''
        typ, code, name = g(1), g(2), re.sub(r'\s+', ' ', g(3)).strip()
        if not name: continue
        x = bool(re.search(r'zu bestätigen|à confirmer|\?\?', name, re.I))
        name = re.sub(r'!?\s*Termin zu bestätigen\s*!?', '', name, flags=re.I).strip()
        k, md = kurs_info(code, name)
        c = 'L' if k else ('U' if 'Übung' in typ else 'W' if 'Weiterbildung' in typ else '')
        if not c: continue
        o = ort(g(4))
        if not o:
            posts = [POSTEN[i] for i in range(10) if g(9 + i).lower() == 'x']
            if len(posts) == 1: o = posts[0]
        # Kursnummer nur für Kurse mit Anmeldung (Weiterbildung, Laufbahn); Übungen haben keine
        n = ''
        if c == 'W' and code.strip() and code.strip().lower() not in ('zonal', 'intern', 'csa'):
            n = re.sub(r'^(AT)\s+(\d)', r'\1\2', re.sub(r'\s+', ' ', code.strip().upper()))
        if c == 'L':
            n = code.strip().upper().replace(' ', '')
            if k == 'NMO1' and md: n = 'NM01/' + '/'.join(f'{m:02d}' for m in md)
            pre = {'NMO1': 'Sergeant (NMO1) – ', 'NOFF1': 'Leutnant (NOFF1) – ', 'NMO2': 'Adjutant (NMO2) – '}.get(k, '')
            if pre and not re.match(r'(Sergeant|Leutnant|Adjutant|Korporal)', name): name = pre + name
        v, b = zeit(g(5)), zeit(g(6))
        h = stunden(g(8))
        if not h and v and b:  # fehlende Stundenzahl: Ende − Anfang − Pause
            p = stunden(g(7)) or 0
            h = round((int(b[:2]) * 60 + int(b[3:]) - int(v[:2]) * 60 - int(v[3:])) / 60 - p, 2) or None
        ev.append(dict(d=d, c=c, k=k or '', t=name, o=o, v=v, b=b, h=h, x=x, n=n, md=md,
                       src='Kalender'))
    return ev

def nb01blatt(rows):
    """Stundenplan Grundausbildung: Spalten Datum, Anfang, Ende, Stunden, Sequenz, Modul, Type, Einheit, h/H, Titel, Ort."""
    raw = []
    for r in rows:
        g = lambda i: r[i].strip() if i < len(r) else ''
        d = datum(g(0))
        m = re.match(r'Modul\s+(\d+)(?:\s*\+\s*(\d+))?', g(5))
        if not d or not m: continue
        md = [int(x) for x in m.groups() if x]
        raw.append(dict(d=d, md=md, v=zeit(g(1)), b=zeit(g(2)), titel=re.sub(r'\s+', ' ', g(9)).strip(),
                        art=g(8), o=ort(g(10))))
    # Halbtage desselben Moduls am selben Tag und Ort zu einem Termin zusammenfassen
    grp = {}
    for x in raw:
        grp.setdefault((x['d'], tuple(x['md']), x['o']), []).append(x)
    ev = []
    for (d, md, o), xs in grp.items():
        v = min((x['v'] for x in xs if x['v']), default=''); b = max((x['b'] for x in xs if x['b']), default='')
        titel = ', '.join(dict.fromkeys(x['titel'] for x in xs if x['titel']))
        mtxt = 'Module ' + ' + '.join(map(str, md)) if len(md) > 1 else f'Modul {md[0]}'
        ev.append(dict(d=d, c='L', k='NBO1', t=f'Grundausbildung NB01 – {mtxt}: {titel}'.rstrip(': '), o=o, v=v, b=b,
                       h=None, x=False, n='', md=list(md), src='Stundenplan NB01'))
    return ev

def parse(text):
    ev, seen = [], []
    for name, rows in blaetter(text):
        if re.fullmatch(r'\d{4}', name.strip()) and int(name) >= MIN_JAHR:
            ev += jahresblatt(rows); seen.append(name)
        elif re.fullmatch(r'NB01 (\d{4})-(\d{4})', name.strip()) and int(name.strip()[-4:]) >= MIN_JAHR:
            ev += nb01blatt(rows); seen.append(name)
    return ev, seen

if __name__ == '__main__':
    ev, seen = parse(open(sys.argv[1], encoding='utf-8').read())
    print(json.dumps({'blaetter': seen, 'anzahl': len(ev)}, ensure_ascii=False))
