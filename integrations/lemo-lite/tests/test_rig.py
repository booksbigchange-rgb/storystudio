"""Layered-artwork character packs: validation, safe import, auto-rig geometry and rendering."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
import cartoon_project as project
import character_rig as rig
import native_scene
import renderer
import sample_character


def sha(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(folder).rglob('*')) if p.is_file()}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.layers = self.root/'layers'
        sample_character.write(self.layers)
        self.library = self.root/'library'
        patcher = patch.dict(os.environ, {'STORYSTUDIO_CHARACTERS': str(self.library)})
        patcher.start()
        self.addCleanup(patcher.stop)
        native_scene._packs.clear()

    def tearDown(self):
        self.temp.cleanup()

    def tiny_rig(self, **override):
        data = dict(kind=rig.KIND, version=1, name='T', scale=1, parts=[dict(id='body', image='body.png', pivot=[5, 5], at=[0, 0], parent=None, z=0)], motion={})
        data.update(override)
        return data


class Validation(Base):
    def test_good_rig(self):
        checked = rig.validate_rig(self.tiny_rig(), {'body.png': (10, 10)})
        self.assertEqual(checked['parts'][0]['id'], 'body')

    def test_bad_rigs_are_rejected(self):
        part = lambda **kw: dict(dict(id='a', image='a.png', pivot=[1, 1], at=[0, 0], parent=None, z=0), **kw)
        cases = {
            'kind': dict(kind='other'), 'version': dict(version=2), 'name': dict(name=''), 'noparts': dict(parts=[]),
            'toomany': dict(parts=[part(id=f'p{i}', image=f'p{i}.png') for i in range(41)]),
            'dupe': dict(parts=[part(), part()]),
            'badid': dict(parts=[part(id='Bad Id')]),
            'traversal': dict(parts=[part(image='../secret.png')]), 'folder': dict(parts=[part(image='sub/a.png')]),
            'jpg': dict(parts=[part(image='a.jpg')]), 'abs': dict(parts=[part(image='C:/a.png')]), 'url': dict(parts=[part(image='http://x/a.png')]),
            'nan': dict(parts=[part(at=[float('nan'), 0])]), 'huge': dict(parts=[part(at=[1e9, 0])]), 'bool': dict(parts=[part(z=True)]),
            'unknownkey': dict(parts=[part(script='x')]),
            'missingparent': dict(parts=[part(parent='ghost')]),
            'loop': dict(parts=[part(id='a', parent='b'), part(id='b', image='b.png', parent='a')]),
            'selfloop': dict(parts=[part(parent='a')]),
            'show': dict(parts=[part(show={'expression': ['angry']})]), 'show2': dict(parts=[part(show={'eval': 1})]),
            'channel': dict(parts=[part()], motion={'wave': [dict(part='a', channel='skew')]}),
            'action': dict(parts=[part()], motion={'fly': []}),
            'driver_part': dict(parts=[part()], motion={'wave': [dict(part='zzz', channel='rotate')]}),
            'drivers': dict(parts=[part()], motion={'wave': [dict(part='a', channel='rotate')]*9}),
            'amp': dict(parts=[part()], motion={'wave': [dict(part='a', channel='rotate', amp=999)]}),
            'speed': dict(parts=[part()], motion={'wave': [dict(part='a', channel='rotate', speed=1000)]}),
            'expr_string': dict(parts=[part()], motion={'wave': [dict(part='a', channel='rotate', amp='__import__(os)')]}),
        }
        for label, override in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                rig.validate_rig(self.tiny_rig(**override))

    def test_pivot_must_be_inside_image(self):
        with self.assertRaisesRegex(ValueError, 'pivot'):
            rig.validate_rig(self.tiny_rig(), {'body.png': (4, 4)})
        with self.assertRaisesRegex(ValueError, 'missing from the pack'):
            rig.validate_rig(self.tiny_rig(), {})

    def test_pack_names_and_scene_references(self):
        self.assertEqual(rig.custom_name('custom:robo'), 'robo')
        for bad in ('fox', 'custom:', 'custom:../x', 'custom:a b', 'custom:' + 'a'*33, None, 5):
            self.assertIsNone(rig.custom_name(bad))
        doc = project.new_project(); doc['scenes'][0]['character'] = 'custom:robo'
        project.validate(doc)
        for bad in ('custom:../x', 'custom:', 'custom:a/b', 'robo'):
            doc['scenes'][0]['character'] = bad
            with self.assertRaises(ValueError):
                project.validate(doc)

    def test_no_code_is_ever_evaluated(self):
        source = Path(rig.__file__).read_text(encoding='utf-8')
        import re
        for word in ('eval(', 'exec(', '__import__', 'pickle', 'subprocess', 'os.system', 'import socket'):
            self.assertNotIn(word, source)
        self.assertIsNone(re.search(r'(?<!re\.)compile\(', source))


class Importing(Base):
    def test_import_auto_rig_and_load(self):
        before = sha(self.layers)
        target = rig.import_pack(self.layers, 'robo', self.library)
        self.assertEqual(sha(self.layers), before)                           # source art untouched
        self.assertEqual(rig.list_packs(self.library), ['robo'])
        pack = rig.load_pack('robo', self.library)
        ids = [p['id'] for p in pack.rig['parts']]
        self.assertEqual(set(ids), {'body', 'head', 'arm_left', 'arm_right', 'leg_left', 'leg_right', 'tail', 'eyes_open', 'eyes_closed', 'mouth_closed', 'mouth_open'})
        self.assertEqual(ids[-1], 'arm_right')                              # drawn last (in front)
        self.assertTrue(all(len(list(target.glob('*'))) for _ in [0]))
        self.assertFalse(list(self.library.glob('.import-*')))

    def test_auto_rig_geometry_comes_from_the_art(self):
        rig.import_pack(self.layers, 'robo', self.library)
        parts = {p['id']: p for p in rig.load_pack('robo', self.library).rig['parts']}
        head, body, arm = parts['head'], parts['body'], parts['arm_right']
        self.assertEqual(head['parent'], 'body')
        self.assertEqual(parts['eyes_open']['parent'], 'head')
        # Head pivots at its bottom centre; the head sits above the body centre (canvas y of the sample art).
        self.assertAlmostEqual(head['pivot'][0], 110, delta=4)
        self.assertAlmostEqual(head['at'][1], 310-445, delta=6)
        self.assertAlmostEqual(arm['pivot'][1], 0, delta=1)                  # arms swing from their top edge
        self.assertAlmostEqual(arm['at'][0], 432-300, delta=6)
        self.assertAlmostEqual(body['at'][0], 0, delta=6)
        self.assertAlmostEqual(body['at'][1], 445-675, delta=10)             # ground = bottom of the art
        self.assertAlmostEqual(rig.load_pack('robo', self.library).rig['scale'], 250/(675-52), delta=.01)

    def test_never_overwrites(self):
        rig.import_pack(self.layers, 'robo', self.library)
        before = sha(self.library/'robo')
        with self.assertRaises(FileExistsError):
            rig.import_pack(self.layers, 'robo', self.library)
        self.assertEqual(sha(self.library/'robo'), before)

    def test_bad_names_and_sources(self):
        for name in ('', 'a b', '../x', 'a/b', 'x'*33, '.hidden', None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                rig.import_pack(self.layers, name, self.library)
        with self.assertRaises(FileNotFoundError):
            rig.import_pack(self.root/'nope', 'ok', self.library)
        self.assertEqual(rig.list_packs(self.library), [])

    def test_failed_import_leaves_nothing_behind(self):
        (self.layers/'head.png').unlink()
        with self.assertRaisesRegex(ValueError, 'head.png'):
            rig.import_pack(self.layers, 'robo', self.library)
        sample_character.make_layers()['head'].save(self.layers/'head.png')
        Image.new('RGBA', sample_character.CANVAS, (0, 0, 0, 0)).save(self.layers/'tail.png')          # empty layer
        with self.assertRaisesRegex(ValueError, 'empty'):
            rig.import_pack(self.layers, 'robo', self.library)
        Image.new('RGBA', (50, 50), (255, 0, 0, 255)).save(self.layers/'tail.png')        # different canvas size
        with self.assertRaisesRegex(ValueError, 'full canvas'):
            rig.import_pack(self.layers, 'robo', self.library)
        self.assertEqual(rig.list_packs(self.library), [])
        self.assertFalse(list(self.library.glob('.import-*')) if self.library.exists() else [])

    def test_finished_pack_is_copied_and_validated(self):
        rig.import_pack(self.layers, 'first', self.library)
        source = self.root/'finished'
        import shutil
        shutil.copytree(self.library/'first', source)
        (source/'notes.exe').write_bytes(b'MZ')                                           # stray files are not copied
        rig.import_pack(source, 'second', self.library)
        self.assertFalse((self.library/'second'/'notes.exe').exists())
        # A pack whose rig points at a missing image is refused and not published.
        data = json.loads((source/'rig.json').read_text()); data['parts'][0]['image'] = 'gone.png'
        (source/'rig.json').write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            rig.import_pack(source, 'third', self.library)
        self.assertNotIn('third', rig.list_packs(self.library))

    def test_size_limits(self):
        rig.import_pack(self.layers, 'robo', self.library)
        big = self.library/'robo'/'body.png'
        Image.new('RGBA', (rig.MAX_SIDE+1, 4)).save(big)
        native_scene._packs.clear()
        with self.assertRaisesRegex(ValueError, 'no larger'):
            rig.load_pack('robo', self.library)
        (self.library/'robo'/'body.png').write_bytes(b'not a png at all')
        with self.assertRaises(Exception):
            rig.load_pack('robo', self.library)
        (self.library/'robo'/'rig.json').write_text(' '*(300*1024))
        with self.assertRaisesRegex(ValueError, '256 KB'):
            rig.load_pack('robo', self.library)

    def test_missing_pack_message(self):
        with self.assertRaisesRegex(FileNotFoundError, 'ghost'):
            rig.load_pack('ghost', self.library)
        doc = project.new_project(); doc['scenes'][0]['character'] = 'custom:ghost'
        with self.assertRaisesRegex(FileNotFoundError, 'ghost'):
            native_scene.require_packs(doc)
        args = type('A', (), dict(document=doc, width=320, height=180, fps=12, duration=2, output=str(self.root/'out.mp4'), overwrite=False, audio=None))()
        with self.assertRaises(FileNotFoundError):
            renderer.export(args)
        self.assertFalse((self.root/'out.mp4').exists())
        args.engine = 'browser'
        with self.assertRaisesRegex(ValueError, 'native renderer'):
            renderer.export(args)


class Rendering(Base):
    def frame(self, t=1.0, **scene):
        doc = project.new_project()
        doc['scenes'][0].update({'duration': 6, 'character': 'custom:robo', 'action': 'idle', **scene})
        return native_scene.NativeScene(doc, 640, 360).frame(t)

    def setUp(self):
        super().setUp()
        rig.import_pack(self.layers, 'robo', self.library)

    def blue(self, image):
        return [(x, y) for x in range(0, 640, 2) for y in range(0, 360, 2) if (lambda p: abs(p[0]-120) < 12 and abs(p[1]-150) < 12 and abs(p[2]-190) < 12)(image.getpixel((x, y)))]

    def test_character_is_drawn_and_moves(self):
        idle, wave = self.frame(action='idle'), self.frame(action='wave')
        self.assertGreater(len(self.blue(idle)), 200)                      # the steel-blue body is visible
        self.assertNotEqual(idle.tobytes(), wave.tobytes())
        self.assertNotEqual(self.frame(action='walk', t=1.0).tobytes(), self.frame(action='walk', t=1.2).tobytes())
        # Waving raises the right arm: the dark arm pixels appear on the right of the body in wave but not in idle.
        from PIL import ImageChops
        diff = ImageChops.difference(idle, wave).convert('L').point(lambda v: 255 if v > 40 else 0)
        right = diff.crop((285, 100, 360, 260)).getbbox()
        left = diff.crop((150, 100, 212, 260)).getbbox()
        self.assertIsNotNone(right)                                          # the right arm moved
        self.assertIsNone(left)                                              # nothing on the left of the body changed

    def test_expression_blink_and_mouth_rules(self):
        closed, opened = self.frame(action='talk', t=0.0), None
        for t in (n/24 for n in range(1, 48)):                              # find a moment when the talking mouth is open
            candidate = self.frame(action='talk', t=t)
            if candidate.tobytes() != closed.tobytes():
                opened = candidate
                break
        self.assertIsNotNone(opened)
        self.assertNotEqual(self.frame(expression='surprised').tobytes(), self.frame(expression='happy').tobytes())   # open mouth for surprise
        blink_time = 3.5                                                    # blink window of pose_at
        self.assertNotEqual(self.frame(t=blink_time).tobytes(), self.frame(t=2.0).tobytes())

    def test_keys_and_tilt_apply_to_custom_characters(self):
        plain = self.frame().tobytes()
        for extra in (dict(keys=[{'at': 0, 'x': .6}]), dict(keys=[{'at': 0, 'tilt': .4}]), dict(keys=[{'at': 0, 'lift': 80}]), dict(keys=[{'at': 0, 'size': 1.2}])):
            self.assertNotEqual(self.frame(**extra).tobytes(), plain, extra)

    def test_sprite_compositing_is_exact(self):
        image = Image.new('RGB', (40, 40), 'white')
        g = native_scene.Painter(image, 1)
        square = Image.new('RGBA', (10, 10), (255, 0, 0, 255)).convert('RGBa')
        g.sprite(square, (1, 0, 0, 1, 10, 10))
        self.assertEqual(image.getpixel((15, 15)), (255, 0, 0))
        self.assertEqual(image.getpixel((5, 5)), (255, 255, 255))
        self.assertEqual(image.getpixel((25, 15)), (255, 255, 255))
        rotated = Image.new('RGB', (60, 60), 'white')
        native_scene.Painter(rotated, 1).sprite(square, (0, 1, -1, 0, 30, 20))            # 90 degrees about the origin
        self.assertEqual(rotated.getpixel((25, 25)), (255, 0, 0))
        edge = Image.new('RGB', (40, 40), 'white')
        native_scene.Painter(edge, 1).sprite(square, (1, 0, 0, 1, -5, -5))                # partly off-canvas: no error
        native_scene.Painter(edge, 1).sprite(square, (1, 0, 0, 1, 500, 500))              # fully off-canvas
        native_scene.Painter(edge, 1).sprite(square, (0, 0, 0, 0, 5, 5))                  # degenerate transform

    def test_no_dark_fringes_around_soft_edges(self):
        soft = Image.new('RGBA', (20, 20), (255, 255, 255, 0))
        for x in range(5, 15):
            for y in range(5, 15):
                soft.putpixel((x, y), (255, 255, 255, 128))
        image = Image.new('RGB', (40, 40), 'white')
        native_scene.Painter(image, 1).sprite(soft.convert('RGBa'), (1, 0, 0, 1, 10, 10))
        self.assertTrue(all(min(image.getpixel((x, y))) > 240 for x in range(40) for y in range(40)))   # white on white stays white

    def test_fast_enough(self):
        doc = project.new_project(); doc['scenes'][0].update(duration=6, character='custom:robo', action='walk')
        scene = native_scene.NativeScene(doc, 1280, 720)
        scene.frame(0)
        start = time.perf_counter()
        for n in range(12):
            scene.frame(n/24)
        self.assertLess((time.perf_counter()-start)/12, .6)

    def test_pack_is_reloaded_when_replaced(self):
        first = self.frame().tobytes()
        shutil_target = self.library/'robo'
        for name in ('body.png',):
            with Image.open(shutil_target/name) as existing:
                size = existing.size
            Image.new('RGBA', size, (200, 0, 0, 255)).save(shutil_target/name)
        os.utime(shutil_target/'rig.json', (time.time()+5, time.time()+5))
        self.assertNotEqual(self.frame().tobytes(), first)


if __name__ == '__main__':
    unittest.main()
