# Undo, trim, split and transitions (shared timeline)

## Undo / Redo
**Undo** and **Redo** buttons, Ctrl+Z / Ctrl+Y. Up to 50 steps cover adding, moving, duplicating and removing
sections, output format, timed text, the audio mix and every section edit below. Opening another timeline clears
the history. Disabled while an export runs.

## Trim · split · transition (select a section, then the button)
- **Trim**: start and end in seconds of the source project (stored as whole frames, 24 fps). Source projects are
  never modified. If a source later gets shorter than a saved trim, the export stops with a message naming the section.
- **Split**: cuts a section in two at a time from its current start. Both halves keep every frame exactly once, so the
  video is identical to before; the transition stays with the first half. Undo reverses it.
- **Transition into the section** (not used on the first section):
  - *Dissolve (overlap)*: cross-fades the end of the previous section into the start of this one over the chosen time.
    The two overlap, so the story gets shorter by that time. Timed text and audio positions are on the final timeline.
  - *Dip to black*: the previous section fades out and this one fades in (audio too); length unchanged.
  - Transitions must be shorter than both neighbours, and a section must be long enough for the transitions on both sides.

The list shows `✂` for trimmed sections and `⇄ kind frames` for transitions; totals and start times use the same frame plan as
the exporter (`engine/mixed_edit.py`).

## How it exports
Untouched sections are joined exactly as before. Only trimmed, faded or dissolved parts are re-encoded (one extra
generation at CRF 20, only for those parts); sections stay in separate processes and cancel/no-overwrite are unchanged.

## Verification
- `tests/test_mixed_edit.py`: plan arithmetic (including 300 random plans where every output frame comes from exactly one clip),
  validation, split, durations vs plan, undo/redo bounds.
- `tests/mixed_edit_integration.py`: real exports decoded frame by frame: trim cut points, mid-dissolve is a blend, dip-to-black
  reaches black, split is invisible, audio stays in step, bad edits rejected before rendering.
- `tests/mixed_edit_gui_integration.py` (Windows): real Tk buttons/shortcuts, dialog, invalid input, split, undo of each, save/reopen, GUI export with exact frame count.
- Run on Windows with `Verify-Section-Edits.cmd`.

Not done: a visual waveform/thumbnail timeline for choosing trim points (times are typed), other transition styles (wipes), per-transition easing.
