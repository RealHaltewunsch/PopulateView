## PopulateView 0.2.3 – Fix pin-1 marker outline selection

Fixes "No usable interior area for label: Q1" on footprints whose fabrication
layer contains only a tiny pin-1 marker. The plugin now rejects undersized or
unusable outline candidates and tries courtyard or silkscreen instead.

When no usable outline exists, actual pad bounds provide a fallback rectangle
with an adaptive stroke width. Original footprints, pads, tracks and silkscreen
are preserved. The interface remains English and the runtime remains SWIG.

Install `PopulateView-0.2.3-pcm.zip` through **Install from File** in KiCad's
Plugin and Content Manager, then restart the PCB editor. Enable **Update / replace
existing PopulateView drawings** and regenerate the affected sides.
A manual installation ZIP is also available.

All 16 integration tests passed with KiCad 10.0.3 on macOS. The reported error
was reproduced on a copy of the affected 195-footprint board. Both assembly
drawings (170 top / 25 bottom) and Gerber exports succeeded after the fix.
Board data used for local testing is not included in the repository or packages.
KiCad 9 and Windows/Linux remain unverified;
KiCad 11+ is not supported. See the README for usage and limitations.
