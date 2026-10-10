# Milestone 3 — Camera keyframes

Each scene now supports start and end values for **zoom**, **horizontal framing** and **vertical framing**.

- Zoom range: 1.0 to 2.0 (1.0 = full image crop; 2.0 = 2× zoom).
- X/Y range: 0.0 to 1.0 (left/top to right/bottom crop position).
- Interpolation: linear across each scene's output frames.
- Default zoom: 1.0 to 1.08, centered, preserving the original subtle zoom behavior.
- Keyframes are stored in scene JSON, alongside image path and duration.
- FFmpeg uses the zoompan filter; no character animation or object motion is implied.

## Workflow

1. Add an image and select its scene.
2. Enter camera start/end values.
3. Click **Apply camera**.
4. Save the project and export MP4.

Example: zoom from 1.0 to 1.5 and pan left to right by setting x_start=0 and x_end=1.

## Test coverage

- Headless tests validate ranges, nonfinite numbers and expression generation.
- FFmpeg integration test includes an animated camera scene and checks MP4 metadata and decoding.
- The desktop GUI itself requires a later interactive acceptance test.

**Limitations:** No per-frame editor, easing curves, live playback, character rigs or layered object keyframes yet.
