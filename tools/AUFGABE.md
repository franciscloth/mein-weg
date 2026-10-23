# Tägliche Prüfung „Mein Weg“

1. Repository `franciscloth/mein-weg` bereitstellen (add_repo, Zugriff „push“) und klonen.
2. Kalender über den Microsoft-365-Connector lesen:
   `read_resource` mit uri `file:///b!zcB8baQ-f0agHX4tTe1Krcc-EJcmOWdPisd9w-0PZWqOtRlugV8XR7oMg_CdvwOS/01NNDXEBC2RRUFSOBQDJB3SZGTI7YKP6UX`,
   startPage 1, endPage = Anzahl der Blätter laut Kopfzeile (alle Blätter). Den vollständigen Text unverändert als `tools/raw.txt` speichern
   (bei großer Antwort liegt er bereits als Datei vor: diese kopieren). Nie committen.
3. `python3 tools/update.py tools/raw.txt`
   - Exit 3: keine Änderung → nichts tun.
   - Exit 2: Prüfung fehlgeschlagen → nichts veröffentlichen, Bericht melden.
   - Exit 0: weiter.
4. `python3 tools/build_index.py`, dann das Skript in index.html auf Syntax prüfen
   (Inhalt zwischen `<script>` und `</script>` in eine .js-Datei schreiben, `node --check`).
5. Commit nur von `termine.json` und `index.html`, Nachricht „Termine aktualisiert JJJJ-MM-TT“, push auf `main`.
6. Kurzmeldung an Francis: Anzahl neue/entfallene Termine, Hinweise aus `tools/bericht.md`.
