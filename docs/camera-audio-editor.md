> Historical implementation notes. For current use and limitations, see `desktop-mvp-guide.md`.

# Camera and audio editor â€” installed update, 13 October 2026

This update extends the existing scene renderer. It is a still-image camera editor,
not a layered character-animation or lip-sync system.

## Use the editor

1. Start `Open-StoryStudio.cmd`, then add one or more images.
2. Select a scene. Set its duration and click Apply. Timing snaps to 24 fps.
3. Choose Start frame or End frame. Increase Zoom, then drag that colored frame
   over the source image. At 1Ã— the entire center-fill crop is visible, so panning
   has no available travel. The adjacent portrait shows the rendered framing.
4. Select linear, smooth, ease-in or ease-out; click Apply easing. Move the
   playhead inside a scene and click Add keyframe here for additional camera
   poses. Click a blue timeline diamond to select that pose, then adjust Zoom
   or drag its blue crop box. Remove keyframe deletes only that interior pose.
   Up to 16 intermediate poses per scene are supported. Changing duration keeps
   their relative timing. Easing applies between every neighboring pair.
   Drag a blue diamond horizontally to change when that pose occurs. Timing
   snaps to 24 fps and stays between neighboring poses, within the same scene.
   Each drag can be undone or redone in one step. Click/drag elsewhere to scrub.
5. Click/drag on the timeline to scrub. Play/Pause, Stop, frame steps and Loop
   preview camera motion. This interactive preview is silent.
6. Add audio, or use Create narration for offline English Kokoro speech. Apply
   volume (0â€“2), timeline start, source skip and fade settings. One soundtrack is
   supported. Narration can replace that track with confirmation; source files
   remain untouched.
   The soundtrack lane now shows its waveform after a short background scan.
   Silence appears flat; speech appears as peaks. Trim, timeline delay, volume
   and fade settings are reflected in the display. This is a relative visual
   envelope, not a loudness meter. Source media is never modified.
7. Save as creates a new project. Save updates the current project atomically.
   Version 1 projects load; version 2 stores easing/audio and relative media paths.
   Use Relink if an image has moved. Add audio again to relink a soundtrack.
8. Export MP4 creates 1080Ã—1920, 24 fps H.264/AAC output. Existing destination
   files are protected: choose a new name. Preview MP4 creates a unique temporary
   export and offers a Play video button for the installed media player.

Undo/Redo covers scene, camera and soundtrack changes. Unsaved edits prompt on
New, Open and Close. During export/narration, switching projects or closing is
blocked until the worker completes. Background workers report through a queue;
only the Tk main thread touches widgets.

## Dependencies and storage

Uses the existing Python 3.12/Tkinter, Pillow, FFmpeg, Kokoro, ONNX Runtime and
soundfile installation. No package/model downloads are required. Always load
`launchers/environment.ps1` before commands. `STORY_STUDIO_PYTHON` optionally
selects an existing interpreter for the root launcher. `STORY_STUDIO_MODEL_ROOT`
optionally selects an existing Kokoro model directory; no automatic downloads.

All project/export destinations selected in the Windows GUI must use the same
drive as StoryStudio. Source images and audio may be read from other drives.
The launcher scopes caches/profiles to D:. OS-managed writes are not audited.

## Verification

- 27 headless unit tests passed using the installed D: Python environment.
- A real Tk root and editor were created. Widget tests passed for image preview,
  visual crop dragging, frame playback, duration/reordering, undo/redo,
  project/audio roundtrip, invalid project retention, unsaved cancellation and
  export-error recovery. Buttons fit within 1000Ã—680 in this Tk session.
- Original 2-scene encode/decode integration passed.
- Real 4-second 1080Ã—1920, 24 fps H.264/AAC export passed complete decoding.
  It contains 96 video frames and real offline Kokoro narration.
- Twenty decoded frames across four easing modes and multiple intermediate poses
  were compared with expected crops; mean RGB error was below 6.3/255.
  Audio delay and non-silent speech passed.
- All 17 pinned dependency versions matched the existing environment.

The Windows restricted-token session could not reopen the private ACLs created
by `tempfile.TemporaryDirectory`. A local test-only harness creates synthetic
fixtures with inherited workspace ACLs. Product code and system security settings
were not changed for that issue. Run normal tests in the user's terminal first;
use the supplied harness only if the same sandbox-specific error occurs.

## Remaining acceptance and development

- The update is applied to `D:\StoryStudio` on `feature/desktop-mvp`.
  Run CI for the new commit before considering release or merge.
- Visually inspect and interact with the actual foreground Windows UI. Computer
  Use could not enumerate the sandbox-launched Tk window, so full desktop visual
  acceptance is not claimed. Listen to the final MP4 for subjective sound quality.
- Add multiple audio tracks, render cancellation.
- Add layered character artwork/rigging, character motion and lip-sync only as a
  separate tested milestone with appropriate assets.
- Validate packaged Windows distribution and low-spec performance.

No merge into main or user-asset overwrite is authorized by this update.

## Live audio preview (14 October 2026)

Play prepares a temporary stereo PCM WAV on D: using the soundtrack trim, delay,
volume and fades, then starts Windows audio and the visual clock together.
Pause, Stop, frame stepping, scrubbing and edits stop playback; Play resumes
from the current playhead. Loop prepares audio again at the beginning. Preparing
audio can be canceled with the transport button. Source media is unchanged.
Preview uses Windows asynchronous audio; hardware latency may cause a small
offset. This is not sample-accurate monitoring. Long stories take longer to
prepare; preparation times out after 60 seconds. No packages were installed.

Verified PCM timing/envelope and real Tk transport lifecycle. Sound-device calls
were mocked in transport tests; subjective speaker output still needs listening.

## Separate narration and music (14 October 2026)

Use the Narration/Music selector beside Add audio. Add/remove and the four audio
settings affect the selected track. The waveform shows that selected track.
Play and Export MP4 mix both tracks together with independent volume, source
trim, start offset and fades. Lower music volume to keep speech clear. A limiter
prevents summed peaks from clipping; automatic speech ducking is not included.
Create narration always replaces the Narration track after confirmation and
keeps Music. Undo/Redo covers both. New project format version 3 stores music;
versions 1 and 2 still load, with their soundtrack mapped to Narration. Older
StoryStudio builds cannot open version 3 projects. Saving is atomic as before.

Two-track integration passed real FFmpeg preview PCM, decoded MP4 with both
frequencies present, full decoding, relative-path save/reopen and real Tk track
selection/edit/remove/undo/redo/save. No new packages or models were installed.

## Cancelable export (14 October 2026)

Export MP4 and Preview MP4 enable Cancel export while the worker runs. Cancel
stops only that export's FFmpeg child, waits for it to exit, removes temporary
render files, and returns the editor to an export-ready state. No partial MP4
is published. Final publication is atomic; canceling after publication leaves
the completed MP4 intact. Existing destination files remain protected.
Progress reports the current scene and its duration, joining, audio mixing and
finalization; these are stage messages, not a measured overall percentage or ETA.
Narration generation is not canceled by this button. Wait for cancellation to
finish before closing.

Verified real encode interruption under eight seconds, cancellation before
publication, output/temp cleanup, Tk cancel and successful retry.
