# StoryStudio 2.0 — Portable Windows beta

Extract every file into a writable folder on D:, such as `D:\StoryStudio\portable-beta`.
Keep `_internal` and `bin` beside `StoryStudio.exe`. Open the executable to start.
No Python, Node, Docker, model download, account or paid service is needed. Use an
existing Edge or Chrome installation. The bundle includes FFmpeg and FFprobe.

## Create a cartoon

1. Choose **Scene** to edit the caption, length and background. Apply scene edits.
2. Choose **Character** for fox, rabbit or bear. Pick an expression and motion.
   Position, size and speed can be adjusted; press Apply character edits.
3. Add, duplicate, remove or reorder scenes in the left panel (up to 20 / 120 seconds).
4. Click the timeline or scrub, then **Refresh frame**. **Play live preview** opens
   a real-time browser player with the same project snapshot. Reopen after editing.
5. Choose **Output**: landscape 16:9 or Shorts / TikTok 9:16; Standard 720p/24fps
   or Draft 360p/12fps. Portrait is composed separately without stretching characters.
6. Optionally import local narration or music. Audio starts at zero; short tracks
   are padded and long tracks trimmed. The browser player is silent. Default
   chimes are sound effects, not narration. Existing Kokoro WAV files work here.
7. Save the JSON project. Ctrl+S saves, Ctrl+O opens, Ctrl+E exports.
8. Export MP4. The app checks H.264/AAC, dimensions, FPS, frame count, audio duration
   and full decoding before replacing a destination. Cancel preserves existing files.

## Storage and compatibility

Exports, logs and temporary files live beside the portable executable. Project
files and exports use your chosen save paths. Keep them on D:. Audio is referenced
by path, not embedded: copy it along with the project when moving to another PC.
Source projects use the version 2 JSON format; legacy Synfig/artwork files and
projects from the separate 2D editor branch are not converted or overwritten.

One capture browser is used at a time and frames stream directly to FFmpeg (two encoder
threads), with no image sequence accumulated in RAM or on disk. Use Draft for
quick checks. A Windows CI pass is not a hardware performance guarantee.
The live player opens a separate browser profile beneath this studio's `cache`
folder and closes with the editor. Your normal browser profile is not used.

## Scope

Three original procedural cutout rigs, four expressions, six motion presets and
three backgrounds are included. This is a small cartoon editor, not a painterly
rigging application or the complete Lemo style gallery. No imported-artwork rigging,
per-limb keyframe editor, lip sync, transitions, soundtrack mixing or undo history
is included. Save copies before exploratory edits. Narration generation remains
in the existing local Kokoro tools; the portable bundle imports finished audio.

## Verification and troubleshooting

The `story-studio-validation` workflow artifact contains actual MP4s, GUI captures,
JSON checks, dependency provenance and bundle hashes. The portable ZIP is uploaded
only after source and compiled GUI/render checks pass. Artifacts expire after 14 days.
The beta executable is unsigned. Export failures are recorded in
`logs/last-export-error.log`. For missing browser errors, install Edge/Chrome or set
`STORYSTUDIO_CHROME` for the current launch only.

## Notices

Selected Lemo interpolation helpers: MIT, copyright LemoLab 2026; see
`licenses/LICENSE-LEMO.md` and https://github.com/lemomo-ai/lemo-opuscar . Character
art and animation code are original. No upstream demo footage/art/music is bundled.
Playwright: Apache-2.0. Pillow: HPND. Python: PSF. PyInstaller: GPL with bootloader exception.
Package metadata and distribution notices remain inside `_internal`.
FFmpeg: GPL-enabled Gyan build, https://www.gyan.dev/ffmpeg/builds/ ; upstream
https://ffmpeg.org/ . Publisher archive checksum, exact binary version and download
URL are in `provenance/ffmpeg-provenance.json`; dependency URLs and hashes are in
`provenance/build-dependencies.json`. Retain notices and corresponding source access
when redistributing. This artifact is a development beta, not a signed public release.
