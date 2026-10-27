"""Where the application lives, for source checkouts and the PyInstaller portable build.

Portable layout (one runtime, one folder):
  StoryStudio.exe        hub plus the documentary, character and shared-timeline editors (windowed)
  StoryStudioWorker.exe  export workers for both engines and the process gate (console, never shown)
  bin/ffmpeg.exe, bin/ffprobe.exe
The documentary model is ``project`` and the character model is ``cartoon_project`` so both live in one process.
"""
import os
from pathlib import Path
import sys

FROZEN = bool(getattr(sys, 'frozen', False))
HELPERS = {'documentary': 'StoryStudioWorker.exe', 'cartoon': 'StoryStudioWorker.exe', 'gate': 'StoryStudioWorker.exe',
           'hub': 'StoryStudio.exe'}


def app_root(source_file=None):
    """Top folder of the portable build, or the repository root when running from source."""
    if FROZEN:
        override = os.environ.get('STORYSTUDIO_HOME')
        if override:
            return Path(override).resolve()
        return Path(sys.executable).resolve().parent
    return Path(source_file or __file__).resolve().parents[1]


def helper(name):
    """Path of a sibling executable in the portable build."""
    return app_root()/HELPERS[name]


def prepare_environment():
    """Point every scoped path at the portable folder; called first by each frozen entry point."""
    root = app_root()
    os.environ['STORYSTUDIO_HOME'] = str(root)
    os.environ['STORY_STUDIO'] = str(root)
    ffmpeg = root/'bin'/'ffmpeg.exe'
    if ffmpeg.is_file():
        os.environ['STORYSTUDIO_FFMPEG'] = str(ffmpeg)
        os.environ['STORY_STUDIO_FFMPEG'] = str(ffmpeg)
    for name in ('logs', 'exports', 'temp', 'projects'):
        (root/name).mkdir(exist_ok=True)
    for key in ('TEMP', 'TMP', 'TMPDIR'):
        os.environ[key] = str(root/'temp')
    os.environ['STORYSTUDIO_TEMP'] = str(root/'temp')
    return root
