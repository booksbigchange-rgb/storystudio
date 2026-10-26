"""Layered-artwork character packs: a folder of PNG parts plus a declarative rig (no code, no scripts).

A pack lives in ``<library>/<name>/`` with ``rig.json`` and the part PNGs. Scenes select it as ``custom:<name>``.
Safety rules, enforced on load and on import:
  * data only: rig.json is validated JSON, never evaluated; images are plain PNG files inside the pack folder
  * hard limits on parts, image size, total pixels, drivers and every number
  * import copies into a staging folder and renames it into place: it never overwrites an existing pack or your source art
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import uuid

from PIL import Image

KIND, VERSION = 'storystudio-character-rig', 1
NAME = re.compile(r'^[A-Za-z0-9_-]{1,32}$')
PART_ID = re.compile(r'^[a-z0-9_]{1,24}$')
IMAGE = re.compile(r'^[A-Za-z0-9_-]{1,40}\.png$')
MAX_PARTS, MAX_SIDE, MAX_PIXELS, MAX_DRIVERS, MAX_BYTES = 40, 2048, 16_000_000, 8, 50*1024*1024
ACTIONS = ('story', 'idle', 'wave', 'walk', 'jump', 'talk')
EXPRESSIONS = ('happy', 'curious', 'sad', 'surprised')
CHANNELS = ('rotate', 'x', 'y', 'scale')
LIMITS = {'rotate': 6.3, 'x': 500.0, 'y': 500.0, 'scale': 4.0}
TARGET_HEIGHT = 250.0                         # logical units: about the height of the built-in characters
Image.MAX_IMAGE_PIXELS = MAX_PIXELS           # Pillow refuses decompression bombs


def library_dir():
    configured = os.environ.get('STORYSTUDIO_CHARACTERS')
    if configured:
        return Path(configured)
    home = os.environ.get('STORY_STUDIO') or Path(__file__).resolve().parents[2]
    return Path(home)/'projects'/'characters'


def custom_name(character):
    """The pack name for a scene's ``custom:<name>`` character, or None for built-ins."""
    return character[7:] if isinstance(character, str) and character.startswith('custom:') and NAME.match(character[7:]) else None


def _number(value, label, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be a number from {low:g} to {high:g}')
    return float(value)


def validate_rig(rig, images=None):
    """Return a normalized copy of ``rig``; ``images`` ({file: (w, h)}) enables pivot/size checks."""
    if not isinstance(rig, dict) or rig.get('kind') != KIND or rig.get('version') != VERSION:
        raise ValueError('Not a StoryStudio character rig (version 1)')
    name = rig.get('name', '')
    if not isinstance(name, str) or not 1 <= len(name) <= 60 or any(ord(c) < 32 for c in name):
        raise ValueError('Rig name must be 1–60 characters')
    parts = rig.get('parts')
    if not isinstance(parts, list) or not 1 <= len(parts) <= MAX_PARTS:
        raise ValueError(f'Use 1–{MAX_PARTS} parts')
    result = dict(kind=KIND, version=VERSION, name=name, scale=_number(rig.get('scale', 1), 'Scale', .05, 8), parts=[], motion={})
    ids = set()
    for part in parts:
        if not isinstance(part, dict) or set(part) - {'id', 'image', 'pivot', 'at', 'parent', 'z', 'show'}:
            raise ValueError('Each part needs id, image, pivot, at, parent, z and optional show')
        pid = part.get('id')
        if not isinstance(pid, str) or not PART_ID.match(pid) or pid in ids:
            raise ValueError(f'Part id “{pid}” must be unique, 1–24 characters of a–z, 0–9 and _')
        ids.add(pid)
        image = part.get('image')
        if not isinstance(image, str) or not IMAGE.match(image):
            raise ValueError(f'Part “{pid}” needs a PNG file name (letters, digits, _ and -; no folders)')
        item = dict(id=pid, image=image, parent=part.get('parent'), z=_number(part.get('z', 0), f'{pid} z', -1000, 1000),
                    at=[_number(v, f'{pid} position', -2000, 2000) for v in part.get('at', [0, 0])],
                    pivot=[_number(v, f'{pid} pivot', 0, MAX_SIDE) for v in part.get('pivot', [0, 0])])
        if len(item['at']) != 2 or len(item['pivot']) != 2:
            raise ValueError(f'Part “{pid}” position and pivot need two numbers')
        if images is not None:
            if image not in images:
                raise ValueError(f'Part “{pid}” image {image} is missing from the pack')
            width, height = images[image]
            if item['pivot'][0] > width or item['pivot'][1] > height:
                raise ValueError(f'Part “{pid}” pivot lies outside its image')
        show = part.get('show')
        if show is not None:
            if not isinstance(show, dict) or set(show) - {'expression', 'action', 'blink', 'mouth'}:
                raise ValueError(f'Part “{pid}” show rules are not valid')
            checked = {}
            if 'expression' in show:
                if not isinstance(show['expression'], list) or not show['expression'] or any(e not in EXPRESSIONS for e in show['expression']):
                    raise ValueError(f'Part “{pid}” expression list is not valid')
                checked['expression'] = list(show['expression'])
            if 'action' in show:
                if not isinstance(show['action'], list) or not show['action'] or any(a not in ACTIONS for a in show['action']):
                    raise ValueError(f'Part “{pid}” action list is not valid')
                checked['action'] = list(show['action'])
            if 'blink' in show:
                if type(show['blink']) is not bool:
                    raise ValueError(f'Part “{pid}” blink must be true or false')
                checked['blink'] = show['blink']
            if 'mouth' in show:
                if show['mouth'] not in ('open', 'closed'):
                    raise ValueError(f'Part “{pid}” mouth must be open or closed')
                checked['mouth'] = show['mouth']
            item['show'] = checked
        result['parts'].append(item)
    by_id = {p['id']: p for p in result['parts']}
    for p in result['parts']:                              # parents exist and the hierarchy has no loops
        seen, current = set(), p
        while current['parent'] is not None:
            if current['parent'] not in by_id or current['id'] in seen:
                raise ValueError(f'Part “{p["id"]}” has a missing parent or a parent loop')
            seen.add(current['id'])
            current = by_id[current['parent']]
    motion = rig.get('motion', {})
    if not isinstance(motion, dict) or set(motion) - set(ACTIONS):
        raise ValueError('Motion may only define: '+', '.join(ACTIONS))
    for action, drivers in motion.items():
        if not isinstance(drivers, list) or len(drivers) > MAX_DRIVERS:
            raise ValueError(f'Use at most {MAX_DRIVERS} drivers per action')
        checked = []
        for d in drivers:
            if not isinstance(d, dict) or set(d) - {'part', 'channel', 'base', 'amp', 'speed', 'phase'} or d.get('part') not in by_id or d.get('channel') not in CHANNELS:
                raise ValueError(f'A {action} driver needs a known part and channel ({", ".join(CHANNELS)})')
            limit = LIMITS[d['channel']]
            checked.append(dict(part=d['part'], channel=d['channel'], base=_number(d.get('base', 1 if d['channel'] == 'scale' else 0), 'Driver base', -limit, limit),
                                amp=_number(d.get('amp', 0), 'Driver amplitude', -limit, limit), speed=_number(d.get('speed', 0), 'Driver speed', 0, 30),
                                phase=_number(d.get('phase', 0), 'Driver phase', -7, 7)))
        result['motion'][action] = checked
    return result


class Pack:
    """A loaded, validated pack with its sprites decoded once (premultiplied for clean rotation)."""
    def __init__(self, name, rig, sprites):
        self.name, self.rig, self.sprites = name, rig, sprites
        self.order = sorted(rig['parts'], key=lambda p: p['z'])
        self.by_id = {p['id']: p for p in rig['parts']}


def load_pack(name, library=None):
    if not NAME.match(name or ''):
        raise ValueError(f'“{name}” is not a valid character pack name')
    folder = (Path(library) if library else library_dir())/name
    if not (folder/'rig.json').is_file():
        raise FileNotFoundError(f'Character pack “{name}” is missing: {folder}')
    return load_folder(folder, name)


def load_folder(folder, name):
    """Validate and decode a pack folder (also used on the staging copy during import)."""
    folder = Path(folder)
    path = folder/'rig.json'
    if path.stat().st_size > 256*1024:
        raise ValueError('rig.json is larger than 256 KB')
    rig = json.loads(path.read_text(encoding='utf-8'))
    sizes, sprites, pixels = {}, {}, 0
    for part in rig.get('parts', []) if isinstance(rig, dict) else []:
        file = part.get('image') if isinstance(part, dict) else None
        if isinstance(file, str) and IMAGE.match(file) and file not in sizes and (folder/file).is_file():
            with Image.open(folder/file) as image:
                image.verify()
            with Image.open(folder/file) as image:
                if image.format != 'PNG' or max(image.size) > MAX_SIDE:
                    raise ValueError(f'{file} must be a PNG no larger than {MAX_SIDE}×{MAX_SIDE}')
                pixels += image.width*image.height
                if pixels > MAX_PIXELS:
                    raise ValueError('The pack images are too large in total')
                sizes[file] = image.size
                sprites[file] = image.convert('RGBA').convert('RGBa')
    return Pack(name, validate_rig(rig, sizes), sprites)


def list_packs(library=None):
    folder = Path(library) if library else library_dir()
    return sorted(p.name for p in folder.iterdir() if p.is_dir() and NAME.match(p.name) and (p/'rig.json').is_file()) if folder.is_dir() else []


# --- automatic rig from aligned full-canvas layers -----------------------------------------------------------
ROLES = {'body': ('body', 'torso'), 'head': ('head',), 'arm_left': ('arm_left', 'arm_l', 'left_arm'), 'arm_right': ('arm_right', 'arm_r', 'right_arm'),
         'leg_left': ('leg_left', 'leg_l', 'left_leg'), 'leg_right': ('leg_right', 'leg_r', 'right_leg'), 'tail': ('tail',),
         'eyes_open': ('eyes_open', 'eyes'), 'eyes_closed': ('eyes_closed', 'blink'), 'mouth_closed': ('mouth_closed', 'mouth'), 'mouth_open': ('mouth_open',)}
DEFAULT_MOTION = {
    'idle': [dict(part='body', channel='y', base=0, amp=2, speed=2), dict(part='tail', channel='rotate', base=0, amp=.12, speed=4)],
    'wave': [dict(part='arm_right', channel='rotate', base=-2.1, amp=.4, speed=8), dict(part='tail', channel='rotate', base=0, amp=.12, speed=4)],
    'walk': [dict(part='leg_left', channel='rotate', base=0, amp=.35, speed=7), dict(part='leg_right', channel='rotate', base=0, amp=-.35, speed=7),
             dict(part='arm_left', channel='rotate', base=0, amp=-.3, speed=7), dict(part='arm_right', channel='rotate', base=0, amp=.3, speed=7)],
    'talk': [dict(part='head', channel='rotate', base=0, amp=.03, speed=5)],
    'story': [dict(part='arm_right', channel='rotate', base=-.5, amp=.15, speed=3)],
    'jump': [dict(part='arm_left', channel='rotate', base=-.8, amp=0, speed=0), dict(part='arm_right', channel='rotate', base=.8, amp=0, speed=0)],
}


def _role(stem):
    stem = stem.lower()
    for role, names in ROLES.items():
        if stem in names:
            return role
    return None


def auto_rig(folder, name):
    """Build (rig, {file: cropped RGBA image}) from aligned full-canvas PNG layers named by role.

    All layers must share one canvas size (as exported from Krita/Photoshop/GIMP with 'layers to files').
    Each layer is cropped to its visible pixels; pivots come from role (arms/legs at the top, head at the
    bottom, tail at its inner edge) and positions from where the art sits on the canvas.
    """
    folder = Path(folder)
    found = {}
    for path in sorted(folder.glob('*.png')):
        role = _role(path.stem)
        if role:
            found[role] = path
    for needed in ('body', 'head'):
        if needed not in found:
            raise ValueError(f'The folder needs a layer named {needed}.png (found: {", ".join(sorted(found)) or "none"})')
    layers, canvas = {}, None
    for role, path in found.items():
        with Image.open(path) as source:
            if source.format != 'PNG':
                raise ValueError(f'{path.name} is not a PNG')
            if source.width*source.height > MAX_PIXELS or max(source.size) > 8192:
                raise ValueError(f'{path.name} is too large')
            image = source.convert('RGBA')
        canvas = canvas or image.size
        if image.size != canvas:
            raise ValueError(f'{path.name} is {image.width}×{image.height} but the other layers are {canvas[0]}×{canvas[1]}; export every layer at the full canvas size')
        box = image.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox()
        if box is None:
            raise ValueError(f'{path.name} is empty')
        layers[role] = (image.crop(box), box)
    union = [min(b[0] for _, b in layers.values()), min(b[1] for _, b in layers.values()), max(b[2] for _, b in layers.values()), max(b[3] for _, b in layers.values())]
    ground = ((layers['body'][1][0]+layers['body'][1][2])/2, union[3])   # origin: under the body's centre, at the bottom of all the art
    height = union[3]-union[1]
    scale = round(TARGET_HEIGHT/height, 4)
    body_box = layers['body'][1]
    anchors = {'body': ((body_box[0]+body_box[2])/2, (body_box[1]+body_box[3])/2)}

    def pivot_for(role, box):
        cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
        if role == 'head':
            return (cx, box[3])
        if role.startswith(('arm', 'leg')):
            return (cx, box[1])
        if role == 'tail':
            return (box[0] if cx > anchors['body'][0] else box[2], cy)
        return (cx, cy)
    parts, images, z = [], {}, 0
    parents = {'body': None, 'head': 'body', 'arm_left': 'body', 'arm_right': 'body', 'leg_left': 'body', 'leg_right': 'body', 'tail': 'body',
               'eyes_open': 'head', 'eyes_closed': 'head', 'mouth_closed': 'head', 'mouth_open': 'head'}
    draw_order = ['tail', 'leg_left', 'leg_right', 'body', 'arm_left', 'head', 'eyes_open', 'eyes_closed', 'mouth_closed', 'mouth_open', 'arm_right']
    world = {}
    for role in draw_order:
        if role not in layers:
            continue
        image, box = layers[role]
        px, py = pivot_for(role, box)
        world[role] = (px, py)
        file = f'{role}.png'
        images[file] = image
        item = dict(id=role, image=file, pivot=[px-box[0], py-box[1]], parent=parents[role] if parents[role] in layers else 'body' if role != 'body' else None, z=z)
        show = {}
        if role == 'eyes_open':
            show['blink'] = False
        elif role == 'eyes_closed':
            show['blink'] = True
        elif role == 'mouth_closed':
            show['mouth'] = 'closed'
        elif role == 'mouth_open':
            show['mouth'] = 'open'
        if show:
            item['show'] = show
        parts.append(item)
        z += 1
    for item in parts:                                              # position of each pivot in its parent's frame, in canvas pixels
        origin = world[item['parent']] if item['parent'] else ground
        here = world[item['id']]
        item['at'] = [round(here[0]-origin[0], 2), round(here[1]-origin[1], 2)]
        if item['parent'] is None:
            item['at'] = [0, 0]
            item['at'] = [round(here[0]-ground[0], 2), round(here[1]-ground[1], 2)]
    motion = {a: [d for d in drivers if d['part'] in layers] for a, drivers in DEFAULT_MOTION.items()}
    rig = dict(kind=KIND, version=VERSION, name=name, scale=scale, parts=parts, motion={a: d for a, d in motion.items() if d})
    return validate_rig(rig, {f: img.size for f, img in images.items()}), images


# --- importing into the library -----------------------------------------------------------------------------
def import_pack(source, name, library=None):
    """Copy a pack (a folder with rig.json, or aligned layer PNGs) into the library under a new name.

    Never overwrites: an existing name is an error. The pack is built in a staging folder, fully validated by
    loading it, and only then renamed into place. Your source folder is only read.
    """
    if not NAME.match(name or ''):
        raise ValueError('Pack name must be 1–32 characters: letters, digits, _ or -')
    source = Path(source)
    if not source.is_dir():
        raise FileNotFoundError(f'Folder not found: {source}')
    library = Path(library) if library else library_dir()
    target = library/name
    if target.exists():
        raise FileExistsError(f'A character pack named “{name}” already exists; choose another name')
    library.mkdir(parents=True, exist_ok=True)
    staging = library/f'.import-{uuid.uuid4().hex[:8]}'
    staging.mkdir()
    try:
        if (source/'rig.json').is_file():
            total = 0
            for path in [source/'rig.json', *sorted(source.glob('*.png'))]:
                total += path.stat().st_size
                if total > MAX_BYTES:
                    raise ValueError('The pack is larger than 50 MB')
                if path.name != 'rig.json' and not IMAGE.match(path.name):
                    continue                                          # ignore stray files; only valid PNG names are copied
                shutil.copyfile(path, staging/path.name)
        else:
            rig, images = auto_rig(source, name)
            for file, image in images.items():
                image.save(staging/file, 'PNG')
            (staging/'rig.json').write_text(json.dumps(rig, indent=2), encoding='utf-8')
        load_folder(staging, name)                                    # validate exactly as rendering will, before publishing
        os.rename(staging, target)                                    # atomic on one volume; fails if the target appeared meanwhile
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)                    # only our own staging folder
        raise
    return target
