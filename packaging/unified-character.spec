# PyInstaller spec: character/StoryStudioCharacter.exe (editor) + StoryStudioCharacterWorker.exe (export/verify).
import os
from PyInstaller.utils.hooks import collect_all
root = os.path.abspath(os.path.join(SPECPATH, '..'))
lemo = os.path.join(root, 'integrations', 'lemo-lite')
engine = os.path.join(root, 'engine')
datas, binaries, hidden = collect_all('playwright')
datas += [(os.path.join(lemo, 'scene'), 'scene'), (os.path.join(lemo, 'vendor'), 'vendor')]

editor = Analysis([os.path.join(lemo, 'portable_app.py')], pathex=[lemo], datas=datas, binaries=binaries,
                  hiddenimports=hidden+['gui_regression', 'presets'], excludes=['desktop_app'])
# The character project model must win over the engine's module of the same name; mixed_worker comes from engine/.
worker = Analysis([os.path.join(lemo, 'frozen_worker.py')], pathex=[lemo, engine], datas=datas, binaries=binaries,
                  hiddenimports=hidden+['mixed_worker'], excludes=['desktop_app', 'tkinter', '_tkinter', 'studio_ui', 'gui_regression'])
editor_pyz, worker_pyz = PYZ(editor.pure), PYZ(worker.pure)
editor_exe = EXE(editor_pyz, editor.scripts, exclude_binaries=True, name='StoryStudioCharacter', console=False)
worker_exe = EXE(worker_pyz, worker.scripts, exclude_binaries=True, name='StoryStudioCharacterWorker', console=True)
COLLECT(editor_exe, editor.binaries, editor.datas, worker_exe, worker.binaries, worker.datas, name='character')
