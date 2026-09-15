# PopulateView

Automatische Bestückungspläne für KiCad: Oberseite, Unterseite oder beide –
mit Bauteilumrissen, lesbaren Referenzen und optionaler DNP-Kennzeichnung.
Die Pläne liegen direkt in der Platine und lassen sich als Gerber exportieren.

Open-source KiCad Action Plugin for top/bottom assembly drawings. German UI;
English developer notes below. MIT licensed. Initial testing release **0.1.0**.

## Installation

1. Unter [Releases](https://github.com/RealHaltewunsch/PopulateView/releases)
   `PopulateView-0.1.0-pcm.zip` herunterladen.
2. Im KiCad-Projektmanager den **Plugin and Content Manager** öffnen und
   **Install from File / Aus Datei installieren** wählen. ZIP auswählen.
3. PCB-Editor neu starten. Unter **Werkzeuge → Externe Plugins**
   (englisch: **Tools → External Plugins**) **PopulateView** starten.

Alternativ das `manual.zip` entpacken und den enthaltenen Ordner `populateview`
in einen KiCad-Scripting-Pluginpfad kopieren. Die tatsächlich verwendeten Pfade
zeigt die PCB-Python-Konsole mit `pcbnew.PLUGIN_DIRECTORIES_SEARCH`.
Nur eine Installationsmethode verwenden, damit kein doppelter Menüeintrag entsteht.
Das GitHub-Quellcode-ZIP ist kein PCM-Installationspaket.

## Bedienung

1. Platine speichern; eine Kontur auf `Edge.Cuts` muss vorhanden sein.
2. PopulateView öffnen und Oberseite, Unterseite oder beide wählen.
3. Bei Bedarf **DNP-Bauteile mit [DNP] kennzeichnen** aktivieren (Standard).
4. **Bestückungsplan erzeugen** drücken. Danach die Dokumentationslayer
   `PopulateView.Front` und/oder `PopulateView.Back` ansehen und speichern.
5. Nach Layoutänderungen erneut ausführen und **aktualisieren / ersetzen** wählen.
   Eine Bestätigung erklärt, dass manuelle Änderungen an Plugin-Objekten entfallen.

Freie `User.N`-Layer werden automatisch aktiviert und benannt. Benutzerdefiniert
benannte oder belegte Layer werden nicht verwendet. Nur die ausgewählten Seiten
werden aktualisiert. Jede Seite besitzt eine eigene persistente KiCad-Gruppe.
Fremde Objekte auf einem Ziellayer führen zu einer erklärenden Fehlermeldung.
Gruppen und Layernamen nicht umbenennen oder auflösen: Sie dienen der Erkennung.

## Gerber-Export

Im PCB-Editor **Datei → Plotten**, Format **Gerber** wählen.
Nur `PopulateView.Front` und/oder `PopulateView.Back` markieren. KiCad zeigt
je nach Version zusätzlich den ursprünglichen technischen Namen `User.N` an.
Jeder Layer wird eine separate Datei.

- **Spiegeln deaktivieren**: Die Unterseite ist bereits geometrisch gespiegelt.
- Keine zusätzlichen Layer als gemeinsame Layer überlagern, insbesondere
  kein zusätzliches `Edge.Cuts`: Die passende Kontur ist bereits enthalten.
- Referenzen/Text nicht in den Plotoptionen deaktivieren; normal gefüllt plotten.
- Die erzeugten Gerber-Dateien in GerbView prüfen. Als Bestückungsdokumente
  eindeutig benennen und getrennt von den Fertigungs-Kupferdaten weitergeben.

Die Unterseite entspricht dem Blick direkt auf ihre Bauteile, nach Umklappen
der Platine um die vertikale Mittellinie ihrer Kontur. Umrisse und Kontur sind
gespiegelt, Texte bleiben normal lesbar. Der Back-Plan ist deshalb kein
deckungsgleiches Overlay zum ursprünglichen Top-Koordinatensystem.

## Verhalten und Grenzen

- Umrisse: `F.Fab`/`B.Fab`, ersatzweise Courtyard, dann Siebdruck; ohne grafische
  Umrisse ein Begrenzungsrechteck ohne Referenz-/Wertfelder. Nur Kopien entstehen.
- Alle Footprints der jeweiligen Seite werden dokumentiert, auch mechanische
  oder aus Positionsdateien ausgeschlossene Footprints. DNP wird aus der
  Footprint-Eigenschaft gelesen; Textfelder namens „DNP“ werden nicht interpretiert.
- KiCad-10-Bestückungsvarianten werden nicht ausgewählt: Es gilt die Basis-DNP-
  Eigenschaft der Platine. Kein BOM-/Variantensystem ist angebunden.
- Schrift ist horizontal, 1 mm hoch. Die Platzierung prüft Textrechtecke gegen
  andere Beschriftungen und Bauteilrechtecke. Sehr dichte Stellen erhalten eine
  externe Spalte mit Zuordnungslinien. Linienkreuzungen sowie Kollisionen mit
  Details innerhalb eines Bauteils oder komplexen Konturen sind möglich;
  die Zeichnungen vor Verwendung visuell prüfen.
- Leiterbahnen, Zonen, Pads und ursprüngliche Footprint-/Siebdruckdaten werden
  nicht verändert. Das Plugin speichert nicht automatisch und bearbeitet keine
  anderen Dateien. Geometrie wird vorab vorbereitet; Fehler während der Übernahme
  lösen einen Rollback der Plugin-Änderungen aus.
- Der Menüaufruf verwendet KiCads Action-Plugin-Undo-Verwaltung. Direkte Aufrufe
  von `engine.generate()` besitzen keinen eigenen Undo-Stack.
- Kein freier User-Layer, fehlende Kontur, ungespeicherte Platine oder veränderte
  Besitzgruppen: Abbruch mit Hinweis, ohne fremde Objekte zu löschen.

## Kompatibilität

| Version | Status |
| --- | --- |
| KiCad 10.0.3, macOS | Integrationstests mit echter KiCad-Python-Laufzeit und Gerber-Plot bestanden |
| KiCad 9.x | API-kompatibel vorgesehen; noch kein Laufzeittest auf Version 9 |
| Windows / Linux | Plattformunabhängiger Python-/wx-Code; lokale GUI-Prüfung noch ausstehend |
| KiCad 11+ | Nicht unterstützt; Portierung auf IPC erforderlich |

Das Plugin benötigt KiCads `pcbnew`-SWIG-Bindings und wxPython aus der
KiCad-Installation, keine zusätzlichen pip-Pakete. Die Legacy-Schnittstelle
ist [seit KiCad 9 abgekündigt](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/).
Die Versionsprüfung verhindert den Betrieb außerhalb von 9/10.
Es ist öffentlich auf GitHub verfügbar; eine Aufnahme in das offizielle
KiCad-Pluginverzeichnis ist damit nicht verbunden.

## Development

`populateview/engine.py` contains generation, layer allocation and rollback.
`populateview/plugin.py` contains the native dialog and menu action.
`tests/test_engine.py` builds synthetic boards; no personal PCB is included.

Run with the Python shipped with KiCad, in a graphical session:

```sh
python3 -m unittest discover -s tests -v
```

On macOS, for the standard installation:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 -m unittest discover -s tests -v
```

Tests cover generation, DNP, orientation, update after save/reload, Gerber
output, serialized layout preservation, foreign-object rejection, missing
input, transaction failure, side isolation and the dialog-to-generator path.
The dialog test supplies the button result programmatically; it does not
replace a manual visual inspection of the installed menu and GerbView.

Build both installation archives with any Python 3.9+:

```sh
python3 tools/build_release.py
```

Output: `dist/*-pcm.zip`, `dist/*-manual.zip`, `SHA256SUMS` and publication
metadata. Packaging follows the [KiCad PCM specification](https://dev-docs.kicad.org/en/addons/index.html).
The archive metadata omits download hashes; publication metadata includes them.

Bug reports: include KiCad version, OS, traceback and a minimal non-sensitive
board reproducing the issue in [GitHub Issues](https://github.com/RealHaltewunsch/PopulateView/issues).
