# StoryStudio Unified — portable Windows build

One folder, no Python install. Delete the folder to remove it; nothing is written outside it
(settings, logs, exports, temp and projects all live here).

## Start

Double-click `StoryStudio.exe`. Choose a workspace:

- **Documentary templates / Dark documentary** – artwork, camera, layers, audio and timed text.
- **Shared timeline** – combine documentary and character projects (up to 200 sections / 60 minutes),
  add timed text and a shared audio mix (music with ducking, narration, sound effects), export MP4.
- **Character animation** – reusable cutout characters with animation keys and presets
  (all inside `StoryStudio.exe`).

If your studio uses `D:\StoryStudio`, install and start with the root launchers instead:
`Install-StoryStudio-Unified-Portable.cmd -Zip <zip>` then `Open-StoryStudio-Unified-Portable.cmd`.

## Folder map

| Path | What |
|---|---|
| `StoryStudio.exe` | hub, documentary and shared-timeline editors |
| `StoryStudio.exe` | hub plus the documentary, character and shared-timeline editors (one program) |
| `StoryStudioWorker.exe` | background export helper for both engines (no window) |
| `bin\ffmpeg.exe`, `bin\ffprobe.exe` | bundled FFmpeg (checksum-verified official build, see `provenance\`) |
| `projects\`, `exports\` | your work; new exports never overwrite existing files |
| `MANIFEST.json`, `SHA256SUMS.txt`, `BUILD-REPORT.md` | what is inside and how it was tested |

## Needs

- Windows 10/11 64-bit. Everything runs offline. Character export and previews are drawn natively; Microsoft Edge or
  Google Chrome is only used by *Play live preview* (none is bundled).
- Self-check: `StoryStudio.exe --self-test --output <new folder>` (writes `results.json`; exit code 0 = pass).

## Limits and honesty

- Unsigned program: Windows SmartScreen or antivirus may ask for confirmation.
- Character animation is a lightweight 2D cutout system (three built-in characters). It is not painterly
  rigging and has no custom-artwork puppets.
- Character sections render at roughly 30 ms per 720p frame on a modern PC (see docs/native-renderer.md); slower machines take longer.
- Automated tests ran on a clean GitHub-hosted Windows machine; see `BUILD-REPORT.md`. Test on your own
  computer before relying on it for real work.
