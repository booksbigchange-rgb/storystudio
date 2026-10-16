"""Failure notification must reach Tk; explicit cancellations stay silent."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from preview_audio import PreviewAudio


class RecoveryTests(unittest.TestCase):
    def test_timeout_reports_error_and_kills_unresponsive_child(self):
        callback = mock.Mock()
        process = mock.Mock()
        process.wait.side_effect = [subprocess.TimeoutExpired('ffmpeg', 3), 0]
        job = PreviewAudio('ffmpeg', Path(__file__).parent, callback)
        job.timeout = 0
        track = dict(path='source.wav', trim=0, offset=0, volume=1, fade=0)
        with mock.patch('preview_audio.subprocess.Popen', return_value=process):
            job.run(track, 2, 0)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertFalse(job.cancelled.is_set())
        self.assertIn('timed out', callback.call_args.args[1])

    def test_explicit_cancel_does_not_notify_or_spawn(self):
        callback = mock.Mock()
        job = PreviewAudio('ffmpeg', Path(__file__).parent, callback)
        job.cancel()
        with mock.patch('preview_audio.subprocess.Popen') as spawn:
            job.run(dict(path='source.wav', trim=0, offset=0, volume=1, fade=0), 2, 0)
        spawn.assert_not_called()
        callback.assert_not_called()
