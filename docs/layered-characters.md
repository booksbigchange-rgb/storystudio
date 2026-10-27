# Layered-artwork characters (simple 2D rig)

You can use your own character art instead of the built-in fox, rabbit and bear. This is a **simple cutout rig**: flat
PNG parts joined in a hierarchy and driven by sine-wave motions for the existing actions. It is not painterly rigging
(no mesh deformation, no bones with IK, no hand-drawn frame animation).

## Make the layers
Draw (Krita, Photoshop, GIMP, Affinity…) and export **each part as its own PNG at the full canvas size** ("layers to
files"), so every PNG has the same width and height and the art sits where it belongs. Name them:

`body.png`, `head.png` (required), `arm_left.png`, `arm_right.png`, `leg_left.png`, `leg_right.png`, `tail.png`,
`eyes_open.png`, `eyes_closed.png` (shown during blinks), `mouth_closed.png`, `mouth_open.png` (shown while talking or surprised).
Missing optional parts are simply left out. **Character tab → Create example layers…** writes an original sample robot
you can look at and replace.

## Import
**Character tab → Import layered character…**, choose the folder, name it (letters, digits, `_`, `-`). The editor crops each
layer, sets pivots (arms and legs swing from the top, the head from its base, the tail from its inner edge), builds the
hierarchy (head/arms/legs/tail on the body, eyes and mouth on the head) and saves it under `projects\characters\<name>\`.
Then pick `custom:<name>` as the character. Existing motions work: idle, wave, walk, talk, story, jump; expressions
change the mouth (open when surprised) and blinking swaps the eye layers; animation keys, tilt, lift, size and presets work too.

Advanced: a folder with a hand-written `rig.json` (kind `storystudio-character-rig`, version 1) is imported as-is after validation;
see `integrations/lemo-lite/character_rig.py` for the exact fields (parts with `pivot`, `at`, `parent`, `z`, optional `show`
rules; per-action `motion` drivers `{part, channel: rotate|x|y|scale, base, amp, speed, phase}`).

## Safety
- Data only: `rig.json` is validated JSON and is never evaluated; there is no scripting. Image names cannot contain folders
  or drive letters; only PNG files are read.
- Limits: 40 parts, 2048 px per side, 16 million pixels in total, 8 drivers per action, bounded numbers, `rig.json` ≤ 256 KB, pack ≤ 50 MB.
- Import never overwrites: an existing name is refused; the pack is built in a hidden staging folder, fully validated, and renamed into place.
  Your source layers are only read. A failed import leaves nothing behind.
- A scene that uses a missing or invalid pack stops the export **before** any frame (also inside the shared timeline).
- Packs are linked, like other media: keep `projects\characters\<name>` while projects use it.

## Limits
- Drawn by the native renderer only. The browser **Play live preview** shows a labelled stand-in; the frame preview and every export are exact.
- Motion is the preset set above (tuned per part by the drivers in `rig.json`); there is no timeline of hand-posed limbs yet.
- Pivots come from the art's bounding boxes. If an arm or leg pivots oddly, edit its `pivot` in `rig.json` (inside the imported pack).

## Verification
`integrations/lemo-lite/tests/test_rig.py` (validation incl. traversal/overflow/loops, safe import, failed import cleanup, auto-rig geometry, rendering,
sprite compositing, fringes, reload), `tests/character_rig_integration.py` (real exports 16:9/9:16, mixed timeline, missing pack, source untouched),
`tests/character_rig_gui_integration.py` (real Tk import/refuse/use/export). On Windows: `Verify-Character-Keys.cmd`.
