"""Seek-safe 2D artwork layers, composited identically for preview and export."""
import math
from pathlib import Path
from camera import camera_at, crop_box, EASINGS

POSE = {'x': .5, 'y': .5, 'size': .4, 'angle': 0., 'opacity': 1.}
MOTION_PRESETS = ('Slow reveal', 'Restrained drift', 'Evidence push')
LIMITS = {'x': (-1, 2), 'y': (-1, 2), 'size': (.01, 3), 'angle': (-720, 720), 'opacity': (0, 1)}


def pose_values(value):
    if not isinstance(value, dict):
        raise ValueError('Layer pose must be an object')
    result = {}
    for key, default in POSE.items():
        number = float(value.get(key, default))
        low, high = LIMITS[key]
        if not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f'Layer {key} must be {low}–{high}')
        result[key] = number
    return result


def layer_values(scene):
    layers = scene.get('layers', [])
    if not isinstance(layers, list) or len(layers) > 8:
        raise ValueError('Use at most eight artwork layers per scene')
    result = []
    for layer in layers:
        if not isinstance(layer, dict) or not isinstance(layer.get('image'), str) or not layer['image']:
            raise ValueError('Each layer needs an image file')
        easing = layer.get('easing', 'smooth')
        if easing not in EASINGS:
            raise ValueError('Invalid layer easing')
        name = layer.get('name', Path(layer['image']).stem)
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError('Layer name must contain 1–80 characters')
        keys = layer.get('keyframes', [])
        if not isinstance(keys, list) or len(keys)>16:
            raise ValueError('Use at most 16 interior keys per layer')
        normalized = []
        previous = 0
        for key in keys:
            if not isinstance(key, dict):
                raise ValueError('Each layer key needs a time and pose')
            t = key.get('t')
            if type(t) not in (int,float) or not math.isfinite(t) or not previous<t<1:
                raise ValueError('Layer keys must have increasing times strictly between 0 and 1')
            normalized.append(dict(t=t, pose=pose_values(key.get('pose'))))
            previous = t
        result.append(dict(image=layer['image'], name=name, easing=easing, keyframes=normalized,
                           start=pose_values(layer.get('start', {})), end=pose_values(layer.get('end', {}))))
    return result


def pose_at(layer, progress):
    t = min(1, max(0, progress))
    points = [dict(t=0,pose=layer['start']), *layer.get('keyframes',[]), dict(t=1,pose=layer['end'])]
    left,right = points[0],points[-1]
    for a,b in zip(points,points[1:]):
        if t<=b['t']:
            left,right=a,b
            break
    t=(t-left['t'])/(right['t']-left['t'])
    easing = layer['easing']
    if easing == 'smooth':
        t = t*t*(3-2*t)
    elif easing == 'ease-in':
        t *= t
    elif easing == 'ease-out':
        t = 1-(1-t)**2
    return {k: left['pose'][k]+(right['pose'][k]-left['pose'][k])*t for k in POSE}


def motion_preset(layer, name):
    """Restrained documentary motion; artwork and factual content stay user-owned."""
    layer = layer_values({'layers': [layer]})[0]
    start = dict(layer['start'])
    end = dict(start)
    if name == 'Slow reveal':
        start['opacity'], end['opacity'] = 0, 1
        end['y'] = max(-1, start['y']-.02)
    elif name == 'Restrained drift':
        end['x'] = min(2, start['x']+.04)
        end['size'] = min(3, start['size']*1.03)
    elif name == 'Evidence push':
        end['size'] = min(3, start['size']*1.12)
    else:
        raise ValueError('Unknown motion preset')
    return dict(layer, start=start, end=end, easing='smooth')


class SceneCompositor:
    def __init__(self, scene, background=None):
        from PIL import Image
        self.scene = scene
        if background is None:
            with Image.open(scene['image']) as image:
                self.background = image.convert('RGB')
        else:
            self.background = background
        self.art = []
        for layer in layer_values(scene):
            with Image.open(layer['image']) as image:
                art = image.convert('RGBA')
                # Bound decoded texture work; original artwork is never changed.
                art.thumbnail((4096, 4096))
            self.art.append((layer, art))

    def frame(self, progress, width, height):
        from PIL import Image
        box = crop_box(*self.background.size, camera_at(self.scene, progress), aspect=width/height)
        canvas = self.background.resize((width, height), Image.Resampling.BICUBIC, box=box).convert('RGBA')
        for layer, art in self.art:
            pose = pose_at(layer, progress)
            if pose['opacity'] <= 0:
                continue
            target_w = max(1, round(width*pose['size']))
            target_h = max(1, round(target_w*art.height/art.width))
            # Tall textures are bounded relative to the output frame as well.
            if target_h > height*4:
                target_w = max(1, round(target_w*(height*4)/target_h))
                target_h = height*4
            sprite = art.resize((target_w, target_h), Image.Resampling.BICUBIC)
            if pose['angle']:
                sprite = sprite.rotate(pose['angle'], resample=Image.Resampling.BICUBIC, expand=True)
            if pose['opacity'] < 1:
                sprite.putalpha(sprite.getchannel('A').point(lambda n: round(n*pose['opacity'])))
            xy = (round(pose['x']*width-sprite.width/2), round(pose['y']*height-sprite.height/2))
            canvas.alpha_composite(sprite, xy)
        return canvas.convert('RGB')
