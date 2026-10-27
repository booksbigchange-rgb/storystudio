"""Trims, dissolves, dip-to-black fades and splits in a real export: exact frames, decoded and measured (no Tk)."""
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
sys.path.insert(0, str(ROOT/'tests'))
from PIL import Image
import mixed_durations as durations
import mixed_edit
import mixed_project as model
from mixed_render import export, tool
from mixed_audio_integration_helpers import probe_streams
from test_mixed_audio import tone, goertzel, decode, window as slice_audio

FFMPEG = tool('ffmpeg')
folder = ROOT/'exports'/('edit-acceptance-'+uuid.uuid4().hex)
folder.mkdir(parents=True)


def artwork(i):
    image = Image.new('RGB', (640, 360), 'black')
    for bit in range(8):
        if i >> (7-bit) & 1:
            image.paste('white', (bit*80, 0, bit*80+80, 360))
    return image


sources = []
tone(folder/'voice.wav', 1000, 6)
for i in (1, 2, 4):                      # three 2-second sections (48 frames) marked 1, 2 and 4
    artwork(i).save(folder/f'a{i}.png')
    path = folder/f'p{i}.json'
    path.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image=f'a{i}.png', duration=2)],
                                    audio=dict(path='voice.wav') if i == 2 else None)), encoding='utf-8')
    sources.append(path)


def timeline(*edits):
    doc = model.new_project()
    doc['sections'] = [dict(engine='documentary', project=str(p), name=f'S{n}', **e) for n, (p, e) in enumerate(zip(sources, edits))]
    return model.validate(doc)


def gray_rows(output, picks):
    select = '+'.join(f'eq(n\\,{n})' for n in picks)
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(output), '-vf', f'select={select},scale=8:1:flags=area', '-fps_mode', 'passthrough',
                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True, check=True).stdout
    assert len(raw) == 8*len(picks), (len(raw), len(picks))
    return [list(raw[k*8:k*8+8]) for k in range(len(picks))]


def number(row):
    return sum((value > 128) << (7-bit) for bit, value in enumerate(row))


def check_media(output, frames):
    video, sound, seconds = probe_streams(output)
    assert video['codec_name'] == 'h264' and (video['width'], video['height']) == (1280, 720)
    assert int(video['nb_read_frames']) == frames, (video['nb_read_frames'], frames)
    assert len(sound) == 1 and sound[0]['codec_name'] == 'aac' and abs(seconds-frames/24) < .15, (seconds, frames/24)
    result = subprocess.run([FFMPEG, '-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'], capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr.strip(), result.stderr[-400:]


results = {}
# 1. trim + dissolve + fade together: 24 + 48 + 48 - 12 = 108 frames.
edits = [dict(trim_in=12, trim_out=36), dict(transition=dict(kind='dissolve', frames=12)), dict(transition=dict(kind='fade', frames=6))]
doc = timeline(*edits)
rows, total = durations.timeline(doc)
assert total == 108 and [start for start, _ in rows] == [0, 12, 60], (rows, total)
output = folder/'combined.mp4'
export(doc, output)
check_media(output, 108)
# main0 = 12 frames (source 12..24), mix = 12 frames (12..24), main1 = 36 frames (24..60), section 2 starts at 60.
picks = [5, 12, 18, 23, 24, 40, 58, 59, 60, 61, 90, 107]
rows_ = dict(zip(picks, gray_rows(output, picks)))
assert number(rows_[5]) == 1 and number(rows_[40]) == 2 and number(rows_[90]) == 4, {k: number(v) for k, v in rows_.items()}
assert number(rows_[12]) in (1, 3) and number(rows_[24]) == 2
blend = rows_[18]
assert 40 < blend[7] < 215 and 40 < blend[6] < 215, f'mid-dissolve is not a blend: {blend}'      # blocks of marker 1 and marker 2 are both half-visible
assert blend[7] < rows_[12][7] and blend[6] > rows_[12][6], 'dissolve does not move from section 1 to 2'
assert max(rows_[59]) < 60 and max(rows_[60]) < 60, ('fade is not through black', rows_[59], rows_[60])
assert max(rows_[58]) > max(rows_[59]) and number(rows_[61]) in (0, 4) or max(rows_[61]) > max(rows_[60])
results['combined'] = dict(frames=108)
# 2. the same trim keeps exactly the chosen frames (marker changes at the cut).
trimmed = folder/'trimmed.mp4'
export(timeline(dict(trim_in=10, trim_out=20), {}, {}), trimmed)
check_media(trimmed, 10+48+48)
got = [number(r) for r in gray_rows(trimmed, [0, 9, 10, 57, 58, 105])]
assert got == [1, 1, 2, 2, 4, 4], got
# 3. splitting a section is invisible: same frames, same order, same length.
whole = timeline({}, {}, {})
parts = mixed_edit.split(whole['sections'][1], 17, 48)
split_doc = dict(whole)
split_doc['sections'] = [whole['sections'][0], *parts, whole['sections'][2]]
assert [p['name'] for p in parts] == ['S1 · 1', 'S1 · 2']
split_doc = model.validate(split_doc)
assert durations.timeline(split_doc)[1] == 144
splitted = folder/'split.mp4'
export(split_doc, splitted)
check_media(splitted, 144)
assert [number(r) for r in gray_rows(splitted, [10, 48+8, 48+20, 96+10])] == [1, 2, 2, 4]
# 4. audio of a trimmed/faded section stays in step: tone only while section 2 plays.
audio = decode(splitted)
assert goertzel(slice_audio(audio, 2.1, 3.9), 1000) > .1 and goertzel(slice_audio(audio, .2, 1.8), 1000) < .01
# 5. invalid edits are explained before rendering.
for bad_edits, message in [([dict(trim_in=0, trim_out=999), {}, {}], 'only 48 frames'),
                           ([dict(), dict(transition=dict(kind='dissolve', frames=60)), dict()], 'longer than a neighbouring'),
                           ([dict(), dict(transition=dict(kind='dissolve', frames=30)), dict(transition=dict(kind='dissolve', frames=30))], 'too short')]:
    target = folder/'never.mp4'
    try:
        export(timeline(*bad_edits), target)
        raise AssertionError('accepted '+message)
    except ValueError as exc:
        assert message in str(exc), str(exc)
    assert not target.exists()
for bad in (dict(trim_in=-1), dict(trim_in=5, trim_out=5), dict(trim_in=1.5), dict(transition=dict(kind='wipe', frames=6)),
            dict(transition=dict(kind='fade', frames=1)), dict(transition=dict(kind='fade', frames=999)), dict(transition='fade')):
    try:
        timeline(bad, {}, {})
        raise AssertionError(f'accepted {bad}')
    except ValueError:
        pass
(folder/'results.json').write_text(json.dumps(dict(status='passed', results=results), indent=2))
print('ACCEPTANCE:', folder)
