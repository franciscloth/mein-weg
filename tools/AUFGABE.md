# Tägliche Aktualisierung „Mein Weg“ – Ablauf und Fehlerbehandlung

**Wer:** geplante Claude-Aufgabe „Mein Weg – tägliche Terminprüfung“, täglich 05:47 Uhr Ortszeit Brüssel
(der Zeitplan ist mit `CRON_TZ=Europe/Brussels` hinterlegt; Sommer- und Winterzeit stellt der Planer selbst um).
**Zugang:** Microsoft-365-Zugang von Francis Cloth (nur lesend) und GitHub-Verzeichnis `franciscloth/mein-weg`.

## Ablauf
1. Verzeichnis klonen (`/home/claude/mein-weg`).
2. Kalenderdatei über den Microsoft-365-Connector lesen (alle Blätter) und unverändert als `tools/raw.txt` speichern.
   `raw.txt` enthält Ausbildernamen: steht in `.gitignore` und wird zusätzlich von der Veröffentlichungsprüfung abgewiesen.
3. `python3 -W ignore -m unittest discover -s tools/tests` – alle Tests müssen bestehen, sonst Abbruch.
4. `python3 tools/update.py tools/raw.txt`
   - Exit 3: keine Änderung → Ende, nichts veröffentlichen.
   - Exit 2: Prüfung fehlgeschlagen (leere/beschädigte Quelle, fehlendes Blatt, starker Rückgang …) → nichts veröffentlichen, FEHLER aus `tools/bericht.md` melden. `termine.json` bleibt unverändert.
   - Exit 0: weiter.
5. `python3 tools/build_index.py` (schreibt index.html atomar, gleiche Termine und gleicher Datenstand wie termine.json).
6. `python3 tools/pruefe_veroeffentlichung.py tools/raw.txt` – prüft: JSON = eingebaute Rückfallkopie, Datenstand gleich, Skript fehlerfrei, keine Platzhalter, keine fremden Mailadressen oder Telefonnummern, kein Name aus den Ausbilderspalten, keine Rohdaten im Repository.
   Schlägt sie fehl: `git checkout -- termine.json index.html`, nichts veröffentlichen, melden.
7. `git status` darf nur `termine.json` und `index.html` als geändert zeigen. Commit „Termine aktualisiert JJJJ-MM-TT“, push auf `main`.
8. Meldung an Francis: neue, geänderte und entfallene Termine getrennt (je die ersten 10), mehrdeutige Zuordnungen, Hinweise.

## Veröffentlichung
- GitHub Actions („Prüfen und veröffentlichen“, `.github/workflows/pages.yml`) führt bei jedem Push die Tests und die Veröffentlichungsprüfung erneut aus und veröffentlicht nur `index.html` und `termine.json`.
  Voraussetzung: Settings → Pages → Source „GitHub Actions“. Solange dort „Deploy from a branch“ steht, veröffentlicht GitHub jeden Push ungeprüft; dann schützt nur Schritt 3–6.
- Die App lädt beim Öffnen `termine.json`; ohne Verbindung zeigt sie die eingebauten Termine mit Datenstand.

## Wenn etwas schiefgeht
| Meldung | Bedeutung | Was tun |
|---|---|---|
| „Kein Jahresblatt gefunden“, „Nur X Termine eingelesen“ | Datei leer, umbenannt oder nicht vollständig gelesen | Kalenderdatei in SharePoint prüfen; Aufgabe am nächsten Tag erneut abwarten |
| „Diese Blätter … fehlen jetzt“ | Ein Blatt wurde umbenannt oder gelöscht | Umbenennung bewusst? Dann einmalig von Hand freigeben (Claude bitten) |
| „Es fehlen plötzlich …“ | Starker Rückgang (> 10 % gesamt oder > 25 % einer Kategorie) | Prüfen, ob Zeilen versehentlich gelöscht wurden |
| „Mehrdeutige Zuordnung“ | Zwei Termine passen gleich gut | Bericht ansehen; Daten sind veröffentlicht, nur die Einordnung im Bericht ist unsicher |
| „Mögliche Dublette“ | Zeile steht mehrfach in der Quelle | In der Kalenderdatei klären (zweite Gruppe oder Versehen) |
| Prüfung konnte nicht laufen | Microsoft-365-Zugang nicht verfügbar | App bleibt auf dem letzten Stand; nächsten Lauf abwarten |
