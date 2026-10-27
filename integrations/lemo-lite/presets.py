"""Reusable character presets: a character, look, motion and animation keys kept in one small JSON library.

Presets hold the same fields a scene already has; they never contain artwork, so this is a
convenience for reusing built-in cutout characters, not a custom rig or painterly puppet.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import uuid

import cartoon_project as project

MAX_PRESETS = 50
FIELDS = ('character', 'expression', 'action', 'x', 'size', 'speed')


def preset_from_scene(scene):
    """Validate and copy only the reusable character fields of a scene."""
    probe = project.new_project()
    probe['scenes'] = [{**project.new_scene(), **{k: scene[k] for k in FIELDS if k in scene}, **({'keys': scene['keys']} if scene.get('keys') else {})}]
    checked = project.validate(probe)['scenes'][0]
    result = {k: checked[k] for k in FIELDS}
    if checked.get('keys'):
        result['keys'] = copy.deepcopy(checked['keys'])
    return result


def check_name(name):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40 or any(ord(c) < 32 for c in name):
        raise ValueError('Preset name must be 1–40 characters')
    return name.strip()


def load(path):
    path = Path(path)
    if not path.exists():
        return {}
    if path.stat().st_size > 1024*1024:
        raise ValueError('Preset library exceeds 1 MB')
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('kind') != 'storystudio-character-presets' or data.get('version') != 1 \
            or not isinstance(data.get('presets'), dict) or len(data['presets']) > MAX_PRESETS:
        raise ValueError('Not a StoryStudio character preset library')
    return {check_name(name): preset_from_scene(value) for name, value in data['presets'].items()}


def _write(path, library):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = dict(kind='storystudio-character-presets', version=1, presets=dict(sorted(library.items())))
    temporary = path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save(path, name, scene, replace=False):
    """Add a preset. An existing name is only replaced when ``replace`` is true."""
    name = check_name(name)
    library = load(path)
    if name in library and not replace:
        raise FileExistsError(f'A preset named “{name}” already exists')
    if name not in library and len(library) >= MAX_PRESETS:
        raise ValueError(f'Use at most {MAX_PRESETS} presets')
    library[name] = preset_from_scene(scene)
    _write(path, library)
    return library


def delete(path, name):
    library = load(path)
    if name not in library:
        raise KeyError(name)
    del library[name]
    _write(path, library)
    return library


def apply(scene, preset):
    """New scene with the preset's character settings; caption, length and backdrop are kept."""
    result = copy.deepcopy(scene)
    result.pop('keys', None)
    result.update(copy.deepcopy(preset))
    return result
