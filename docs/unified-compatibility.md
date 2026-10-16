# StoryStudio compatibility integration — 16 October 2026

Branch: `feature/unified-story-studio`, based on portable commit `9d8c3c4`.
Documentary engine restored from `feature/desktop-mvp` commit `14b87b5`.

## Entry point

Run `Open-StoryStudio-Unified.cmd` to select Documentary or Character animation,
or open a saved project. Existing launchers and portable executable remain intact.
The new launcher is source-only; the existing packaged EXE does not contain it.

## Compatibility review

| Area | Documentary | Character animation | Integration decision |
|---|---|---|---|
| Project | Versions 1–5, image scenes | Version 2, rig scenes | Inspect scene structure as well as version; never silently convert |
| Rendering | Pillow layers and FFmpeg camera | Browser Canvas2D and FFmpeg | Keep both tested renderers |
| Audio | Narration + music with trim, gain, offset, repeat | One soundtrack | Preserve each contract |
| Size | 1080p, 24 fps | 720p/24 or 360p/12 | Retain existing export choices |
| Editing | Undo, camera keys, independent artwork layers | Character/expression/action presets | Separate workspaces under one launcher |
| Imports | Modules named project, local engine imports | Also project, plus renderer | Separate child processes prevent module collisions |

This initial compatibility checkpoint provided a combined entry point and source tree, not a single mixed-scene
timeline. Character scenes cannot yet become editable documentary layers. Neither
existing project format can represent all features of the other. The subsequent
shared-timeline milestone adds an explicit section format and renderer dispatch
without converting legacy scenes; see `shared-timeline.md` for current capabilities.

## Verification

- 54 documentary and launcher unit tests passed.
- All 11 documentary verification groups passed, including actual Tk checks,
  narration, both dimensions, cancellation and fully decoded master MP4.
- 12 character-editor unit tests passed with normal Windows access. An initial
  restricted-token run stalled and was interrupted; it is not counted as a pass.
- Shared launcher and both editor startup smoke checks passed.
- Report: `exports/verification-runs/run-4a8cd93554fb49c9b71b154e0f8c168c/report.json`.
- Character render regression: `exports/unified-compatibility-20261016/`.
  Passed deterministic seeking, all three rigs, expressions/actions, both 720p
  formats, decoded animation/audio, cancellation and short-audio padding.
- Opening the existing widescreen noir project through the shared dispatcher
  passed a real Tk startup/load smoke check.

## Remaining milestones

1. Section-level mixed timeline is now implemented; see `shared-timeline.md`. Individual scene unification remains later work.
2. Timed titles, dates, sources and captions are implemented; see `timed-titles.md` for validation and limits.
3. Documentary templates: evidence desk, chronological timeline and maps.
4. Layer interior keys, anchors, masks and camera-linked depth.
5. Shared narration/music/SFX mixing with ducking.
6. Longer-story management and endurance tests beyond the cartoon 120-second limit.
7. Expand reusable rigs to the documentary visual style; imported rigging and lip-sync.
8. Package the combined application and validate on another computer.

The existing cartoon rigs and portable packaging are already present; their
existence does not mean mixed-scene editing or the documentary release is done.
Manual listening, usability and another physical computer remain separate checks.
