"""Real Tk handling of a 200-section story: ordering, totals, limits, save/reopen, cancel and retry (Windows)."""
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
import mixed_durations as durations
import mixed_project as model
from mixed_editor import MixedEditor
from mixed_audio_integration_helpers import probe_streams

folder = ROOT/'exports'/('long-gui-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
Image.new('RGB', (640, 360), '#445566').save(folder/'a.png')
lengths = [1.5, 2, 2.25, 3]
sources = []
for i in range(model.MAX_SECTIONS):
    path = folder/f'p{i:03d}.json'
    path.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=lengths[i % 4])])), encoding='utf-8')
    sources.append(path)
hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
errors = []
patch('mixed_editor.messagebox.showerror', side_effect=lambda title, text, **kw: errors.append(text)).start()
ctypes.windll.user32.SetProcessDPIAware()
root = tk.Tk()
app = MixedEditor(root)
started = time.monotonic()
for path in sources:
    app.add_path(path)
elapsed = time.monotonic()-started
root.update()
assert len(app.doc['sections']) == model.MAX_SECTIONS and app.items.size() == model.MAX_SECTIONS
assert elapsed < 30, f'Adding {model.MAX_SECTIONS} sections took {elapsed:.1f}s'
total_frames = sum(round(lengths[i % 4]*24) for i in range(model.MAX_SECTIONS))
assert durations.clock(total_frames) in app.summary.get() and f'{model.MAX_SECTIONS} of {model.MAX_SECTIONS}' in app.summary.get(), app.summary.get()
assert len(app.hitboxes) == model.MAX_SECTIONS
assert app.items.yview()[1] < 1, 'list must scroll'
assert 'starts' in app.items.get(5) and app.items.get(5).startswith('006')

# Past the limit: explained, nothing added.
try:
    app.add_path(sources[0])
    raise AssertionError('201st section accepted')
except ValueError as exc:
    assert str(model.MAX_SECTIONS) in str(exc)
assert len(app.doc['sections']) == model.MAX_SECTIONS

# Reordering through real buttons keeps the total and every section.
names = lambda: [s['name'] for s in app.doc['sections']]
buttons = {b.cget('text'): b for b in app.buttons}
original = names()
app.items.selection_clear(0, 'end'); app.items.selection_set(150)
buttons['To top'].invoke()
assert names()[0] == original[150] and names()[1:151] == original[:150] and app.selected() == 0
buttons['To bottom'].invoke()
assert names()[-1] == original[150] and names()[:150] == original[:150]
app.items.selection_clear(0, 'end'); app.items.selection_set(10)
buttons['Duplicate'].invoke()          # blocked at capacity
assert errors and str(model.MAX_SECTIONS) in errors[-1] and len(app.doc['sections']) == model.MAX_SECTIONS
errors.clear()
app.items.selection_set(10)
buttons['Remove'].invoke()
app.items.selection_clear(0, 'end'); app.items.selection_set(10)
buttons['Duplicate'].invoke()
assert len(app.doc['sections']) == model.MAX_SECTIONS and names()[10] == names()[11]
rows, total = durations.timeline(app.doc)
assert sum(c for _, c in rows) == total and f'{model.MAX_SECTIONS} of' in app.summary.get()
# Clicking the duration strip selects the section under the pointer.
left, right, index = app.hitboxes[120]
app.select_section(type('E', (), {'x': (left+right)/2})())
assert app.selected() == 120
root.update()
window = ctypes.windll.user32.GetAncestor(app.root.winfo_id(), 2)
ImageGrab.grab(window=window).save(folder/'long-story.png')

# Save and reopen: identical order, totals and relative links.
app.path = folder/'long.json'; app.save()
before = names()
reloaded = model.load(app.path)
assert [s['name'] for s in reloaded['sections']] == before and len(reloaded['sections']) == model.MAX_SECTIONS
assert json.loads(app.path.read_text())['sections'][0]['project'].startswith('p')

# Keep a smaller timeline for exports: 12 sections, cancel part-way through with the real button, then retry.
app.doc['sections'] = app.doc['sections'][:12]
app.refresh()
output = folder/'cancel-me.mp4'
with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(output)):
    app.export()
deadline = time.monotonic()+120
while time.monotonic() < deadline and not app.status.get().startswith('Rendering section 3/'):
    root.update(); time.sleep(.02)
assert app.status.get().startswith('Rendering section'), app.status.get()
app.cancel_button.invoke()
deadline = time.monotonic()+30
while app.busy and time.monotonic() < deadline:
    root.update(); time.sleep(.05)
assert not app.busy and 'canceled' in app.status.get().lower(), app.status.get()
assert not output.exists() and not list(folder.glob('.*.partial.mp4'))
assert all('disabled' not in b.state() for b in app.buttons) and 'disabled' in app.cancel_button.state()
retry = folder/'retry.mp4'
with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(retry)):
    app.export()
deadline = time.monotonic()+240
while app.busy and time.monotonic() < deadline:
    root.update(); time.sleep(.05)
assert retry.exists() and not errors, (errors, app.status.get())
video, sound, seconds = probe_streams(retry)
expected = durations.timeline(app.doc)[1]
assert int(video['nb_read_frames']) == expected and video['codec_name'] == 'h264' and sound and abs(seconds-expected/24) < .15
assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources} == hashes
app.dirty = False
app.close()
(folder/'results.json').write_text(json.dumps(dict(status='passed', sections=model.MAX_SECTIONS, add_seconds=round(elapsed, 2),
    export_frames=expected, checks=['200 sections added/scrolled/totalled', 'limit explained', 'top/bottom/duplicate/remove',
    'strip click selects', 'save/reopen order', 'GUI cancel mid-way then retry decoded', 'sources unchanged']), indent=2))
print('ACCEPTANCE:', folder)
