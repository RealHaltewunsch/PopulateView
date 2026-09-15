## PopulateView 0.2.0 – Adaptive Beschriftung

Schriftgröße und Strichstärke passen sich jetzt dem Bauteilrechteck und der
tatsächlichen Textlänge an, einschließlich DNP. Kleine Bauteile erhalten kleine
Schrift, große bis zu 5 mm große Schrift. Gedrehte Footprints werden entlang
ihrer eigenen Achsen gemessen. Externe Beschriftungen entfallen.

- Automatische Referenzplatzierung und optionale `[DNP]`-Kennzeichnung.
- Unterseite als gespiegelte Bauteilansicht mit normal lesbarer Schrift.
- Gezieltes Aktualisieren eigener Gruppen mit Bestätigung und Fehler-Rollback.
- Gerber-Export über KiCads normalen Plotdialog.

Installation: `PopulateView-0.2.0-pcm.zip` im KiCad Plugin and Content Manager
über **Aus Datei installieren** öffnen. Alternativ das `manual.zip` verwenden.
Das automatisch von GitHub angebotene Source-code-ZIP ist kein PCM-Paket.

Getestet mit KiCad 10.0.3 auf macOS: elf Integrationstests einschließlich
Gerber-Plot, Speichern/Neuladen, Layout-Erhaltung und Dialoganbindung bestanden.
KiCad 9 ist vorgesehen, aber noch nicht zur Laufzeit geprüft; Windows/Linux
und die manuelle GUI-Abnahme sind noch ausstehend. KiCad 11+ wird nicht unterstützt.

Export ohne zusätzliche Spiegelung und ohne Edge.Cuts-Überlagerung.
Die DNP-Basisattribute werden ausgewertet, keine KiCad-10-Bestückungsvarianten.
Sehr kleine Texte benötigen Zoom oder vergrößerte Ausdrucke. Eingepasst wird
in das orientierte Umrissrechteck; Aussparungen komplexer Konturen werden nicht
berücksichtigt. Nach dem Update vorhandene Pläne erneut erzeugen.

MIT-Lizenz. Installations- und Bedienungsanleitung im README.
