"""Real mixed-timeline exports with shared audio, decoded and measured (no Tk needed).

Runs on Windows with the bundled FFmpeg and, for development, on any system with
FFmpeg on PATH. The character engine is included when ``--cartoon`` is passed
(the Windows CI/launcher always does).
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
sys.path.insert(0, str(ROOT/'tests'))
from PIL import Image
import mixed_project as model
from mixed_control import MixedControl, RenderCancelled
from mixed_render import export, tool
from mixed_audio_integration_helpers import probe_streams
from test_mixed_audio import tone, goertzel, decode, window, RATE

FFMPEG, FFPROBE = tool('ffmpeg'), tool('ffprobe')
CARTOON = '--cartoon' in sys.argv
folder = ROOT/'exports'/('audio-acceptance-'+uuid.uuid4().hex)
folder.mkdir(parents=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


probe = probe_streams


def decoded(path):
    result = subprocess.run([FFMPEG, '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'], capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr.strip(), result.stderr


# Source projects: a narrated documentary (2 s source speech tone) and, optionally, a character scene.
Image.new('RGB', (1280, 720), '#dddddd').save(folder/'a.png')
Image.new('RGB', (1280, 720), '#556677').save(folder/'b.png')
tone(folder/'source-narration.wav', 1000, 1.5, .4)
documentary = folder/'documentary.json'
documentary.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=2), dict(image='b.png', duration=2), dict(image='a.png', duration=2)],
                                       audio=dict(path='source-narration.wav'))), encoding='utf-8')
sources = [documentary]
if CARTOON:
    cartoon = folder/'character.json'
    cartoon.write_text(json.dumps(dict(version=2, name='Audio test', format='Landscape 16:9', quality='Standard · 720p / 24 fps', audio=None,
        scenes=[dict(title='', duration=2, character='bear', expression='curious', action='wave', background='meadow', x=.4, size=1, speed=1)])), encoding='utf-8')
    sources.append(cartoon)
total = 6 + (2 if CARTOON else 0)
frames = total*24
source_hashes = {p: sha(p) for p in sources + [folder/'source-narration.wav']}
music = tone(folder/'music.wav', 220, 2, .5)
narration = tone(folder/'narration.wav', 1500, 1, .4)
sfx = tone(folder/'sfx.wav', 3000, .5, .5)
settings = {'music': {'file': str(music), 'volume': .6}, 'duck': 'strong',
            'narration': [{'file': str(narration), 'start': 3.0, 'volume': 1}],
            'sfx': [{'file': str(sfx), 'start': total-1, 'volume': 1}]}


def timeline(format_name, audio):
    doc = model.new_project()
    doc['format'] = format_name
    doc['sections'] = [dict(engine='documentary', project=str(documentary), name='Documentary')]
    if CARTOON:
        doc['sections'].append(dict(engine='cartoon', project=str(sources[1]), name='Character'))
    if audio is not None:
        doc['audio'] = audio
    return model.validate(doc)


def verify(path, format_name, expect_tones):
    width, height = model.FORMATS[format_name]
    video, sound, seconds = probe(path)
    assert video['codec_name'] == 'h264' and video['pix_fmt'] == 'yuv420p', video
    assert (video['width'], video['height']) == (width, height)
    assert int(video['nb_read_frames']) == frames, video['nb_read_frames']
    assert len(sound) == 1 and sound[0]['codec_name'] == 'aac' and int(sound[0]['channels']) == 2, sound
    assert abs(seconds-total) < .12, seconds
    decoded(path)
    samples = decode(path)
    for hertz, start, end, minimum in expect_tones:
        level = goertzel(window(samples, start, end), hertz)
        assert (level > minimum) if minimum else (level < .01), (hertz, start, end, level)
    return samples


results = []
for format_name in model.FORMATS:
    output = folder/f'mixed-audio-{format_name}.mp4'
    messages = []
    export(timeline(format_name, settings), output, messages.append)
    assert any('Mixing' in m for m in messages)
    samples = verify(output, format_name, [(1000, .3, 1.3, .15), (1500, 3.1, 3.9, .15), (3000, total-.95, total-.55, .15), (3000, .3, 1.7, 0)])
    free = goertzel(window(samples, 2.2, 2.9), 220)
    ducked = goertzel(window(samples, .3, 1.3), 220)
    assert free > .1 and ducked < free*.5, (free, ducked)
    first = sha(output)
    try:
        export(timeline(format_name, settings), output)
        raise AssertionError('Existing export overwritten')
    except FileExistsError:
        pass
    assert sha(output) == first
    results.append(dict(format=format_name, output=output.name, frames=frames, music_free=round(free, 3), music_under_speech=round(ducked, 3), sha256=first))

# Source-project audio is the only audio when no shared mix exists, and a mix keeps it.
plain = folder/'source-only.mp4'
export(timeline('widescreen', None), plain)
verify(plain, 'widescreen', [(1000, .3, 1.3, .15), (220, .3, 1.3, 0)])
reduced = folder/'source-half.mp4'
export(timeline('widescreen', {'source_volume': .5}), reduced)
full_level, half_level = goertzel(window(decode(plain), .3, 1.3), 1000), goertzel(window(decode(reduced), .3, 1.3), 1000)
assert abs(half_level/full_level-.5) < .1, (full_level, half_level)

# Bad or missing media is explained and nothing is rendered or published.
def work_dirs():
    return set((ROOT/'exports').glob('mixed-run-*'))


damaged = folder/'damaged.wav'
damaged.write_bytes(music.read_bytes()[:60]+b'\xff'*3000)
text = folder/'not-audio.mp3'
text.write_text('plain text')
for label, bad, error, message in [
        ('missing', {'music': {'file': str(folder/'gone.wav')}}, FileNotFoundError, 'Music file is missing'),
        ('text', {'sfx': [{'file': str(text), 'start': 1}]}, ValueError, 'not readable audio'),
        ('damaged', {'narration': [{'file': str(damaged), 'start': 1}]}, ValueError, ''),
        ('late', {'sfx': [{'file': str(sfx), 'start': total+1}]}, ValueError, 'after the')]:
    before = work_dirs()
    target = folder/f'bad-{label}.mp4'
    try:
        export(timeline('widescreen', bad), target)
        raise AssertionError(label+' accepted')
    except error as exc:
        assert message in str(exc), str(exc)
    assert not target.exists() and not list(folder.glob('.*.partial.mp4'))
    created = work_dirs()-before
    assert all(not list(d.glob('raw-*')) and not list(d.glob('section-*')) for d in created), 'sections rendered before media validation'

# Cancellation while the shared mix is running publishes nothing.
control = MixedControl()
target = folder/'cancelled-mix.mp4'
def cancel_on_mix(message):
    if 'Mixing' in message:
        control.cancel()
try:
    export(timeline('widescreen', settings), target, cancel_on_mix, control=control)
    raise AssertionError('Canceled mix published')
except RenderCancelled:
    pass
assert not target.exists() and not list(folder.glob('.*.partial.mp4'))
retry = folder/'after-cancel.mp4'
export(timeline('widescreen', settings), retry)
verify(retry, 'widescreen', [(1000, .3, 1.3, .15)])

assert all(sha(p) == value for p, value in source_hashes.items()), 'source files changed'
(folder/'results.json').write_text(json.dumps(dict(status='passed', cartoon=CARTOON, results=results,
    checks=['narration+music+sfx timing', 'music loops and ducks under source and shared narration', 'source volume',
            'no-overwrite', 'missing/text/damaged/late media rejected before rendering', 'cancel during mix then retry',
            'full decode, codec, resolution, frame count, duration, audio'], source_hashes_unchanged=True), indent=2))
print('ACCEPTANCE:', folder)
