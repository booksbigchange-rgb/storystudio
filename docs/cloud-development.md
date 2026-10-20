# Cloud development and verification

This branch is designed to develop without the original D: drive.

## Configurable paths

- `STORY_STUDIO`: optional root for projects, exports, temp and local tools. Defaults to the checked-out repository root.
- `STORY_STUDIO_FFMPEG`: optional full path to an FFmpeg executable. If omitted, the application looks in `<root>/tools/ffmpeg/ffmpeg.exe`, then in `PATH`.
- On the original Windows workstation, the existing `launchers/environment.ps1` still configures the D: layout.

## GitHub Actions

The workflow in `.github/workflows/ci.yml` is configured to run:
- Python syntax compilation on Windows and Ubuntu.
- Unit tests for missing images, duration validation, empty stories and FFmpeg path selection.
- A separate FFmpeg synthetic-video encode/decode smoke test on Ubuntu, with MP4 uploaded as a workflow artifact.

**Important:** Passing the synthetic FFmpeg smoke test does not establish that the desktop application's image-to-video renderer works end to end. A later integration test with real scene images is required.

To run tests in a checked-out copy:
```sh
python -m compileall -q engine tests
python -m unittest discover -s tests -v
```

## Outstanding blockers

1. Confirm CI workflow runs are enabled and passing. A workflow definition alone is not evidence of a successful run.
2. Validate the GUI startup with a Python interpreter containing Tcl/Tk.
3. Test a real multi-scene export and inspect its duration, orientation, decode and visuals.
4. Remove remaining D:-specific assumptions in narration, PowerShell launchers and user documentation.
5. Build and validate a Windows distributable, without embedding models or private projects.

Do not merge this draft PR until CI results and basic application behavior have been checked.
