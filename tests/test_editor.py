"""Regression tests for project safety, camera easing, and audio settings."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from camera import camera_at, crop_box, zoompan_filter, keyframe_values
from project import read_project, write_project, validate_document, audio_values
import desktop_app


class EditorTests(unittest.TestCase):
    def test_intermediate_keyframes_change_direction(self):
        scene = {"zoom_start": 1, "zoom_end": 1, "keyframes": [{"at": .5, "zoom": 2, "x": 1, "y": 0}]}
        self.assertEqual(camera_at(scene, .25)["zoom"], 1.5)
        self.assertEqual(camera_at(scene, .5)["zoom"], 2)
        self.assertEqual(camera_at(scene, .75)["zoom"], 1.5)
        self.assertEqual(camera_at(scene, 1)["zoom"], 1)
        self.assertIn("if(lt(", zoompan_filter(scene, 48, 160, 288, 24))

    def test_bad_interior_keys_rejected(self):
        point = {"at": .5, "zoom": 1.5, "x": .5, "y": .5}
        for points in ([{**point, "at": 0}], [{**point, "at": 1}], [{**point, "at": float("nan")}],
                       [{**point, "zoom": 3}], [point, point], [None], "bad", [point]*17):
            with self.assertRaises((TypeError, ValueError)):
                keyframe_values({"keyframes": points})

    def test_interior_keys_survive_project_validation(self):
        point = {"at": .5, "zoom": 1.8, "x": .2, "y": .7}
        doc = validate_document({"version": 2, "scenes": [{"image": "a.png", "duration": 2, "keyframes": [point]}]})
        self.assertEqual(doc["scenes"][0]["keyframes"], [point])
        point["zoom"] = 1
        self.assertEqual(doc["scenes"][0]["keyframes"][0]["zoom"], 1.8)

    def test_maximum_keys_fit_windows_command_line(self):
        points = [{"at": n/17, "zoom": 1+n/17, "x": n/17, "y": 1-n/17} for n in range(1, 17)]
        vf = zoompan_filter({"keyframes": points, "easing": "smooth"}, 2880, 1080, 1920, 24)
        self.assertLess(len(vf), 24000)

    def test_interpolation_is_seek_order_independent(self):
        scene = {"zoom_start": 1, "zoom_end": 2, "easing": "smooth"}
        self.assertEqual(camera_at(scene, 1)["zoom"], 2)
        self.assertEqual(camera_at(scene, 0)["zoom"], 1)
        self.assertEqual(camera_at(scene, .5)["zoom"], 1.5)
        self.assertAlmostEqual(camera_at(scene, .25)["zoom"], 1.15625)

    def test_each_easing_and_endpoint(self):
        for easing, quarter in (("linear", .25), ("smooth", .15625), ("ease-in", .0625), ("ease-out", .4375)):
            scene = {"zoom_start": 1, "zoom_end": 2, "easing": easing}
            self.assertAlmostEqual(camera_at(scene, .25)["zoom"], 1+quarter)
            self.assertEqual(camera_at(scene, 0)["zoom"], 1)
            self.assertEqual(camera_at(scene, 1)["zoom"], 2)
            self.assertIn("zoompan", zoompan_filter(scene, 24, 160, 288, 24))
        with self.assertRaises(ValueError):
            zoompan_filter({"easing": "invalid"}, 24, 160, 288, 24)

    def test_crop_fills_portrait_without_stretch(self):
        left, top, right, bottom = crop_box(1600, 900, {"zoom": 2, "x": 1, "y": 0})
        self.assertAlmostEqual((right-left)/(bottom-top), 9/16)
        self.assertGreater(left, 0)
        self.assertEqual(top, 0)
        self.assertLessEqual(right, 1600)
        self.assertLessEqual(bottom, 900)

    def test_project_roundtrip_relative_media_and_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "story.json"
            scenes = [{"image": str(root / "image.png"), "duration": 2, "easing": "smooth"}]
            audio = {"path": str(root / "voice.wav"), "volume": .5, "offset": .2}
            write_project(path, scenes, audio)
            serialized = json.loads(path.read_text())
            self.assertEqual(serialized["scenes"][0]["image"], "image.png")
            doc = read_project(path)
            self.assertEqual(doc["scenes"][0]["image"], str(root / "image.png"))
            self.assertEqual(doc["audio"]["volume"], .5)
            self.assertEqual(scenes[0]["image"], str(root / "image.png"))

    def test_legacy_and_malformed_documents(self):
        doc = validate_document({"version": 1, "scenes": [{"image": "a.png", "duration": 5}]})
        self.assertEqual(doc["scenes"][0]["easing"], "linear")
        self.assertIsNone(doc["audio"])
        for bad in ([], None, {"version": 999, "scenes": []}, {"version": 1, "scenes": [None]},
                    {"version": 1, "scenes": [{"image": "a", "duration": float("nan")}]},
                    {"version": 1, "scenes": [{"image": "a", "duration": 2, "easing": "bad"}]}):
            with self.assertRaises((ValueError, TypeError, KeyError)):
                validate_document(bad)

    def test_failed_save_preserves_existing_project(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "story.json"
            path.write_text("original")
            with mock.patch.object(Path, "replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    write_project(path, [], None)
            self.assertEqual(path.read_text(), "original")
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_audio_rejects_nonfinite_negative_and_missing_path(self):
        for audio in ({}, {"path": "a", "volume": float("nan")}, {"path": "a", "trim": -1},
                      {"path": "a", "offset": float("inf")}, {"path": "a", "fade": 31}):
            with self.assertRaises(ValueError):
                audio_values(audio)

    def test_project_duration_matches_export_frames(self):
        doc = validate_document({"version": 1, "scenes": [{"image": "a.png", "duration": .52}]})
        self.assertEqual(doc["scenes"][0]["duration"], round(.52*24)/24)

    def test_export_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "asset.png"
            path.write_bytes(b"protected")
            with mock.patch.object(desktop_app, "ffmpeg_binary", return_value="ffmpeg"):
                with self.assertRaises(FileExistsError):
                    desktop_app.render_scenes([{"image": str(path), "duration": 1}], path)
            self.assertEqual(path.read_bytes(), b"protected")

    def test_missing_audio_rejected_before_render(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(desktop_app, "ffmpeg_binary", return_value="ffmpeg"):
                with self.assertRaises(FileNotFoundError):
                    desktop_app.render_scenes([{"image": "unused", "duration": 1}], Path(folder)/"out.mp4", audio={"path": str(Path(folder)/"missing.wav")})


if __name__ == "__main__":
    unittest.main()
