# Desktop MVP (development branch)

This first milestone is an **image-to-video scene editor**, not character puppet animation.

## Run on the Windows workstation

1. Pull the branch: `git fetch origin feature/desktop-mvp` and `git switch feature/desktop-mvp`.
2. Run `Open-StoryStudio.cmd` from `D:\StoryStudio`.
3. Add PNG/JPG illustrations, reorder scenes, and set durations.
4. Save the scene list to `projects/desktop-mvp/story.json`.
5. Use **Export MP4** to render a vertical 1080 × 1920, 24 fps H.264 video in `exports/`.

The UI uses Python's `tkinter` standard library. Some standalone/uv Python distributions do **not** bundle Tcl/Tk. Check with:
```powershell
& D:\StoryStudio\engine\.venv\Scripts\python.exe -c "import tkinter; print(tk.TkVersion)"
```
If it fails, the GUI is not runnable with that interpreter yet; a Tcl/Tk-equipped Python installation or a Qt interface is needed. Do not overwrite the existing offline narration environment just to resolve this.

The renderer relies on the existing `tools/ffmpeg/ffmpeg.exe` and exports muted scene videos with a subtle camera push. It does not create character movement, lip-sync, or talking characters from a flat image. Narration remains accessible through the existing command-line launcher and is not yet integrated into this GUI.

## Boundaries / testing

- Works on a **copy** of the user-selected image files; originals are not modified.
- Project JSON stores absolute local image paths and is not portable until paths are relinked.
- No image embedding, audio mixing, character rigging, live preview, or automated scene generation yet.
- The branch's code was added through GitHub; **GUI startup and MP4 rendering must still be tested on the actual Windows machine**.
- Large tools, models, exports, projects and caches remain on D: and are excluded from Git.

## Suggested acceptance checks

- Open the UI without errors.
- Import two scene images and change their order and duration.
- Save, close, relaunch and confirm scenes reload.
- Export an MP4, verify with `ffprobe`, and watch the complete video for timing and cropped composition.
- Check that no new caches or temporary exports are placed on C:.

Do not merge until the on-device startup and export checks pass.
