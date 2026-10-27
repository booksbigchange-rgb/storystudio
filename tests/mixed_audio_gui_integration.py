"""Real Tk audio-mix editing and a GUI-driven export, decoded and measured (Windows)."""
import ctypes
import hashlib
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from unittest.mock import patch
import uuid
from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
sys.path.insert(0, str(ROOT/'tests'))
import mixed_project as model
from mixed_editor import MixedEditor
from test_mixed_audio import tone, goertzel, decode, window
from mixed_audio_integration_helpers import probe_streams

folder = ROOT/'exports'/('audio-gui-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
Image.new('RGB', (1280, 720), '#dddddd').save(folder/'a.png')
tone(folder/'source.wav', 1000, 1.5, .4)
documentary = folder/'documentary.json'
documentary.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=2), dict(image='a.png', duration=2),
                                       dict(image='a.png', duration=2)], audio=dict(path='source.wav'))), encoding='utf-8')
music, narration, sfx = tone(folder/'music.wav', 220, 2, .5), tone(folder/'narration.wav', 1500, 1, .4), tone(folder/'sfx.wav', 3000, .5, .5)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
source_hash = sha(documentary), sha(folder/'source.wav')
errors = []
patch('mixed_audio_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
patch('mixed_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
ctypes.windll.user32.SetProcessDPIAware()
root = tk.Tk()
app = MixedEditor(root)
app.add_path(documentary)
root.update()
assert 'audio' not in app.doc

dialog = app.edit_audio()
dialog.window.geometry('+30+30')
# Invalid input is explained and does not change the clip list.
dialog.kind.set('Sound effect'); dialog.file.set(str(sfx)); dialog.start.set('-3')
dialog.buttons['Add'].invoke()
assert errors and not dialog.entries, errors
errors.clear()
dialog.start.set('abc'); dialog.buttons['Add'].invoke()
assert errors and not dialog.entries
errors.clear()
dialog.file.set(str(folder/'wrong.txt')); dialog.start.set('1'); dialog.buttons['Add'].invoke()
assert errors and not dialog.entries
errors.clear()

with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(music)):
    dialog.music_buttons['Choose music…'].invoke()
assert dialog.music_file.get() == str(music.resolve())
dialog.music_volume.set(.6)
dialog.duck.set('strong')
dialog.source_volume.set(1.0)
with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(narration)):
    dialog.kind.set('Narration'); dialog.buttons['Browse'].invoke()
dialog.start.set('3'); dialog.volume.set('1'); dialog.buttons['Add'].invoke()
with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(sfx)):
    dialog.kind.set('Sound effect'); dialog.buttons['Browse'].invoke()
dialog.start.set('9'); dialog.buttons['Add'].invoke()   # deliberately too late; fixed below with Update
dialog.items.selection_set(1); dialog.select()
dialog.start.set('5'); dialog.buttons['Update'].invoke()
assert not errors, errors
assert [(k, c['start']) for k, c in dialog.entries] == [('narration', 3.0), ('sfx', 5.0)]
dialog.window.lift(); dialog.window.update()
settled = tk.BooleanVar(value=False)
root.after(700, lambda: settled.set(True))
root.wait_variable(settled)
window_id = ctypes.windll.user32.GetAncestor(dialog.window.winfo_id(), 2)
ImageGrab.grab(window=window_id).save(folder/'audio-editor.png')
dialog.apply_button.invoke()
audio = app.doc['audio']
assert app.dirty and audio['music']['volume'] == .6 and audio['duck'] == 'strong'
assert [c['start'] for c in audio['narration']] == [3.0] and [c['start'] for c in audio['sfx']] == [5.0]

# Cancel leaves the timeline unchanged.
before = json.dumps(app.doc, sort_keys=True)
second = app.edit_audio()
second.entries.clear(); second.duck.set('off')
second.window.destroy()
assert json.dumps(app.doc, sort_keys=True) == before

app.path = folder/'timeline.json'; app.save()
assert model.load(app.path) == app.doc
saved = json.loads(app.path.read_text())['audio']
assert saved['music']['file'] == 'music.wav', saved['music']

# Re-open: dialog shows saved values, then Clear removes the mix without touching the sources.
reopened = app.edit_audio()
assert reopened.music_file.get() == str(music.resolve()) and len(reopened.entries) == 2
reopened.window.destroy()


def export_through_gui(target, timeout=180):
    with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(target)):
        app.export()
    assert app.busy and 'disabled' not in app.cancel_button.state()
    deadline = time.monotonic()+timeout
    while app.busy and time.monotonic() < deadline:
        root.update(); time.sleep(.05)
    assert not app.busy, 'Export never finished'


output = folder/'gui-mix.mp4'
export_through_gui(output)
assert output.exists() and not errors, (errors, app.status.get())
video, sound, seconds = probe_streams(output)
assert video['codec_name'] == 'h264' and (video['width'], video['height']) == (1280, 720) and int(video['nb_read_frames']) == 144
assert len(sound) == 1 and sound[0]['codec_name'] == 'aac' and abs(seconds-6) < .12
samples = decode(output)
assert goertzel(window(samples, .3, 1.3), 1000) > .15 and goertzel(window(samples, 3.1, 3.9), 1500) > .15
assert goertzel(window(samples, 5.05, 5.45), 3000) > .15
assert goertzel(window(samples, .3, 1.3), 220) < goertzel(window(samples, 2.2, 2.9), 220)*.5
original = sha(output)
# GUI export to an existing name is refused and the file is untouched.
export_through_gui(output)
assert errors and ('existing' in errors[-1].lower() or 'protected' in errors[-1].lower()), errors
assert sha(output) == original
errors.clear()
# Missing media is reported through the GUI; no output appears.
(folder/'music.wav').rename(folder/'music-moved.wav')
missing = folder/'missing-media.mp4'
export_through_gui(missing)
assert errors and 'Music file is missing' in errors[-1], errors
assert not missing.exists() and all('disabled' not in b.state() for b in app.buttons)
(folder/'music-moved.wav').rename(folder/'music.wav')
errors.clear()
# Clearing the mix returns to plain source-project audio.
cleared = app.edit_audio()
cleared.clear_music(); cleared.entries.clear(); cleared.duck.set('medium'); cleared.source_volume.set(1.0)
cleared.apply_button.invoke()
assert 'audio' not in app.doc
plain = folder/'gui-plain.mp4'
export_through_gui(plain)
plain_samples = decode(plain)
assert goertzel(window(plain_samples, .3, 1.3), 1000) > .15 and goertzel(window(plain_samples, 2.2, 2.9), 220) < .01
assert (sha(documentary), sha(folder/'source.wav')) == source_hash
app.dirty = False
app.close()
(folder/'results.json').write_text(json.dumps(dict(status='passed', checks=['audio dialog add/update/remove/cancel/apply/save/reopen',
    'invalid start/number/file rejected', 'GUI export decoded and measured', 'no-overwrite shown in GUI', 'missing media shown in GUI',
    'clearing the mix restores source-only audio', 'sources unchanged']), indent=2))
print('ACCEPTANCE:', folder)
