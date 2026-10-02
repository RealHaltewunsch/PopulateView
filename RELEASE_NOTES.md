## PopulateView 0.2.4 – Keep bottom drawings in board coordinates

Fixes bottom documentation appearing at unexpected positions in the PCB editor.
`PopulateView.Back` now keeps the original coordinates of the board outline and
back-side footprints. TP1 at X = 207 mm stays at X = 207 mm rather than being
reflected to X = 140 mm. Adaptive reference fitting, DNP marking and the Q1
outline-selection fix remain in place. Original layout data is not modified.

Both documentation layers now align with the layout. Bottom drawings are labelled
**BOTTOM (board coordinates)** and have readable, unmirrored text. Export without
mirroring. This is not a physically flipped component-side view; a separate
mirrored export with readable lettering is not included in this release.

Install `PopulateView-0.2.4-pcm.zip` using **Install from File** in KiCad's Plugin
and Content Manager and restart the PCB editor. Select **Bottom** or **Both sides**,
enable **Update / replace existing PopulateView drawings**, and regenerate.
Existing mirrored drawings from older releases are not automatically migrated;
the update option replaces them without touching an unselected front drawing.
A manual-install ZIP is also available.

All 19 integration tests passed using KiCad 10.0.3 on macOS, including rotated
back-side footprints, asymmetric outlines, pad-only fallbacks, legacy-drawing
migration, layout preservation and Gerber output. Board data used in local
testing is not included in the repository or packages. KiCad 9 and Windows/Linux
remain unverified; KiCad 11+ is not supported. The interface remains English and
the runtime remains SWIG. This is a public testing release.
