# StoryStudio 2.0 — Lemo-lite portable editor

This integration uses Lemo OpusCar's deterministic `window.render(t)` convention
and selected MIT motion helpers. The reusable character artwork is original.
No cloud generation, Docker, GPU, Node runtime or full Lemo installation is needed.

Read [the editor guide](PORTABLE-README.md) for features, controls and limitations.
From the repository root, use `Open-StoryStudio.cmd`. It loads the existing
`launchers/environment.ps1` and D: Python environment. Playwright 1.55.0 and Pillow
are required in that environment. Use existing Chrome/Edge; do not download a
second browser. Keep dependency downloads and logs beneath D:\StoryStudio.

## Automated checks

Load `launchers/environment.ps1` before these commands:

```powershell
& .\engine\.venv\Scripts\python.exe -m unittest discover -s integrations/lemo-lite/tests -v
& .\engine\.venv\Scripts\python.exe integrations/lemo-lite/tests/render_regression.py --output exports/regression
& .\Open-StoryStudio.cmd --gui-test --output D:\StoryStudio\exports\gui-regression
```

The Windows workflow runs those checks, builds with PyInstaller, and tests the
compiled executable. Use fresh output folders for packaged `--self-test`, which
refuses to overwrite existing MP4s. The GUI file-save dialog asks before replacement.

For command-line exports use `renderer.py --project my-cartoon.json --duration 10
--width 1280 --height 720 --fps 24 --output exports/my-cartoon.mp4`. Set duration
and dimensions to the desired project export. Without `--project`, the original
10-second Pip story preset is used. `--audio` overrides project audio. `--overwrite`
is opt-in; failed/cancelled exports preserve existing destinations.

## Implementation

- `project.py`: validation, presets, atomic saves, referenced audio paths.
- `studio_ui.py`: Windows Tk editor and main-thread event queue.
- `renderer.py`: single-browser capture, streamed FFmpeg encoding, verification.
- `scene/characters.js`: reusable cutout rigs and deterministic action poses.
- `scene/scene.js`: multi-scene playback and aspect-aware composition.
- `gui_regression.py` and `tests/`: source and packaged checks.

The standalone editor does not replace the separate Synfig/Krita/Kdenlive workflow.
Legacy projects and artwork are retained. See `LICENSE-LEMO.md` for upstream notice.
