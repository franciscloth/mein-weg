#!/usr/bin/env python3
"""Regressionstests für tools/update.py (Abgleich der Kalenderdaten).
Aufruf: python3 -m unittest discover -s tools/tests -v
Die Tests arbeiten mit künstlichen Quelldaten in einem temporären Ordner; das Repository bleibt unberührt."""
import os, sys, json, shutil, tempfile, unittest, re
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import update

KOPF = 'Datum\tTyp\tNUMMER Übungszyklus\tName\tBemerkung\tAnfang\tEnde\tPause\tAnzahl Stunden\tAmel\tBüllingen\tBurg-Reuland\tEupen\tKelmis\tLontzen\tSankt Vith\tAmay\tSeraing\tAndere\tVerantwortlicher Ausbilder'
MONATE = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']

def basiszeilen():
    """60 Übungen/Weiterbildungen + 2 Laufbahntermine (NMO1 Modul 5) im Jahresblatt."""
    z = []
    for i in range(60):
        tag, mon = i % 27 + 1, i % 12
        typ = 'Übung' if i % 2 else 'Weiterbildung'
        code = 'intern' if i % 2 else f'AT{7100 + i}'
        z.append(f'samedi {tag} {MONATE[mon]} 2027\t{typ}\t{code}\tThema {i}\tEupen\t19:00\t21:00\t00:00\t02:00\t\t\t\tx\t\t\t\t\t\t\tAusbilder Muster')
    z.append('samedi 6 mars 2027\tWeiterbildung\tNM0105\tIndustriebrände Juribise\tJuribise\t09:00\t16:00\t01:00\t06:00')
    z.append('samedi 13 mars 2027\tWeiterbildung\tNM0102\tSequenz 1 - Gruppe 1\tEupen\t18:30\t21:30\t00:00\t03:00')
    return z

NB01 = ['Datum\tAnfang\tEnde\tStunden\tSequenz\tModul\tType\tEinheit\th/H\tTitel\tOrt\tHauptausbilder',
        'samedi 17 avril 2027\t09:00\t12:00\t03:00\t1\tModul 6\tTh\t01v07\t3v23\tSOP Material\tLontzen\tAusbilder Muster']

def roh(zeilen, nb01=NB01):
    return ('Workbook: 2 worksheets.\n## Sheet: NB01 2026-2027 — 3 rows × 12 columns\n' + '\n'.join(nb01) +
            '\n## Sheet: 2026 — 70 rows × 20 columns (A1:T70)\nROT = Abgesagt\n' + KOPF + '\n' + '\n'.join(zeilen) + '\n')

class Abgleich(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, 'tools'))
        os.environ['MEINWEG_HEUTE'] = '2026-10-24'
        self.lauf(roh(basiszeilen()))            # Ausgangsstand erzeugen
        self.basis = self.termine()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def lauf(self, text, *extra):
        p = os.path.join(self.dir, 'raw.txt')
        open(p, 'w', encoding='utf-8').write(text)
        return update.main([p, '--ziel', self.dir, *extra])

    def termine(self):
        return json.load(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8'))['termine']

    def bericht(self):
        return open(os.path.join(self.dir, 'tools', 'bericht.md'), encoding='utf-8').read()

    def zahl(self, art):
        m = re.search(art + r' (\d+)', self.bericht()); return int(m.group(1))

    def geaendert(self, zeilen, nb01=NB01):
        rc = self.lauf(roh(zeilen, nb01))
        return rc, self.zahl('neu'), self.zahl('geändert'), self.zahl('entfallen'), self.bericht()

    # 1
    def test_01_identisch(self):
        self.assertEqual(self.lauf(roh(basiszeilen())), 3)
    # 2
    def test_02_neuer_termin(self):
        z = basiszeilen() + ['samedi 20 novembre 2027\tWeiterbildung\tAT9999\tNeuer Kurs\tKelmis\t18:00\t22:00\t00:00\t04:00']
        rc, n, g, e, _ = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 1, 0, 0))
    # 3
    def test_03_entfallen(self):
        z = basiszeilen(); del z[5]
        rc, n, g, e, _ = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 0, 0, 1))
    # 4
    def test_04_modulnummer(self):
        z = [x.replace('NM0105', 'NM0106') for x in basiszeilen()]
        rc, n, g, e, b = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Modul: [5] → [6]', b)
    # 5
    def test_05_kursnummer(self):
        z = [x.replace('\tAT7100\t', '\tAT7199\t') for x in basiszeilen()]
        rc, n, g, e, b = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Kursnummer: AT7100 → AT7199', b)
    # 6
    def test_06_modulbezeichnung(self):
        nb = [NB01[0], NB01[1].replace('\tModul 6\t', '\tModul 7\t')]
        rc, n, g, e, b = self.geaendert(basiszeilen(), nb)
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Modul: [6] → [7]', b)
    # 7
    def test_07_uhrzeit(self):
        z = basiszeilen(); z[3] = z[3].replace('\t19:00\t21:00\t', '\t18:30\t21:00\t')
        rc, n, g, e, b = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Beginn: 19:00 → 18:30', b)
    # 8
    def test_08_ort(self):
        z = basiszeilen(); z[3] = z[3].replace('\tEupen\t', '\tKelmis\t')
        rc, n, g, e, b = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Ort: Eupen → Kelmis', b)
    # 9
    def test_09_status(self):
        z = basiszeilen(); z[4] = z[4].replace('\tThema 4\t', '\t!Termin zu bestätigen! Thema 4\t')
        rc, n, g, e, b = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Status (unbestätigt): False → True', b)
    # 10
    def test_10_gruppe(self):
        z = [x.replace('Sequenz 1 - Gruppe 1', 'Sequenz 1 - Gruppe 2') for x in basiszeilen()]
        rc, n, g, e, b = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Gruppe: Gruppe 1 → Gruppe 2', b)
    # 11
    def test_11_zwei_termine_gleicher_tag_ort(self):
        z = basiszeilen() + ['samedi 1 janvier 2027\tÜbung\tintern\tZweite Übung am selben Abend\tEupen\t19:00\t21:00\t00:00\t02:00']
        rc, n, g, e, _ = self.geaendert(z)
        self.assertEqual((rc, n, g, e), (0, 1, 0, 0))
        tag = [x for x in self.termine() if x['d'] == '2027-01-01' and x['o'] == 'Eupen']
        self.assertEqual(len(tag), 2)
    # 12
    def test_12_reihenfolge(self):
        z = list(reversed(basiszeilen()))
        self.assertEqual(self.lauf(roh(z)), 3)
    # 13
    def test_13_leere_oder_kaputte_quelle(self):
        vorher = open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read()
        for text in ['', 'Workbook: 0 worksheets.\n', '## Sheet: 2026 — 1 rows\nDatum\tTyp\n', roh([])]:
            self.assertEqual(self.lauf(text), 2, repr(text[:40]))
            self.assertEqual(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read(), vorher)
        self.assertIn('FEHLER', self.bericht())
    # 14
    def test_14_starker_rueckgang(self):
        vorher = open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read()
        z = basiszeilen()[:35] + basiszeilen()[60:]          # 25 von 81 Terminen fehlen
        self.assertEqual(self.lauf(roh(z)), 2)
        self.assertIn('Es fehlen plötzlich', self.bericht())
        self.assertEqual(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read(), vorher)
    # 14b: ein vorher gelesenes Blatt fehlt
    def test_14b_blatt_fehlt(self):
        vorher = open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read()
        text = roh(basiszeilen()).replace('## Sheet: NB01 2026-2027', '## Sheet: Notizen')
        self.assertEqual(self.lauf(text), 2)
        self.assertIn('fehlen jetzt: NB01 2026-2027', self.bericht())
        self.assertEqual(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read(), vorher)
    # 15
    def test_15_wiederholung(self):
        z = basiszeilen() + ['samedi 20 novembre 2027\tWeiterbildung\tAT9999\tNeuer Kurs\tKelmis\t18:00\t22:00\t00:00\t04:00']
        self.assertEqual(self.lauf(roh(z)), 0)
        self.assertEqual(self.lauf(roh(z)), 3)
        self.assertEqual(self.lauf(roh(z)), 3)
    # Zusatz: Ausbildernamen landen nie in termine.json
    def test_16_keine_ausbildernamen(self):
        self.assertNotIn('Ausbilder Muster', open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read())
    # Zusatz: Probelauf (--dry-run) schreibt nichts
    def test_17_dry_run(self):
        vorher = open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read()
        z = basiszeilen() + ['samedi 20 novembre 2027\tWeiterbildung\tAT9999\tNeuer Kurs\tKelmis\t18:00\t22:00\t00:00\t04:00']
        self.assertEqual(self.lauf(roh(z), '--dry-run'), 0)
        self.assertEqual(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read(), vorher)

    # Absagen aus Mails (tools/absagen.json)
    def absagen(self, liste):
        open(os.path.join(self.dir, 'tools', 'absagen.json'), 'w', encoding='utf-8').write(json.dumps(liste, ensure_ascii=False))
    def test_18_absage_eindeutig(self):
        self.absagen([{'d': '2027-01-01', 'v': '19:00', 'n': 'AT7100', 'grund': 'mangels Teilnehmer', 'gemeldet': '2026-10-27'}])
        rc, n, g, e, b = self.geaendert(basiszeilen())
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0))
        t = [x for x in self.termine() if x.get('a')]
        self.assertEqual(len(t), 1); self.assertEqual((t[0]['d'], t[0]['n'], t[0]['ag']), ('2027-01-01', 'AT7100', 'mangels Teilnehmer'))
        self.assertIn('Annulliert: None → True', b); self.assertIn('Als annulliert gekennzeichnet', b)
        self.assertEqual(self.lauf(roh(basiszeilen())), 3)          # zweiter Lauf: keine Änderung mehr
    def test_19_absage_ohne_grund(self):
        self.absagen([{'d': '2027-01-01', 't': 'Thema 0'}])
        self.assertEqual(self.lauf(roh(basiszeilen())), 0)
        t = [x for x in self.termine() if x.get('a')]
        self.assertEqual(len(t), 1); self.assertNotIn('ag', t[0])
    def test_20_absage_ohne_termin(self):
        self.absagen([{'d': '2027-12-30', 'n': 'AT0000', 'grund': 'mangels Teilnehmer'}])
        self.assertEqual(self.lauf(roh(basiszeilen())), 3)
        self.assertIn('ohne passenden Termin', self.bericht())
    def test_21_absage_mehrdeutig(self):
        z = basiszeilen() + ['samedi 1 janvier 2027\tWeiterbildung\tAT7100\tThema 0 b\tKelmis\t19:00\t21:00\t00:00\t02:00']
        self.lauf(roh(z))
        self.absagen([{'d': '2027-01-01', 'n': 'AT7100'}])
        self.assertEqual(self.lauf(roh(z)), 3)
        self.assertIn('passt auf 2 Termine', self.bericht())
        self.assertFalse(any(x.get('a') for x in self.termine()))
    def test_22_absage_kaputte_datei(self):
        vorher = open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read()
        open(os.path.join(self.dir, 'tools', 'absagen.json'), 'w').write('[{')
        self.assertEqual(self.lauf(roh(basiszeilen())), 2)
        self.assertEqual(open(os.path.join(self.dir, 'termine.json'), encoding='utf-8').read(), vorher)
    def test_23_absage_ungueltiger_eintrag(self):
        self.absagen([{'d': '2027-01-01', 'n': 'AT7100', 'grund': 'Rückfragen an max@example.com'}, {'d': 'morgen', 'n': 'AT7102'}])
        self.assertEqual(self.lauf(roh(basiszeilen())), 3)
        self.assertIn('übersprungen', self.bericht()); self.assertFalse(any(x.get('a') for x in self.termine()))
    def test_24_absage_zurueckgenommen(self):
        self.absagen([{'d': '2027-01-01', 'n': 'AT7100'}]); self.lauf(roh(basiszeilen()))
        self.absagen([])
        rc, n, g, e, b = self.geaendert(basiszeilen())
        self.assertEqual((rc, n, g, e), (0, 0, 1, 0)); self.assertIn('Annulliert: True → None', b)

if __name__ == '__main__':
    unittest.main(verbosity=2)
