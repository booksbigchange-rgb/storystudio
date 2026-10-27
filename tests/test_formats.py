import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from formats import format_value, output_size
from camera import crop_box
from project import validate_document


class FormatTests(unittest.TestCase):
    def test_formats_are_bounded_and_known(self):
        self.assertEqual(output_size('widescreen'), (1920,1080))
        self.assertEqual(output_size(), (1080,1920))
        for value in [None, {}, [], 'square', 123]:
            with self.assertRaises(ValueError):
                format_value(value)

    def test_legacy_documents_default_to_portrait(self):
        for version in (1,2,3,4):
            self.assertEqual(validate_document({'version':version,'scenes':[]})['format'], 'portrait')
        doc = validate_document({'version':5, 'format':'widescreen', 'scenes':[]})
        self.assertEqual(doc['format'], 'widescreen')

    def test_crop_uses_selected_aspect(self):
        for aspect in (9/16, 16/9):
            left,top,right,bottom = crop_box(1000,1000,dict(zoom=1.5,x=.2,y=.8),aspect=aspect)
            self.assertAlmostEqual((right-left)/(bottom-top),aspect)
            self.assertTrue(0<=left<right<=1000 and 0<=top<bottom<=1000)
