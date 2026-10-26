"""Pillow scene renderer: sizes, determinism, every character/expression/action, keys, portrait and speed."""
import copy
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_scene
import project


def doc(**scene):
    value = project.new_project()
    value['scenes'][0].update({'duration': 6, 'action': 'idle', **scene})
    return value


class Frames(unittest.TestCase):
    def test_sizes_and_both_orientations(self):
        landscape = native_scene.NativeScene(doc(), 640, 360).frame(1)
        self.assertEqual(landscape.size, (640, 360))
        portrait_doc = doc(); portrait_doc['format'] = 'Shorts / TikTok 9:16'
        portrait = native_scene.NativeScene(portrait_doc, 360, 640).frame(1)
        self.assertEqual(portrait.size, (360, 640))

    def test_deterministic_and_seekable(self):
        scene = native_scene.NativeScene(doc(action='walk'), 320, 180)
        first = scene.frame(1.5).tobytes()
        scene.frame(3.0)
        self.assertEqual(scene.frame(1.5).tobytes(), first)
        self.assertEqual(native_scene.NativeScene(doc(action='walk'), 320, 180).frame(1.5).tobytes(), first)
        self.assertNotEqual(scene.frame(1.6).tobytes(), first)

    def test_every_look_is_distinct(self):
        for field, values in (('character', project.CHARACTERS), ('expression', project.EXPRESSIONS), ('action', project.ACTIONS), ('background', project.BACKGROUNDS)):
            frames = {native_scene.NativeScene(doc(**{field: value}), 320, 180).frame(1.0).tobytes() for value in values}
            self.assertEqual(len(frames), len(values), field)

    def test_keys_and_caption_change_the_picture(self):
        plain = native_scene.NativeScene(doc(), 320, 180).frame(1).tobytes()
        for extra in (dict(keys=[{'at': 0, 'x': .6}]), dict(keys=[{'at': 0, 'tilt': .4}]), dict(keys=[{'at': 0, 'lift': 80}]),
                      dict(keys=[{'at': 0, 'size': 1.2}]), dict(title='Hello!')):
            self.assertNotEqual(native_scene.NativeScene(doc(**extra), 320, 180).frame(1).tobytes(), plain, extra)
        neutral = doc(keys=[{'at': 0, 'x': .4, 'size': 1.0, 'lift': 0, 'tilt': 0}])
        self.assertEqual(native_scene.NativeScene(neutral, 320, 180).frame(1).tobytes(), plain)

    def test_scene_change_and_clamped_time(self):
        two = doc(character='fox'); two['scenes'].append(dict(project.new_scene(), duration=2, character='bear', background='night'))
        scene = native_scene.NativeScene(two, 320, 180)
        self.assertNotEqual(scene.frame(1).tobytes(), scene.frame(7).tobytes())
        self.assertEqual(scene.frame(-5).tobytes(), scene.frame(0).tobytes())
        self.assertEqual(scene.frame(999).tobytes(), scene.frame(8).tobytes())

    def test_character_stays_in_frame(self):
        # The fox is orange; it must be visible and horizontally follow the position key.
        def centre(position):
            image = native_scene.NativeScene(doc(x=position), 320, 180).frame(1.0)
            xs = [x for x in range(320) for y in range(0, 180, 3) if abs(image.getpixel((x, y))[0]-233) < 20 and abs(image.getpixel((x, y))[1]-131) < 25 and abs(image.getpixel((x, y))[2]-67) < 25]
            self.assertGreater(len(xs), 100)
            return sum(xs)/len(xs)
        self.assertLess(centre(.3), centre(.6)-60)

    def test_fast_enough(self):
        scene = native_scene.NativeScene(doc(action='walk', title='Speed check'), 1280, 720)
        scene.frame(0)
        start = time.perf_counter()
        for n in range(24):
            scene.frame(n/24)
        per_frame = (time.perf_counter()-start)/24
        self.assertLess(per_frame, .5, f'{per_frame:.3f}s per 720p frame')       # generous: CI runners are slow

    def test_renderer_choice(self):
        import renderer
        from unittest.mock import patch
        self.assertEqual(renderer.render_engine(), 'native')
        with patch.dict('os.environ', {'STORYSTUDIO_RENDERER': 'browser'}):
            self.assertEqual(renderer.render_engine(), 'browser')
        with patch.dict('os.environ', {'STORYSTUDIO_RENDERER': 'gpu'}):
            with self.assertRaises(ValueError):
                renderer.render_engine()


if __name__ == '__main__':
    unittest.main()
