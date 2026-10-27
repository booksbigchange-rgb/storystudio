# StoryStudio desktop MVP — user guide

Verified local milestone: 14 October 2026. This is the existing D:\StoryStudio installation, not a standalone installer.

## Start

- Double-click Open-StoryStudio.cmd in D:\StoryStudio.
- Double-click Open-Little-Lantern.cmd to explore the illustrated example as an unsaved copy.
- Check-StoryStudio.cmd checks setup without installing anything.
- Run-Video-Check.cmd regenerates and verifies the unchanged master regression project in a fresh export folder.

Keep the D:\StoryStudio folder in its current location: runtime paths are configured for it. Do not move the environment or model folders.

## Make a video

1. Add image. Select a scene, enter Seconds and Apply. Reorder or duplicate as needed.
2. Select Start frame or End frame. Increase Zoom and drag the crop box. The portrait preview shows output framing.
3. Move the playhead inside a scene and Add keyframe here. Select/drag blue timeline diamonds to edit pose/timing. Apply easing sets the motion curve.
4. Select Narration beside Add audio. Import speech or Create narration using the local English voice. Create narration asks before replacing existing narration.
5. Select Music and Add audio. Lower its Volume, then Apply audio. Narration and Music keep independent volume, start offset, source skip and fades. The waveform shows the selected track; the mix summary identifies populated tracks.
6. Play prepares temporary audio and starts sound/camera playback together. Pause, Stop or scrubbing stop sound. Play resumes at the playhead. Loop restarts both. Audio preparation may take a moment and can be canceled.
7. Save as to your own project on D:. Save updates that file atomically. Media paths are linked rather than copied: keep the source files. Relink repairs an image; Add audio again relinks a track.
8. Export MP4 to a new filename on D:. Output follows the selected format: 1080 x 1920 portrait or 1920 x 1080 widescreen at 24 fps, H.264/AAC. Existing output files are protected. Cancel export stops encoding and discards incomplete work. A completed file stays if publication finished before cancellation.
9. Preview MP4 creates a temporary encoded preview and offers Play video in your installed media player.

Ctrl+S saves. Ctrl+Z undoes. Ctrl+Y redoes. Undo/redo includes both audio tracks. New/Open/Close prompt for unsaved edits.

## Compatibility and boundaries

- Versions 1 and 2 load. New saves use version 3 for two audio tracks; older builds cannot open version 3.
- Still artwork is animated through camera movement. No body animation, rigging or lip-sync.
- Two audio tracks; no automatic speech ducking, captions or per-scene sound layers.
- Preview uses Windows audio and a software clock. Hardware latency may produce a small offset; it is not sample-accurate monitoring.
- Audio preparation has a 60-second timeout. Export progress reports stages, not overall percentages or ETAs.
- Narration generation is not cancelable. Wait for it, or for export cancellation to finish, before closing.
- Launchers scope application caches and temporary files to D:. Windows-managed writes are outside this audit.

## Validation and release status

The acceptance report records setup, 43 unit tests, real Tk editor/transport/waveform/two-track/cancel checks and full master-video regression, including newly generated narration and complete MP4 decoding. The fixture harness works around restricted-token temporary-folder ACLs without changing product or Windows security settings.

This milestone is a tested local desktop MVP. Subjective speaker listening, another low-spec computer, a standalone installer, clean-machine installation and GitHub CI are not certified. Source changes are local/uncommitted; main is unchanged. Do not treat the source snapshot as an installer or a merged release.

Preview recovery follow-up: preparation timeout now reports an error and resets Play. An unresponsive decoder is killed after a bounded wait. Explicit user cancellation stays silent. Timeout, kill fallback and real Tk recovery tests passed; the transport integration passed three consecutive runs after settling Tk startup events.

## Repeat the complete MVP checks

Double-click Verify-StoryStudio.cmd. It uses the existing D: environment, runs
setup and all nine check groups, and saves a unique report.json plus per-check
logs under D:\StoryStudio\exports\verification-runs. It exits with failure if
any check fails; a failed setup stops before running rendering tests.

For this restricted-token automation session only, run:

    powershell -NoProfile -ExecutionPolicy Bypass -File D:\StoryStudio\launchers\verify.ps1 -SandboxFixtures

The explicit switch adjusts synthetic temporary-fixture creation inside test
processes. Normal desktop runs use standard Python temporary directories. No
Windows permissions or product storage logic are changed. Speaker output and
clean-machine installation still require separate acceptance.

## Repeat short music

Select Music, add an audio file, check Repeat audio and click Apply audio. The
source repeats until the end of the story. Narration keeps its own repeat setting
and defaults to off. Start offset and fades apply to the complete track, not to
every repetition. Source skip removes time once at the beginning of the repeated
stream; subsequent repetitions include the full source. The waveform repeats to
match. Undo/Redo and project saving preserve the setting. Audio is not modified.

Repeat defaults to off for existing projects. Project format stays version 3, but
earlier builds ignore this optional field; use this build to preserve repetition.
This is a simple loop with no crossfade at the source boundary: choose music
with a suitable loop point to avoid clicks. Waveform analysis covers at most two
hours of source audio; repeated envelopes for longer sources are approximate.

## Layer animation milestone

Select a scene and Animate layers. Add transparent PNG/WebP artwork, choose
start/end positions, width, rotation, opacity and easing; preview poses and Apply
to scene. Layers draw bottom to top. Move behind/forward controls stacking.
Apply is one undoable edit; Cancel discards the draft. Slow reveal, Restrained
drift and Evidence push provide documentary-oriented starting motion.

Projects now save as version 4 and preserve relative layer links. Versions 1–3
still load. Older builds cannot open version 4. Layers are 2D output-space artwork,
not rigged characters or camera-linked 3D objects. Use original/lawfully sourced
layer artwork. Open-Layer-Demo.cmd opens the installed Orbit technical sample
as an unsaved copy. Creative direction and next priorities are recorded in
dark-true-story-direction.md; the sample is not the channel's final theme.

## Widescreen channel output

Use the format selector in the editor header: Portrait 9:16 or Widescreen 16:9.
It is a project setting, included in Undo/Redo and Save. Changing it changes
framing: review every camera crop, layer position and any text baked into images.
It does not automatically redesign artwork or create a second platform layout.
Background camera boxes, drag travel, output preview, layer-editor preview and
export all use the selected aspect ratio. Audio timing and frame rate stay the same.

New saves use version 5. Versions 1–4 load as portrait unless an explicit valid
format is provided; older builds cannot open version 5. Open a sample as a copy
and Save as to preserve its original project. Widescreen sample assets are in
projects/noir-widescreen-v2; open story.json to edit the fictional style study.
