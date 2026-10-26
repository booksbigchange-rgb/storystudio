# Faster character renderer (no browser)

Character exports and editor preview frames are now drawn by `integrations/lemo-lite/native_scene.py` with Pillow,
instead of capturing a Chrome/Edge page frame by frame. The shapes, motion, keys, expressions, captions and layout
mirror `scene/scene.js` and `scene/characters.js`; the browser renderer is kept (`--engine browser` or
`STORYSTUDIO_RENDERER=browser`) as the reference and for **Play live preview**.

## What changed for you
- **Speed**: a 5-second 720p/24 fps clip took 26.5 s with the browser and 4.9 s natively on the test machine (about 5x; ~30 ms per frame).
  Mixed-timeline character sections benefit directly.
- **Memory**: one frame at a time piped to FFmpeg as raw video (no JPEG pass, no browser process); about 75 MB peak versus a browser plus its children.
- **No Edge/Chrome needed for export or the preview frame.** Only *Play live preview* still opens a browser window.
- **Colour**: the native path tags and converts colours as BT.709 correctly. The old browser path stored BT.601-matrix data tagged as BT.709,
  so colours were slightly off in players that honor the tag; native decoded frames match the rendered frames within 3/255.
- Exports, no-overwrite, cancellation and verification are unchanged.

## Differences to know
- Anti-aliasing and the caption font differ very slightly (Windows uses Segoe UI Bold). Parity against the browser: mean difference ~1.2/255 per pixel.
- It renders the built-in characters only, exactly like the browser version. It is not painterly rigging.

## Verification
- `integrations/lemo-lite/tests/test_native.py` (runs everywhere): sizes, both orientations, determinism and seeking, every character/expression/action/backdrop distinct,
  keys change the picture while neutral keys do not, character position follows the key, clamped time, speed bound.
- `tests/native_render_integration.py` (needs the browser for the reference): 17 cases (3 characters, 4 expressions, 6 actions, night, keyed, two portrait) compared with
  browser screenshots; real 3 s exports with both engines decoded, verified, frame-distinct; native clearly faster; native MP4 colours match rendered frames; no-overwrite and cancel on the native path.
- Run `Verify-Character-Keys.cmd` on Windows.
