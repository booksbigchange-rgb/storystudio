# StoryStudio workspace instructions

- Keep new tools, Python environments, models, caches, temporary files, projects,
  and exports under `D:\StoryStudio`.
- Load `launchers/environment.ps1` before shell operations using these tools.
- Use the existing D: FFmpeg, Python environment and Kokoro model. Do not install
  another runtime on C: or use a cloud service for supported offline capabilities.
- Launch GUI applications through the root `.cmd` launchers so their profile
  settings stay scoped to this studio. Do not change global Windows environment
  variables or relocate existing applications.
- Preserve user projects and source artwork. Keep changes small and reversible.
- Models, wheels and application archives must come from official upstream
  sources. Retain source URLs, exact versions and checksums in the local logs.
- Verify real narration and a decoded MP4 before claiming a video is complete.
- The starter test uses simple shapes. Painterly character animation requires
  layered artwork and a rig; do not describe the technical test as a finished story.
