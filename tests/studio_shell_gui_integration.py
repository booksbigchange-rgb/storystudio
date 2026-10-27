"""One-window studio: every editor in a tab of one process, shortcuts per tab, exports, close rules (Windows)."""
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
import uuid
from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
sys.path.insert(0, str(ROOT/'tests'))
import mixed_project as model
from mixed_audio_integration_helpers import probe_streams
from studio_shell import StudioShell

folder = ROOT/'exports'/('shell-gui-'+uuid.uuid4().hex)
folder.mkdir(parents=True)
Image.new('RGB', (1280, 720), '#556677').save(folder/'a.png')
documentary = folder/'documentary.json'
documentary.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='a.png', duration=1), dict(image='a.png', duration=1)])), encoding='utf-8')
cartoon = folder/'character.json'
cartoon.write_text(json.dumps(dict(version=2, name='Shell fox', format='Landscape 16:9', quality='Standard · 720p / 24 fps', audio=None,
    scenes=[dict(title='', duration=1, character='fox', expression='happy', action='wave', background='meadow', x=.4, size=1, speed=1)])), encoding='utf-8')

# The launchers start without errors: the new one-window studio and the classic chooser.
for extra in ([], ['--classic']):
    result = subprocess.run([sys.executable, str(ROOT/'engine'/'studio_hub.py'), '--smoke', *extra], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, (extra, result.stderr[-800:])

ctypes.windll.shcore.SetProcessDpiAwareness(1)
root = tk.Tk()
theme = ttk.Style(root).theme_use()
shell = StudioShell(root)
errors = []
root.report_callback_exception = lambda *a: errors.append(str(a))
root.update()


def pump(check, timeout=180):
    deadline = time.monotonic()+timeout
    while not check():
        root.update(); time.sleep(.03)
        assert time.monotonic() < deadline, 'timed out'


tabs = lambda: len(shell.notebook.tabs())
assert tabs() == 1 and shell.current() is None
shell.buttons['Shared timeline'].invoke(); root.update()
mixed = shell.current()
assert tabs() == 2 and mixed.app.__class__.__name__ == 'MixedEditor'
mixed.app.add_path(documentary); mixed.app.add_path(cartoon)
shell.buttons['Documentary'].invoke(); root.update()
doc_tab = shell.current()
assert doc_tab.app.__class__.__name__ == 'EditorApp' and tabs() == 3
shell.buttons['Character'].invoke(); root.update()
char_tab = shell.current()
assert char_tab.app is char_tab and tabs() == 4
assert ttk.Style(root).theme_use() == theme, 'the character tab changed the studio theme'
for widget in (char_tab.export_button, char_tab.tabs, char_tab.stage):
    assert widget.winfo_ismapped(), widget
root.update()
ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(folder/'one-window.png')

# Shortcuts act only on the visible tab.
shell.notebook.select(mixed); root.update()
mixed.app.items.selection_clear(0, 'end'); mixed.app.items.selection_set(1); mixed.app.move(-1)
moved = [s['name'] for s in mixed.app.doc['sections']]
shell.notebook.select(doc_tab); root.update()
root.focus_force(); root.event_generate('<Control-z>'); root.update()
assert [s['name'] for s in mixed.app.doc['sections']] == moved, 'Ctrl+Z in the documentary tab changed the timeline'
shell.notebook.select(mixed); root.update()
root.focus_force(); root.event_generate('<Control-z>'); root.update()
assert [s['name'] for s in mixed.app.doc['sections']] != moved, 'Ctrl+Z did not undo in the timeline tab'

# "Edit source" from the timeline opens the source as another tab, not another program.
before = tabs()
mixed.app.items.selection_clear(0, 'end'); mixed.app.items.selection_set([i for i, s in enumerate(mixed.app.doc['sections']) if s['engine'] == 'cartoon'][0])
mixed.app.edit(); root.update()
source_tab = shell.current()
assert tabs() == before+1 and source_tab.document['name'] == 'Shell fox' and 'Shell fox' in shell.notebook.tab(source_tab, 'text')
with patch('studio_shell.filedialog.askopenfilename', return_value=str(documentary)):
    shell.buttons['Open project…'].invoke()
opened = shell.current()
assert opened.app.__class__.__name__ == 'EditorApp' and len(opened.app.scenes) == 2

# Real exports from inside the one window.
shell.notebook.select(mixed); root.update()
output = folder/'shell-mixed.mp4'
with patch('mixed_editor.filedialog.asksaveasfilename', return_value=str(output)):
    mixed.app.export()
pump(lambda: not mixed.app.busy)
video, sound, seconds = probe_streams(output)
assert int(video['nb_read_frames']) == 72 and sound and abs(seconds-3) < .15, (video['nb_read_frames'], seconds)
shell.notebook.select(source_tab); root.update()
character_out = folder/'shell-character.mp4'
source_tab.preview_enabled = False
with patch('studio_ui.filedialog.asksaveasfilename', return_value=str(character_out)):
    source_tab.export_button.invoke()
pump(lambda: not source_tab.busy)
assert character_out.is_file() and 'Verified MP4 saved' in source_tab.status.get(), source_tab.status.get()

# Closing a tab with unsaved work asks first; declining keeps it.
shell.notebook.select(mixed); root.update()
assert mixed.app.dirty
with patch('mixed_editor.messagebox.askyesno', return_value=False):
    shell.buttons['Close tab'].invoke()
assert mixed in shell.hosts and str(mixed) in shell.notebook.tabs()
with patch('mixed_editor.messagebox.askyesno', return_value=True):
    shell.buttons['Close tab'].invoke()
assert mixed not in shell.hosts and str(mixed) not in shell.notebook.tabs()
shell.notebook.select(shell.home); shell.buttons['Close tab'].invoke()
assert 'Home tab' in shell.status.get()
assert not errors, errors

# Closing the window closes every tab (each asks about its own work) and then the studio.
with patch('mixed_editor.messagebox.askyesno', return_value=True), patch('studio_ui.messagebox.askyesno', return_value=True), \
        patch('editor_app.messagebox.askyesno', return_value=True), patch('desktop_app.messagebox.askyesno', return_value=True):
    for host in shell.hosts:
        if hasattr(host.app, 'dirty'):
            host.app.dirty = False
    shell.close_all()
    deadline = time.monotonic()+60
    alive = True
    remaining = []
    while alive and time.monotonic() < deadline:
        remaining = [(type(h.app).__name__, getattr(h.app, 'closing', None), getattr(h.app, 'busy', None), getattr(h.app, 'dirty', None),
                      getattr(h.app, 'preview_busy', None)) for h in shell.hosts]
        try:
            root.update(); time.sleep(.05)
            root.winfo_exists()          # update() alone does not fail once the window is gone; winfo does
        except tk.TclError:
            alive = False
assert not alive, f'the studio did not close: {remaining} {shell.status.get()!r} callback errors: {errors}'
(folder/'results.json').write_text(json.dumps(dict(status='passed', checks=['one-window and classic launchers start', 'three workspaces as tabs in one process',
    'theme unchanged by the character tab', 'shortcuts act on the visible tab only', 'Edit source and Open project open tabs',
    'mixed and character exports from inside the window', 'close tab asks about unsaved work', 'close window closes every tab']), indent=2))
print('ACCEPTANCE:', folder)
