"""Regression coverage for layered 2D scene behavior."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from animation import validated_layers, layer_state


class AnimationTests(unittest.TestCase):
    def setUp(self):
        self.layer = {
            "id": "hero", "image": "character.png",
            "x": 0.2, "y": 0.6, "width": 0.35,
            "keyframes": [
                {"time": 0, "x": 0.2},
                {"time": 2, "x": 0.8, "ease": "linear"},
            ],
        }

    def test_motion_start_middle_end(self):
        layer = validated_layers([self.layer], 2)[0]
        self.assertAlmostEqual(layer_state(layer, 0)["x"], 0.2)
        self.assertAlmostEqual(layer_state(layer, 1)["x"], 0.5)
        self.assertAlmostEqual(layer_state(layer, 2)["x"], 0.8)

    def test_holds_final_frame_and_partial_properties(self):
        layer = validated_layers([self.layer], 2)[0]
        self.assertEqual(layer_state(layer, 5)["x"], 0.8)
        self.assertEqual(layer_state(layer, 1)["y"], 0.6)

    def test_smooth_easing_and_hold(self):
        layer = validated_layers([dict(self.layer, keyframes=[
            {"time": 2, "x": 0.8, "ease": "smooth"}])], 2)[0]
        self.assertLess(layer_state(layer, 0.5)["x"], 0.35)
        hold = validated_layers([dict(self.layer, keyframes=[
            {"time": 2, "x": 0.8, "ease": "hold"}])], 2)[0]
        self.assertEqual(layer_state(hold, 1.5)["x"], 0.2)
        self.assertEqual(layer_state(hold, 2)["x"], 0.8)

    def test_validation_rejects_corrupt_motion(self):
        bads = [
            {"x": float("nan")},
            {"x": 999},
            {"opacity": -0.5},
            {"keyframes": [{"time": 3, "x": 0.8}]},
            {"keyframes": [{"time": 1}, {"time": 1}]},
            {"keyframes": [{"time": 1, "ease": "unsupported"}]},
            {"keyframes": [{"time": 1, "x": float("inf")}]},
        ]
        for bad in bads:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validated_layers([dict(self.layer, **bad)], 2)

    def test_no_layers_and_legacy_scene(self):
        self.assertEqual(validated_layers([], 3), [])
        layer = validated_layers([{"image": "old.png"}], 3)[0]
        self.assertEqual(layer["x"], 0.5)
        self.assertEqual(layer["keyframes"], [])

    def test_does_not_mutate_project(self):
        source = dict(self.layer)
        validated_layers([source], 2)
        self.assertNotIn("opacity", source)


if __name__ == "__main__":
    unittest.main()
