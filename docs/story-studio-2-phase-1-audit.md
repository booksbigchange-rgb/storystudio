# StoryStudio 2.0 — Phase 1 Audit (2026-10-14)

## Repositories examined
- StoryStudio: https://github.com/booksbigchange-rgb/storystudio (main at 961b0a0acb1bb1ba28ef53ffeb77e3b4ffd1d82c before development)
- Lemo OpusCar: https://github.com/lemomo-ai/lemo-opuscar (MIT license, copyright LemoLab 2026)

## Existing StoryStudio capabilities to preserve
- engine/create_test.py generates an editable Synfig starter scene.
- engine/narrate.py and engine/phonemes.py drive offline Kokoro speech.
- Windows launchers for Synfig, Krita and Kdenlive.
- D: environment redirection in launchers/environment.ps1.
- FFmpeg and Kokoro runtime documented as provisioned locally; binaries/models are ignored by Git and not on GitHub.
- Existing AGENTS.md forbids moving user project files, installing heavy local models or modifying upstream tools.

## Upstream Lemo review
- core/lib.js: deterministic easing/keyframe/math helpers. MIT; selected code integrated in integrations/lemo-lite/vendor/.
- core/render/video.mjs: screenshot-by-frame into FFmpeg. Uses Node 20+, playwright-core, normally multiple browser workers. A design reference, not transplanted.
- core/render/page.mjs: serves HTML, waits for window.READY, calls window.render(t). Pilot uses these conventions through Python.
- TECHNIQUE.md: music, voice, captions, quality checks, multiple styles. Full stack and optional 3D/post-processing not part of Phase 1.
- plugin/skills/lemo-opuscar/scripts/setup.sh uses sh, Unix virtualenv paths, sparse cloning and can hard-reset its own managed clone. Avoid running it on D:/StoryStudio.
- Upstream demo footage, art and music not copied; independently licensed and may have third-party rights.
- OpusCar is an agent-oriented filmmaking toolkit, NOT a turnkey desktop editor.

## Compatibility and resource decisions
- Target: Ryzen 3 5425U, Radeon integrated GPU, 12 GB RAM.
- CPU-friendly Canvas2D only, output 720p/24fps; 2s smoke render on slow machines.
- Python Playwright uses existing Chrome/Edge. No WSL, Docker or 3D.
- FFmpeg and FFprobe reused from D: runtime; --audio accepts Kokoro WAV and test mode synthesizes original chimes.
- Local cache/storage should stay under D:/StoryStudio by loading launchers/environment.ps1.
- No paid AI API, full 43-style clone or large model download.
- Repo changes isolated to feature/story-studio-2-lemo-lite; user local files untouched.

## Review gates
1. Python compile and Node syntax checks for scripts.
2. Playwright scene load: READY true, DUR positive, no JavaScript exception.
3. MP4 export with audio, correct dimensions/duration/fps, FFprobe metadata.
4. Full MP4 decode via FFmpeg.
5. Download pilot artifact from CI and inspect visually.
6. Benchmark on Windows Ryzen 3 with D: drive before merge.

## Limitations
- No visual timeline editor, character rig library, multi-scene export or all Lemo styles yet.
- Linux CI test does not establish Windows runtime performance.
- Local sandbox browser access was blocked by administrator policy; use CI and Windows for render checks.
- main remains unchanged until smoke test, visual review and Windows test pass.
