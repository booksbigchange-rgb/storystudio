"""Regression coverage for cancellation between mixed export stages.

These tests mock external workers and rendering so they run without FFmpeg or a GUI.
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import mixed_render
from mixed_control import RenderCancelled


class CancelAfterValidation:
    def __init__(self):
        self.calls = 0

    def check(self):
        self.calls += 1
        if self.calls == 2:
            raise RenderCancelled()

    def run(self, *_):
        raise AssertionError('Worker must not start after cancellation')


class MixedStageCancellationTests(unittest.TestCase):
    def test_cancel_before_first_source_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            control = CancelAfterValidation()
            doc = {
                'kind': 'storystudio-mixed', 'version': 1,
                'format': 'widescreen',
                'sections': [{
                    'engine': 'cartoon', 'project': str(Path(folder) / 'source.json'),
                    'name': 'Test scene'
                }]
            }
            output = Path(folder) / 'output.mp4'
            with patch.object(mixed_render, 'project_kind', side_effect=AssertionError('Should not read source')):
                with self.assertRaises(RenderCancelled):
                    mixed_render.export(doc, output, control=control)
            self.assertFalse(output.exists())

    def test_cancel_between_source_snapshots(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            doc = {'kind': 'storystudio-mixed', 'version': 1, 'format': 'widescreen',
                   'sections': [{'engine': 'cartoon', 'project': str(root / f'source-{i}.json'),
                                 'name': f'Scene {i}'} for i in range(2)]}

            class CancelAfterFirstSnapshot:
                def __init__(self):
                    self.calls = 0
                    self.snapshots = 0
                def check(self):
                    self.calls += 1
                    if self.calls == 3:
                        raise RenderCancelled()
                def run(self, command, log):
                    self.snapshots += 1
                    return '{"duration": 1}'

            control = CancelAfterFirstSnapshot()
            with patch.object(mixed_render, 'project_kind', return_value='cartoon'):
                with self.assertRaises(RenderCancelled):
                    mixed_render.export(doc, root / 'video.mp4', control=control)
            self.assertEqual(control.snapshots, 1)
            self.assertFalse((root / 'video.mp4').exists())


    def test_cancel_before_render_after_snapshots(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            doc = {'kind': 'storystudio-mixed', 'version': 1, 'format': 'widescreen',
                   'sections': [{'engine': 'cartoon', 'project': str(root / 'source.json'),
                                 'name': 'Scene'}]}

            class CancelAtRender:
                def __init__(self):
                    self.calls = 0
                    self.snapshots = 0
                def check(self):
                    self.calls += 1
                    # initial, before snapshot, after snapshots, before
                    # expected.json, then before the first render
                    if self.calls == 5:
                        raise RenderCancelled()
                def run(self, command, log):
                    self.snapshots += 1
                    if self.snapshots != 1:
                        raise AssertionError('Render must not start after cancellation')
                    return '{"duration": 1}'

            control = CancelAtRender()
            with patch.object(mixed_render, 'project_kind', return_value='cartoon'):
                with self.assertRaises(RenderCancelled):
                    mixed_render.export(doc, root / 'video.mp4', control=control)
            self.assertEqual(control.snapshots, 1)
            self.assertFalse((root / 'video.mp4').exists())


if __name__ == '__main__':
    unittest.main()
