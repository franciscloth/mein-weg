#!/usr/bin/env python3
"""Tests für tools/parse_kalender.py: Jahresblätter mit unterschiedlichem Spaltenaufbau."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parse_kalender as P

KOPF_2026 = 'Datum\tTyp\tNUMMER Übungszyklus\tName\tBemerkung\tAnfang\tEnde\tPause\tAnzahl Stunden\tAmel\tBüllingen\tBurg-Reuland\tEupen\tKelmis\tLontzen\tSankt Vith\tAmay\tSeraing\tAndere\tVerantwortlicher Ausbilder'
KOPF_2027 = 'Datum \tFW-RD\tTyp\t Typ Bemerkung \tName \tOrt\tAnfang\tEnde\tPause \tAnzahl Stunden\tVerantwortlicher Ausbilder  ECO FEU'

class Jahresblatt(unittest.TestCase):
    def test_aufbau_2026(self):
        r = [KOPF_2026.split('\t'), 'samedi 7 mars 2026\tÜbung\tzonal\tAtemschutz\t\t19:00\t21:00\t00:00\t02:00\t\t\t\tx\t\t\t\t\t\t\tMuster'.split('\t')]
        e = P.jahresblatt(r)[0]
        self.assertEqual((e['d'], e['c'], e['t'], e['o'], e['v'], e['b'], e['h'], e['n']),
                         ('2026-03-07', 'U', 'Atemschutz', 'Eupen', '19:00', '21:00', 2.0, ''))

    def test_aufbau_2027_mit_spalte_fw_rd(self):
        r = [KOPF_2027.split('\t'),
             'mardi 6 avril 2027\tRD+FW\tÜbung\tINFRABEL\t Begehung TGV-Tunnel\tWalhorn Tunnel \t13:30\t15:30\t00:00\t02:00\tMuster'.split('\t'),
             'lundi 25 janvier 2027\tFW\tWeiterbildung\tAT4514\tRecyclage FOROP Pädagogik\tEupen \t18:30\t21:30\t00:00\t03:00\tMuster'.split('\t'),
             'jeudi 7 janvier 2027\tFW\tWeiterbildung\tNM02 \tModul 2  \tKelmis\t19:00\t22:00\t00:00\t03:00\tMuster'.split('\t')]
        ev = P.jahresblatt(r)
        self.assertEqual(len(ev), 3)
        u, w, l = ev
        self.assertEqual((u['c'], u['t'], u['o'], u['v'], u['h'], u['n']), ('U', 'Begehung TGV-Tunnel', 'Walhorn Tunnel', '13:30', 2.0, ''))
        self.assertEqual((w['c'], w['n'], w['o'], w['v'], w['b']), ('W', 'AT4514', 'Eupen', '18:30', '21:30'))
        self.assertEqual((l['c'], l['k'], l['o']), ('L', 'NMO2', 'Kelmis'))

if __name__ == '__main__':
    unittest.main()
