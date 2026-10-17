"""Timeline logic is testable without a display or installed FFmpeg."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from timeline import scene_at, scene_ranges, total_duration, keyframe_target_time


class TimelineTests(unittest.TestCase):
    def test_keyframe_drag_snaps_and_stays_inside_scene(self):
        scene = {"duration": 2, "keyframes": [{"at": .5, "zoom": 1.5, "x": .5, "y": .5}]}
        self.assertEqual(keyframe_target_time(scene, .5, .51), 12/47)
        self.assertEqual(keyframe_target_time(scene, .5, -5), 1/47)
        self.assertEqual(keyframe_target_time(scene, .5, 50), 46/47)

    def test_keyframe_drag_cannot_cross_neighbor(self):
        scene = {"duration": 2, "keyframes": [{"at": at, "zoom": 1.5, "x": .5, "y": .5} for at in (.25, .5, .75)]}
        self.assertEqual(keyframe_target_time(scene, .5, 0), 12/47)
        self.assertEqual(keyframe_target_time(scene, .5, 10), 35/47)

    def test_keyframe_drag_keeps_dense_imported_keys_valid(self):
        scene = {"duration": .5, "keyframes": [{"at": at, "zoom": 1.5, "x": .5, "y": .5} for at in (.4, .41, .42)]}
        self.assertEqual(keyframe_target_time(scene, .41, 1), .41)

    def test_keyframe_drag_rejects_unknown_or_nonfinite_time(self):
        scene = {"duration": 2, "keyframes": [{"at": .5, "zoom": 1.5, "x": .5, "y": .5}]}
        with self.assertRaises(ValueError):
            keyframe_target_time(scene, .4, 1)
        with self.assertRaises(ValueError):
            keyframe_target_time(scene, .5, float("nan"))
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
