"""Cancel an actual character render from Tk, then export again from the same UI."""
import copy
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
from mixed_editor import MixedEditor

folder = ROOT/'exports'/('mixed-cancel-'+uuid.uuid4().hex)
folder.mkdir()
source = folder/'source.json'
doc = dict(version=2, name='Cancel test', format='Landscape 16:9', quality='Standard · 720p / 24 fps',
           audio=None, scenes=[dict(title='Cancellation regression',duration=30,character='bear',
           expression='curious',action='wave',background='meadow',x=.4,size=1,speed=1)])
source.write_text(json.dumps(doc), encoding='utf-8')
original = source.read_bytes()
errors = []
error_dialog = patch('mixed_editor.messagebox.showerror', side_effect=lambda title, text, **kwargs:errors.append(text))
error_dialog.start()  # Record failures; never block unattended tests on a modal dialog.
root = tk.Tk(); app = MixedEditor(root)
app.add_path(source)
prior = set((ROOT/'exports').glob('mixed-run-*'))
output = folder/'cancelled.mp4'
with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(output)):
    app.export()
deadline = time.monotonic()+60
started = False
while time.monotonic()<deadline:
    root.update()
    runs = set((ROOT/'exports').glob('mixed-run-*'))-prior
    if any(p.stat().st_size>0 for run in runs for p in run.glob('.raw-*.partial.mp4')):
        started = True
        break
    if not app.busy: break
    time.sleep(.05)
if not started:
    app.cancel_export()
    raise AssertionError('Never observed actual encoder staging output')
app.cancel_button.invoke()
deadline = time.monotonic()+10
while app.busy and time.monotonic()<deadline:
    root.update(); time.sleep(.05)
assert not app.busy, 'UI did not recover after cancellation'
assert 'canceled' in app.status.get().lower(), app.status.get()
assert not output.exists()
assert not list(folder.glob('*.partial.mp4'))
assert source.read_bytes()==original
assert all('disabled' not in button.state() for button in app.buttons)
assert 'disabled' in app.cancel_button.state()
# Fresh controller must allow another export, not inherit the canceled event.
short = copy.deepcopy(doc); short['scenes'][0]['duration']=1
retry_source = folder/'retry.json'; retry_source.write_text(json.dumps(short),encoding='utf-8')
app.doc['sections'][0]['project']=str(retry_source)
retry = folder/'retry.mp4'
with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(retry)):
    app.export()
deadline = time.monotonic()+90
while app.busy and time.monotonic()<deadline:
    root.update(); time.sleep(.05)
assert not app.busy and retry.is_file(), app.status.get()
app.dirty=False; app.close()
error_dialog.stop()
assert not errors, errors
(folder/'results.json').write_text(json.dumps(dict(status='passed',checks=[
    'real encoder started','GUI cancellation','no published canceled MP4','no partial destination',
    'source unchanged','controls restored','successful verified retry from same editor']),indent=2))
print('ACCEPTANCE:', folder)
