# Changelog

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
