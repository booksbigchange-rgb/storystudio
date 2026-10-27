# Shared audio mix for mixed timelines

Open a mixed timeline, then **Audio mix**. The mix is optional: a timeline with
no `audio` block keeps exactly the audio of its source projects.

## What can be mixed

- **Source audio** – the narration/sound already inside each documentary or
  character section (unchanged behavior, padded/trimmed per section). Level 0–2.
- **Music** – one local file. It loops under the whole timeline, fades in
  (0.5 s) and out (1.5 s), level 0–2.
- **Ducking** – `off`, `light`, `medium`, `strong`. The music is compressed by a
  side-chain keyed on all speech (source audio + shared narration), so it drops
  while anyone speaks and recovers afterward.
- **Narration clips** (up to 16) and **sound-effect clips** (up to 32) – local
  files placed at a start time (seconds from the start of the whole timeline) with
  their own level. Sound effects are not ducked. Clips running past the end are trimmed.
- A final limiter (ceiling about -1 dBFS) prevents clipping when levels add up.

## Audio timeline (drag and fades)
The dialog shows three lanes (Music, Narration, Sound effects) over the whole story with real waveforms (decoded in
the background by FFmpeg and cached under `cache\waveforms`). Click a clip to select it; drag it left or right to move it
(snaps to frames, stays inside the story). Yellow lines show fades. Each clip has **Fade in / Fade out** seconds (0–30);
music has its own fade in/out (defaults 0.5 s / 1.5 s, as before). Typing exact times in the form still works.
Fade-outs need the file length, which the exporter measures; a fade-out never starts before the fade-in ends.

## Rules

- Files must be local `.wav .mp3 .flac .ogg .m4a .aac`. URLs and network paths are rejected.
- Files are linked, never copied or changed. They are saved relative to the
  timeline file where possible.
- Before any section renders, every file is checked: exists, non-empty and under 200 MB,
  contains an audio stream, 0.05 s–60 min, fully decodable, and clips start before the timeline ends.
  Problems stop the export with a message naming the file; nothing is published.
- Export never overwrites an existing MP4; cancel works during the mix step.
- Output is unchanged: H.264 video, AAC stereo 48 kHz.

## Format (additive, still `storystudio-mixed` version 1)

```json
"audio": {"source_volume": 1.0, "duck": "medium",
  "music": {"file": "media/bed.wav", "volume": 0.5, "fade_in": 0.5, "fade_out": 1.5},
  "narration": [{"file": "media/vo.wav", "start": 3.0, "volume": 1.0, "fade_in": 0.2, "fade_out": 0.4}],
  "sfx": [{"file": "media/hit.wav", "start": 5.0, "volume": 1.0}]}
```
Older readers that validate strictly will not understand the new field; older
timelines open unchanged.

## Verification

- `tests/test_mixed_audio.py` – validation, relative-path round trip, media checks
  (missing / empty / text-as-audio / damaged / video-only / late clip) and measured FFmpeg output
  (frequency-specific levels for source speech, narration, music, SFX; looping; ducking depth;
  volume scaling; limiter; trimming).
- `tests/mixed_audio_integration.py [--cartoon]` – real exports in both orientations, decoded and measured,
  no-overwrite, bad media rejected before rendering, cancel during mix then retry, source hashes unchanged.
- `tests/mixed_audio_gui_integration.py` – real Tk dialog, GUI export, no-overwrite and missing-media errors.
- `tests/mixed_audio_timeline_gui_integration.py` – real Tk timeline: waveforms arrive, real mouse drag (frame-snapped, clamped), fades, decoded export matches the dragged position.
- Run all on Windows with `Verify-Audio-Mix.cmd`.

Automated tests use synthetic tones, not real music or speech. Listening on your
own speakers/headphones is still needed to judge balance and ducking taste.
