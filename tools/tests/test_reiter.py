#!/usr/bin/env python3
"""Vollständigkeitsprüfung aller Reiter (tools/update.py → pruefe_reiter).
Fängt Fälle wie im November 2026 ab: Reiter „2027“ gelesen, aber wegen anderem Spaltenaufbau nichts übernommen."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import test_update
from test_update import roh, basiszeilen, NB01, KOPF
import update

KOPF_2027 = 'Datum \tFW-RD\tTyp\t Typ Bemerkung \tName \tOrt\tAnfang\tEnde\tPause \tAnzahl Stunden\tVerantwortlicher Ausbilder'
Z2027 = [f'samedi {t} mars 2027\tFW\tÜbung\tzonal\tÜbung {t}\tEupen\t19:00\t21:00\t00:00\t02:00\tMuster' for t in range(1, 11)]

def mit_reiter(text, kopf, zeilen, name='2027', liste=None):
    t = text + f'## Sheet: {name} — 20 rows × 11 columns\n' + kopf + '\n' + '\n'.join(zeilen) + '\n'
    if liste is not None:
        t = t.replace('Workbook: 2 worksheets.\n', f'Workbook: {len(liste)} worksheets.\nWorksheets (startPage and endPage select them by these numbers):\n'
                      + ''.join(f'{i}. {n}\n' for i, n in enumerate(liste, 1)) + 'This read covers sheets.\n')
    return t

class Reiter(unittest.TestCase):
    setUp, tearDown, lauf, termine, bericht = test_update.Abgleich.setUp, test_update.Abgleich.tearDown, test_update.Abgleich.lauf, test_update.Abgleich.termine, test_update.Abgleich.bericht

    def test_r1_reiter_in_datei_aber_nicht_gelesen(self):
        t = mit_reiter(roh(basiszeilen()), KOPF_2027, Z2027, liste=['NB01 2026-2027', '2026', '2027', 'NB02 Korporal'])
        self.assertEqual(self.lauf(t), 2)
        self.assertIn('Reiter „NB02 Korporal“ steht in der Datei, wurde aber nicht gelesen', self.bericht())

    def test_r2_gekuerzt(self):
        t = roh(basiszeilen()) + '[Sheet 2 "2026" was cut partway at row 40]\n'
        self.assertEqual(self.lauf(t), 2)
        self.assertIn('nur teilweise gelesen', self.bericht())

    def test_r3_reiter_gelesen_aber_nichts_uebernommen(self):
        kaputt = KOPF_2027.replace('\tTyp\t', '\tArt\t')   # Spalte umbenannt → Typ wird nicht gefunden
        self.assertEqual(self.lauf(mit_reiter(roh(basiszeilen()), kaputt, Z2027)), 2)
        self.assertIn('Reiter „2027“: Spalte(n) typ nicht gefunden', self.bericht())

    def test_r4_neuer_aufbau_wird_uebernommen(self):
        self.assertEqual(self.lauf(mit_reiter(roh(basiszeilen()), KOPF_2027, Z2027)), 0)
        self.assertIn('2027 (Jahresblatt): 10 Zeilen mit Datum · 10 übernommen', self.bericht())

    def test_r5_unbekannter_reiter_mit_terminen(self):
        rc = self.lauf(mit_reiter(roh(basiszeilen()), 'Datum\tKurs', ['samedi 3 avril 2027\tNeuer Kurs'], name='NB02 Korporal 2027'))
        self.assertEqual(rc, 3)
        self.assertIn('Reiter „NB02 Korporal 2027“ enthält 1 Zeilen mit Datum, wird aber nicht ausgewertet', self.bericht())

    def test_r6_unbekannter_typ_kuenftig(self):
        z = Z2027 + ['samedi 20 mars 2027\tFW\tSeminar\tX1\tNeues Format\tEupen\t19:00\t21:00\t00:00\t02:00\tMuster']
        self.assertEqual(self.lauf(mit_reiter(roh(basiszeilen()), KOPF_2027, z)), 0)
        self.assertIn('1 künftige Zeile(n) mit Typ „Seminar“ nicht übernommen', self.bericht())

    def test_r7_bewusst_ausgelassen_kein_hinweis(self):
        z = Z2027 + ['mardi 16 mars 2027\tRD\tEPAMU\tEPAMU\tGrundkurs Sanitäter\tSeraing\t18:00\t22:00\t00:00\t04:00\tEPAMU']
        self.lauf(mit_reiter(roh(basiszeilen()), KOPF_2027, z))
        b = self.bericht()
        self.assertIn('1 bewusst ausgelassen (EPAMU)', b); self.assertNotIn('Hinweise zur Prüfung', b)

    def test_r8_zwei_nb01_kurse_mit_reitername(self):
        nb2 = ['Datum\tAnfang\tEnde\tStunden\tSequenz\tModul\tType\tEinheit\th/H\tTitel\tOrt\tHauptausbilder',
               'samedi 17 avril 2027\t09:00\t12:00\t03:00\t1\tModul 1\tTh\t01v07\t3v23\tEinleitung\tEupen\tAusbilder Muster']
        t = mit_reiter(roh(basiszeilen()), nb2[0], nb2[1:], name='NB01 2027-2028')
        self.assertEqual(self.lauf(t), 0)
        titel = {e['t'] for e in self.termine() if e['c'] == 'L' and e.get('k') == 'NBO1'}
        self.assertIn('Grundausbildung NB01 2026-2027 – Modul 6: SOP Material', titel)
        self.assertIn('Grundausbildung NB01 2027-2028 – Modul 1: Einleitung', titel)

    def test_r9_leerer_reiter(self):
        t = roh(basiszeilen()) + '## Sheet: NB01 2027-2028 (empty)\n'
        t = t.replace('Workbook: 2 worksheets.\n', 'Workbook: 3 worksheets.\nWorksheets (x):\n1. NB01 2026-2027\n2. 2026\n3. NB01 2027-2028\nThis read covers sheets 1–3.\n')
        self.assertIn(self.lauf(t), (0, 3))
        self.assertIn('NB01 2027-2028 (Stundenplan NB01): 0 Zeilen mit Datum', self.bericht())
        self.assertNotIn('FEHLER', self.bericht())

if __name__ == '__main__':
    unittest.main(verbosity=2)
