"""Validated camera keyframes for still-image scenes.

The FFmpeg zoompan filter uses output-frame index 'on' for interpolation.
Coordinates are normalized crop positions: 0=left/top, 1=right/bottom.
"""
import math

DEFAULT = {"zoom_start": 1.0, "zoom_end": 1.08,
           "x_start": 0.5, "x_end": 0.5,
           "y_start": 0.5, "y_end": 0.5}

EASINGS = ("linear", "smooth", "ease-in", "ease-out")
MAX_INTERIOR_KEYS = 16


def keyframe_values(scene):
    """Interior times are normalized, so duration edits preserve their ordering."""
    frames = scene.get("keyframes", [])
    if not isinstance(frames, list) or len(frames) > MAX_INTERIOR_KEYS:
        raise ValueError(f"Use at most {MAX_INTERIOR_KEYS} intermediate camera keyframes")
    result = []
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("Invalid camera keyframe")
        at = float(frame.get("at", -1))
        if not math.isfinite(at) or not 0 < at < 1:
            raise ValueError("Intermediate keyframes must be between start and end")
        values = camera_values({key+"_start": frame.get(key) for key in ("zoom", "x", "y")})
        result.append({"at": at, **{key: values[key+"_start"] for key in ("zoom", "x", "y")}})
    result.sort(key=lambda point: point["at"])
    if any(b["at"]-a["at"] < 1e-6 for a, b in zip(result, result[1:])):
        raise ValueError("Camera keyframe times must be distinct")
    return result


def camera_sequence(scene):
    values = camera_values(scene)
    return ([{"at": 0.0, **{key: values[key+"_start"] for key in ("zoom", "x", "y")}}]
            + keyframe_values(scene)
            + [{"at": 1.0, **{key: values[key+"_end"] for key in ("zoom", "x", "y")}}])


def easing_value(scene):
    value = scene.get("easing", "linear")
    if value not in EASINGS:
        raise ValueError("Choose linear, smooth, ease-in or ease-out easing")
    return value


def camera_at(scene, progress):
    """Same interpolation as the exported animation, independent of seeking order."""
    t = max(0.0, min(float(progress), 1.0))
    sequence = camera_sequence(scene)
    left, right = sequence[-2:]
    for first, second in zip(sequence, sequence[1:]):
        if t <= second["at"]:
            left, right = first, second
            break
    t = (t-left["at"]) / (right["at"]-left["at"])
    easing = easing_value(scene)
    if easing == "smooth":
        t = t * t * (3 - 2 * t)
    elif easing == "ease-in":
        t *= t
    elif easing == "ease-out":
        t = 1 - (1 - t) ** 2
    return {key: left[key] + (right[key] - left[key]) * t
            for key in ("zoom", "x", "y")}


def crop_box(width, height, camera, aspect=9 / 16):
    """Center-fill crop followed by camera crop, matching the render pipeline."""
    base_w, base_h = min(width, height * aspect), min(height, width / aspect)
    crop_w, crop_h = base_w / camera["zoom"], base_h / camera["zoom"]
    left = (width - base_w) / 2 + (base_w - crop_w) * camera["x"]
    top = (height - base_h) / 2 + (base_h - crop_h) * camera["y"]
    return left, top, left + crop_w, top + crop_h


def camera_values(scene):
    result = {}
    for key, fallback in DEFAULT.items():
        value = float(scene.get(key, fallback))
        if not math.isfinite(value):
            raise ValueError(f"Camera {key} must be finite")
        if key.startswith("zoom"):
            if not 1.0 <= value <= 2.0:
                raise ValueError(f"Camera {key} must be 1.0–2.0")
        elif not 0.0 <= value <= 1.0:
            raise ValueError(f"Camera {key} must be 0.0–1.0")
        result[key] = value
    return result


def zoompan_filter(scene, frames, width, height, fps):
    """Build safe zoompan expressions from validated numeric keyframes."""
    if frames < 1:
        raise ValueError("At least one frame is required")
    values = camera_values(scene)
    last = max(frames - 1, 1)
    t = f"min(on/{last},1)"
    easing = easing_value(scene)
    if easing == "smooth":
        t = f"({t}*{t}*(3-2*{t}))"
    elif easing == "ease-in":
        t = f"({t}*{t})"
    elif easing == "ease-out":
        t = f"(1-(1-{t})*(1-{t}))"
    def lerp(start, end):
        return f"({values[start]:.6f}+({values[end]:.6f}-{values[start]:.6f})*{t})"
    zoom = lerp("zoom_start", "zoom_end")
    x = lerp("x_start", "x_end")
    y = lerp("y_start", "y_end")
    if keyframe_values(scene):
        sequence = camera_sequence(scene)
        raw = f"min(on/{last},1)"
        def expression(key):
            result = f"{sequence[-1][key]:.9g}"
            for left, right in reversed(list(zip(sequence, sequence[1:]))):
                local = f"(({raw}-{left['at']:.9g})/{right['at']-left['at']:.9g})"
                if easing == "smooth":
                    local = f"({local}*{local}*(3-2*{local}))"
                elif easing == "ease-in":
                    local = f"({local}*{local})"
                elif easing == "ease-out":
                    local = f"(1-(1-{local})*(1-{local}))"
                segment = f"({left[key]:.9g}+({right[key]-left[key]:.9g})*{local})"
                result = f"if(lt({raw},{right['at']:.9g}),{segment},{result})"
            return result
        zoom, x, y = (expression(key) for key in ("zoom", "x", "y"))
    return (
        f"zoompan=z='{zoom}':"
        f"x='(iw-iw/zoom)*{x}':"
        f"y='(ih-ih/zoom)*{y}':"
        f"d=1:s={width}x{height}:fps={fps}"
    )
