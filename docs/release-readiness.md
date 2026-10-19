# StoryStudio release readiness checklist

This branch starts from `feature/unified-story-studio`. Do not merge into `main` until the gates below pass.

## Current architecture
- Workspace launcher: `engine/studio_hub.py`; documentary, cartoon and mixed editors are separate processes.
- Cartoon renderer: `integrations/lemo-lite/`.
- Mixed export: `engine/mixed_worker.py` and associated render/control modules.
- Windows CI: `.github/workflows/story-studio-unified.yml`.

## Release gates
- [ ] Run the unified Windows workflow on this branch; verify unit and real GUI/render integration tests.
- [ ] Confirm a real user can launch the workspace and locate Export without a command line.
- [ ] Save, close, reopen and export an editable cartoon project and mixed project.
- [ ] Verify MP4 with ffprobe and full decode; check audio, aspect ratio and frame count.
- [ ] Test cancellation and retry; never overwrite a successful export with a failed attempt.
- [ ] Confirm assets and browser caches stay under the intended D: workspace where feasible.
- [ ] Produce a fresh downloadable portable Windows artifact and verify its contents.
- [ ] Manually inspect UI on 1366x768 and 1000x680 and test on a second Windows computer if available.
- [ ] Review licensing and notices for redistributed dependencies.
- [ ] Update README with a single first-run path, known limitations, and release download.

## Known limitations to preserve in documentation
The earlier portable beta report does not claim imported-artwork rigging, per-limb keyframes, lip sync, undo history, soundtrack mixing, or manual cross-machine usability testing. Do not advertise these as complete without new evidence.

## Branch policy
Keep `main` unchanged. Make isolated, reviewed changes here and merge only after acceptance evidence is available.
