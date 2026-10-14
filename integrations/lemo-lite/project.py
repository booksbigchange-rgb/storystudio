"""Small versioned project format. Loading never changes the source document."""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import tempfile

CHARACTERS = ('fox', 'rabbit', 'bear')
EXPRESSIONS = ('happy', 'curious', 'sad', 'surprised')
ACTIONS = ('story', 'idle', 'wave', 'walk', 'jump', 'talk')
BACKGROUNDS = ('meadow', 'sunset', 'night')
CAMERAS = ('still', 'push-in', 'pull-back', 'pan-left', 'pan-right')
FORMATS = {'Landscape 16:9': (1280, 720), 'Shorts / TikTok 9:16': (720, 1280)}
QUALITIES = {'Standard · 720p / 24 fps': (1, 24), 'Draft · 360p / 12 fps': (.5, 12)}


def new_scene():
    return dict(title='A little magic!', duration=10.0, character='fox',
                expression='happy', action='story', background='meadow', camera='still',
                x=.4, size=1.0, speed=1.0)


def new_project():
    return dict(version=2, name='My cartoon', format='Landscape 16:9',
                quality=next(iter(QUALITIES)), audio=None, scenes=[new_scene()])


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be between {low} and {high}')
    return float(value)


def validate(data):
    if not isinstance(data, dict) or data.get('version') != 2:
        raise ValueError('Expected a StoryStudio version 2 project')
    doc = copy.deepcopy(data)
    if not isinstance(doc.get('name'), str) or not 1 <= len(doc['name']) <= 80:
        raise ValueError('Project name must be 1–80 characters')
    if doc.get('format') not in FORMATS or doc.get('quality') not in QUALITIES:
        raise ValueError('Unsupported format or quality')
    if doc.get('audio') is not None and not isinstance(doc['audio'], str):
        raise ValueError('Audio must be a file path or null')
    scenes = doc.get('scenes')
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 20:
        raise ValueError('Use 1–20 scenes')
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError('Each scene must be an object')
        if not isinstance(scene.get('title'), str) or len(scene['title']) > 60:
            raise ValueError('Scene caption must be at most 60 characters')
        for field, options in [('character', CHARACTERS), ('expression', EXPRESSIONS),
                               ('action', ACTIONS), ('background', BACKGROUNDS)]:
            if scene.get(field) not in options:
                raise ValueError(f'Unsupported {field}')
        if scene.get('camera', 'still') not in CAMERAS:
            raise ValueError('Unsupported camera move')
        for field, low, high in [('duration', 1, 30), ('x', .2, .7),
                                 ('size', .6, 1.25), ('speed', .5, 2)]:
            scene[field] = number(scene.get(field), field, low, high)

        # Optional per-scene animation poses, measured in seconds from scene start.
        # Keep version 2 documents fully compatible with projects saved before
        # keyframes existed. Reject malformed/unsorted keyframes rather than
        # silently changing animation timing on load.
        if 'keyframes' in scene:
            frames = scene['keyframes']
            if not isinstance(frames, list) or len(frames) > 12:
                raise ValueError('Use at most 12 keyframes per scene')
            previous = -1.0
            for frame in frames:
                if not isinstance(frame, dict) or set(frame) != {'t', 'x', 'size'}:
                    raise ValueError('Each keyframe needs t, x and size')
                frame['t'] = number(frame['t'], 'Keyframe time', 0, scene['duration'])
                frame['x'] = number(frame['x'], 'Keyframe position', .2, .7)
                frame['size'] = number(frame['size'], 'Keyframe size', .6, 1.25)
                if frame['t'] <= previous:
                    raise ValueError('Keyframes must have strictly increasing times')
                previous = frame['t']
    if total_duration(doc) > 120:
        raise ValueError('A project can be at most 120 seconds')
    return doc


def total_duration(doc):
    return sum(s['duration'] for s in doc['scenes'])


def dimensions(doc):
    width, height = FORMATS[doc['format']]
    scale, fps = QUALITIES[doc['quality']]
    return int(width * scale), int(height * scale), fps


def load(path):
    path = Path(path).resolve()
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Project file exceeds 1 MB')
    doc = validate(json.loads(path.read_text(encoding='utf-8')))
    if doc['audio']:
        doc['audio'] = str((path.parent / doc['audio']).resolve())
    return doc


def save(doc, path):
    """Atomic save; keep referenced audio relative when on the same drive."""
    doc = validate(doc)
    path = Path(path).resolve()
    if doc['audio'] and Path(doc['audio']).resolve() == path:
        raise ValueError('Project cannot replace source audio')
    path.parent.mkdir(parents=True, exist_ok=True)
    if doc['audio']:
        try:
            # Windows may supply an 8.3 TEMP path; normalize both sides first.
            doc['audio'] = os.path.relpath(Path(doc['audio']).resolve(), path.parent)
        except ValueError:
            pass
    fd, tmp = tempfile.mkstemp(prefix='.story-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(doc, handle, indent=2, ensure_ascii=False, allow_nan=False)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)
