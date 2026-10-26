"""Real Tk import and use of a layered-artwork character in the character editor (Windows)."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid
from unittest.mock import patch
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT/'exports'/('rig-gui-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
os.environ['STORYSTUDIO_CHARACTERS'] = str(folder/'projects'/'characters')
sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
import character_rig
import cartoon_project as project
import renderer
import sample_character
from studio_ui import StudioApp

layers = folder/'my-layers'
sample_character.write(layers)
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in layers.glob('*.png')}
app = StudioApp(workspace=folder, auto_preview=False)
errors, callback_errors = [], []
app.report_callback_exception = lambda *a: callback_errors.append(str(a))
app.update()


def pump(check, timeout=120):
    deadline = time.monotonic()+timeout
    while not check():
        app.update(); time.sleep(.03)
        assert time.monotonic() < deadline, 'timed out: '+app.status.get()


assert 'Import layered character…' in app.pack_buttons and 'Create example layers…' in app.pack_buttons
assert app.character_combo.cget('values') == tuple(project.CHARACTERS)
app.tabs.select(1); app.update()
for button in app.pack_buttons.values():
    assert button.winfo_ismapped() and button.winfo_rooty()+button.winfo_height() <= app.winfo_rooty()+app.winfo_height()

with patch('studio_ui.filedialog.askdirectory', return_value=str(layers)), patch('studio_ui.simpledialog.askstring', return_value='robo'), \
        patch('studio_ui.messagebox.showerror', side_effect=lambda t, m, **k: errors.append(m)):
    app.pack_buttons['Import layered character…'].invoke()
    assert not errors, errors
    assert (folder/'projects'/'characters'/'robo'/'rig.json').is_file() and app.fields['character'].get() == 'custom:robo'
    assert 'custom:robo' in app.character_combo.cget('values') and 'Imported' in app.status.get()
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in layers.glob('*.png')} == hashes, 'source art changed'
    # Importing the same name again is refused and changes nothing.
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder/'projects'/'characters'/'robo').iterdir()}
    app.pack_buttons['Import layered character…'].invoke()
    assert errors and 'already exists' in errors[-1], errors
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder/'projects'/'characters'/'robo').iterdir()} == before
    errors.clear()
    # A bad name is explained.
with patch('studio_ui.filedialog.askdirectory', return_value=str(layers)), patch('studio_ui.simpledialog.askstring', return_value='../evil'), \
        patch('studio_ui.messagebox.showerror', side_effect=lambda t, m, **k: errors.append(m)):
    app.pack_buttons['Import layered character…'].invoke()
    assert errors and 'Pack name' in errors[-1], errors
    assert not (folder/'projects'/'evil').exists() and not (folder/'evil').exists()
    errors.clear()
# The example-layers helper writes into a new folder and refuses a used one.
example = folder/'example-layers'
with patch('studio_ui.filedialog.askdirectory', return_value=str(example)):
    app.pack_buttons['Create example layers…'].invoke()
assert (example/'head.png').is_file() and 'Wrote example layers' in app.status.get()
with patch('studio_ui.filedialog.askdirectory', return_value=str(example)):
    app.pack_buttons['Create example layers…'].invoke()
assert 'not empty' in app.status.get()

# Use it: apply, preview a frame with the real preview path, scene keeps working with keys and presets.
app.fields['action'].set('wave'); app.fields['duration'].set('2')
assert app.apply_scene()
assert app.document['scenes'][0]['character'] == 'custom:robo'
app.preview_enabled = True
app.preview_button.invoke()
pump(lambda: not app.preview_busy)
assert app.snapshot, app.status.get()
app.update()
ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(), app.winfo_rootx()+app.winfo_width(), app.winfo_rooty()+app.winfo_height())).save(folder/'editor-with-layered-character.png')
app.preview_enabled = False
app.tabs.select(3); app.update()
app.key_fields['at'].set('100'); app.key_fields['x'].set('0.6'); app.key_buttons['Add key'].invoke()
assert app.document['scenes'][0]['keys']
app.tabs.select(4); app.update()
app.preset_name.set('Robo wave'); app.preset_buttons['Save preset'].invoke()
assert 'Robo wave' in character_rig.library_dir().parent.joinpath('character-presets.json').read_text()

# Export through the UI and decode.
output = folder/'gui-layered.mp4'
with patch('studio_ui.filedialog.asksaveasfilename', return_value=str(output)):
    app.export_button.invoke()
pump(lambda: not app.busy, 240)
assert output.is_file() and 'Verified MP4 saved' in app.status.get(), app.status.get()
renderer.verify(output, 2, 1280, 720, 24)
# Removing the pack makes the next export fail clearly instead of drawing a stand-in.
import shutil
shutil.rmtree(folder/'projects'/'characters'/'robo')
import native_scene
native_scene._packs.clear()
blocked = folder/'blocked.mp4'
with patch('studio_ui.filedialog.asksaveasfilename', return_value=str(blocked)):
    app.export_button.invoke()
pump(lambda: not app.busy, 60)
assert not blocked.exists() and 'robo' in app.status.get().lower(), app.status.get()
assert not callback_errors, callback_errors
app.dirty = False
app.destroy()
(folder/'results.json').write_text(json.dumps(dict(status='passed', checks=['import button, name prompt, combobox refresh', 'source art unchanged', 'duplicate and bad names refused',
    'example layers helper', 'preview frame and GUI export decoded', 'keys and preset work with a layered character', 'missing pack explained']), indent=2))
print('ACCEPTANCE:', folder)
