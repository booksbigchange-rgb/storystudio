# StoryStudio 2.0 — Lemo-lite (Phase 1 pilot)

An isolated, original 10-second Canvas 2D cartoon built around **Lemo OpusCar's deterministic window.render(t) approach** and its MIT-licensed interpolation helpers (vendor/lemo-lib.js). No AI/cloud service or 3D model is needed at render time.

Nothing replaces Synfig, Krita, Kdenlive, FFmpeg, Kokoro or the existing native .sif test. No D: configuration, user projects, installers or main branch files are modified. This is an **integration pilot**, not the full 43-style application or a visual timeline editor.

## Windows installation (keep everything on D:)

From PowerShell after checking out the feature branch into D:\StoryStudio, run:

1. Load the existing environment: . .\launchers\environment.ps1
2. Install Playwright in the *existing* Python virtual environment: .\tools\uv\uv.exe pip install --python .\engine\.venv\Scripts\python.exe playwright
3. Render: .\engine\.venv\Scripts\python.exe .\integrations\lemo-lite\renderer.py --overwrite

If uv.exe is in a different folder, use its real location, or run the environment's python.exe -m pip install playwright (when pip is available).

Chrome or Edge must already be installed; no additional browser download is needed locally. Chrome can be specified with STORYSTUDIO_CHROME and FFmpeg with STORYSTUDIO_FFMPEG. Dependencies: Python 3.11+, Playwright Python, Chrome/Edge, FFmpeg and FFprobe. **No Node, Docker, WSL, or paid model is needed for this pilot.**

## Browser preview without exporting

From the D:\StoryStudio folder:

1. Load the existing environment: . .\launchers\environment.ps1
2. Run: .\engine\.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1 --directory .\integrations\lemo-lite
3. Open http://127.0.0.1:8765/scene/ in a browser. Use Play and the scrub slider. Stop the server with Ctrl+C.

## Export and verification

- Default: 10 seconds, 1280×720, 24 fps. Use --overwrite only when intended.
- Smoke test: --duration 2 --width 640 --height 360 --fps 12 --overwrite
- Existing narrated WAV: --audio D:\StoryStudio\exports\narration.wav
- Output defaults to D:\StoryStudio\exports\lemo-pip-test.mp4 when placed in that project directory.
- Audio defaults to newly synthesized original chime cues, **not narration**.
- Verification checks dimensions, duration, FPS, video and audio streams, and decodes the whole output.
- CI test: .github/workflows/lemo-lite-smoke.yml, on the feature branch. It exports both 2-second and 10-second examples and uploads the MP4 files as a short-lived workflow artifact.

## License and limitations

The upstream project is https://github.com/lemomo-ai/lemo-opuscar. The selected interpolation helpers are from its MIT-licensed core/lib.js, acknowledged in LICENSE-LEMO.md. The fox and star art is original and procedural. The full OpusCar engine and its 43 sample films **have not** been imported.

The renderer runs one original scene. Supporting more styles/scenes and measuring actual Ryzen 3 Windows performance are future milestones. Do not claim that a hosted runner test proves performance on a local Windows laptop.
