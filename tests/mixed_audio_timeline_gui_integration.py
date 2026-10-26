"""Real Tk multi-lane audio timeline: waveforms, mouse dragging, fades and a decoded GUI export (Windows)."""
import ctypes
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
from mixed_editor import MixedEditor
from mixed_audio_integration_helpers import probe_streams
from test_mixed_audio import tone, goertzel, decode, window as audio_window

folder = ROOT/'exports'/('audio-timeline-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
Image.new('RGB', (640, 360), '#445566').save(folder/'a.png')
source = folder/'p.json'
source.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=2)]*3)), encoding='utf-8')  # 6 seconds
music, voice, hit = tone(folder/'music.wav', 220, 3, .5), tone(folder/'voice.wav', 1500, 1.5, .4), tone(folder/'hit.wav', 3000, .5, .5)
errors = []
patch('mixed_audio_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
patch('mixed_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
ctypes.windll.user32.SetProcessDPIAware()
root = tk.Tk()
app = MixedEditor(root)
app.add_path(source)
root.update()


def pump(check, timeout=60):
    deadline = time.monotonic()+timeout
    while not check():
        root.update(); time.sleep(.03)
        assert time.monotonic() < deadline, 'timed out'


dialog = app.edit_audio()
dialog.window.geometry('+20+20')
with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(music)):
    dialog.music_buttons['Choose music…'].invoke()
for kind, path, start in (('Narration', voice, '1'), ('Sound effect', hit, '4.5')):
    with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(path)):
        dialog.kind.set(kind); dialog.buttons['Browse'].invoke()
    dialog.start.set(start); dialog.buttons['Add'].invoke()
assert not errors, errors
# Waveforms are decoded in the background and drawn when they arrive.
pump(lambda: len(dialog.waves) == 3)
for path, data in dialog.waves.items():
    assert max(data['peaks']) > .3 and len(data['peaks']) > 20, path
timeline = dialog.timeline
dialog.window.update()
assert abs(dialog.total_seconds()-6) < 1e-9 and len(timeline.hitboxes) == 2, (dialog.total_seconds(), timeline.hitboxes)
assert len(timeline.find_all()) > 150, 'waveforms were not drawn'
window_id = ctypes.windll.user32.GetAncestor(dialog.window.winfo_id(), 2)
ImageGrab.grab(window=window_id).save(folder/'timeline-before.png')


def center(index):
    x0, y0, x1, y1, _ = next(h for h in timeline.hitboxes if h[4] == index)
    return (x0+x1)/2, (y0+y1)/2, x0


# Drag the narration clip (index 0) 1 s to the right with real mouse events.
x, y, left = center(0)
pixels = timeline.scale
timeline.event_generate('<ButtonPress-1>', x=int(x), y=int(y)); dialog.window.update()
assert timeline.selected == 0 and dialog.items.curselection() == (0,) and dialog.kind.get() == 'Narration'
timeline.event_generate('<B1-Motion>', x=int(x+pixels), y=int(y)); dialog.window.update()
timeline.event_generate('<ButtonRelease-1>', x=int(x+pixels), y=int(y)); dialog.window.update()
moved = dialog.entries[0][1]['start']
assert abs(moved-2.0) <= 1/24+1e-9 and dialog.start.get() == f'{moved:g}', moved
assert round(moved*24) == moved*24 or abs(moved*24-round(moved*24)) < 1e-6, 'start is not frame-snapped'
assert dialog.entries[1][1]['start'] == 4.5, 'the other clip must not move'
# Clamped at both ends.
x, y, left = center(0)
timeline.press(x, y); assert timeline.drag(-500) == 0
assert timeline.drag(5000) <= 6-.1+1e-9; timeline.release()
assert dialog.entries[0][1]['start'] <= 5.9 + 1e-9
# Put it back exactly at 2 s through the form so the export check below is exact, then add fades.
dialog.items.selection_clear(0, 'end'); dialog.items.selection_set(0); dialog.select()
dialog.start.set('2'); dialog.fade_in.set('0.5'); dialog.fade_out.set('0.5'); dialog.buttons['Update'].invoke()
assert not errors, errors
assert dialog.entries[0][1]['start'] == 2.0 and dialog.entries[0][1]['fade_in'] == .5, dialog.entries[0][1]
assert 'fade 0.5/0.5' in dialog.items.get(0)
# Invalid fades are explained and change nothing.
before = [dict(c) for _, c in dialog.entries]
dialog.fade_in.set('99'); dialog.buttons['Update'].invoke()
assert errors and 'fade in' in errors[-1].lower() and [dict(c) for _, c in dialog.entries] == before
errors.clear(); dialog.fade_in.set('0.5')
# Clicking empty space deselects nothing and moves nothing; clicking a clip selects it in the list.
assert timeline.press(timeline.winfo_width()-20, 10) is None
timeline.press(*center(1)[:2]); timeline.release()
assert dialog.items.curselection() == (1,) and dialog.kind.get() == 'Sound effect'
dialog.music_fade_in.set('0'); dialog.music_fade_out.set('0')
dialog.window.update()
ImageGrab.grab(window=window_id).save(folder/'timeline-after.png')
dialog.apply_button.invoke()
audio = app.doc['audio']
assert audio['narration'][0]['start'] == 2.0 and audio['music']['fade_in'] == 0 and audio['sfx'][0]['start'] == 4.5

output = folder/'timeline.mp4'
with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(output)):
    app.export()
pump(lambda: not app.busy, 240)
assert output.exists() and not errors, (errors, app.status.get())
video, sound, seconds = probe_streams(output)
assert int(video['nb_read_frames']) == 144 and sound and abs(seconds-6) < .15
samples = decode(output)
level = lambda a, b, hz: goertzel(audio_window(samples, a, b), hz)
assert level(1.1, 1.9, 1500) < .01, 'narration still plays at its old position'
assert level(2.6, 3.2, 1500) > .15 and level(2.0, 2.15, 1500) < level(2.6, 3.2, 1500)*.5, 'narration is not at 2 s, or its fade-in is missing'
assert level(3.38, 3.5, 1500) < level(2.6, 3.2, 1500)*.5, 'fade-out missing'
assert level(4.55, 4.95, 3000) > .15 and level(.3, 1.0, 3000) < .01
assert level(.3, 1.0, 220) > .1 and level(5.7, 5.95, 220) > .1, 'music fades were set to zero, so it should be full at both ends'
[b for b in app.buttons if b.cget('text') == 'Undo'][0].invoke()
assert 'audio' not in app.doc
app.dirty = False
app.close()
(folder/'results.json').write_text(json.dumps(dict(status='passed', checks=['waveforms decoded and drawn', 'real mouse drag moves a clip, frame-snapped and clamped',
    'timeline click selects list row', 'clip and music fades', 'invalid fade explained', 'decoded export matches dragged positions', 'undo']), indent=2))
print('ACCEPTANCE:', folder)
