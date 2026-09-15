## PopulateView 0.2.2 – Resolve internal symbol conflicts

When reference text overlaps internal graphics inside a verified rectangular
outline, the generated drawing omits the interior graphics and refits the label.
This resolves cases such as a diode symbol crossing its reference designator.

The outer rectangle and all original footprint/silkscreen data are preserved.
Internal polarity information may be omitted from the assembly drawing.
Native rectangles and complete rectangles made of segments are supported,
including rotated and mirrored footprints. Unknown or open outlines remain intact.

Install `PopulateView-0.2.2-pcm.zip` through **Install from File** in KiCad's
Plugin and Content Manager, then restart the PCB editor. Enable **Update / replace
existing PopulateView drawings** and regenerate the affected sides.
A manual installation ZIP is also available.

All 13 integration tests passed with KiCad 10.0.3 on macOS, including symbol
removal, rotation, mirroring, original layout preservation and Gerber export.
The reported issue was reproduced on a synthetic board; no user PCB was available.
KiCad 9 and Windows/Linux remain unverified;
KiCad 11+ is not supported. See the README for usage and limitations.
