# PyInstaller spec: StoryStudio.exe (hub, documentary and shared-timeline editors) + StoryStudioWorker.exe.
# The character editor is a separate build (unified-character.spec) because both editors define a module named "project".
import os
root = os.path.abspath(os.path.join(SPECPATH, '..'))
engine = os.path.join(root, 'engine')

app = Analysis([os.path.join(engine, 'unified_app.py')], pathex=[engine],
               hiddenimports=['frozen_selftest', 'mixed_audio_editor', 'mixed_titles_editor', 'template_editor'],
               excludes=['renderer', 'studio_ui', 'playwright'])
worker = Analysis([os.path.join(engine, 'worker_entry.py')], pathex=[engine],
                  excludes=['tkinter', '_tkinter', 'renderer', 'studio_ui', 'playwright'])
app_pyz, worker_pyz = PYZ(app.pure), PYZ(worker.pure)
app_exe = EXE(app_pyz, app.scripts, exclude_binaries=True, name='StoryStudio', console=False)
worker_exe = EXE(worker_pyz, worker.scripts, exclude_binaries=True, name='StoryStudioWorker', console=True)
COLLECT(app_exe, app.binaries, app.datas, worker_exe, worker.binaries, worker.datas, name='StoryStudio')
