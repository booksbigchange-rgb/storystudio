# StoryStudio 2.0 — Portable Windows Beta

This is a **first portable prototype**, not a finished animation editor or official release.

## Use on Windows 10/11

1. Download the `story-studio-windows-portable` artifact from the successful Windows Portable workflow.
2. Extract **every file** into a folder on D:, for example `D:\StoryStudio-Portable`. Keep `_internal` and `bin` beside `StoryStudio.exe`.
3. Double-click `StoryStudio.exe`. Use **Open Live Preview** to play and scrub the fox-and-star cartoon in Edge/Chrome.
4. Use **Export MP4** to choose a save location and quality.
5. Logs, cache and exports remain in the portable folder wherever possible.

**No Docker, Python, Node, WSL, cloud AI credits or paid apps required for these offline functions.** The computer needs a compatible Microsoft Edge or Google Chrome installation. The bundle includes FFmpeg and FFprobe, but not a standalone browser.

Windows may warn about unsigned executables. Do not bypass a security warning without independently verifying the release source; this prototype is not code-signed.

## Included
- Portable executable with local GUI and browser preview.
- Animation rendering from an original 10-second Lemo-style code-driven scene.
- MP4 export with procedural sound effects and full-decode verification.
- Local output folders and basic dependency diagnostics.

## Not included
- Full Lemo 43-style gallery/engine, full visual editor, complex character rigs, AI scene generation, or multi-scene timeline.
- Local Kokoro narration model, which remains in existing D:\StoryStudio.
- Verified performance on the user's specific Windows Ryzen 3 laptop.

## License and distribution
- Selected motion helpers adapted from Lemo OpusCar: MIT; see `licenses/LICENSE-LEMO.md`.
- FFmpeg binary: upstream https://ffmpeg.org/download.html ; binary source https://www.gyan.dev/ffmpeg/builds/ .
- Playwright: Apache 2.0; PyInstaller: GPL plus exception; Python: PSF; all original scene artwork is generated in code.
- Before **general public redistribution**, confirm the exact FFmpeg build license obligations and corresponding source-code availability. Retain all included notices.
- Lemo demo movies and third-party demo artwork are not included.

## Troubleshooting
- No browser: use a compatible installation of Edge or Chrome.
- Export problem: inspect `logs/last-export-error.log`.
- Memory tight: try the lower-resolution preview preset; close other video apps.
- C: almost full: extract and export on D:.
