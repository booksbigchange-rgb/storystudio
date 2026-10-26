"""Layered-artwork character through real exports: import safely, render both formats, mixed timeline, missing pack (no Tk)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT/'exports'/('rig-acceptance-'+uuid.uuid4().hex)
library = folder/'library'
folder.mkdir(parents=True)
os.environ['STORYSTUDIO_CHARACTERS'] = str(library)           # inherited by the export worker processes
sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
sys.path.insert(0, str(ROOT/'engine'))
from PIL import Image
import cartoon_project as project
import character_rig
import renderer
import sample_character

FFMPEG = renderer.find_ffmpeg()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
layers = folder/'my-layers'
sample_character.write(layers)
source_hashes = {p.name: sha(p) for p in layers.glob('*.png')}
character_rig.import_pack(layers, 'robo', library)
assert {p.name: sha(p) for p in layers.glob('*.png')} == source_hashes, 'source layers were modified'
try:
    character_rig.import_pack(layers, 'robo', library)
    raise AssertionError('overwrote an existing pack')
except FileExistsError:
    pass
checks = ['import leaves the source layers untouched', 'second import refused']


def robot_pixels(image):
    return sum(1 for x in range(image.width) for y in range(image.height)
               if (lambda p: abs(p[0]-120) < 14 and abs(p[1]-150) < 14 and abs(p[2]-190) < 14)(image.getpixel((x, y))))


def frames_of(path, width, height, step=6):
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(path), '-vf', f'scale={width}:{height}:in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    size = width*height*3
    return [Image.frombytes('RGB', (width, height), raw[i:i+size]) for i in range(0, len(raw), size)][::step]


# 1. Real exports in both formats with the layered character.
doc = project.new_project()
doc['scenes'][0].update(character='custom:robo', action='wave', duration=2, title='Hello from layers')
doc['scenes'].append(dict(project.new_scene(), character='custom:robo', action='walk', duration=2, expression='surprised', background='night',
                          keys=[{'at': 0, 'x': .3}, {'at': 1, 'x': .6, 'tilt': .15}]))
doc = project.validate(doc)
for name in project.FORMATS:
    variant = json.loads(json.dumps(doc)); variant['format'] = name
    width, height, fps = project.dimensions(variant)
    out = folder/f'{"portrait" if height > width else "landscape"}.mp4'
    renderer.export(argparse.Namespace(document=variant, output=str(out), duration=4, width=width, height=height, fps=fps, audio=None, overwrite=False))
    renderer.verify(out, 4, width, height, fps)
    frames = frames_of(out, 160, 90 if width > height else 284, step=8)
    assert all(robot_pixels(f) > 25 for f in frames), [robot_pixels(f) for f in frames]
    assert len({f.tobytes() for f in frames}) == len(frames), 'frozen frames'
    try:
        renderer.export(argparse.Namespace(document=variant, output=str(out), duration=4, width=width, height=height, fps=fps, audio=None, overwrite=False))
        raise AssertionError('overwrote an export')
    except FileExistsError:
        pass
checks += ['layered character exports 16:9 and 9:16, decoded, animated, no-overwrite']

# 2. Inside a mixed timeline (documentary + layered character) through the export workers.
import mixed_project as model
from mixed_render import export
Image.new('RGB', (1280, 720), '#556677').save(folder/'a.png')
(folder/'doc.json').write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=1)])))
short = json.loads(json.dumps(doc)); short['scenes'] = short['scenes'][:1]; short['scenes'][0]['duration'] = 1
(folder/'char.json').write_text(json.dumps(short))
timeline = model.new_project()
timeline['sections'] = [dict(engine='documentary', project=str(folder/'doc.json'), name='Doc'), dict(engine='cartoon', project=str(folder/'char.json'), name='Robo')]
mixed = folder/'mixed.mp4'
export(timeline, mixed)
info = json.loads(subprocess.run([renderer.find_ffprobe(), '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(mixed)], capture_output=True, text=True, check=True).stdout)
video = next(s for s in info['streams'] if s['codec_type'] == 'video')
assert int(video['nb_read_frames']) == 48 and any(s['codec_type'] == 'audio' for s in info['streams'])
assert robot_pixels(frames_of(mixed, 160, 90, step=1)[36]) > 25, 'robot missing from the mixed export'
checks.append('mixed timeline export with a layered character (48 frames, audio, decoded)')

# 3. A missing pack stops the export before anything is rendered.
ghost = json.loads(json.dumps(short)); ghost['scenes'][0]['character'] = 'custom:ghost'
(folder/'ghost.json').write_text(json.dumps(ghost))
timeline['sections'][1]['project'] = str(folder/'ghost.json')
before = set((ROOT/'exports').glob('mixed-run-*'))
target = folder/'never.mp4'
try:
    export(timeline, target)
    raise AssertionError('missing pack accepted')
except Exception as exc:
    assert 'ghost' in str(exc), str(exc)
assert not target.exists()
for run in set((ROOT/'exports').glob('mixed-run-*'))-before:
    assert not list(run.glob('raw-*')) and not list(run.glob('section-*')), 'rendered before the pack check'
checks.append('missing pack explained before rendering')
assert {p.name: sha(p) for p in layers.glob('*.png')} == source_hashes
assert not list(library.glob('.import-*'))
(folder/'results.json').write_text(json.dumps(dict(status='passed', checks=checks), indent=2))
print('ACCEPTANCE:', folder)
