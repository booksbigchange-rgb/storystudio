"""Frame-exact section durations shared by the editor preview and the exporter.

The exporter renders every section at 24 fps, so a section lasts a whole number of
frames. Using the same rule for the on-screen strip keeps start times and the total
identical to the finished video, however many sections the story has.
"""
import json
import math
from pathlib import Path
import mixed_edit

FPS = 24
_cache = {}


def frames(engine, source):
    """Whole frames a source project renders to, matching mixed_worker's snapshot."""
    scenes = source['scenes']
    if engine == 'documentary':
        total = sum(round(float(s['duration'])*FPS) for s in scenes)
    else:
        total = round(sum(float(s['duration']) for s in scenes)*FPS)
    if not scenes or total <= 0:
        raise ValueError('A section must contain scenes')
    return total


def section_frames(section):
    """Frame count for one section, or None when its source is missing/invalid.

    Cached by file identity so redrawing a 200-section strip does not re-read every file.
    """
    path = Path(section['project'])
    try:
        stat = path.stat()
        key = (str(path), section['engine'], stat.st_mtime_ns, stat.st_size)
        if key in _cache:
            return _cache[key]
        if stat.st_size > 1024*1024:
            raise ValueError('Source too large')
        value = frames(section['engine'], json.loads(path.read_text(encoding='utf-8')))
        if len(_cache) > 2000:
            _cache.clear()
        _cache[key] = value
        return value
    except (OSError, ValueError, KeyError, TypeError):
        return None


def timeline(doc):
    """[(start_frame, frames or None)] per section plus the total frame count.

    Unreadable sections contribute no frames, so the total is a lower bound until fixed.
    """
    sections = doc['sections']
    lengths = []
    for section in sections:
        count = section_frames(section)
        try:
            count = mixed_edit.window(section, count)
            count = count[1]-count[0]
        except (ValueError, TypeError, KeyError):
            count = None  # missing source, or the source shrank below the saved trim
        lengths.append(count)
    rows, cursor = [], 0
    for i, section in enumerate(sections):
        transition = section.get('transition')
        overlap = 0
        if i and transition and transition['kind'] == 'dissolve' and lengths[i] and lengths[i-1]:
            overlap = min(transition['frames'], lengths[i], lengths[i-1])
        cursor -= overlap
        rows.append((cursor, lengths[i]))
        cursor += lengths[i] or 0
    return rows, cursor


def clock(frame_count):
    seconds = frame_count/FPS
    hours, rest = divmod(seconds, 3600)
    minutes, rest = divmod(rest, 60)
    return f'{int(hours)}:{int(minutes):02d}:{rest:05.2f}' if hours else f'{int(minutes)}:{rest:05.2f}'


def estimated_bytes(seconds):
    """Conservative scratch-disk estimate for intermediates, join and optional title pass."""
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Invalid duration')
    return int(seconds*3_000_000)+300_000_000
