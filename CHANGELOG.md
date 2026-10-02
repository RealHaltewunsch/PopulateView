# Changelog

## 0.2.4

- Keep bottom drawing shapes, outline and labels in the original board coordinates.
- Remove the additional reflection and keep text fitted to the actual footprint rotation.
- Label bottom drawings as board-coordinate documentation, not component-side views.
- Update English UI and export instructions to state the coordinate convention.
- Replace legacy mirrored bottom drawings using the existing update option.
- Add regressions for asymmetric outlines, rotations, pad fallbacks and bottom-only migration.

## 0.2.3

- Skip tiny Fab pin-1 markers when selecting component body outlines.
- Try courtyard and silkscreen when a candidate has no usable interior area.
- Use actual pad bounds and proportional rectangle strokes for the fallback.
- Reproduce and fix Q1 on a 195-footprint board with top/bottom and Gerber checks.
- Add regression tests for unusable/fit-eligible markers and tiny pad-only footprints.

## 0.2.2

- Resolve label conflicts with interior decoration inside verified rectangular outlines.
- Omit interior decoration only from generated drawings and refit the reference.
- Preserve original footprint graphics and silkscreen, including polarity marks.
- Recognize native and segmented rectangles with rotation and bottom mirroring.
- Keep unknown/open outlines intact; add diode-symbol regression coverage.

## 0.2.1

- Translate the complete plugin interface, messages and menu entry into English.
- Use English labels for confirmation and cancellation buttons.
- Include the English README in installation packages. Continue using SWIG.

## 0.2.0

- Adaptive font size and proportional stroke width per footprint.
- Fit actual KiCad text bounds including long references and DNP suffixes.
- Measure in footprint coordinates; choose the larger fit along either axis.
- Replace external callouts with labels inside the outline envelope.
- Report text below 0.5 mm; cap large text at 5 mm.
- Test tiny bodies, rotated labels, length sensitivity and small-text Gerber export.

## 0.1.0

- Initial public testing release for KiCad 9/10 Action Plugin runtime.
- Separate user documentation layers for top and bottom assembly views.
- Footprint outlines, automatic references, optional DNP labels and callouts.
- Mirrored bottom geometry with readable unmirrored text.
- Persistent ownership groups, selective replacement and transaction rollback.
- PCM and manual installation packages; integration tests with Gerber output.
