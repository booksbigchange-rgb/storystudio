import json
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from waveform import waveform_columns, read_cache, WaveformJob


class WaveformTests(unittest.TestCase):
    def settings(self, **changes):
        return {"offset": 0, "trim": 0, "volume": 1, "fade": 0, **changes}

    def test_delay_trim_and_silence_align_with_timeline(self):
        data = {"duration": 2, "step": .02, "peaks": [1]*50+[0]*50}
        self.assertEqual(waveform_columns(data, self.settings(offset=1, trim=.5), 4, 8), [0, 0, 1, 0, 0, 0, 0, 0])

    def test_gain_and_fade_are_visible(self):
        data = {"duration": 8, "step": 1, "peaks": [1]*8}
        self.assertEqual(waveform_columns(data, self.settings(fade=2, volume=.5), 8, 8), [.125,.375,.5,.5,.5,.5,.375,.125])
        self.assertEqual(waveform_columns(data, self.settings(volume=0), 8, 8), [0]*8)

    def test_trim_past_source_and_empty_timeline(self):
        data = {"duration": 1, "step": .02, "peaks": [1]*50}
        self.assertEqual(waveform_columns(data, self.settings(trim=2), 2, 10), [0]*10)
        self.assertEqual(waveform_columns(data, self.settings(), 0, 10), [])

    def test_cache_validation_rejects_malformed_or_nonfinite_data(self):
        valid = {"version": 1, "step": .02, "duration": 1, "peaks": [.5]*50}
        for bad in ([], {**valid, "peaks": [float("nan")]*50}, {**valid, "duration": float("inf")},
                    {**valid, "peaks": [1.1]*50}, {**valid, "peaks": []}, {**valid, "step": 0}):
            with mock.patch.object(Path, "read_text", return_value=json.dumps(bad)):
                with self.assertRaises(ValueError):
                    read_cache("unused.json")
        with mock.patch.object(Path, "read_text", return_value=json.dumps(valid)):
            self.assertEqual(read_cache("unused.json"), valid)

    def test_cancel_terminates_only_the_waveform_process(self):
        job = WaveformJob("unused.wav", "ffmpeg", "cache", lambda *_args: None)
        job.process = mock.Mock()
        job.process.poll.return_value = None
        job.cancel()
        self.assertTrue(job.stop.is_set())
        job.process.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
