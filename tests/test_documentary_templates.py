import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from documentary_templates import create,validate,load_recipe,KINDS,SIZES
from project import read_project


def recipe(image,kind='Evidence desk',format='widescreen'):
    return dict(kind=kind,format=format,title='A documented sequence',detail='2001 | First event\n2003 | Second event' if kind=='Chronology' else 'User-supplied contextual notes.',source='Synthetic test fixture',image=str(image),seconds=1,focus_x=.25,focus_y=.75)


class TemplatesTests(unittest.TestCase):
    def test_six_layouts_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);image=root/'original.png';Image.new('RGB',(640,480),'#7299b0').save(image)
            digest=hashlib.sha256(image.read_bytes()).hexdigest()
            for kind in KINDS:
                for format in SIZES:
                    spec=recipe(image,kind,format);before=copy.deepcopy(spec)
                    path=create(spec,root/'projects');doc=read_project(path)
                    self.assertEqual(spec,before);self.assertEqual(doc['format'],format)
                    self.assertTrue(3<=len(doc['scenes'][0]['layers'])<=6)
                    for layer in doc['scenes'][0]['layers']:self.assertTrue(Path(layer['image']).is_file())
                    second=create(load_recipe(path.parent/'template.json'),root/'projects')
                    self.assertNotEqual(path,second);self.assertTrue(path.is_file())
            self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(),digest)

    def test_invalid_inputs(self):
        base=recipe('missing.png')
        for key,value in [('title',''),('source',''),('seconds',float('nan')),('focus_x',True),('focus_y',2),('kind','unknown'),('format','square'),('detail','x'*401)]:
            item=dict(base);item[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(item)
        for text in ['no separator','date |','| event','\n'.join(['date | event']*5)]:
            item=recipe('',kind='Chronology');item['detail']=text
            with self.assertRaises(ValueError):validate(item)

    def test_missing_image_never_creates_project(self):
        with tempfile.TemporaryDirectory() as folder:
            parent=Path(folder)/'projects'
            with self.assertRaises(OSError):create(recipe(Path(folder)/'absent.png'),parent)
            self.assertFalse(parent.exists())


if __name__=='__main__':unittest.main()
