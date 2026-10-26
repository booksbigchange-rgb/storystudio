"""Animation keys through the real browser renderer: JS/Python parity, pixels, decoded MP4, mixed export.

Run with the character-editor environment (Playwright + Chrome/Edge). The mixed export needs the
engine's FFmpeg layout (tools/ffmpeg) or ffmpeg on PATH.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
import cartoon_project as project
import renderer
import argparse

folder = ROOT/'exports'/('cartoon-keys-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
FFMPEG = renderer.find_ffmpeg()
checks = []


def base():
    doc = project.new_project()
    doc['scenes'][0].update(character='fox', action='idle', expression='happy', duration=2, title='', x=.4)
    return doc


swept = base()
swept['scenes'][0]['keys'] = [{'at': 0, 'x': .25, 'tilt': -.25, 'lift': 0},
                              {'at': .5, 'x': .45, 'tilt': 0, 'lift': 70, 'expression': 'surprised', 'action': 'wave'},
                              {'at': 1, 'x': .65, 'tilt': .25, 'lift': 0, 'size': 1.15}]
swept = project.validate(swept)

# 1. The JavaScript renderer and Python model agree everywhere, in both orientations.
with renderer.scene_page(swept, 640, 360) as (page, errors):
    for portrait in (False, True):
        variant = copy.deepcopy(swept)
        if portrait:
            variant['format'] = 'Shorts / TikTok 9:16'
            page.set_viewport_size(dict(width=360, height=640))
            page.wait_for_timeout(300)  # let the page's own resize handler finish before sampling
        page.evaluate('(doc)=>window.setProject(doc)', variant)
        for step in range(0, 49):
            t = step/24
            page.evaluate('(t)=>window.render(t)', t)
            js = page.evaluate('window.frameInfo.keys')
            py = project.key_values(variant['scenes'][0], t/2)
            for name in ('x', 'size', 'lift', 'tilt'):
                assert abs(js[name]-py[name]) < 1e-9, (portrait, t, name, js[name], py[name])
            assert js['expression'] == py['expression'] and js['action'] == py['action'], (t, js, py)
    assert not errors, errors
    checks.append('JS keyValues equals Python key_values at 49 times in both orientations')

    # 2. Keys change pixels and geometry; neutral keys leave an unkeyed scene byte-identical.
    plain = base()
    neutral = copy.deepcopy(plain)
    neutral['scenes'][0]['keys'] = [{'at': 0, 'x': .4, 'size': 1.0, 'lift': 0, 'tilt': 0, 'expression': 'happy', 'action': 'idle'}]
    shots = {}
    page.set_viewport_size(dict(width=640, height=360))
    page.wait_for_timeout(300)
    for name, doc in (('plain', plain), ('neutral', neutral)):
        page.evaluate('(doc)=>window.setProject(doc)', project.validate(doc))
        page.evaluate('window.render(.8)')
        shots[name] = page.screenshot()
    assert shots['plain'] == shots['neutral'], 'Neutral keys altered the picture'
    base_info = None
    for name, extra in (('lift', {'lift': 80}), ('tilt', {'tilt': .4}), ('size', {'size': 1.2})):
        doc = base(); doc['scenes'][0]['keys'] = [{'at': 0, **extra}]
        page.evaluate('(doc)=>window.setProject(doc)', project.validate(doc))
        page.evaluate('window.render(.8)')
        shot = page.screenshot()
        assert shot != shots['plain'], name+' key has no visual effect'
        (folder/f'key-{name}.png').write_bytes(shot)
        info = page.evaluate('window.frameInfo')
        if name == 'lift':
            page.evaluate('(doc)=>window.setProject(doc)', project.validate(plain)); page.evaluate('window.render(.8)')
            base_info = page.evaluate('window.frameInfo')
            assert abs(base_info['y']-info['y']-80) < 1e-6, (base_info, info)
    checks.append('neutral keys byte-identical to no keys; lift/tilt/size change the frame; lift moves exactly 80 units')

# 3. A real MP4: the character visibly travels, tilts and changes pose; fully decoded and verified.
output = folder/'keyed-landscape.mp4'
width, height, fps = project.dimensions(swept)
renderer.export(argparse.Namespace(document=swept, output=str(output), duration=2, width=width, height=height, fps=fps, audio=None, overwrite=False))
details = renderer.verify(output, 2, width, height, fps)
raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(output), '-vf', 'scale=320:180', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                     capture_output=True, check=True).stdout
size = 320*180*3
assert len(raw) == 48*size, len(raw)


def fur_centroid(frame):
    xs = [i % 320 for i in range(320*180) if abs(frame[i*3]-233) < 32 and abs(frame[i*3+1]-131) < 32 and abs(frame[i*3+2]-67) < 32]
    assert len(xs) > 200, 'character not found'
    return sum(xs)/len(xs)


positions = [fur_centroid(raw[n*size:(n+1)*size]) for n in (0, 24, 47)]
assert positions[0] < positions[1] < positions[2], positions
assert 110 < positions[2]-positions[0] < 180, positions            # .25→.65 of 320 px is 128 px; tail and tilt shift the centroid
assert len({hashlib.sha256(raw[n*size:(n+1)*size]).hexdigest() for n in range(48)}) > 30, 'frames not animated'
checks.append(f'decoded 48-frame MP4 moves right: centroid {positions[0]:.0f}→{positions[1]:.0f}→{positions[2]:.0f}px')

# 4. Keyed cartoon section inside a mixed timeline (shared engine, audio mix and no-overwrite).
sys.path.insert(0, str(ROOT/'engine'))
import project as engine_project            # the documentary model; both models now live in one process
assert hasattr(engine_project, 'read_project') and not hasattr(engine_project, 'key_values')
assert hasattr(project, 'key_values')
import mixed_project as model
from mixed_render import export
source = folder/'keyed.json'
short = copy.deepcopy(swept); short['scenes'][0]['duration'] = 1
short['scenes'][0]['keys'] = [{'at': 0, 'x': .25}, {'at': 1, 'x': .65}]
source.write_text(json.dumps(short), encoding='utf-8')
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
timeline = model.new_project()
timeline['sections'] = [dict(engine='cartoon', project=str(source), name='Keyed fox')]
mixed = folder/'mixed.mp4'
export(timeline, mixed)
result = json.loads(subprocess.run([ROOT.joinpath('tools/ffmpeg/ffprobe.exe') if ROOT.joinpath('tools/ffmpeg/ffprobe.exe').is_file() else 'ffprobe',
    '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(mixed)], capture_output=True, text=True, check=True).stdout)
video = next(s for s in result['streams'] if s['codec_type'] == 'video')
assert int(video['nb_read_frames']) == 24 and (video['width'], video['height']) == (1280, 720) and any(s['codec_type'] == 'audio' for s in result['streams'])
try:
    export(timeline, mixed)
    raise AssertionError('overwrote')
except FileExistsError:
    pass
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
checks.append('keyed character section exports inside a mixed timeline (24 frames, audio, no overwrite)')
(folder/'results.json').write_text(json.dumps(dict(status='passed', checks=checks, centroids=positions, sha256=hashlib.sha256(output.read_bytes()).hexdigest()), indent=2))
print('ACCEPTANCE:', folder)
