"""Pure scene-timeline calculations, independent of desktop UI."""
import math


def scene_ranges(scenes):
    """Return (start, end) seconds for each scene, in sequence."""
    cursor = 0.0
    ranges = []
    for scene in scenes:
        duration = float(scene["duration"])
        if not math.isfinite(duration) or not 0.5 <= duration <= 120:
            raise ValueError("Scene duration must be between 0.5 and 120 seconds")
        ranges.append((cursor, cursor + duration))
        cursor += duration
    return ranges


def total_duration(scenes):
    ranges = scene_ranges(scenes)
    return ranges[-1][1] if ranges else 0.0


def scene_at(scenes, seconds):
    """Find scene index at playhead time; last endpoint maps to final scene."""
    if not scenes:
        return None
    ranges = scene_ranges(scenes)
    seconds = float(seconds)
    if not math.isfinite(seconds) or seconds < 0 or seconds > ranges[-1][1]:
        return None
    for i, (_, end) in enumerate(ranges):
        if seconds < end or i == len(ranges) - 1:
            return i
    return None
