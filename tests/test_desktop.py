"""Headless tests for StoryStudio's first desktop renderer."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import desktop_app


class RendererTests(unittest.TestCase):
    def test_empty_story_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                desktop_app.render_scenes([], Path(folder) / "out.mp4")

    def test_configured_ffmpeg_override(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "ffmpeg.exe"
            fake.write_bytes(b"placeholder")
            with mock.patch.dict(os.environ, {"STORY_STUDIO_FFMPEG": str(fake)}):
                self.assertEqual(desktop_app.ffmpeg_binary(), str(fake))

    def test_missing_ffmpeg_override(self):
        with mock.patch.dict(os.environ, {"STORY_STUDIO_FFMPEG": "/missing/ffmpeg"}):
            self.assertIsNone(desktop_app.ffmpeg_binary())

    def test_render_rejects_missing_images(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(desktop_app, "TEMP", Path(folder)):
                with mock.patch.object(desktop_app, "ffmpeg_binary", return_value="ffmpeg"):
                    with self.assertRaises(FileNotFoundError):
                        desktop_app.render_scenes(
                            [{"image": str(Path(folder) / "missing.png"), "duration": 2}],
                            Path(folder) / "out.mp4",
                        )

    def test_duration_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "test.png"
            image.write_bytes(b"placeholder")
            with mock.patch.object(desktop_app, "TEMP", Path(folder)):
                with mock.patch.object(desktop_app, "ffmpeg_binary", return_value="ffmpeg"):
                    for duration in (0, 121, -1):
                        with self.subTest(duration=duration):
                            with self.assertRaises(ValueError):
                                desktop_app.render_scenes(
                                    [{"image": str(image), "duration": duration}],
                                    Path(folder) / "out.mp4",
                                )


if __name__ == "__main__":
    unittest.main()
