# StoryStudio

Free local animation tools, installed on 10 October 2026.

## Start here

Double-click one of these files in this folder:

- `Open-Synfig.cmd` — character and layer animation.
- `Open-Krita.cmd` — painted artwork and character layers.
- `Open-Kdenlive.cmd` — editing, captions, sound and final assembly.
- `Open-Starter-Test.cmd` — editable movement and blinking test.
- `Generate-Narration.cmd` — drag a UTF-8 text file onto it to generate a WAV file.

Use the launchers to retain the D: storage settings. Opening an executable directly
may use its normal Windows profile defaults.

## Installed versions

| Component | Version / model | Location |
|---|---|---|
| FFmpeg + FFprobe | 9.0.2 full build | tools/ffmpeg |
| Synfig Studio | 1.4.5 stable portable | tools/synfig |
| Krita | 5.3.4.1 portable | tools/krita |
| Kdenlive | 26.08.1 standalone | tools/kdenlive |
| uv | 0.13.0 | tools/uv |
| Python | 3.12.15 | tools/python |
| Kokoro ONNX | runtime 0.6.1, model v1.0 INT8 | engine/.venv, models/kokoro |

The engine dependency versions are recorded in `engine/requirements.lock.txt`.
Models and voices are downloaded once. Subsequent narration does not need a
network connection, account, API key or cloud credits.

## Storage and scope

The launchers redirect application profiles, Python/uv caches, model caches and
temporary files to this folder. No global environment variables, Windows folders,
registry file associations or existing applications were relocated.
The original FFmpeg installation on C: remains untouched; our tools use the D: copies.
Windows itself may still write OS-level logs or registry entries on C:.

## Local code

`engine/narrate.py` generates local narration using a preset voice.
`engine/phonemes.py` calls the bundled eSpeak public API through one sequential
instance, avoiding the temporary DLL-copy path that failed in the sandbox.
Upstream packages were not edited. This helper is not designed for concurrent calls.
`engine/create_test.py` creates the native editable Synfig test project.

Example from PowerShell:

```powershell
. D:\StoryStudio\launchers\environment.ps1
& D:\StoryStudio\engine\.venv\Scripts\python.exe D:\StoryStudio\engine\narrate.py D:\StoryStudio\projects\my-story\script.txt --output D:\StoryStudio\exports\my-story.wav
```

## Sources and licenses

- Synfig GPLv3: https://github.com/synfig/synfig/releases/tag/v1.4.5
- Krita GPLv3: https://krita.org/en/download/
- Kdenlive GPL: https://kdenlive.org/download
- uv MIT/Apache-2.0: https://github.com/astral-sh/uv/releases/tag/0.13.0
- Kokoro ONNX MIT; Kokoro model Apache-2.0: https://github.com/thewh1teagle/kokoro-onnx
- eSpeak NG GPLv3: https://github.com/espeak-ng/espeak-ng
- FFmpeg license depends on build options; this copied full build enables GPL components:
  https://www.gyan.dev/ffmpeg/builds/ and https://ffmpeg.org/legal.html

Archives came from upstream GitHub releases and KDE's official download servers.
`logs/downloads.jsonl` records hashes and source URLs. uv's published SHA-256 was
verified. Other archives have locally recorded hashes; publisher verification is
not claimed where no published digest was provided.

## Boundaries

The starter is a technical test with simple shapes, not a finished painterly story.
The next creative step is prepared layered character artwork and a reusable rig.
Large AI image/video generation models and a new Blender installation were not added.

## Verified results

- FFmpeg and FFprobe version checks passed from the D: copies.
- Krita and Kdenlive console version checks passed.
- Synfig rendered the native starter project; movement and blinking frames were inspected.
- Kokoro generated 8.3627 seconds of offline speech with a preset male voice.
- `exports/starter-animation.mp4` is 10 seconds, 1280 x 720, 24 fps, H.264/AAC.
- Full MP4 decoding passed without errors.
- Application profile and graphics-cache files were observed beneath the D: profile.
- GUI drawing/editing sessions are not yet tested.

No API key, cloud credits or subscription is required for these verified functions.
