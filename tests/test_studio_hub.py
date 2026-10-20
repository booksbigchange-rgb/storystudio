import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from studio_hub import project_kind, command


class HubTests(unittest.TestCase):
    def classify(self, doc):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'project.json'
            raw = json.dumps(doc)
            path.write_text(raw, encoding='utf-8')
            try:
                return project_kind(path)
            finally:
                self.assertEqual(path.read_text(encoding='utf-8'), raw)

    def test_overlapping_version_two(self):
        self.assertEqual(self.classify({'version':2, 'scenes':[{'image':'a.png'}]}), 'documentary')
        self.assertEqual(self.classify({'version':2, 'scenes':[{'character':'fox'}]}), 'cartoon')

    def test_reject_mixed_and_future_without_writing(self):
        for doc in ({'version':2,'scenes':[{'image':'a'}, {'character':'fox'}]},
                    {'version':6,'scenes':[{'image':'a'}]},
                    {'version':2,'scenes':[{'image':'a','character':'fox'}]}):
            with self.assertRaises(ValueError):
                self.classify(doc)

    def test_empty_documentary(self):
        self.assertEqual(self.classify({'version':5,'scenes':[]}), 'documentary')

    def test_path_is_argument_not_shell_code(self):
        result = command('cartoon', 'space & name.json')
        self.assertEqual(result[-2], '--project')
        self.assertTrue(result[-1].endswith('space & name.json'))


if __name__ == '__main__':
    unittest.main()
