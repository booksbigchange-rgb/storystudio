"""Trim/split/transition planning, durations, validation and undo history."""
import copy
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
import mixed_durations as durations
import mixed_edit as edit
import mixed_project as model
from mixed_history import History


def sec(name, **extra):
    return dict(name=name, engine='documentary', project=name+'.json', **extra)


class Plan(unittest.TestCase):
    def test_plain_sections_are_untouched(self):
        p = edit.plan([sec('A'), sec('B')], [48, 72])
        self.assertEqual((p['total'], p['starts'], p['lengths']), (120, [0, 48], [48, 72]))
        self.assertEqual(p['parts'], [('main', 0, 0, 48, 0, 0), ('main', 1, 0, 72, 0, 0)])

    def test_trim_dissolve_fade_arithmetic(self):
        sections = [sec('A', trim_in=12, trim_out=36), sec('B', transition=dict(kind='dissolve', frames=12)),
                    sec('C', transition=dict(kind='fade', frames=6))]
        p = edit.plan(sections, [48, 48, 60])
        self.assertEqual(p['lengths'], [24, 48, 60])
        self.assertEqual(p['total'], 24+48+60-12)
        self.assertEqual(p['starts'], [0, 12, 60])
        self.assertEqual(p['fades'], [(0, 0), (0, 6), (6, 0)])
        self.assertEqual(p['parts'], [('main', 0, 12, 24, 0, 0), ('mix', 1, 12), ('main', 1, 12, 48, 0, 6), ('main', 2, 0, 60, 6, 0)])
        covered = sum(part[3]-part[2] if part[0] == 'main' else part[2] for part in p['parts'])
        self.assertEqual(covered, p['total'])                       # every output frame comes from exactly one clip

    def test_every_plan_covers_the_total_exactly(self):
        rng = random.Random(5)
        for _ in range(300):
            count = rng.randint(1, 8)
            frames = [rng.randint(12, 120) for _ in range(count)]
            sections = []
            for i in range(count):
                s = sec(f'S{i}')
                if rng.random() < .4:
                    s['trim_in'] = rng.randint(0, frames[i]//3)
                if rng.random() < .3:
                    s['trim_out'] = rng.randint(s.get('trim_in', 0)+2, frames[i])
                if i and rng.random() < .6:
                    s['transition'] = dict(kind=rng.choice(edit.KINDS), frames=rng.randint(2, 10))
                sections.append(s)
            try:
                p = edit.plan(sections, frames)
            except ValueError:
                continue
            covered = sum(part[3]-part[2] if part[0] == 'main' else part[2] for part in p['parts'])
            self.assertEqual(covered, p['total'])
            self.assertEqual(p['total'], sum(p['lengths'])-sum(p['overlaps']))
            self.assertEqual(p['starts'], sorted(p['starts']))

    def test_errors_are_explained(self):
        with self.assertRaisesRegex(ValueError, 'only 48 frames'):
            edit.plan([sec('A', trim_out=99)], [48])
        with self.assertRaisesRegex(ValueError, 'no frames left'):
            edit.plan([sec('A', trim_in=60)], [48])
        with self.assertRaisesRegex(ValueError, 'longer than a neighbouring'):
            edit.plan([sec('A'), sec('B', transition=dict(kind='dissolve', frames=50))], [48, 48])
        with self.assertRaisesRegex(ValueError, 'too short'):
            edit.plan([sec('A'), sec('B', transition=dict(kind='dissolve', frames=30)), sec('C', transition=dict(kind='dissolve', frames=30))], [48, 48, 48])
        with self.assertRaisesRegex(ValueError, 'fades on both sides'):
            edit.plan([sec('A'), sec('B', transition=dict(kind='fade', frames=20)), sec('C', transition=dict(kind='fade', frames=20))], [48, 30, 48])

    def test_first_section_transition_is_ignored(self):
        p = edit.plan([sec('A', transition=dict(kind='dissolve', frames=10)), sec('B')], [48, 48])
        self.assertEqual(p['total'], 96)


class Fields(unittest.TestCase):
    def test_validation(self):
        good = [dict(trim_in=0), dict(trim_in=3, trim_out=9), dict(transition=dict(kind='fade', frames=2)), dict(transition=dict(kind='dissolve', frames=96))]
        for extra in good:
            edit.validate_edit({'name': 'x', **extra})
        bad = [dict(trim_in=-1), dict(trim_in=True), dict(trim_in=1.5), dict(trim_out=0), dict(trim_in=5, trim_out=5), dict(trim_out='9'),
               dict(transition='fade'), dict(transition=dict(kind='wipe', frames=6)), dict(transition=dict(kind='fade', frames=1)),
               dict(transition=dict(kind='fade', frames=97)), dict(transition=dict(kind='fade', frames=6, extra=1)), dict(transition=dict(kind='fade'))]
        for extra in bad:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                edit.validate_edit({'name': 'x', **extra})

    def test_old_timelines_load_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = model.new_project()
            doc['sections'] = [dict(engine='documentary', project=str(Path(folder)/'a.json'), name='A', trim_in=5, trim_out=20,
                                    transition=dict(kind='fade', frames=4))]
            path = Path(folder)/'t.json'
            model.save(doc, path)
            self.assertEqual(model.load(path)['sections'][0]['trim_out'], 20)
            plain = json.loads(path.read_text()); plain['sections'][0] = {k: v for k, v in plain['sections'][0].items() if k not in ('trim_in', 'trim_out', 'transition')}
            model.validate(plain)


class Split(unittest.TestCase):
    def test_split_keeps_every_frame_once(self):
        left, right = edit.split(sec('A'), 17, 48)
        self.assertEqual((left.get('trim_in'), left['trim_out'], right['trim_in'], right.get('trim_out')), (None, 17, 17, None))
        p = edit.plan([left, right], [48, 48])
        self.assertEqual(p['total'], 48)

    def test_split_of_trimmed_section_and_transition_stay_with_first_half(self):
        s = sec('A', trim_in=10, trim_out=40, transition=dict(kind='dissolve', frames=6))
        left, right = edit.split(s, 10, 48)
        self.assertEqual((left['trim_in'], left['trim_out'], right['trim_in'], right['trim_out']), (10, 20, 20, 40))
        self.assertIn('transition', left)
        self.assertNotIn('transition', right)
        self.assertEqual(s['trim_out'], 40)                                    # original untouched

    def test_bad_split_points(self):
        for at in (0, 48, 99, -1):
            with self.assertRaises(ValueError):
                edit.split(sec('A'), at, 48)


class DurationsAndHistory(unittest.TestCase):
    def test_timeline_matches_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for i, seconds in enumerate((2, 2, 2.5)):
                path = Path(folder)/f'p{i}.json'
                path.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='x.png', duration=seconds)])))
                paths.append(path)
            doc = model.new_project()
            doc['sections'] = [dict(engine='documentary', project=str(paths[0]), name='A', trim_in=12),
                               dict(engine='documentary', project=str(paths[1]), name='B', transition=dict(kind='dissolve', frames=10)),
                               dict(engine='documentary', project=str(paths[2]), name='C', trim_out=24, transition=dict(kind='fade', frames=4))]
            rows, total = durations.timeline(doc)
            plan = edit.plan(doc['sections'], [48, 48, 60])
            self.assertEqual(total, plan['total'])
            self.assertEqual([r[0] for r in rows], plan['starts'])
            self.assertEqual([r[1] for r in rows], plan['lengths'])
            doc['sections'][2]['trim_out'] = 99                                # source only has 60 frames
            self.assertIsNone(durations.timeline(doc)[0][2][1])

    def test_history_undo_redo_bounds(self):
        history = History(limit=3)
        doc = {'v': 0}
        for n in range(1, 6):
            history.checkpoint(doc)
            doc = {'v': n}
        self.assertEqual(len(history.past), 3)
        back = history.undo(doc)
        self.assertEqual(back, {'v': 4})
        self.assertEqual(history.redo(back), {'v': 5})
        history.undo(doc)
        history.checkpoint({'v': 99})
        self.assertFalse(history.can_redo())                                    # a new change drops the redo branch
        history.clear()
        self.assertIsNone(history.undo(doc))
        self.assertIsNone(history.redo(doc))

    def test_history_copies_and_ignores_duplicates(self):
        history = History()
        doc = {'a': [1]}
        history.checkpoint(doc)
        doc['a'].append(2)
        self.assertEqual(history.past[0], {'a': [1]})                           # snapshot not aliased
        history.checkpoint({'a': [1]})
        self.assertEqual(len(history.past), 1)


if __name__ == '__main__':
    unittest.main()
