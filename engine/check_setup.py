"""Read-only runtime checks plus disposable D:-local write probes. No installs."""
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


def inspect_setup():
    root = Path(os.environ.get('STORY_STUDIO', Path(__file__).resolve().parents[1])).resolve()
    checks = []

    def check(name, action):
        try:
            value = action()
            checks.append(dict(name=name, passed=True, detail=str(value)))
        except Exception as exc:
            checks.append(dict(name=name, passed=False, detail=str(exc)))

    def python():
        if Path(sys.prefix).resolve() != (root/'engine'/'.venv').resolve():
            raise RuntimeError('Use engine/.venv/Scripts/python.exe')
        if sys.version_info[:2] != (3, 12):
            raise RuntimeError('Expected Python 3.12')
        return sys.version.split()[0]+'; '+sys.executable

    check('Python environment', python)
    for module in ('tkinter', 'PIL', 'numpy', 'onnxruntime', 'kokoro_onnx', 'soundfile', 'winsound'):
        check('Import '+module, lambda module=module: importlib.import_module(module).__name__)

    def dependencies():
        count = 0
        for line in (root/'engine'/'requirements.lock.txt').read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            name, expected = line.split('==')
            actual = importlib.metadata.version(name)
            if actual != expected:
                raise RuntimeError(f'{name}: expected {expected}, found {actual}')
            count += 1
        return f'{count} pinned versions match'

    check('Pinned dependencies', dependencies)
    for tool in ('ffmpeg', 'ffprobe'):
        def version(tool=tool):
            result = subprocess.run([str(root/'tools'/'ffmpeg'/(tool+'.exe')), '-version'],
                                    capture_output=True, text=True, check=True, timeout=10,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            return result.stdout.splitlines()[0]
        check(tool, version)
    model = Path(os.environ.get('STORY_STUDIO_MODEL_ROOT', root/'models'/'kokoro'))
    for name in ('kokoro-v1.0.int8.onnx', 'voices-v1.0.bin'):
        def model_file(name=name):
            size = (model/name).stat().st_size
            if size < 1000000:
                raise RuntimeError('Model file is too small')
            return f'{size:,} bytes (presence check; not a checksum audit)'
        check(name, model_file)

    def tk_window():
        import tkinter as tk
        window = tk.Tk()
        try:
            window.withdraw()
            window.update()
            return 'Tk '+str(window.tk.call('info', 'patchlevel'))
        finally:
            window.destroy()
    check('Tk window creation', tk_window)
    for directory in ('temp', 'cache', 'projects', 'exports', 'logs'):
        def writable(directory=directory):
            path = root/directory/('.setup-probe-'+uuid.uuid4().hex)
            try:
                with path.open('xb') as handle:
                    handle.write(b'StoryStudio setup probe')
                return 'Writable'
            finally:
                path.unlink(missing_ok=True)
        check('Storage '+directory, writable)
    check('Bundled phonemizer', lambda: importlib.import_module('phonemes').phonemize('Ready to tell a story.'))
    return dict(passed=all(c['passed'] for c in checks), checks=checks,
                platform=platform.platform(), free_bytes=shutil.disk_usage(root).free,
                note='Does not verify audible speakers, model hashes, low-spec hardware or a standalone installer.')


if __name__ == '__main__':
    report = inspect_setup()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report['passed'] else 1)
