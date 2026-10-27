import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from project import audio_values
from waveform import waveform_columns


class RepeatTests(unittest.TestCase):
    def test_old_track_defaults_to_not_repeating(self):
        self.assertFalse(audio_values({'path': 'music.wav'})['repeat'])

    def test_repeat_is_boolean(self):
        for value in ('false', 1, [], None):
            with self.assertRaises(ValueError):
                audio_values({'path': 'music.wav', 'repeat': value})

    def test_repeated_waveform_wraps_trim_and_honors_delay(self):
        data = dict(peaks=[1, 0, .5, 0], step=.25, duration=1)
        settings = dict(offset=.5, trim=.5, volume=1, fade=0, repeat=True)
        columns = waveform_columns(data, settings, 3, 12)
        self.assertEqual(columns, [0, 0, .5, 0, 1, 0, .5, 0, 1, 0, .5, 0])
        self.assertEqual(waveform_columns(data, settings, 3, 1), [1])
