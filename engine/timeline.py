"""Pure scene-timeline calculations, independent of desktop UI."""
import math


def keyframe_target_time(scene, at, seconds, fps=24):
    """Snap a moved interior key to a frame without crossing its neighbors."""
    from camera import keyframe_values
    duration = scene_ranges([scene])[0][1]
    seconds = float(seconds)
    if not math.isfinite(seconds):
        raise ValueError("Keyframe time must be finite")
    points = keyframe_values(scene)
    index = next((i for i, point in enumerate(points) if point["at"] == at), None)
    if index is None:
        raise ValueError("Select an existing intermediate keyframe")
    last = round(duration * fps) - 1
    before = points[index-1]["at"] if index else 0
    after = points[index+1]["at"] if index+1 < len(points) else 1
    first_frame = math.floor(before * last + 1e-9) + 1
    last_frame = math.ceil(after * last - 1e-9) - 1
    if first_frame > last_frame:
        return at
    frame = min(last_frame, max(first_frame, round(seconds * fps)))
    return frame / last


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
