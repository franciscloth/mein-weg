#!/usr/bin/env python3
"""Prüft vor jeder Veröffentlichung, ob die öffentlichen Dateien stimmig und unbedenklich sind.

Aufruf:
  python3 tools/pruefe_veroeffentlichung.py                 → Prüfung ohne Rohdaten (z. B. in GitHub Actions)
  python3 tools/pruefe_veroeffentlichung.py tools/raw.txt   → zusätzlich: kein Name aus den Ausbilderspalten der Quelle
Exit 0 = in Ordnung, Exit 1 = nicht veröffentlichen.

Öffentlich sind nur index.html und termine.json (GitHub Actions veröffentlicht nur diese beiden Dateien)."""
import json, os, re, subprocess, sys, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.environ.get('MEINWEG_ROOT') or os.path.dirname(HERE)
OEFFENTLICH = ['index.html', 'termine.json']
# Liegt im (öffentlichen) Repository, wird aber nicht veröffentlicht: gleiche Datenschutzprüfung
IM_REPOSITORY = ['tools/absagen.json']
ERLAUBTE_MAILS = {'ausbildungszelle@hlzdg.be'}

def eingebettet(html):
    m = re.search(r'let EVENTS=(\[.*?\]);let STAND=\'(\d{4}-\d{2}-\d{2})\';', html, re.S)
    if not m: return None, None
    return json.loads(m.group(1)), m.group(2)

def ausbildernamen(raw):
    """Namen aus den Ausbilderspalten der Quelle (Jahresblätter: Spalten ab „Verantwortlicher Ausbilder“; Stundenplan NB01: Hauptausbilder, 2. Ausbilder)."""
    namen, spalten = set(), []
    for line in raw.split('\n'):
        if line.startswith('## Sheet:'): spalten = []; continue
        c = line.split('\t')
        if c and c[0].strip() == 'Datum':
            spalten = [i for i, h in enumerate(c) if re.search(r'Ausbilder|Fahrer|Logistik|Lehrbeauftragt', h, re.I)]
            continue
        for i in spalten:
            if i < len(c):
                for teil in re.split(r'[/+,;]| - |\(|\)', c[i]):
                    teil = re.sub(r'^(O\.|Lt\.|Sgt\.|Adj\.|Kpt\.|Animator:|Operator:|reserve|Reserve)\s*', '', teil.strip())
                    if len(teil) >= 6 and re.search(r'[A-Za-zÀ-ÿ]{3,}\s+[A-Za-zÀ-ÿ]{3,}', teil) and not re.search(r'CFBT|Francochamps|Plan|Zone|HLZ|Ausbilder', teil):
                        namen.add(teil)
    return namen

def main(argv):
    fehler = []
    pfade = {f: os.path.join(ROOT, f) for f in OEFFENTLICH}
    for f, p in pfade.items():
        if not os.path.exists(p): fehler.append(f'{f} fehlt')
    if fehler: return melden(fehler)
    html = open(pfade['index.html'], encoding='utf-8').read()
    tj = json.load(open(pfade['termine.json'], encoding='utf-8'))
    ev, stand = eingebettet(html)
    # 1. JSON und eingebaute Rückfallkopie gleich
    if ev is None: fehler.append('In index.html wurden keine eingebauten Termine gefunden.')
    else:
        if ev != tj.get('termine'): fehler.append('Die in index.html eingebauten Termine weichen von termine.json ab.')
        if stand != tj.get('stand'): fehler.append(f'Datenstand verschieden: index.html {stand}, termine.json {tj.get("stand")}.')
    # 2. Grundprüfung der Daten
    t = tj.get('termine') or []
    if len(t) < 50: fehler.append(f'termine.json enthält nur {len(t)} Termine.')
    for e in t:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', e.get('d', '')) or not e.get('t') or e.get('c') not in ('L', 'W', 'U'):
            fehler.append(f'Ungültiger Termin: {e}'); break
        if 'a' in e and not isinstance(e['a'], bool): fehler.append(f'Ungültige Annullierung: {e}'); break
    # 3. Keine Platzhalter, Skript lauffähig
    if re.search(r'__(DATA|STAND|FAV|ICON|EMB|FULL|CSS)__', html): fehler.append('index.html enthält noch Platzhalter.')
    if shutil.which('node'):
        s = html.rindex('<script>'); e = html.rindex('</script>')
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f: f.write(html[s + 8:e]); js = f.name
        r = subprocess.run(['node', '--check', js], capture_output=True, text=True); os.unlink(js)
        if r.returncode: fehler.append('Syntaxfehler im Skript von index.html: ' + r.stderr.strip()[:300])
    # 4. Datenschutz: keine fremden Mailadressen, keine Telefonnummern, keine Ausbildernamen
    pruef = dict(pfade)
    for f in IM_REPOSITORY:
        if os.path.exists(os.path.join(ROOT, f)): pruef[f] = os.path.join(ROOT, f)
    for f, p in pruef.items():
        text = open(p, encoding='utf-8').read()
        ohne_bilder = re.sub(r'data:image/[a-z]+;base64,[A-Za-z0-9+/=]+', '', text)
        for m in set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', ohne_bilder)):
            if m.lower() not in ERLAUBTE_MAILS: fehler.append(f'{f}: Mailadresse „{m}“ ist nicht zur Veröffentlichung vorgesehen.')
        for m in set(re.findall(r'(?<![\d.])(?:\+32|0032|0)\s?\d{2,3}(?:[\s/.]?\d{2}){3}(?![\d])', ohne_bilder)):
            fehler.append(f'{f}: mögliche Telefonnummer „{m}“.')
        if len(argv) > 1:
            for n in ausbildernamen(open(argv[1], encoding='utf-8').read()):
                if n in ohne_bilder: fehler.append(f'{f}: enthält einen Namen aus den Ausbilderspalten („{n}“).')
    # 5. Rohdaten nie im Repository
    try:
        r = subprocess.run(['git', '-C', ROOT, 'ls-files'], capture_output=True, text=True)
        for f in r.stdout.split():
            if re.search(r'(^|/)raw[^/]*\.txt$|bericht\.md$', f): fehler.append(f'Datei {f} darf nicht im Repository liegen.')
    except Exception: pass
    return melden(fehler)

def melden(fehler):
    if fehler:
        print('NICHT VERÖFFENTLICHEN:'); [print(' -', x) for x in fehler]; return 1
    print('Veröffentlichungsprüfung bestanden.'); return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
