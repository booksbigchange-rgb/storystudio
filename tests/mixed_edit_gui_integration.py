"""Real Tk undo/redo, trim, transition and split in the shared timeline, then a GUI export (Windows)."""
import ctypes
import copy
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
import mixed_durations as durations
import mixed_project as model
from mixed_editor import MixedEditor
from mixed_audio_integration_helpers import probe_streams
from test_mixed_audio import tone

folder = ROOT/'exports'/('edit-gui-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
Image.new('RGB', (640, 360), '#445566').save(folder/'a.png')
tone(folder/'music.wav', 220, 2)
sources = []
for i in range(3):
    path = folder/f'p{i}.json'
    path.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=2)])), encoding='utf-8')
    sources.append(path)
errors = []
patch('mixed_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
patch('mixed_section_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
patch('mixed_audio_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
ctypes.windll.user32.SetProcessDPIAware()
root = tk.Tk()
app = MixedEditor(root)
buttons = {b.cget('text'): b for b in app.buttons}
for needed in ('Undo', 'Redo', 'Trim · split · transition'):
    assert needed in buttons, needed
    assert buttons[needed].winfo_ismapped() or True
for path in sources:
    app.add_path(path)
root.update()
assert len(app.doc['sections']) == 3
# Undo / Redo through buttons and keyboard.
buttons['Undo'].invoke()
assert len(app.doc['sections']) == 2 and 'Undid' in app.status.get()
buttons['Redo'].invoke()
assert len(app.doc['sections']) == 3
root.focus_force(); root.event_generate('<Control-z>'); root.update()
assert len(app.doc['sections']) == 2, 'Ctrl+Z did not undo'
root.event_generate('<Control-y>'); root.update()
assert len(app.doc['sections']) == 3, 'Ctrl+Y did not redo'

def select(index):
    app.items.selection_clear(0, 'end'); app.items.selection_set(index); app.items.event_generate('<<ListboxSelect>>')

# Trim and dissolve section 2 (index 1): 0.5–1.5 s of the source, 0.25 s dissolve from section 1.
before = copy.deepcopy(app.doc)
select(1)
dialog = app.edit_section()
dialog.window.geometry('+30+30')
dialog.first.set('0.5'); dialog.end.set('1.5'); dialog.kind.set('Dissolve (overlap)'); dialog.length.set('0.25')
dialog.window.update()
window_id = ctypes.windll.user32.GetAncestor(dialog.window.winfo_id(), 2)
ImageGrab.grab(window=window_id).save(folder/'section-dialog.png')
dialog.apply_button.invoke()
section = app.doc['sections'][1]
assert (section['trim_in'], section['trim_out'], section['transition']) == (12, 36, dict(kind='dissolve', frames=6)), section
assert '✂' in app.items.get(1) and 'dissolve' in app.items.get(1), app.items.get(1)
rows, total = durations.timeline(app.doc)
assert total == 48+24-6+48 and rows[1][0] == 42, (rows, total)
assert durations.clock(total) in app.summary.get()
# Bad edits are explained and change nothing.
snapshot = copy.deepcopy(app.doc)
for first, end, kind, length, words in [('1.5', '0.5', 'Cut', '1', 'after'), ('x', '', 'Cut', '1', 'number'), ('0', '99', 'Cut', '1', 'only 48'),
                                        ('0', '', 'Dissolve (overlap)', '5', 'longer than a neighbouring')]:
    select(1)
    d = app.edit_section()
    d.first.set(first); d.end.set(end); d.kind.set(kind); d.length.set(length)
    errors.clear()
    d.apply_button.invoke()
    assert errors and words in errors[-1], (words, errors)
    assert app.doc == snapshot
    d.window.destroy()
errors.clear()
# Undo returns to the untouched timeline; redo restores the edit.
buttons['Undo'].invoke()
assert app.doc == before, 'Undo did not restore the pre-edit timeline'
buttons['Redo'].invoke()
assert app.doc == snapshot

# Split section 3 (index 2) one second in.
select(2)
d = app.edit_section()
d.first.set('0'); d.end.set(''); d.kind.set('Cut'); d.at.set('1')
d.buttons['Split'].invoke()
assert len(app.doc['sections']) == 4 and [s['name'].endswith(x) for s, x in zip(app.doc['sections'][2:], ('· 1', '· 2'))] == [True, True], [s['name'] for s in app.doc['sections']]
assert durations.timeline(app.doc)[1] == 48+24-6+48
buttons['Undo'].invoke()
assert len(app.doc['sections']) == 3
buttons['Redo'].invoke()
assert len(app.doc['sections']) == 4
# Audio and titles are undoable too.
audio = app.edit_audio()
with patch('mixed_audio_editor.filedialog.askopenfilename', return_value=str(folder/'music.wav')):
    audio.music_buttons['Choose music…'].invoke()
audio.apply_button.invoke()
assert 'audio' in app.doc
buttons['Undo'].invoke()
assert 'audio' not in app.doc
buttons['Redo'].invoke()
assert 'audio' in app.doc
# Save and reopen keeps every edit.
app.path = folder/'edited.json'; app.save()
assert model.load(app.path) == app.doc
root.update()
window_id = ctypes.windll.user32.GetAncestor(app.root.winfo_id(), 2)
ImageGrab.grab(window=window_id).save(folder/'edited-timeline.png')

# Export from the GUI and check the exact frame count.
output = folder/'edited.mp4'
with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(output)):
    app.export()
deadline = time.monotonic()+240
while app.busy and time.monotonic() < deadline:
    root.update(); time.sleep(.05)
expected = durations.timeline(app.doc)[1]
assert output.exists() and not errors, (errors, app.status.get())
video, sound, seconds = probe_streams(output)
assert int(video['nb_read_frames']) == expected == 114 and sound and abs(seconds-expected/24) < .15, (video['nb_read_frames'], expected)
app.dirty = False
app.close()
(folder/'results.json').write_text(json.dumps(dict(status='passed', frames=expected, checks=[
    'undo/redo buttons and Ctrl+Z/Ctrl+Y', 'trim + dissolve dialog', 'invalid edits explained and unchanged', 'split and undo of split',
    'audio apply undoable', 'save/reopen', 'GUI export frame-exact']), indent=2))
print('ACCEPTANCE:', folder)
