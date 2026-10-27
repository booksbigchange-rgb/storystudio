"""Animation keys and reusable character presets (pure Python; no browser)."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import presets
import cartoon_project as project


def scene(**keys):
    value = project.new_scene()
    value.update(action='idle', duration=4)
    if keys:
        value['keys'] = keys['keys']
    return value


class KeyValidation(unittest.TestCase):
    def doc(self, keys):
        doc = project.new_project()
        doc['scenes'][0]['keys'] = keys
        return doc

    def test_valid_keys_round_trip_and_old_scenes_untouched(self):
        old = project.validate(project.new_project())
        self.assertNotIn('keys', old['scenes'][0])
        keys = [{'at': 0, 'x': .3}, {'at': .5, 'lift': -20, 'tilt': .2, 'expression': 'sad', 'action': 'wave'}, {'at': 1, 'size': 1.1}]
        doc = project.validate(self.doc(keys))
        self.assertEqual(doc['scenes'][0]['keys'][1]['action'], 'wave')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'story.json'
            project.save(doc, path)
            self.assertEqual(project.load(path), doc)

    def test_rejects_bad_keys(self):
        bad = [[{'at': 0}], [{'at': .5, 'x': .3}, {'at': .5, 'x': .4}], [{'at': .6, 'x': .3}, {'at': .2, 'x': .4}],
               [{'at': -.1, 'x': .3}], [{'at': 1.1, 'x': .3}], [{'at': .5, 'x': 5}], [{'at': .5, 'tilt': 2}],
               [{'at': .5, 'lift': 999}], [{'at': .5, 'expression': 'angry'}], [{'at': .5, 'action': 'fly'}],
               [{'at': .5, 'x': float('nan')}], [{'at': .5, 'x': True}], [{'at': .5, 'colour': 'red'}],
               [{'x': .3}], ['text'], 'text', [{'at': i/10, 'x': .3} for i in range(9)]]
        for keys in bad:
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                project.validate(self.doc(keys))

    def test_validation_does_not_mutate(self):
        doc = self.doc([{'at': 0, 'x': .3}])
        before = copy.deepcopy(doc)
        project.validate(doc)['scenes'][0]['keys'][0]['x'] = .6
        self.assertEqual(doc, before)


class Interpolation(unittest.TestCase):
    def test_no_keys_is_scene_values(self):
        value = project.key_values(scene(), .5)
        self.assertEqual((value['x'], value['size'], value['lift'], value['tilt'], value['expression'], value['action']),
                         (.4, 1.0, 0.0, 0.0, 'happy', 'idle'))

    def test_eased_between_keys_and_held_outside(self):
        s = scene(keys=[{'at': .25, 'x': .3}, {'at': .75, 'x': .6, 'lift': 100}])
        self.assertEqual(project.key_values(s, 0)['x'], .3)
        self.assertEqual(project.key_values(s, 1)['x'], .6)
        self.assertAlmostEqual(project.key_values(s, .5)['x'], .45)               # eased midpoint
        self.assertAlmostEqual(project.key_values(s, .375)['x'], .3+.3*(0.25*0.25*(3-0.5)))
        self.assertEqual(project.key_values(s, .1)['lift'], 100)                    # single-track hold
        xs = [project.key_values(s, f/100)['x'] for f in range(101)]
        self.assertEqual(xs, sorted(xs))                                           # monotonic, no overshoot
        self.assertTrue(all(.3 <= x <= .6 for x in xs))

    def test_expression_and_action_switch_at_key(self):
        s = scene(keys=[{'at': .5, 'expression': 'surprised', 'action': 'jump'}, {'at': .8, 'expression': 'sad'}])
        self.assertEqual(project.key_values(s, .49)['expression'], 'happy')
        self.assertEqual(project.key_values(s, .5)['expression'], 'surprised')
        self.assertEqual(project.key_values(s, .5)['action'], 'jump')
        self.assertEqual(project.key_values(s, .9)['expression'], 'sad')
        self.assertEqual(project.key_values(s, .9)['action'], 'jump')

    def test_fraction_is_clamped(self):
        s = scene(keys=[{'at': 0, 'x': .3}, {'at': 1, 'x': .6}])
        self.assertEqual(project.key_values(s, -5)['x'], .3)
        self.assertEqual(project.key_values(s, 9)['x'], .6)


class Presets(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'projects'/'character-presets.json'

    def tearDown(self):
        self.temp.cleanup()

    def source(self):
        value = project.new_scene()
        value.update(character='bear', expression='curious', action='walk', x=.3, size=1.1, speed=1.5, title='Caption stays', duration=7,
                     background='night', keys=[{'at': 0, 'x': .3}, {'at': 1, 'x': .6, 'tilt': .2}])
        return value

    def test_save_load_apply_keeps_caption_length_backdrop(self):
        self.assertEqual(presets.load(self.path), {})
        presets.save(self.path, '  Bear walk  ', self.source())
        library = presets.load(self.path)
        self.assertEqual(list(library), ['Bear walk'])
        self.assertNotIn('title', library['Bear walk'])
        target = project.new_scene()
        target.update(title='Mine', duration=3, background='sunset', keys=[{'at': .5, 'lift': 10}])
        result = presets.apply(target, library['Bear walk'])
        self.assertEqual((result['character'], result['action'], result['title'], result['duration'], result['background']),
                         ('bear', 'walk', 'Mine', 3, 'sunset'))
        self.assertEqual(result['keys'][1]['tilt'], .2)
        self.assertEqual(target['keys'], [{'at': .5, 'lift': 10}])                  # source scene untouched
        doc = project.new_project(); doc['scenes'] = [result]
        project.validate(doc)

    def test_apply_preset_without_keys_clears_old_keys(self):
        presets.save(self.path, 'Plain', project.new_scene())
        target = project.new_scene(); target['keys'] = [{'at': .5, 'x': .5}]
        self.assertNotIn('keys', presets.apply(target, presets.load(self.path)['Plain']))

    def test_name_rules_and_no_silent_replace(self):
        presets.save(self.path, 'One', self.source())
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            presets.save(self.path, 'One', project.new_scene())
        self.assertEqual(self.path.read_bytes(), before)
        presets.save(self.path, 'One', project.new_scene(), replace=True)
        self.assertEqual(presets.load(self.path)['One']['character'], 'fox')
        for name in ('', '   ', 'x'*41, 'bad\nname', None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                presets.save(self.path, name, project.new_scene())

    def test_limit_delete_and_corrupt_library(self):
        for i in range(presets.MAX_PRESETS):
            presets.save(self.path, f'P{i}', project.new_scene())
        with self.assertRaises(ValueError):
            presets.save(self.path, 'one too many', project.new_scene())
        presets.delete(self.path, 'P0')
        presets.save(self.path, 'fits now', project.new_scene())
        with self.assertRaises(KeyError):
            presets.delete(self.path, 'missing')
        self.path.write_text('{"kind":"other"}')
        with self.assertRaises(ValueError):
            presets.load(self.path)
        self.path.write_text('{broken')
        with self.assertRaises(ValueError):
            presets.load(self.path)

    def test_invalid_scene_not_saved_and_failed_write_keeps_library(self):
        presets.save(self.path, 'Keep', self.source())
        before = self.path.read_bytes()
        bad = self.source(); bad['x'] = 5
        with self.assertRaises(ValueError):
            presets.save(self.path, 'Bad', bad)
        with patch('presets.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                presets.save(self.path, 'Other', self.source())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob('.*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
