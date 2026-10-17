# StoryStudio master video check

Use this same reference project after updates. The approved video is 34 seconds,
1080 × 1920, 24 fps, H.264 with AAC narration. It is technical test artwork.

## After an update

1. Double-click `D:\StoryStudio\Run-Video-Check.cmd`.
2. Wait for **Video check PASSED**. Each run creates a new folder in
   `D:\StoryStudio\exports\video-checks`; existing videos are preserved.
3. Watch the new `StoryStudio-Master-Check.mp4`. Listen to every numbered scene.
4. Compare the result with the approved master video and the table below.
5. If the check fails, read that run's `report.json` and the terminal error.
   Fix the application before approving a new reference. Never regenerate the
   reference images just to make a failed update pass.

The test uses the actual application renderer and project reader/writer. Its
reference artwork, audio and 42 expected frames are frozen and checked by SHA-256.
The soundtrack is reused for comparisons, and a separate short speech clip is
generated each run to check the current offline narration code.

| Time | Scene | What to watch/listen for |
|---|---|---|
| 0–4 s | Still picture | Sharp title; steady image; sound begins after a short delay |
| 4–8 s | Steady zoom | Even push toward the center |
| 8–12 s | Left to right | Smooth movement from target A toward B |
| 12–16 s | Top to bottom | Movement downward that accelerates |
| 16–21 s | Three turns | Zoom and move left, then right, then return toward center |
| 21–26 s | Wide to tall | Wide JPEG fills the portrait frame; outer panels are cropped |
| 26–30 s | Up and slow | BMP image moves upward and slows down |
| 30–34 s | Check complete | Stable closing card; narration and final note fade out |

## Open the project

Double-click `D:\StoryStudio\Open-Test-Project.cmd`. It opens the master as an
unsaved copy. Save asks for a new project name, preserving the reference.
The original is `D:\StoryStudio\projects\regression-master-v1\story.json`.

For a quick manual check, scrub the timeline, select a blue keyframe diamond,
change its zoom or framing, undo/redo, then save a copy and export to a new name.

## What passed on 13 October 2026

- All 816 video frames decoded, with continuous 24 fps timestamps.
- All frames use consistent limited-range BT.709 color settings.
- 42 exported images matched the frozen crops; maximum mean RGB error 5.69/255.
- Audio decoded to the full 34 seconds. Waveform correlation exceeded 0.997.
- Source trim, start delay, volume, fade, and speech in all eight scenes passed.
- Current Kokoro code generated a new valid speech clip.
- Save/reopen preserved all project, camera and audio settings.
- Actual Tk widgets loaded the project and all eight image previews.
- The checker rejected previous exports with color-metadata and audio-gap faults.
- 27 existing unit tests passed with the session's temporary-folder test harness.

This master test caught and helped fix two renderer issues: inconsistent color
metadata when PNG/JPEG scenes were concatenated, and audio timestamp gaps when
trimming and delaying a soundtrack together.

Manual desktop interaction and listening remain useful. This test does not
establish CI, Windows packaging, low-spec performance, live audio playback,
multiple audio tracks, or character rigging. Those have separate acceptance gates.
