import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
import mixed_project as model
from studio_hub import project_kind


class MixedTests(unittest.TestCase):
    def test_save_relative_roundtrip_and_protect_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'source.json'
            source.write_text('ORIGINAL')
            doc = model.new_project()
            doc['sections'] = [dict(engine='cartoon', project=str(source), name='Character')]
            path = Path(folder)/'mixed.json'
            model.save(doc,path)
            self.assertEqual(json.loads(path.read_text())['sections'][0]['project'],'source.json')
            self.assertEqual(model.load(path), doc)
            self.assertEqual(project_kind(path),'mixed')
            with self.assertRaises(ValueError):model.save(doc,source)
            self.assertEqual(source.read_text(),'ORIGINAL')

    def test_order_and_bounds(self):
        doc = model.new_project()
        doc['sections'] = [dict(engine='cartoon',project='a.json',name='A'),dict(engine='documentary',project='b.json',name='B')]
        self.assertEqual(model.move(doc,0,-1),0)
        self.assertEqual(model.move(doc,0,1),1)
        self.assertEqual([s['name'] for s in doc['sections']],['B','A'])

    def test_validation_no_mutation_and_bad_versions(self):
        doc = model.new_project()
        result = model.validate(doc)
        result['sections'].append({})
        self.assertEqual(doc['sections'],[])
        for field,value in [('version',True),('version',2),('format','square'),('sections',[{}]),('kind','unknown')]:
            bad = copy.deepcopy(doc);bad[field]=value
            with self.assertRaises(ValueError):model.validate(bad)


if __name__ == '__main__':unittest.main()
