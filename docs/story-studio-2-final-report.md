# StoryStudio 2.0 — final development report

**Date:** 15 October 2026 (Africa/Nairobi)  
**Working branch:** `feature/story-studio-portable-windows`  
**Tested application commit:** `766646f2eb663d62c41422a7393c69dd612ab0c3`  
**Draft PR:** https://github.com/booksbigchange-rgb/storystudio/pull/4  
**Successful Windows run:** https://github.com/booksbigchange-rgb/storystudio/actions/runs/38638678990

## Outcome

The portable prototype is now a working multi-scene cartoon editor. All required
source and compiled Windows checks passed on the final application commit. The PR
remains a draft against its existing `feature/story-studio-2-lemo-lite` base. Nothing
was merged into main. Existing user projects, source artwork, Kokoro models and
Synfig/Krita/Kdenlive installations were not modified.

## Milestone results

| Milestone | Delivered | Automated evidence |
|---|---|---|
| Audit / preservation | Audited the requested branch at `06470a8`; retained offline render and narration toolchain; older 2D editor branch left intact | Git diff, schema preservation and source tests; audit document |
| Windows interface | Light workspace, scene list, frame preview, timeline, Scene / Character / Output tabs, keyboard shortcuts, progress and cancel | Real Tk controls, 1000×680 and 1366×768 layouts, save/open and actual GUI export; source and EXE |
| Reusable characters | Fox, rabbit, bear; happy/curious/sad/surprised; story/idle/wave/walk/jump/talk; blink, position, size, speed; three backdrops | Deterministic seek, distinct rendered rigs/expressions/actions, no browser JavaScript errors |
| Vertical / landscape | Re-composed 9:16 and preserved 16:9; 720p/24fps and draft 360p/12fps | Both 720p formats rendered in source; both orientations plus GUI portrait export from compiled EXE |
| Regression suite | 12 unit tests plus real GUI/browser/render/audio checks | All required Windows workflow steps passed |
| Executable | Python-free portable Windows folder, bundled FFmpeg/FFprobe, existing Chrome/Edge | PyInstaller build; EXE GUI + MP4 tests with source FFmpeg override removed |
| Failure repair | YUV color-range compatibility, Windows short-path audio links, DPI capture geometry, scene buttons, scoped browser profile | Repaired checks rerun; final full Windows CI passed |
| Artifacts / report | Tested executable, verification package, local narrated demo, this report | GitHub artifact digests, MP4 decode and local demo checksums |

## Downloads

- [Tested Windows executable ZIP — 130.2 MiB](https://github.com/booksbigchange-rgb/storystudio/actions/runs/38638678990/artifacts/11929322648)
- [Windows verification evidence — 793 KiB](https://github.com/booksbigchange-rgb/storystudio/actions/runs/38638678990/artifacts/11929647449)
- Local demo ZIP: `D:\StoryStudio\exports\story-studio-2-demo.zip` (about 593 KiB).
- Local editable demo folder: `D:\StoryStudio\exports\story-studio-2-demo`.
- Local source launcher: `D:\StoryStudio\Open-StoryStudio.cmd`.
- Local verified executable ZIP: `D:\StoryStudio\exports\StoryStudio-2.0-Windows-766646f.zip`.
- Local compiled-app launcher: `D:\StoryStudio\Open-StoryStudio-Portable.cmd`.
- Local compiled-app evidence: `D:\StoryStudio\exports\portable-local-validation-766646f.zip`.

GitHub downloads require access to the repository. Current artifacts expire on
**29 October 2026 at about 00:16 EAT**. Save the ZIP before expiry or rerun the workflow.
Extract the entire Windows ZIP into a writable folder under D:\StoryStudio, keeping
`_internal` and `bin` beside `StoryStudio.exe`. The executable is unsigned.

GitHub-reported SHA-256:

```text
Windows ZIP: 0916caafe9046d79f98d35f135698f848fb5187951c9715db73ba1a7b42e6220
Evidence ZIP: 3d2b062226c7fd0c9cf069303a819b0b9ab99ca28478bb044d82706f0dd5d125
Local demo ZIP: afa4c6a7be88252e0dec79ea9f78a1c9ad0967b79ea0a1958eafefd65ca81b56
```

The complete Windows ZIP was downloaded locally and matched the GitHub SHA-256.
All 1,429 extracted files matched the CI checksum manifest. The verified executable
is in `exports/portable-766646f`; the root portable launcher scopes its environment
to D:. The final CI evidence ZIP also matched its digest. Its source/compiled GUI
reports and render report all say PASS; GUI screenshots were inspected.

## What the automated checks actually established

- Project validation, immutable input handling, relative audio round-trips,
  rejected invalid/oversized documents and atomic-save failure preservation.
- Deterministic same-time frames even after seeking elsewhere; visible movement,
  scene transitions, three distinct characters, all expressions and actions.
- Actual 1280×720 and 720×1280 H.264/yuv420p videos at 24fps, with AAC sound.
- Correct 48-frame counts for two-second source regression clips; full decoding,
  changing decoded frames, non-silent decoded audio and audio spanning the story.
- Cancellation after encoding starts preserves an existing destination and removes
  staging files. A half-second audio file is padded to the two-second story length.
- Real desktop widgets add/duplicate/remove/reorder scenes, edit controls, save/open
  projects, change format, show a real browser-rendered frame and export an MP4.
- Compiled executable tests run without relying on the source FFmpeg override.
- Live preview launch arguments use a studio-local browser profile; that particular
  launch-path assertion is mocked. Capture rendering and GUI MP4 export are real.
- CI records exact dependency URLs/hashes and FFmpeg version/provenance, and checks
  the FFmpeg archive against its publisher checksum.

The local six-second demo contains all three characters, both video orientations,
editable JSON and **real offline Kokoro narration**. It is a procedural cartoon,
not a painterly artwork or arbitrary character-rigging demonstration. The narration
WAV is 4.565 seconds; the remainder is padded. Local generation took 9.61 seconds.
CI separately used real Windows offline speech for its audio fixture.

## Testing on this computer versus hosted CI

The local Windows machine was identified as **AMD Ryzen 3 5425U with Radeon Graphics**,
with **11.36 GiB reported physical memory** (the nominal 12 GB configuration).
Local source GUI, Chrome rendering, FFmpeg exports and Kokoro generation were tested
automatically. The downloaded compiled executable also passed its real GUI tests
on this computer: laptop geometry, widget edits, scene order, portrait preset,
save/open, browser frame, GUI MP4 export and worker completion.

The compiled app then exported the maximum supported **20 scenes / 120 seconds**
at **720×1280, 24fps**, using its bundled FFmpeg. Export and verification took
**155.86 seconds**, with a sampled peak process-tree working set of **763.1 MiB**
(below the 2 GiB test budget). Independent verification confirmed H.264/AAC,
2,880 frames, full error-free decoding and 20 distinct, nonblank scene samples
with the expected backdrops in order. This test uses the default chimes; the
separate six-second demo verifies real Kokoro narration.

Evidence is in `exports/portable-local-validation-766646f`: `integrity.json`,
`endurance-results.json`, `independent-video-verification.json`, memory samples,
the actual MP4, decoded scene samples, and `gui-20261015-092126/gui-results.json`.
The two-minute MP4 SHA-256 is
`5f96a12c1952d49bc3482390c7a0b6f15317a4a99ded7bf84c8e3bf65246c4b7`.
The GUI suite can be rerun with `Open-StoryStudio-Portable.cmd -GuiTest`.

A local six-second, 720×1280, 24fps portrait render and verification took **16.13 seconds**.
The maximum sampled sum of process-tree working sets was **706.24 MiB**. Sampling was
approximately every 400ms; shared pages may be counted more than once. This is a
short smoke measurement, not a sustained thermal, long-project or battery benchmark.
The evidence is `exports/studio-2-validation/hardware-smoke.json`.

## Constraints and remaining scope

- $0 additional services; no paid API, Docker, WSL, GPU requirement or new large model.
- Local wheels, caches, logs and exports are under D:\StoryStudio. The live preview
  now uses a separate profile there; it does not reuse the normal browser profile.
- One capture browser at a time, two FFmpeg encoder threads, streamed frames, no
  full frame sequence held in memory. The live player may run as a separate browser.
- Reuses installed Chrome/Edge and the existing D: Python/FFmpeg/Kokoro tools.
- JSON projects reference audio rather than embedding it; move audio with the project.
- Up to 20 scenes and 120 seconds. Live preview is silent; sound is in the export.
- No imported-artwork rigging, per-limb keyframe editor, lip sync, undo history,
  soundtrack mixing or transition editor. The separate legacy 2D editor is not
  silently migrated into this portable app.
- Manual usability, listening quality, repeated-export thermal/battery endurance,
  and installation on other physical computers remain untested. The maximum-length
  project passed on this computer; that does not establish those separate checks.

## Repairs and traceability

1. Explicit JPEG-to-limited-range YUV conversion fixed the real FFmpeg pixel-format failure.
2. CI run `38637738578` found Windows `RUNNER~1` short-path normalization was needed
   before calculating relative audio paths. The next full run passed.
3. DPI awareness aligned actual window and screenshot coordinates; compact scene
   buttons fixed observed text clipping.
4. Final commit `766646f` isolates live browser profiles beneath the portable workspace.
   Its full Windows run `38638678990` passed.

The code uses original procedural artwork with the already-vendored MIT Lemo
helpers. Upstream reference: https://github.com/lemomo-ai/lemo-opuscar . License
notices are retained. No upstream demo films, music or stock artwork were copied.
