# PopulateView

Automatic assembly drawings for KiCad: top, bottom or both sides, with component
outlines, readable reference designators and optional DNP markings. Drawings are
stored directly in the board and can be exported as Gerber files.

Open-source KiCad Action Plugin using the SWIG runtime, with an English interface.
MIT licensed. Testing release **0.2.2**.

## Installation

1. Download `PopulateView-0.2.2-pcm.zip` from
   [Releases](https://github.com/RealHaltewunsch/PopulateView/releases).
2. Open the **Plugin and Content Manager** in the KiCad project manager,
   choose **Install from File** and select the ZIP archive.
3. Restart the PCB editor. Launch **PopulateView** from
   **Tools → External Plugins**.

Alternatively, extract the `manual.zip` archive and copy its `populateview`
folder into a KiCad scripting plugin directory. To see the search paths used
by your installation, enter `pcbnew.PLUGIN_DIRECTORIES_SEARCH` in the PCB
Python console. Use only one installation method to avoid duplicate menu entries.
GitHub's source code ZIP is not a PCM installation package.

## Usage

1. Save the board. It must have an outline on `Edge.Cuts`.
2. Open PopulateView and select top, bottom or both sides.
3. Enable the option to mark DNP components with `[DNP]` if needed (on by default).
4. Click the button to generate the assembly drawing. Inspect the
   `PopulateView.Front` and/or `PopulateView.Back` documentation layers and save.
5. After layout changes, run the plugin again and select the update/replace option.
   A confirmation explains that manual edits to plugin-owned objects will be lost.

Available `User.N` layers are automatically enabled and named. Layers with
custom names or existing content are not allocated. Only the selected sides
are updated. Each side has its own persistent KiCad group. Unrelated objects
on a target layer cause an explanatory error. Do not rename the layers or
rename or dissolve the groups: they identify the generated drawings.

## Gerber export

In the PCB editor, choose **File → Plot** and select **Gerber** as the format.
Select only `PopulateView.Front` and/or `PopulateView.Back`. Depending on the
KiCad version, the original technical name `User.N` may also be displayed.
Each layer produces a separate file.

- **Disable mirroring**: the bottom view is already geometrically mirrored.
- Do not overlay additional common layers, especially `Edge.Cuts`: the correctly
  oriented board outline is already included.
- Keep references/text enabled in the plot options and use normal filled plotting.
- Inspect the generated files in GerbView. Name them clearly as assembly drawings
  and distribute them separately from manufacturing copper data.

The bottom view looks directly at the bottom components after flipping the board
about the vertical centre line of its outline. Component and board outlines are
mirrored; text remains readable. The bottom drawing therefore does not align as
an overlay with the original top-view coordinate system.

## Behavior and limitations

- Outlines come from `F.Fab`/`B.Fab`, with courtyard and then silkscreen as
  fallbacks. If no graphical outline exists, a bounding rectangle excluding
  reference/value fields is used. Only copies are created.
- All footprints on the selected side are documented, including mechanical
  footprints and those excluded from position files. DNP comes from the footprint
  property; text fields named "DNP" are not interpreted.
- KiCad 10 assembly variants are not selected: the board's base DNP property
  is used. No BOM or variant system is integrated.
- Font size and stroke thickness adapt to each footprint. Actual KiCad text
  bounds, including `[DNP]`, determine the size: long designators become smaller,
  while large components receive larger text (up to 5 mm). A proportional inner
  margin accounts for outline strokes.
- Text is fitted into the outline's bounding rectangle aligned with the footprint
  axes. Rotated components are also measured in these local axes; the better of
  the two text orientations is used. There are no external labels. This rectangle
  is not the exact interior of arbitrary concave or circular outlines: cutouts,
  internal graphics and overlapping footprints are not treated as obstacles.
- If a label overlaps internal graphics inside a verified rectangular outline,
  the interior graphics are omitted from the generated drawing and the label is
  fitted again. The rectangle is preserved. Both native rectangles and complete
  rectangles made of line segments are recognized, including rotated and mirrored
  footprints. Internal polarity marks may be omitted too. Original fabrication
  and silkscreen graphics are untouched. Open or unrecognized outlines are kept;
  this rule does not resolve every conflict in arbitrary footprint geometry.
- Tiny components (such as 0201) and long references can produce very small text
  and strokes. There is no fixed minimum font size that would force text outside
  the bounds. The results dialog counts labels below 0.5 mm; reading them may
  require zooming or an enlarged printout. If there is no usable interior area,
  generation stops before making changes.
- Tracks, zones, pads and original footprint/silkscreen data are not modified.
  The plugin does not save automatically or edit other files. Geometry is prepared
  before changes are applied; an error during application rolls back plugin changes.
- Launching from the menu uses KiCad's Action Plugin undo handling. Direct calls
  to `engine.generate()` do not have their own undo stack.
- No available user layer, missing outline, unsaved board or modified ownership
  groups: generation stops with an explanation without deleting unrelated objects.

## Compatibility

| Version | Status |
| --- | --- |
| KiCad 10.0.3, macOS | Integration tests using the actual KiCad Python runtime and Gerber plotting passed |
| KiCad 9.x | Intended to be API-compatible; not yet runtime-tested on version 9 |
| Windows / Linux | Platform-independent Python/wx code; local GUI verification pending |
| KiCad 11+ | Not supported; requires an IPC port |

The plugin requires KiCad's `pcbnew` SWIG bindings and wxPython from the KiCad
installation, with no additional pip packages. The legacy interface has been
[deprecated since KiCad 9](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/).
A version check prevents operation outside KiCad 9/10. PopulateView continues
to use SWIG for now. It is publicly available on GitHub; this does not imply
inclusion in the official KiCad plugin directory.

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
