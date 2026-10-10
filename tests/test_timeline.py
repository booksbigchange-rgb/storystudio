"""Timeline logic is testable without a display or installed FFmpeg."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from timeline import scene_at, scene_ranges, total_duration


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.scenes = [{"duration": 2}, {"duration": 3}, {"duration": 0.5}]

    def test_ranges(self):
        self.assertEqual(scene_ranges(self.scenes), [(0, 2), (2, 5), (5, 5.5)])

    def test_total(self):
        self.assertEqual(total_duration(self.scenes), 5.5)
        self.assertEqual(total_duration([]), 0)

    def test_boundaries(self):
        self.assertEqual(scene_at(self.scenes, 0), 0)
        self.assertEqual(scene_at(self.scenes, 2), 1)
        self.assertEqual(scene_at(self.scenes, 5.5), 2)
        self.assertIsNone(scene_at(self.scenes, 5.6))
        self.assertIsNone(scene_at([], 0))

    def test_bad_durations(self):
        for duration in (0, -1, 121, float("nan"), float("inf")):
            with self.subTest(duration=duration):
                with self.assertRaises(ValueError):
                    scene_ranges([{"duration": duration}])


if __name__ == "__main__":
    unittest.main()
