"""Long-story model rules: limits, ordering, frame-exact durations, cache and cleanup."""
import copy
import json
from pathlib import Path
import random
import sys
import tempfile
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
import mixed_durations as durations
import mixed_project as model
import mixed_render


def write(folder, name, scenes, version=5, engine='documentary'):
    path = Path(folder)/name
    if engine == 'documentary':
        doc = dict(version=version, format='widescreen', scenes=[dict(image='x.png', duration=d) for d in scenes])
    else:
        doc = dict(version=2, name='c', format='Landscape 16:9', quality='Standard · 720p / 24 fps', audio=None,
                   scenes=[dict(title='', duration=d, character='bear', expression='curious', action='wave', background='meadow', x=.4, size=1, speed=1) for d in scenes])
    path.write_text(json.dumps(doc), encoding='utf-8')
    return path


class Durations(unittest.TestCase):
    def test_frame_rules_match_exporter(self):
        # Documentary rounds each scene; the character engine rounds the section total.
        doc = {'scenes': [{'duration': 1.01}, {'duration': 1.01}, {'duration': 1.01}]}
        self.assertEqual(durations.frames('documentary', doc), 72)
        self.assertEqual(durations.frames('cartoon', doc), round(3.03*24))
        half = {'scenes': [{'duration': .52}]*3}
        self.assertEqual(durations.frames('documentary', half), 3*round(.52*24))
        self.assertEqual(durations.frames('cartoon', half), round(1.56*24))
        for bad in ({'scenes': []}, {}):
            with self.assertRaises((ValueError, KeyError)):
                durations.frames('documentary', bad)

    def test_timeline_prefix_sums_are_stable_under_reordering(self):
        with tempfile.TemporaryDirectory() as folder:
            lengths = [1.5, 2, 2.25, 3, .52]
            paths = [write(folder, f'p{i}.json', [lengths[i % 5]]) for i in range(60)]
            doc = model.new_project()
            doc['sections'] = [dict(engine='documentary', project=str(p), name=f'S{i}') for i, p in enumerate(paths)]
            rows, total = durations.timeline(doc)
            self.assertEqual(rows[0][0], 0)
            for (start, count), (next_start, _) in zip(rows, rows[1:]):
                self.assertEqual(start+count, next_start)
            self.assertEqual(total, rows[-1][0]+rows[-1][1])
            order = list(range(60))
            random.Random(3).shuffle(order)
            shuffled = copy.deepcopy(doc)
            shuffled['sections'] = [doc['sections'][i] for i in order]
            rows2, total2 = durations.timeline(shuffled)
            self.assertEqual(total, total2)
            self.assertEqual([c for _, c in rows2], [rows[i][1] for i in order])

    def test_missing_and_changed_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write(folder, 'a.json', [2])
            section = dict(engine='documentary', project=str(path), name='A')
            self.assertEqual(durations.section_frames(section), 48)
            time.sleep(.01)
            write(folder, 'a.json', [2, 1])
            self.assertEqual(durations.section_frames(section), 72)   # cache follows the file
            path.write_text('{broken')
            self.assertIsNone(durations.section_frames(section))
            path.unlink()
            self.assertIsNone(durations.section_frames(section))
            doc = model.new_project(); doc['sections'] = [section]
            self.assertEqual(durations.timeline(doc), ([(0, None)], 0))

    def test_clock_and_disk_estimate(self):
        self.assertEqual(durations.clock(0), '0:00.00')
        self.assertEqual(durations.clock(36), '0:01.50')
        self.assertEqual(durations.clock(24*3725), '1:02:05.00')
        self.assertGreater(durations.estimated_bytes(3600), durations.estimated_bytes(60))
        with self.assertRaises(ValueError):
            durations.estimated_bytes(float('nan'))


class Management(unittest.TestCase):
    def doc(self, count):
        doc = model.new_project()
        doc['sections'] = [dict(engine='documentary', project=f'p{i}.json', name=f'S{i}') for i in range(count)]
        return doc

    def test_capacity(self):
        doc = self.doc(model.MAX_SECTIONS)
        model.validate(doc)
        doc['sections'].append(dict(engine='cartoon', project='x.json', name='extra'))
        with self.assertRaisesRegex(ValueError, str(model.MAX_SECTIONS)):
            model.validate(doc)
        full = self.doc(model.MAX_SECTIONS)
        with self.assertRaises(ValueError):
            model.duplicate(full, 3)
        self.assertEqual(len(full['sections']), model.MAX_SECTIONS)

    def test_move_to_duplicate_keep_order_stable(self):
        doc = self.doc(6)
        names = lambda: [s['name'] for s in doc['sections']]
        self.assertEqual(model.move_to(doc, 4, 0), 0)
        self.assertEqual(names(), ['S4', 'S0', 'S1', 'S2', 'S3', 'S5'])
        self.assertEqual(model.move_to(doc, 0, 10**6), 5)
        self.assertEqual(names(), ['S0', 'S1', 'S2', 'S3', 'S5', 'S4'])
        self.assertEqual(model.move_to(doc, 9, 0), 9)                      # out of range: no change
        self.assertEqual(model.duplicate(doc, 1), 2)
        self.assertEqual(names(), ['S0', 'S1', 'S1', 'S2', 'S3', 'S5', 'S4'])
        doc['sections'][2]['name'] = 'copy'
        self.assertEqual(doc['sections'][1]['name'], 'S1')                  # a real copy, not an alias
        self.assertEqual(model.duplicate(doc, 99), 99)

    def test_random_moves_preserve_every_section(self):
        doc = self.doc(50)
        rng = random.Random(11)
        for _ in range(500):
            model.move(doc, rng.randrange(50), rng.choice([-1, 1]))
            model.move_to(doc, rng.randrange(50), rng.randrange(-3, 60))
        self.assertEqual(sorted(s['name'] for s in doc['sections']), sorted(f'S{i}' for i in range(50)))

    def test_hour_limit_for_text(self):
        doc = self.doc(1)
        doc['titles'] = [dict(kind='Title', text='Late', start=3000, end=3001)]
        model.validate(doc)
        doc['titles'][0]['end'] = 4000
        with self.assertRaises(ValueError):
            model.validate(doc)


class Cleanup(unittest.TestCase):
    def test_clean_removes_media_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            for name in ('raw-0.mp4', 'section-0.mov', 'joined.mp4', 'title-0.png', '.out.partial.mp4', '.raw-1.partial.mp4'):
                (work/name).write_bytes(b'x'*10)
            for name in ('render.log', 'source-0.json', 'expected.json', 'result.json'):
                (work/name).write_text('keep')
            mixed_render.clean(work)
            self.assertEqual(sorted(p.name for p in work.iterdir()), ['expected.json', 'render.log', 'result.json', 'source-0.json'])


if __name__ == '__main__':
    unittest.main()
