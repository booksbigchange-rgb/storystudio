"""Execute a check; optional fixture ACL workaround is confined to this process."""
import argparse
import os
from pathlib import Path
import runpy
import tempfile
import unittest
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sandbox-fixtures', action='store_true')
    parser.add_argument('check')
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent
    if args.sandbox_fixtures:
        # Restricted Windows tokens cannot reopen CPython's private 0700 ACLs.
        # Change only this check's synthetic fixtures, never system permissions.
        def fixture_dir(suffix=None, prefix=None, dir=None):
            path = Path(dir or os.environ['TEMP']) / ((prefix or 'fixture-')+uuid.uuid4().hex+(suffix or ''))
            path.mkdir()
            return str(path)
        tempfile.mkdtemp = fixture_dir
    if args.check == 'unit':
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(tests)))
        return 0 if result.wasSuccessful() else 1
    allowed = {'gui_integration', 'preview_audio_integration', 'waveform_integration',
               'two_track_integration', 'cancel_export_integration', 'repeat_audio_integration', 'layers_integration', 'formats_integration'}
    if args.check not in allowed:
        parser.error('Unknown check')
    runpy.run_path(str(tests/(args.check+'.py')), run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
