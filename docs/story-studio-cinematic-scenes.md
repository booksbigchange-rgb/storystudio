# StoryStudio Cinematic Scenes — Lemo-inspired filmmaking milestone

## Creative direction
Lemo OpusCar's core strength is code-directed films: motivated framing, camera motion, atmospheric cues, readable silhouettes, disciplined style, and sound. This milestone adopts that *workflow*, not the upstream demo footage, characters, rendered movies or proprietary creative content.

## What's new
- Five selectable camera directions in the **Scene** tab: still, push-in, pull-back, pan-left, and pan-right.
- Progressive camera movement, eased by scene-relative time so re-seeking frames is deterministic.
- Light foreground glow/particle atmosphere and background parallax in moving-camera scenes.
- All moves run on Canvas2D and reuse the existing Playwright + FFmpeg engine: no Docker, paid API or GPU.
- The composition is recalculated for landscape (16:9) and portrait (9:16).
- The caption remains screen anchored and readable while the scene moves.

## How to use
1. Open StoryStudio on Windows, select or add a scene.
2. In **Scene** choose **Camera direction**, then choose a move.
3. Click **Apply scene edits** (selection changes also apply automatically).
4. Play or scrub **Live preview**; export MP4 in the Output tab.
5. For deliberate beats, use Character > Set pose keyframes in the previous milestone.

Camera moves apply over the **entire duration of each scene**. To create multiple shots, duplicate a scene, set different durations/camera moves and reorder the scene list. This is not an arbitrary camera keyframe editor yet.

## Compatibility and safety
- Old version-2 StoryStudio projects without `camera` remain valid and retain the exact still camera behavior.
- New scenes have `camera: "still"` by default.
- Unsupported camera modes are rejected before export.
- The new JS file is served by the existing allowlisted local-only HTTP server; it does not expose additional project files.
- Upstream Lemo animation helper attribution remains preserved in `integrations/lemo-lite/LICENSE-LEMO.md`.

## Validation
Windows CI must pass unit tests, actual browser frames with distinct camera compositions, deterministic seeking, portrait/landscape MP4 exports, sound, GUI checks and the portable EXE packaging test. Manual assessment of animation quality and on-device performance is still needed before any public release.

## Future improvements
1. Import artist-created backgrounds and layered props.
2. Custom camera keyframes with stage overlays (not presets alone).
3. Scene art direction: lighting palette, compositions, shadows, transition staging.
4. Dialogue timing, sound/music mix, facial acting/lip-sync.
5. Build episode templates and a repeatable low-cost film pipeline.
