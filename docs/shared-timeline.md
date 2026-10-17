# Shared timeline milestone — 16 October 2026

Open `Open-StoryStudio-Unified.cmd`, then **Shared timeline**.

1. Add a saved documentary project and/or character project.
2. Select sections in the list or duration strip; use Move up/down or Remove.
3. Use Edit source to change scenes in the appropriate editor, then save there.
4. Save this timeline as a new JSON file. It stores relative project links.
5. Choose widescreen or portrait and export to a new MP4 filename.

## What is combined

The mixed version-1 format has an explicit `storystudio-mixed` identifier,
avoiding the legacy version-2 collision. One timeline holds up to 20 source
projects, with a maximum export duration of 10 minutes. Each section retains
its source scene order and its renderer's audio behavior. The strip displays
current source durations; export independently validates the source projects.

Both renderers export sections in isolated processes. Validated project settings
are snapshotted before rendering; linked media itself is not copied or frozen.
Keep source media available and unchanged during export. Output is 720p at 24 fps,
with aspect-preserving fitting and black padding where necessary, H.264 video and
AAC stereo audio. Silent sections receive silence. Source audio is padded or
trimmed to its section; sections join with hard cuts.

The output is fully decoded and its dimensions, duration, audio and frame count
checked before atomic no-overwrite publication. This publication requires a file
system supporting hard links (tested on the local D: NTFS drive).
Per-run source snapshots, intermediate videos and diagnostic logs remain in
`exports/mixed-run-*` for inspection. These consume disk space; automatic cache
cleanup is not part of this milestone.

## Verification

- 57 unit tests passed, including format routing, persistence, ordering, invalid
  documents and protection against saving over a linked source project.
- Real Tk add/reorder/save/reopen checks passed; updated duration-strip startup passed.
- An 11-second widescreen export joined the existing narrated noir demonstration
  to a 2-second animated bear test; 264 frames, full decode and audio-span checks passed.
- A 3-second portrait export joined a silent documentary section to character
  audio; 72 frames and full decode passed.
- Original noir project hash stayed unchanged; a second export to an existing
  filename was rejected and its hash remained unchanged.
- Decoded frames from both sections were visually inspected. This is a technical
  compatibility demonstration, not a coherent finished dark documentary.
- Final repeatable-run evidence: `exports/mixed-acceptance-9864ab03910340d68d14bae694865da3/`.
- Repeat with `Verify-Mixed-Timeline.cmd`; each run uses a fresh output folder.

## Still outside this milestone

This is section-level sequencing, not a single scene/limb editor. No crossfades,
shared soundtrack, undo, live mixed playback or
mixed portable executable yet. The window blocks editing/closing during export;
**Cancel export** stops its process tree and restores editing; see
[cancellation validation](mixed-export-cancellation.md).
individual source editors retain their existing capabilities. Manual listening,
another-computer validation and the full 10-minute endurance case remain untested.

Timed titles, dates, source labels and captions are now implemented across both
renderers; see [timed text instructions and validation](timed-titles.md).
