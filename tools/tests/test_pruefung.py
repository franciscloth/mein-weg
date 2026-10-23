#!/usr/bin/env python3
"""Gegenproben für tools/pruefe_veroeffentlichung.py: die Prüfung muss bei Problemen anschlagen."""
import os, sys, json, shutil, tempfile, unittest, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(HERE); ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

class Pruefung(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        for f in ('index.html', 'termine.json'): shutil.copy(os.path.join(ROOT, f), self.dir)
        os.environ['MEINWEG_ROOT'] = self.dir
        import importlib, pruefe_veroeffentlichung; self.p = importlib.reload(pruefe_veroeffentlichung)
    def tearDown(self):
        shutil.rmtree(self.dir); os.environ.pop('MEINWEG_ROOT', None)
    def lauf(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out: rc = self.p.main(['x', *args])
        return rc, out.getvalue()
    def aendere(self, f, alt, neu):
        p = os.path.join(self.dir, f); t = open(p, encoding='utf-8').read(); assert alt in t; open(p, 'w', encoding='utf-8').write(t.replace(alt, neu, 1))
    def test_aktueller_stand_ok(self):
        self.assertEqual(self.lauf()[0], 0)
    def test_json_und_html_verschieden(self):
        j = json.load(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8')); j['termine'][0]['t'] += ' X'
        json.dump(j, open(os.path.join(self.dir, 'termine.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        rc, out = self.lauf(); self.assertEqual(rc, 1); self.assertIn('weichen von termine.json ab', out)
    def test_stand_verschieden(self):
        j = json.load(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8')); j['stand'] = '2099-01-01'
        json.dump(j, open(os.path.join(self.dir, 'termine.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        self.assertEqual(self.lauf()[0], 1)
    def test_fremde_mailadresse(self):
        self.aendere('index.html', 'ausbildungszelle@hlzdg.be', 'max.muster@example.com')
        rc, out = self.lauf(); self.assertEqual(rc, 1); self.assertIn('max.muster@example.com', out)
    def test_ausbildername_aus_quelle(self):
        raw = os.path.join(self.dir, 'raw.txt')
        open(raw, 'w', encoding='utf-8').write('## Sheet: 2026 — 2 rows\nDatum\tTyp\tVerantwortlicher Ausbilder\nsamedi 1 mai 2027\tÜbung\tMustermann Erika\n')
        self.assertEqual(self.lauf(raw)[0], 0)
        self.aendere('termine.json', '"t":"', '"t":"Mustermann Erika ')
        self.aendere('index.html', '"t":"', '"t":"Mustermann Erika ')
        rc, out = self.lauf(raw); self.assertEqual(rc, 1); self.assertIn('Mustermann Erika', out)
    def test_platzhalter(self):
        self.aendere('index.html', '<title>', '<title>__DATA__')
        self.assertEqual(self.lauf()[0], 1)
    def test_kaputtes_skript(self):
        self.aendere('index.html', 'function renderWeg(){', 'function renderWeg(){{')
        self.assertEqual(self.lauf()[0], 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)
