"""Explicit mixed timeline format. Source projects remain linked and unmodified."""
import copy
import json
import os
from pathlib import Path
import uuid
from mixed_titles import validate_titles
from mixed_audio import validate_audio, map_files

FORMATS = {'widescreen': (1280, 720), 'portrait': (720, 1280)}
MAX_SECTIONS = 200
MAX_SECONDS = 3600


def new_project():
    return dict(kind='storystudio-mixed', version=1, format='widescreen', sections=[])


def validate(doc):
    if not isinstance(doc, dict) or doc.get('kind') != 'storystudio-mixed' or type(doc.get('version')) is not int or doc['version'] != 1:
        raise ValueError('Expected a StoryStudio mixed timeline version 1')
    if doc.get('format') not in FORMATS:
        raise ValueError('Unsupported timeline format')
    sections = doc.get('sections')
    validate_titles(doc.get('titles', []), MAX_SECONDS)
    if not isinstance(sections, list) or len(sections) > MAX_SECTIONS:
        raise ValueError(f'Use at most {MAX_SECTIONS} sections')
    for section in sections:
        if not isinstance(section, dict) or section.get('engine') not in ('documentary', 'cartoon'):
            raise ValueError('Each section needs a supported editor')
        if not isinstance(section.get('project'), str) or not section['project'].strip():
            raise ValueError('Each section needs a source project')
        if not isinstance(section.get('name'), str) or not 1 <= len(section['name']) <= 100:
            raise ValueError('Section name must contain 1–100 characters')
    result = copy.deepcopy(doc)
    if doc.get('audio') is not None:
        result['audio'] = validate_audio(doc['audio'])
    return result


def load(path):
    path = Path(path).resolve()
    if path.stat().st_size > 1024*1024:
        raise ValueError('Timeline exceeds 1 MB')
    doc = validate(json.loads(path.read_text(encoding='utf-8')))
    for section in doc['sections']:
        section['project'] = str((path.parent/section['project']).resolve())
    if doc.get('audio'):
        doc['audio'] = map_files(doc['audio'], lambda name: str((path.parent/name).resolve()))
    return doc


def save(doc, path):
    doc = validate(doc)
    path = Path(path).resolve()
    if any(Path(s['project']).resolve() == path for s in doc['sections']):
        raise ValueError('Timeline cannot replace a source project')
    path.parent.mkdir(parents=True, exist_ok=True)
    for section in doc['sections']:
        try:
            section['project'] = os.path.relpath(Path(section['project']).resolve(), path.parent)
        except ValueError:
            pass
    if doc.get('audio'):
        def relative(name):
            try:
                return os.path.relpath(Path(name).resolve(), path.parent)
            except ValueError:
                return name
        doc['audio'] = map_files(doc['audio'], relative)
    temporary = path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps(doc, indent=2, allow_nan=False), encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def move(doc, index, delta):
    target = index + delta
    if not 0 <= index < len(doc['sections']) or not 0 <= target < len(doc['sections']):
        return index
    doc['sections'].insert(target, doc['sections'].pop(index))
    return target


def move_to(doc, index, target):
    """Move a section to an absolute position (clamped); returns its new index."""
    if not 0 <= index < len(doc['sections']) or not doc['sections']:
        return index
    target = min(max(target, 0), len(doc['sections'])-1)
    doc['sections'].insert(target, doc['sections'].pop(index))
    return target


def duplicate(doc, index):
    """Insert a copy right after ``index``; returns the copy's index."""
    if not 0 <= index < len(doc['sections']):
        return index
    if len(doc['sections']) >= MAX_SECTIONS:
        raise ValueError(f'Use at most {MAX_SECTIONS} sections')
    doc['sections'].insert(index+1, copy.deepcopy(doc['sections'][index]))
    return index+1
