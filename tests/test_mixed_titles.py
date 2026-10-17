import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from mixed_titles import validate_titles, card
import mixed_project as model


class TitlesTests(unittest.TestCase):
    def test_old_project_and_roundtrip(self):
        doc = model.new_project()
        self.assertNotIn('titles', model.validate(doc))
        doc['titles'] = [dict(kind='Caption', text="Literal: 50% {x} ' \\ 世界", start=.5, end=2)]
        original = copy.deepcopy(doc)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'timeline.json'
            model.save(doc, path)
            self.assertEqual(model.load(path), original)
        self.assertEqual(doc, original)

    def test_invalid_timing_and_payloads(self):
        valid = dict(kind='Title', text='Hello', start=0, end=1)
        for field, value in [('start', True), ('start', float('nan')), ('end', float('inf')),
                             ('end', 0), ('end', .001), ('end', 601), ('text', ''), ('text', 'x'*241),
                             ('text', '\x00'), ('kind', 'Unknown')]:
            bad = dict(valid); bad[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_titles([bad])
        with self.assertRaises(ValueError): validate_titles([valid], .5)
        with self.assertRaises(ValueError): validate_titles([valid]*33)

    def test_same_lane_overlap_and_boundary(self):
        a = dict(kind='Title', text='Top', start=0, end=1)
        b = dict(kind='Date', text='Next', start=1, end=2)
        validate_titles([a, b])
        b['start'] = .5
        with self.assertRaises(ValueError): validate_titles([a, b])
        b['kind'] = 'Caption'
        validate_titles([a, b])

    def test_cards_fit_both_formats(self):
        for width, height in model.FORMATS.values():
            for kind in ('Title', 'Date', 'Source', 'Caption'):
                image, (x, y) = card(dict(kind=kind, text='Long URL '+('abc/'*55)), width, height)
                self.assertGreater(x, 0); self.assertGreater(y, 0)
                self.assertLessEqual(x+image.width, width)
                self.assertLessEqual(y+image.height, height)
                self.assertLessEqual(image.height, height*.30)


if __name__ == '__main__': unittest.main()
