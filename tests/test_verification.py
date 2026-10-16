"""Verification must preserve evidence and return failure when a check fails."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import verify_mvp


class VerificationTests(unittest.TestCase):
    def exercise(self, returncodes):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with mock.patch.object(verify_mvp, '__file__', str(root/'tests'/'verify_mvp.py')), \
                 mock.patch.object(verify_mvp.sys, 'prefix', str(root/'engine'/'.venv')), \
                 mock.patch.object(verify_mvp.sys, 'argv', ['verify_mvp.py']), \
                 mock.patch.dict(verify_mvp.os.environ, {'TEMP': str(root/'temp')}), \
                 mock.patch.object(verify_mvp.subprocess, 'run', side_effect=[mock.Mock(returncode=c) for c in returncodes]) as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                code = verify_mvp.main()
            report_path = next((root/'exports'/'verification-runs').glob('*/report.json'))
            report = json.loads(report_path.read_text())
            self.assertEqual(code, 1)
            self.assertEqual(report['status'], 'failed')
            self.assertTrue(all((report_path.parent/r['log']).exists() for r in report['results']))
            return report, run.call_count

    def test_setup_failure_stops_before_rendering(self):
        report, count = self.exercise([1])
        self.assertEqual(count, 1)
        self.assertEqual(len(report['results']), 1)

    def test_failed_check_is_not_masked_by_later_success(self):
        report, count = self.exercise([0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(count, 11)
        self.assertFalse(report['results'][1]['passed'])
        self.assertTrue(report['results'][-1]['passed'])
