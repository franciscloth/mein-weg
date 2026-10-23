# Mein Weg – HLZ DG

Laufbahn, Ausbildungstermine und Überblick für die Einsatzkräfte der Hilfeleistungszone DG.

- **App:** `index.html` (eine Datei, läuft auch offline mit den eingebauten Terminen)
- **Termine:** `termine.json`, wird täglich automatisch aus dem Übungs- und Weiterbildungskalender (SharePoint) erzeugt
- **Werkzeuge:** `tools/`
  - `parse_kalender.py` liest den Kalender (Jahresblätter und Stundenplan NB01), ohne Ausbildernamen
  - `update.py` prüft die Daten und schreibt `termine.json`; veröffentlicht nur, wenn alle Prüfungen bestehen
  - `korrekturen.json` geprüfte Titel und Orte (Prüfrunden Loop 1–3)
  - `feste_termine.json` Termine, die nicht in der Kalenderdatei stehen (NMO2 Adjutant, Korporal Modul 1)
  - `build_index.py` baut `index.html`
  - `AUFGABE.md` Ablauf der täglichen Prüfung

Verantwortlich: Zonenkommandant HLZ DG. Ansprechpartner: ausbildungszelle@hlzdg.be
