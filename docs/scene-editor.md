# Milestone 2 — Scene preview and timeline

This is the first **visual scene editor**, not a character-animation system.

## Added to the desktop UI

- A scene list on the left and a still-image preview on the right.
- A proportional timeline below the editor. Each scene block represents its duration.
- Click a timeline block to select its scene; change duration, reorder or remove scenes using existing controls.
- The timeline duration calculations live in `engine/timeline.py` and have display-independent unit tests.
- Optional Pillow provides aspect-preserving previews for PNG, JPEG and BMP. Without Pillow, Tk's built-in PhotoImage is used when it supports the image format.

To enable broad preview support in a Python environment with Tkinter:
```sh
python -m pip install Pillow
```

## Known limitations

- The preview shows the **still source image**; it does not play the zoompan animation or the final MP4.
- The timeline shows scene durations, not individual keyframes or layered tracks.
- UI startup and image display still need to be verified interactively on a desktop with Tkinter.
- Rendering tests are headless and do not require Pillow or a GUI.
- Existing projects use absolute image paths, so missing media needs manual relinking.

## Cloud checks

```sh
python -m compileall -q engine tests
python -m unittest discover -s tests -v
python tests/render_integration.py  # requires ffmpeg and ffprobe
```

Do not merge into main until the latest GitHub Actions run passes and a desktop UI smoke test is performed.
