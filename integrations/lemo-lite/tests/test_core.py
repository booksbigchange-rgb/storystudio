import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import project
import renderer


class ProjectTests(unittest.TestCase):
    def test_default_and_dimensions(self):
        doc=project.validate(project.new_project())
        self.assertEqual(project.dimensions(doc),(1280,720,24))
        doc['format']='Shorts / TikTok 9:16'
        self.assertEqual(project.dimensions(doc),(720,1280,24))
        doc['quality']=list(project.QUALITIES)[1]
        self.assertEqual(project.dimensions(doc),(360,640,12))

    def test_validation_does_not_mutate(self):
        doc=project.new_project();original=copy.deepcopy(doc)
        validated=project.validate(doc);validated['scenes'][0]['title']='Changed'
        self.assertEqual(doc,original)

    def test_invalid_scene_fields(self):
        for key,value in [('duration',float('nan')),('duration',float('inf')),('duration',0),
                          ('duration',True),('speed',8),('x',-1),('size',5),('character','unknown'),
                          ('expression','angry'),('title','x'*61),('action',None),('background','bad')]:
            with self.subTest(key=key,value=value):
                doc=project.new_project();doc['scenes'][0][key]=value
                with self.assertRaises(ValueError):project.validate(doc)

    def test_resource_limits(self):
        for count in (0,21):
            doc=project.new_project();doc['scenes']=[project.new_scene() for _ in range(count)]
            with self.assertRaises(ValueError):project.validate(doc)
        doc=project.new_project();doc['scenes']=[project.new_scene() for _ in range(13)]
        with self.assertRaises(ValueError):project.validate(doc)

    def test_round_trip_relative_audio(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);audio=folder/'voice.wav';audio.write_bytes(b'original')
            doc=project.new_project();doc['audio']=str(audio);doc['scenes'][0]['title']='A fox & a star!'
            path=folder/'story.json';project.save(doc,path)
            self.assertEqual(json.loads(path.read_text())['audio'],'voice.wav')
            self.assertEqual(project.load(path),project.validate(doc))
            self.assertEqual(audio.read_bytes(),b'original')

    def test_failed_save_preserves_original(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'story.json';project.save(project.new_project(),path);original=path.read_bytes()
            doc=project.new_project();doc['scenes'][0]['duration']=0
            with self.assertRaises(ValueError):project.save(doc,path)
            self.assertEqual(path.read_bytes(),original)
            with patch('project.os.replace',side_effect=PermissionError('test')):
                with self.assertRaises(PermissionError):project.save(project.new_project(),path)
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(list(Path(td).glob('.story-*')),[])

    def test_bad_format_and_oversized_document(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'bad.json';path.write_text('{"version":1}')
            with self.assertRaises(ValueError):project.load(path)
            path.write_bytes(b'x'*(1024*1024+1))
            with self.assertRaises(ValueError):project.load(path)


class RendererTests(unittest.TestCase):
    def args(self,**kwargs):
        return argparse.Namespace(**(dict(width=640,height=360,fps=12,duration=2,output='unused.mp4',overwrite=False,audio=None)|kwargs))

    def test_bad_render_parameters(self):
        for kwargs in [dict(width=0),dict(width=641),dict(width=4000),dict(height=1),dict(fps=0),
                       dict(duration=float('nan')),dict(duration=.001),dict(duration=20),dict(width=640.0)]:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):renderer.validate_args(self.args(**kwargs),project.new_project())

    def test_pre_cancelled_does_not_touch_output(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'existing.mp4';out.write_bytes(b'KEEP')
            event=threading.Event();event.set()
            with self.assertRaises(renderer.Cancelled):renderer.export(self.args(output=str(out),overwrite=True),cancel=event)
            self.assertEqual(out.read_bytes(),b'KEEP')

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'existing.mp4';out.write_bytes(b'KEEP')
            with patch('renderer.find_ffmpeg',return_value='ffmpeg'),patch('renderer.find_ffprobe',return_value='ffprobe'):
                with self.assertRaises(FileExistsError):renderer.export(self.args(output=str(out)))
            self.assertEqual(out.read_bytes(),b'KEEP')

    def test_override_must_exist(self):
        with patch.dict('os.environ',{'STORYSTUDIO_FFMPEG':'missing.exe'}):
            with self.assertRaises(RuntimeError):renderer.find_ffmpeg()

    def test_server_restricts_files(self):
        with renderer.local_server() as url:
            base=url.split('/scene/')[0]
            self.assertEqual(json.load(urllib.request.urlopen(base+'/project.json'))['version'],2)
            for path in ['/renderer.py','/','/scene/../project.py','/vendor/']:
                with self.subTest(path=path):
                    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+path)


if __name__=='__main__':unittest.main()
