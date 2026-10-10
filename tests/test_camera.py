"""Camera keyframe validation and filter generation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from camera import camera_values, zoompan_filter


class CameraTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(camera_values({})["zoom_end"], 1.08)

    def test_custom_keyframes(self):
        vf = zoompan_filter(
            {"zoom_start": 1.1, "zoom_end": 1.5, "x_start": 0,
             "x_end": 1, "y_start": 0.2, "y_end": 0.8},
            24, 160, 288, 24,
        )
        self.assertIn("zoompan=z=", vf)
        self.assertIn("min(on/23,1)", vf)
        self.assertIn("s=160x288:fps=24", vf)
        self.assertIn("d=1", vf)

    def test_invalid_values(self):
        for key, value in (
            ("zoom_start", 0.9), ("zoom_end", 2.1),
            ("x_start", -0.1), ("y_end", 1.1),
            ("zoom_end", float("nan")), ("x_end", float("inf")),
        ):
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    camera_values({key: value})

    def test_zero_frames(self):
        with self.assertRaises(ValueError):
            zoompan_filter({}, 0, 160, 288, 24)


if __name__ == "__main__":
    unittest.main()
