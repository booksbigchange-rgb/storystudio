import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from layers import layer_values, pose_at, motion_preset


class LayerTests(unittest.TestCase):
    def test_validated_endpoint_interpolation_is_seek_safe(self):
        layer = layer_values({'layers':[dict(image='art.png', start={'x':.1, 'opacity':0},
                                            end={'x':.9, 'opacity':1}, easing='linear')]})[0]
        self.assertAlmostEqual(pose_at(layer, .5)['x'], .5)
        self.assertEqual(pose_at(layer, 0)['opacity'], 0)
        self.assertEqual(pose_at(layer, 1)['opacity'], 1)
        self.assertEqual(pose_at(layer, .3), pose_at(layer, .3))

    def test_invalid_layers_rejected(self):
        for value in [None, {}, [None], [{'image':''}], [{'image':'a', 'start':{'angle':float('nan')}}],
                      [{'image':'a','end':{'size':0}}], [{'image':'a','easing':'unknown'}], [{'image':'a'}]*9]:
            with self.assertRaises((ValueError, TypeError)):
                layer_values({'layers':value})

    def test_legacy_scene_has_no_layers(self):
        self.assertEqual(layer_values({}), [])

    def test_documentary_presets_preserve_source_and_bounds(self):
        original = layer_values({'layers':[dict(image='evidence.png', start={'size':3, 'x':2, 'y':-1})]})[0]
        for name in ('Slow reveal', 'Restrained drift', 'Evidence push'):
            preset = motion_preset(original, name)
            self.assertEqual(preset['image'], original['image'])
            self.assertEqual(layer_values({'layers':[preset]})[0], preset)
        self.assertEqual(motion_preset(original, 'Slow reveal')['start']['opacity'], 0)
        self.assertEqual(original['start']['opacity'], 1)
