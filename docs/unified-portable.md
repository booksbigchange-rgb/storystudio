# Unified portable Windows build

A new, separate build of the unified application. The earlier character-only build
(`exports\portable-766646f`) is never touched: the installer writes only to a **new** folder named
`exports\unified-portable-<version>` and refuses to continue if that folder already exists.

## What it contains

| Program | Role |
|---|---|
| `StoryStudio.exe` | hub, documentary editor, shared timeline (with audio mix, timed text, 200 sections) |
| `character\StoryStudioCharacter.exe` | character editor (animation keys, presets) |
| `StoryStudioWorker.exe`, `character\StoryStudioCharacterWorker.exe` | hidden export helpers |
| `bin\ffmpeg.exe`, `bin\ffprobe.exe` | official FFmpeg build, publisher checksum verified at build time |

Two program groups are needed because the documentary and character editors each contain a module named
`project`; each group has its own runtime. They share one top folder for projects, exports, temp, logs and FFmpeg.
Nothing is installed on C:, no Docker, no cloud rendering.

## Install and start (on your computer)

1. Download the `story-studio-unified-portable` artifact from the GitHub Actions run (a zip containing the
   build zip, its `.sha256`, `MANIFEST.json`, `SHA256SUMS.txt`, `BUILD-REPORT.md`, `VALIDATION-SUMMARY.md`).
   Save them to a folder under `D:\StoryStudio`.
2. `Install-StoryStudio-Unified-Portable.cmd -Zip "D:\StoryStudio\...\StoryStudio-Unified-<version>-windows-portable.zip"`
   - checks the zip's SHA-256 against the `.sha256` file beside it (or `-Sha256 <hash>`),
   - extracts into a hidden staging folder, verifies every file against `SHA256SUMS.txt`,
   - then renames it to `exports\unified-portable-<version>` and writes `exports\unified-portable-<version>.install-report.txt`.
3. `Open-StoryStudio-Unified-Portable.cmd` starts the newest installed build (`-Version <v>` for a specific one).
   `Open-StoryStudio-Unified-Portable.cmd -SelfTest` runs the build's built-in check into
   `exports\unified-portable-validation-<version>-<time>` (never reused).

The launchers load `launchers\environment.ps1` unless `-StudioRoot` is given.

## Artifact set

`release/` in the Actions artifact: `StoryStudio-Unified-<version>-windows-portable.zip`, `…zip.sha256`,
`MANIFEST.json` (every file, size, SHA-256, tool provenance, commit, run id), `SHA256SUMS.txt`
(`sha256sum`-style, includes the manifest and report), `BUILD-REPORT.md`, `VALIDATION-SUMMARY.md`.

## What the workflow verifies automatically

Workflow `story-studio-unified-portable.yml` on a clean Windows runner: syntax, unit tests; builds both groups
with PyInstaller 6.16.0; tests **the compiled programs** on a copy (unified self-test: real Tk editors, audio-mix
dialog, a documentary+character timeline exported through the compiled helper programs, protection of an
existing file, H.264/AAC 1280x720 frame count and full decode; character GUI test; two compiled character exports,
decoded); creates manifest/checksums/report; zips; then installs with **Windows PowerShell 5.1** into a fresh folder:
first install succeeds with all files verified, a second install over the same version and a wrong checksum are both
refused, a pre-existing `portable-766646f` folder is untouched, no staging folder remains, and the installed copy
passes its own self-test.

## Not verified automatically

- Your computer (Ryzen 3, 12 GB, integrated graphics, display scaling, Defender/SmartScreen on unsigned exes).
- Real projects, long renders, and how mixes and animation sound/feel.
- Character rendering needs Microsoft Edge or Chrome already installed.
- Installation under `D:\StoryStudio` itself. The workflow only checks that the longest packaged path fits within
  Windows' 260-character limit when installed at `D:\StoryStudio\exports\unified-portable-<version>\`.
