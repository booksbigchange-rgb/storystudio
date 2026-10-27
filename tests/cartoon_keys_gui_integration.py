"""Real Tk Animate and Presets tabs of the character editor (Windows)."""
import copy
import ctypes
import json
from pathlib import Path
import sys
import uuid
from unittest.mock import patch
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
import presets
import cartoon_project as project
from studio_ui import StudioApp

folder = ROOT/'exports'/('cartoon-keys-gui-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
app = StudioApp(workspace=folder, auto_preview=False)
errors = []
app.report_callback_exception = lambda *args: errors.append(str(args))
app.update()


def inside(widget):
    return (widget.winfo_ismapped() and widget.winfo_rooty()+widget.winfo_height() <= app.winfo_rooty()+app.winfo_height()
            and widget.winfo_rootx()+widget.winfo_width() <= app.winfo_rootx()+app.winfo_width())


def tab(name):
    labels = [app.tabs.tab(i, 'text') for i in range(app.tabs.index('end'))]
    app.tabs.select(labels.index(name)); app.update()


# Existing tab order is unchanged; the new tabs come after Output.
assert [app.tabs.tab(i, 'text') for i in range(app.tabs.index('end'))] == ['Scene', 'Character', 'Output', 'Animate', 'Presets']
for width, height in [(1000, 680), (1366, 768)]:
    app.geometry(f'{width}x{height}'); app.update()
    tab('Animate')
    for widget in [app.key_list, *app.key_buttons.values(), app.export_button, app.timeline, app.stage]:
        assert inside(widget), (width, height, str(widget))
    tab('Presets')
    for widget in [*app.preset_buttons.values(), app.preset_combo]:
        assert inside(widget), (width, height, str(widget))
tab('Animate')


def fill(**values):
    for name in app.key_fields:
        app.key_fields[name].set(values.get(name, ''))


fill(at='0', x='0.25', tilt='-0.2')
app.key_buttons['Add key'].invoke()
fill(at='100', x='0.65', lift='40', expression='surprised', action='wave')
app.key_buttons['Add key'].invoke()
fill(at='50', size='1.1')
app.key_buttons['Add key'].invoke()
keys = app.document['scenes'][0]['keys']
assert [k['at'] for k in keys] == [0, .5, 1] and keys[1] == {'at': .5, 'size': 1.1} and keys[2]['action'] == 'wave', keys
assert app.key_list.size() == 3 and app.dirty
# Invalid entries are explained and change nothing.
for values, words in [(dict(at='50', x='0.4'), 'increasing'), (dict(at='abc'), ''), (dict(at='20', x='9'), 'between'), (dict(at='20'), 'at least one')]:
    fill(**values); before = copy.deepcopy(app.document)
    app.key_buttons['Add key'].invoke()
    assert app.document == before and words in app.status.get(), (values, app.status.get())
# Select, update and remove through the real list.
app.key_list.selection_clear(0, 'end'); app.key_list.selection_set(1); app.select_key()
assert app.key_fields['size'].get() == '1.1' and app.key_fields['at'].get() == '50'
assert abs(app.time.get()-5.0) < 1e-9, app.time.get()                     # scrubbed to the key: 50% of the 10 s scene
app.key_fields['size'].set('1.2'); app.key_buttons['Update'].invoke()
assert app.document['scenes'][0]['keys'][1]['size'] == 1.2
app.key_list.selection_clear(0, 'end'); app.key_list.selection_set(0); app.key_buttons['Remove'].invoke()
assert [k['at'] for k in app.document['scenes'][0]['keys']] == [.5, 1]
# Editing the Scene tab must keep the animation keys.
app.fields['duration'].set('6'); app.apply_scene()
assert app.document['scenes'][0]['duration'] == 6 and len(app.document['scenes'][0]['keys']) == 2
# Keys travel with a duplicated scene and survive save/open.
app.duplicate_button.invoke()
assert app.document['scenes'][1]['keys'] == app.document['scenes'][0]['keys']
path = folder/'keyed-story.json'
with patch('studio_ui.filedialog.asksaveasfilename', return_value=str(path)):
    app.save_button.invoke()
saved = project.load(path)
assert saved == project.validate(app.document) and saved['scenes'][1]['keys'][1]['at'] == 1
app.document = project.new_project(); app.refresh()
with patch('studio_ui.filedialog.askopenfilename', return_value=str(path)):
    app.open_project()
assert app.document == saved
app.scene_list.selection_clear(0, 'end'); app.scene_list.selection_set(0); app.select_scene()
assert app.key_list.size() == 2
# Remove every key: the scene returns to the old unkeyed form.
for _ in range(2):
    app.key_list.selection_clear(0, 'end'); app.key_list.selection_set(0); app.key_buttons['Remove'].invoke()
assert 'keys' not in app.document['scenes'][0]
app.update(); ctypes.windll.user32.SetProcessDPIAware()
fill(at='25', x='0.3', tilt='0.2'); app.key_buttons['Add key'].invoke()
app.update(); ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(), app.winfo_rootx()+app.winfo_width(), app.winfo_rooty()+app.winfo_height())).save(folder/'animate-tab.png')

# Presets: save, list, refuse silent replace, apply to another scene, delete.
tab('Presets')
app.fields['character'].set('bear'); app.fields['action'].set('walk'); app.apply_scene()
app.preset_name.set('Bear walk'); app.preset_buttons['Save preset'].invoke()
assert 'Bear walk' in presets.load(folder/'projects'/'character-presets.json') and app.preset_choice.get() == 'Bear walk'
before = (folder/'projects'/'character-presets.json').read_bytes()
with patch('studio_ui.messagebox.askyesno', return_value=False) as ask:
    app.fields['character'].set('rabbit'); app.apply_scene()
    app.preset_buttons['Save preset'].invoke()
    assert ask.called
assert (folder/'projects'/'character-presets.json').read_bytes() == before, 'declined replacement changed the library'
app.add_button.invoke()
app.fields['title'].set('Keep this caption'); app.fields['duration'].set('4'); app.apply_scene()
app.preset_buttons['Apply preset'].invoke()
scene = app.document['scenes'][app.selected()]
assert (scene['character'], scene['action'], scene['title'], scene['duration']) == ('bear', 'walk', 'Keep this caption', 4), scene
assert 'Applied preset' in app.status.get()
app.preset_buttons['Delete preset'].invoke()
assert presets.load(folder/'projects'/'character-presets.json') == {} and not app.preset_combo.cget('values')
app.preset_buttons['Apply preset'].invoke()
assert 'Choose a saved preset' in app.status.get()
app.preset_name.set('   '); app.preset_buttons['Save preset'].invoke()
assert '1–40' in app.status.get()
assert not errors, errors
app.dirty = False
app.destroy()
(folder/'results.json').write_text(json.dumps(dict(status='passed', checks=['tab order and visibility at two laptop sizes', 'add/update/remove/select keys',
    'invalid keys explained', 'scene edits keep keys', 'duplicate/save/open keeps keys', 'preset save/decline replace/apply/delete', 'caption length backdrop kept']), indent=2))
print('ACCEPTANCE:', folder)
