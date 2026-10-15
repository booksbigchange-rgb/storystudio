# StoryStudio 2.0 development audit — 15 October 2026

## Baseline

Requested branch: `feature/story-studio-portable-windows`, starting commit
`06470a8391b4e27cd7241dd2d341946c8bdb9d78`. Existing draft PR: #4.
The branch contains the portable Tk launcher and deterministic Canvas2D Pip scene,
not the layer/keyframe editor from `feature/2d-animation`. The older branch remains
intact. No merge into main, reset, user-project migration or source-artwork edits.

Preserved: offline Canvas-to-FFmpeg pipeline, original Pip/story motion, Lemo MIT
helpers, 16:9 output, imported audio, frozen executable paths and D: tool setup.
Kokoro, Synfig, Krita and Kdenlive scripts remain untouched.

## Changes under validation

- Light Windows editor: scene list, real browser-rendered frame preview, timeline,
  scene/character/output tabs, persistence and keyboard shortcuts.
- Version 2 JSON schema, bounded scene counts/duration, relative audio paths,
  atomic saves and validation without modifying the source document.
- Original reusable fox/rabbit/bear cutout rigs, four expressions, six motion
  presets, automatic blinking, position/size/speed controls and three backdrops.
- Multi-scene story playback; deterministic render(t) shared by preview/export.
- 16:9 and recomposed 9:16, 720p/24fps and 360p/12fps presets.
- Queued worker UI updates, export progress and cancellation; one browser at a time.
- Atomic verified exports, padded short audio, explicit video/audio mapping,
  bounded dimensions, two encoder threads and full decode checks.
- Real GUI, browser, render, audio, cancellation and packaged executable tests.

## Automated local findings

12 headless unit tests passed with normal Windows file permissions. The restricted
sandbox stalled tempfile tests; the identical suite passed outside that sandbox.
Local Chrome and the existing D: FFmpeg ran the render suite. Both 720p orientations
passed with 48 decoded frames at 24fps, H.264/yuv420p/AAC, non-silent audio and full
decoding. The suite also tests deterministic seeking, distinct rigs/expressions/
actions, scene switching, cancellation and short-audio padding.

Real narration was generated using the existing D: Kokoro model (4.565 seconds).
It was imported into the regression exports. This is narration generation and
export verification, not listening-quality or intelligibility certification.

The GUI test uses real Tk controls, actual browser rendering and actual export,
with file dialogs supplied deterministic temporary test paths. It runs at 1000x680
and 1366x768. Windows DPI coordinates were corrected after visual inspection found
a cropped capture. This is automated testing on this Windows host, not a manual
user acceptance session or a sustained Ryzen 3 thermal/performance benchmark.

## Repairs prompted by checks

- FFmpeg 9 emitted full-range YUV despite the pixel-format option. Explicit range
  conversion fixed the H.264 compatibility check; the full regression suite passed.
- Per-monitor DPI handling aligned screenshot/window coordinates.
- Compact scene-action buttons prevent text clipping in the left rail.

## CI and deliverables

The Windows workflow records dependency URLs/hashes, verifies the FFmpeg archive
against the publisher checksum, synthesizes real Windows offline narration, runs
source tests, builds the EXE, then tests its GUI and both export formats using its
bundled FFmpeg. MP4s, screenshots, JSON evidence and checksums are uploaded separately.
The portable artifact is published only after every required check succeeds.
See the final development report for the exact run, commit and artifact results.

## Remaining boundaries

No full rigging editor, arbitrary artwork import, lip sync, undo stack or painterly
animation. Browser preview is silent. Imported audio must travel with saved projects.
No GPU or Docker dependency. No paid services or local replacement runtimes.
All local installs and output files stay under D:\StoryStudio. Hosted CI tool paths
are GitHub-managed and are not installations on the user's computer.
