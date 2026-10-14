"""Project canvas normalization and Fit/Fill regression coverage."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from stage import DEFAULT, PRESETS, resized_background, validate_canvas


class CanvasTests(unittest.TestCase):
    def test_legacy_defaults(self):
        self.assertEqual(validate_canvas(), DEFAULT)

    def test_standard_presets(self):
        for width, height in PRESETS.values():
            self.assertEqual(validate_canvas(
                {"width": width, "height": height, "fit": "fit"}
            ), {"width": width, "height": height, "fit": "fit"})

    def test_invalid_dimensions_and_fit(self):
        bad = [{"width": 0}, {"height": 65}, {"width": "nan"},
               {"width": 4000}, {"fit": "stretch"}, {"width": 3840, "height": 3840}]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(ValueError):
                validate_canvas(item)

    def test_fit_keeps_whole_image_and_adds_matte(self):
        from PIL import Image
        image = Image.new("RGB", (160, 90), (210, 40, 40))
        fitted = resized_background(image, 90, 160, "fit")
        self.assertEqual(fitted.getpixel((45, 4))[:3], (20, 24, 32))
        self.assertEqual(fitted.getpixel((45, 80))[:3], (210, 40, 40))
        filled = resized_background(image, 90, 160, "fill")
        self.assertEqual(filled.getpixel((45, 4))[:3], (210, 40, 40))


if __name__ == "__main__":
    unittest.main()
