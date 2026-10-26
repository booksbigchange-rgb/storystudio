# PyInstaller spec for the one-runtime portable build:
#   StoryStudio.exe        hub + documentary, character and shared-timeline editors (windowed)
#   StoryStudioWorker.exe  export workers for both engines and the process gate (console, run hidden)
# The documentary model is "project" and the character model is "cartoon_project", so one runtime holds both.
# Playwright/Chrome are not bundled: export and previews use the native renderer.
import os
root = os.path.abspath(os.path.join(SPECPATH, '..'))
engine = os.path.join(root, 'engine')
lemo = os.path.join(root, 'integrations', 'lemo-lite')
datas = [(os.path.join(lemo, 'scene'), 'scene'), (os.path.join(lemo, 'vendor'), 'vendor')]   # served to the optional live preview

app = Analysis([os.path.join(engine, 'unified_app.py')], pathex=[engine, lemo], datas=datas,
               hiddenimports=['frozen_selftest', 'mixed_audio_editor', 'mixed_titles_editor', 'mixed_section_editor', 'template_editor',
                              'studio_ui', 'gui_regression', 'presets', 'native_scene', 'cartoon_project', 'renderer'],
               excludes=['playwright'])
worker = Analysis([os.path.join(engine, 'worker_entry.py')], pathex=[engine, lemo],
                  hiddenimports=['mixed_worker', 'cartoon_project', 'renderer', 'native_scene'],
                  excludes=['tkinter', '_tkinter', 'playwright', 'studio_ui', 'gui_regression'])
app_pyz, worker_pyz = PYZ(app.pure), PYZ(worker.pure)
app_exe = EXE(app_pyz, app.scripts, exclude_binaries=True, name='StoryStudio', console=False)
worker_exe = EXE(worker_pyz, worker.scripts, exclude_binaries=True, name='StoryStudioWorker', console=True)
COLLECT(app_exe, app.binaries, app.datas, worker_exe, worker.binaries, worker.datas, name='StoryStudio')
