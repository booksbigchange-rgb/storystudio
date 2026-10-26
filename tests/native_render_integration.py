"""Native (Pillow) character renderer against the browser renderer: parity, decoded MP4s and speed."""
import argparse
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
from PIL import Image, ImageChops, ImageStat
import native_scene
import project
import renderer

folder = ROOT/'exports'/('native-render-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
FFMPEG = renderer.find_ffmpeg()
report = dict(parity=[], exports={})


def scene(**kw):
    doc = project.new_project()
    doc['scenes'][0].update({'duration': 6, 'title': 'Hello, little star!', **kw})
    return project.validate(doc)


def compare(browser_page, doc, t, size, label):
    browser_page.evaluate('(d)=>window.setProject(d)', doc)
    browser_page.evaluate('(t)=>window.render(t)', t)
    reference = Image.open(io.BytesIO(browser_page.screenshot())).convert('RGB')
    mine = native_scene.NativeScene(doc, *size).frame(t)
    diff = ImageChops.difference(reference, mine)
    mean = sum(ImageStat.Stat(diff).mean)/3
    strong = sum(1 for px in diff.convert('L').getdata() if px > 60)/(size[0]*size[1])
    report['parity'].append(dict(case=label, mean=round(mean, 2), strong=round(strong, 4)))
    # Small differences come from anti-aliasing and the caption font; real layout errors are far larger.
    assert mean < 4 and strong < .02, (label, mean, strong)
    if label.endswith('landscape fox wave 1.0'):
        side = Image.new('RGB', (size[0]*2, size[1])); side.paste(reference, (0, 0)); side.paste(mine, (size[0], 0)); side.save(folder/'browser-left-native-right.png')


cases = []
for character in project.CHARACTERS:
    cases.append((f'{character} landscape', dict(character=character, action='wave'), 1.0, False))
for expression in project.EXPRESSIONS:
    cases.append((f'{expression}', dict(expression=expression, action='talk', character='rabbit'), 1.3, False))
for action in project.ACTIONS:
    cases.append((f'{action}', dict(action=action, character='bear', background='sunset'), 4.0, False))
cases += [('night', dict(background='night', character='fox'), 2.0, False),
          ('keyed', dict(character='fox', action='idle', keys=[{'at': 0, 'x': .3, 'tilt': -.3}, {'at': 1, 'x': .6, 'lift': 60, 'tilt': .3, 'expression': 'surprised'}]), 3.0, False),
          ('portrait', dict(character='fox', action='wave'), 1.0, True), ('portrait story', dict(character='rabbit', action='story'), 8.0, True)]
for name, extra, t, portrait in cases:
    doc = scene(**extra)
    size = (360, 640) if portrait else (640, 360)
    if portrait:
        doc['format'] = 'Shorts / TikTok 9:16'
    with renderer.scene_page(doc, *size) as (page, errors):
        compare(page, doc, t, size, f'{name} {"portrait" if portrait else "landscape"} fox wave {t:.1f}' if name == 'fox wave' else f'{name} {t:.1f}' if 'landscape' not in name and not portrait else f'{name} {t:.1f}')
        assert not errors, errors

# Real 3-second exports with both engines: both decode and verify; native must be clearly faster.
doc = scene(character='bear', action='walk')
width, height, fps = 1280, 720, 24
timings = {}
for engine in ('browser', 'native'):
    out = folder/f'{engine}.mp4'
    args = argparse.Namespace(document=doc, output=str(out), duration=3, width=width, height=height, fps=fps, audio=None, overwrite=False, engine=engine)
    started = time.perf_counter()
    renderer.export(args)
    timings[engine] = round(time.perf_counter()-started, 2)
    renderer.verify(out, 3, width, height, fps)
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(out), '-vf', 'scale=64:36', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    frames = [raw[i:i+6912] for i in range(0, len(raw), 6912)]
    assert len(frames) == 72 and len(set(frames)) > 40, 'frozen or missing frames'
    report['exports'][engine] = dict(seconds=timings[engine], sha256=__import__('hashlib').sha256(out.read_bytes()).hexdigest())
assert timings['native'] < timings['browser']*.7, timings         # CI runners vary; locally it is ~5x faster
# Decode exactly as players do (BT.709, limited range) so the check does not depend on the FFmpeg version.
def decoded(engine):
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(folder/f'{engine}.mp4'), '-vf', 'scale=160:90:in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return [Image.frombytes('RGB', (160, 90), raw[i:i+43200]) for i in range(0, len(raw), 43200)]
source = native_scene.NativeScene(doc, width, height)
native_frames = decoded('native')
worst = max(sum(ImageStat.Stat(ImageChops.difference(source.frame(n/fps).resize((160, 90), Image.BOX), native_frames[n])).mean)/3 for n in range(0, 72, 6))
report['native_decoded_vs_rendered_frame_difference'] = round(worst, 2)
assert worst < 3.5, f'native MP4 colours drifted from the rendered frames: {worst}'      # correct BT.709 conversion
browser_gap = max(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean)/3 for a, b in zip(decoded('browser'), native_frames))
report['browser_vs_native_decoded'] = round(browser_gap, 2)
assert browser_gap < 12, browser_gap      # the browser path tags BT.601 data as BT.709, so it is slightly off; native is the accurate one
# Existing outputs are protected and cancellation still works on the native path.
try:
    renderer.export(argparse.Namespace(document=doc, output=str(folder/'native.mp4'), duration=3, width=width, height=height, fps=fps, audio=None, overwrite=False, engine='native'))
    raise AssertionError('overwrote')
except FileExistsError:
    pass
import threading
event = threading.Event()
partial = folder/'cancelled.mp4'
try:
    renderer.export(argparse.Namespace(document=doc, output=str(partial), duration=3, width=width, height=height, fps=fps, audio=None, overwrite=False, engine='native'), lambda *_: event.set(), event)
    raise AssertionError('cancel ignored')
except renderer.Cancelled:
    pass
assert not partial.exists() and not list(folder.glob('.*.partial.mp4'))
report['status'] = 'passed'
(folder/'results.json').write_text(json.dumps(report, indent=2))
print('ACCEPTANCE:', folder, json.dumps(timings), json.dumps({k: v for k, v in report.items() if 'decoded' in k}))
