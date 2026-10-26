"""Self-test of the unified portable build: real Tk editors and a real mixed export through the helper exes.

Runs inside StoryStudio.exe (windowed), so every result is written to files:
  StoryStudio.exe --self-test --output <new folder>   -> results.json, selftest.log
Exit code 0 means every check passed.
"""
import json
import hashlib
from pathlib import Path
import math
import struct
import subprocess
import sys
import time
import traceback
import wave


def tone(path, hertz, seconds, amplitude=.4):
    rate = 48000
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate)
        handle.writeframes(b''.join(struct.pack('<h', round(32767*amplitude*math.sin(2*math.pi*hertz*n/rate))) for n in range(round(rate*seconds))))
    return path


def run(argv):
    import runtime
    output = Path(argv[argv.index('--output')+1]) if '--output' in argv else runtime.app_root(__file__)/'exports'/time.strftime('unified-self-test-%Y%m%d-%H%M%S')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)  # never reuse or overwrite a previous result folder
    log = output/'selftest.log'
    try:
        results = checks(output)
        (output/'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        log.write_text('PASS\n', encoding='utf-8')
        return 0
    except BaseException:
        log.write_text(traceback.format_exc(), encoding='utf-8')
        return 1


def checks(folder):
    import tkinter as tk
    from unittest.mock import patch
    from PIL import Image
    import mixed_project
    import mixed_render
    import studio_hub
    from mixed_editor import MixedEditor
    done = []
    Image.new('RGB', (1280, 720), '#556677').save(folder/'a.png')
    Image.new('RGB', (1280, 720), '#bb9955').save(folder/'b.png')
    tone(folder/'narration.wav', 1000, 1.5)
    tone(folder/'music.wav', 220, 1)
    tone(folder/'effect.wav', 3000, .4, .5)
    documentary = folder/'documentary.json'
    documentary.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=1), dict(image='b.png', duration=1)],
                                           audio=dict(path='narration.wav'))), encoding='utf-8')
    cartoon = folder/'character.json'
    cartoon.write_text(json.dumps(dict(version=2, name='Self test', format='Landscape 16:9', quality='Standard · 720p / 24 fps', audio=None,
        scenes=[dict(title='', duration=2, character='fox', expression='happy', action='idle', background='meadow', x=.4, size=1, speed=1,
                     keys=[{'at': 0, 'x': .25}, {'at': 1, 'x': .6, 'tilt': .2}])])), encoding='utf-8')
    hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (documentary, cartoon, folder/'narration.wav')}
    # The helper executables and bundled tools must exist exactly where the launcher expects them.
    for name in ('hub', 'gate', 'cartoon'):
        assert runtime_helper(name).is_file(), name
    done.append('helper executables present')
    # Editors open (smoke) from the compiled hub.
    for kind in ('documentary', 'mixed'):
        studio_hub.run_editor(kind, None, smoke=True)
    done.append('documentary and shared-timeline editors open')
    errors = []
    patch('mixed_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
    root = tk.Tk()
    app = MixedEditor(root)
    app.add_path(documentary)
    app.add_path(cartoon)
    root.update()
    dialog = app.edit_audio()
    with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(folder/'music.wav')):
        dialog.music_buttons['Choose music…'].invoke()
    dialog.duck.set('strong')
    with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(folder/'effect.wav')):
        dialog.kind.set('Sound effect'); dialog.buttons['Browse'].invoke()
    dialog.start.set('3'); dialog.buttons['Add'].invoke()
    assert not errors, errors
    dialog.apply_button.invoke()
    assert app.doc['audio']['music'] and len(app.doc['audio']['sfx']) == 1
    done.append('audio mix dialog applied')
    output = folder/'unified-export.mp4'
    with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(output)):
        app.export()
    deadline = time.monotonic()+420
    while app.busy and time.monotonic() < deadline:
        root.update(); time.sleep(.05)
    assert not app.busy and output.is_file() and not errors, (errors, app.status.get())
    first = hashlib.sha256(output.read_bytes()).hexdigest()
    with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(output)):
        app.export()
    while app.busy and time.monotonic() < deadline:
        root.update(); time.sleep(.05)
    assert errors and 'protected' in errors[-1] and hashlib.sha256(output.read_bytes()).hexdigest() == first
    done.append('mixed export through compiled workers; existing export protected')
    # Same story in portrait: both orientations through the compiled workers.
    portrait = folder/'unified-export-portrait.mp4'
    app.format.set('portrait'); app.change_format()
    with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(portrait)):
        app.export()
    deadline = time.monotonic()+420
    while app.busy and time.monotonic() < deadline:
        root.update(); time.sleep(.05)
    assert portrait.is_file(), (errors, app.status.get())
    app.dirty = False
    app.close()

    def verify(path, size):
        probe = mixed_render.tool('ffprobe')
        info = json.loads(subprocess.run([probe, '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(path)],
                                         capture_output=True, text=True, check=True).stdout)
        video = next(s for s in info['streams'] if s['codec_type'] == 'video')
        sound = [s for s in info['streams'] if s['codec_type'] == 'audio']
        assert video['codec_name'] == 'h264' and (video['width'], video['height']) == size and int(video['nb_read_frames']) == 96, video
        assert sound and sound[0]['codec_name'] == 'aac' and abs(float(info['format']['duration'])-4) < .15
        decode = subprocess.run([mixed_render.tool('ffmpeg'), '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'], capture_output=True, text=True)
        assert decode.returncode == 0 and not decode.stderr.strip(), decode.stderr
    verify(output, (1280, 720))
    verify(portrait, (720, 1280))
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in hashes} == hashes, 'source project or audio changed'
    done.append('H.264/AAC 1280x720 and 720x1280, 96 frames, 4 s each, fully decoded; sources unchanged')
    return dict(status='passed', checks=done, frames=96, sha256=first, output=output.name)


def runtime_helper(name):
    import runtime
    return runtime.helper(name)
