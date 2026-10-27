"""Many-section exports: exact ordering and frame counts, bounded memory, safe cancellation (no Tk).

``--sections N`` (default 60) sets the size of the long story.
"""
import colorsys
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
sys.path.insert(0, str(ROOT/'tests'))
from PIL import Image
import mixed_durations as durations
import mixed_project as model
from mixed_control import MixedControl, RenderCancelled
from mixed_render import export, tool
from mixed_audio_integration_helpers import probe_streams

COUNT = int(sys.argv[sys.argv.index('--sections')+1]) if '--sections' in sys.argv else 40
FFMPEG = tool('ffmpeg')
LIMIT_BYTES = 1_500_000_000
folder = ROOT/'exports'/('endurance-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def artwork(i):
    """Eight black/white blocks spell the section number in binary: robust to colour conversion."""
    image = Image.new('RGB', (640, 360), 'black')
    for bit in range(8):
        if i >> (7-bit) & 1:
            image.paste('white', (bit*80, 0, bit*80+80, 360))
    return image


# Sections cycle 1.5 / 2 / 2.25 / 3 s so frame rounding is exercised (36, 48, 54, 72 frames).
lengths = [1.5, 2, 2.25, 3]
sources = []
for i in range(COUNT):
    artwork(i).save(folder/f'c{i}.png')
    path = folder/f'p{i}.json'
    path.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image=f'c{i}.png', duration=lengths[i % 4])])), encoding='utf-8')
    sources.append(path)
source_hashes = {p: sha(p) for p in sources}


def timeline(order, format_name='widescreen'):
    doc = model.new_project()
    doc['format'] = format_name
    doc['sections'] = [dict(engine='documentary', project=str(sources[i]), name=f'Section {i}') for i in order]
    return model.validate(doc)


def expected_frames(i):
    return round(lengths[i % 4]*24)


def check(output, order, control=None):
    doc = timeline(order)
    rows, total = durations.timeline(doc)
    assert total == sum(expected_frames(i) for i in order), (total, rows[:3])
    video, sound, seconds = probe_streams(output)
    assert video['codec_name'] == 'h264' and (video['width'], video['height']) == (1280, 720)
    assert int(video['nb_read_frames']) == total, (video['nb_read_frames'], total)
    assert len(sound) == 1 and sound[0]['codec_name'] == 'aac' and abs(seconds-total/24) < .15, (seconds, total/24)
    result = subprocess.run([FFMPEG, '-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'], capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr.strip(), result.stderr[-500:]
    # The mid-frame of every section must spell that section's number, in list order.
    picks = [start + count//2 for start, count in rows]
    select = '+'.join(f'eq(n\\,{n})' for n in picks)
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(output), '-vf', f'select={select},scale=8:1:flags=area', '-fps_mode', 'passthrough',
                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True, check=True).stdout
    assert len(raw) == len(order)*8, len(raw)
    for position, section in enumerate(order):
        number = sum((raw[position*8+bit] > 128) << (7-bit) for bit in range(8))
        assert number == section, (position, section, number, list(raw[position*8:position*8+8]))
    return total, seconds


results = {}
existing_runs = set((ROOT/'exports').glob('mixed-run-*'))
# 1. Whole story in list order, then the same sections shuffled; both exact.
order = list(range(COUNT))
control = MixedControl()
output = folder/'story.mp4'
started = time.monotonic()
export(timeline(order), output, control=control)
elapsed = time.monotonic()-started
total, seconds = check(output, order)
peak = control.peak_bytes
assert peak < LIMIT_BYTES, f'Peak step memory {peak/1e6:.0f} MB exceeds {LIMIT_BYTES/1e6:.0f} MB'
results['story'] = dict(sections=COUNT, frames=total, seconds=round(seconds, 2), render_seconds=round(elapsed, 1), peak_step_memory_mb=round(peak/1e6), sha256=sha(output))
first = sha(output)
try:
    export(timeline(order), output)
    raise AssertionError('Existing export overwritten')
except FileExistsError:
    pass
assert sha(output) == first
shuffled = order[:]
random.Random(7).shuffle(shuffled)
reorder = folder/'shuffled.mp4'
export(timeline(shuffled), reorder)
check(reorder, shuffled)
results['shuffled'] = dict(sha256=sha(reorder))

# 2. Intermediates do not accumulate: runs keep logs/snapshots but no bulky media.
runs = [d for d in set((ROOT/'exports').glob('mixed-run-*'))-existing_runs if (d/'result.json').exists()]
assert len(runs) == 2 and all(not list(d.glob('*.mov')) and not list(d.glob('raw-*')) and not list(d.glob('joined.mp4')) and (d/'render.log').exists() for d in runs)

# 3. Limits are explained before any rendering.
before = set((ROOT/'exports').glob('mixed-run-*'))
too_many = model.new_project()
too_many['sections'] = [dict(engine='documentary', project=str(sources[0]), name='X')]*(model.MAX_SECTIONS+1)
try:
    export(too_many, folder/'too-many.mp4')
    raise AssertionError('Too many sections accepted')
except ValueError as exc:
    assert str(model.MAX_SECTIONS) in str(exc)
long_source = folder/'long.json'
long_source.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='c0.png', duration=120)]*31)), encoding='utf-8')
long_doc = model.new_project()
long_doc['sections'] = [dict(engine='documentary', project=str(long_source), name='Over an hour')]
try:
    export(long_doc, folder/'too-long.mp4')
    raise AssertionError('Over-length story accepted')
except ValueError as exc:
    assert '60 minutes' in str(exc), exc
assert not (folder/'too-long.mp4').exists() and not (folder/'too-many.mp4').exists()
for run in set((ROOT/'exports').glob('mixed-run-*'))-before:
    assert not list(run.glob('raw-*')), 'rendered despite exceeding limits'

# 4. Cancel part-way through a long story: nothing published, no media left, retry succeeds.
cancel = MixedControl()
target = folder/'cancelled.mp4'
before = set((ROOT/'exports').glob('mixed-run-*'))
seen = []
def stop_midway(message):
    if message.startswith('Rendering section'):
        seen.append(message)
        if len(seen) == min(8, COUNT//2):
            cancel.cancel()
try:
    export(timeline(order), target, stop_midway, control=cancel)
    raise AssertionError('Canceled export published')
except RenderCancelled:
    pass
assert not target.exists() and not list(folder.glob('.*.partial.mp4')) and len(seen) <= min(8, COUNT//2)+1
for run in set((ROOT/'exports').glob('mixed-run-*'))-before:
    assert not list(run.glob('*.mov')) and not list(run.glob('*.mp4')) and not list(run.glob('.*.partial.mp4')), 'media left after cancel'
retry = folder/'retry.mp4'
export(timeline(order[:5]), retry)
check(retry, order[:5])
results['cancel'] = dict(stopped_after_sections=len(seen))
assert {p: sha(p) for p in sources} == source_hashes
(folder/'results.json').write_text(json.dumps(dict(status='passed', results=results), indent=2))
print('ACCEPTANCE:', folder, json.dumps(results['story']))
