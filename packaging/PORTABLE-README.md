# StoryStudio Unified — portable Windows build

One folder, no Python install. Delete the folder to remove it; nothing is written outside it
(settings, logs, exports, temp and projects all live here).

## Start

Double-click `StoryStudio.exe`. Choose a workspace:

- **Documentary templates / Dark documentary** – artwork, camera, layers, audio and timed text.
- **Shared timeline** – combine documentary and character projects (up to 200 sections / 60 minutes),
  add timed text and a shared audio mix (music with ducking, narration, sound effects), export MP4.
- **Character animation** – reusable cutout characters with animation keys and presets
  (`character\StoryStudioCharacter.exe`, started for you).

If your studio uses `D:\StoryStudio`, install and start with the root launchers instead:
`Install-StoryStudio-Unified-Portable.cmd -Zip <zip>` then `Open-StoryStudio-Unified-Portable.cmd`.

## Folder map

| Path | What |
|---|---|
| `StoryStudio.exe` | hub, documentary and shared-timeline editors |
| `character\StoryStudioCharacter.exe` | character editor |
| `StoryStudioWorker.exe`, `character\StoryStudioCharacterWorker.exe` | background export helpers (no window) |
| `bin\ffmpeg.exe`, `bin\ffprobe.exe` | bundled FFmpeg (checksum-verified official build, see `provenance\`) |
| `projects\`, `exports\` | your work; new exports never overwrite existing files |
| `MANIFEST.json`, `SHA256SUMS.txt`, `BUILD-REPORT.md` | what is inside and how it was tested |

## Needs

- Windows 10/11 64-bit. Microsoft Edge or Google Chrome already installed (used only to draw character
  scenes; none is bundled). Everything runs offline.
- Self-check: `StoryStudio.exe --self-test --output <new folder>` (writes `results.json`; exit code 0 = pass).

## Limits and honesty

- Unsigned program: Windows SmartScreen or antivirus may ask for confirmation.
- Character animation is a lightweight 2D cutout system (three built-in characters). It is not painterly
  rigging and has no custom-artwork puppets.
- Long character sections render slowly because each frame is captured from a browser.
- Automated tests ran on a clean GitHub-hosted Windows machine; see `BUILD-REPORT.md`. Test on your own
  computer before relying on it for real work.
