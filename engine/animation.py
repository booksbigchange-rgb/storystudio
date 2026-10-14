"""Version-1-compatible 2D layer and keyframe calculations.

All coordinates are normalized to stage dimensions. Layer x/y refer to the
center of the sprite; width is a proportion of the stage width.
"""
import math

DEFAULTS = {"x": 0.5, "y": 0.5, "width": 0.3, "scale": 1.0,
            "rotation": 0.0, "opacity": 1.0}
BOUNDS = {"x": (-1.0, 2.0), "y": (-1.0, 2.0),
          "width": (0.02, 1.5), "scale": (0.1, 4.0),
          "rotation": (-360.0, 360.0), "opacity": (0.0, 1.0)}
ANIMATABLE = ("x", "y", "scale", "rotation", "opacity")
EASINGS = ("linear", "smooth", "hold")


def _number(value, name, minimum, maximum):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return result


def validated_layers(layers, duration):
    """Return safe copies; do not mutate a caller's project data."""
    duration = _number(duration, "duration", 0.5, 120.0)
    if not isinstance(layers, list) or len(layers) > 32:
        raise ValueError("Scene layers must be a list of at most 32 items")
    normalized = []
    ids = set()
    for index, raw in enumerate(layers):
        if not isinstance(raw, dict) or not isinstance(raw.get("image"), str) or not raw["image"].strip():
            raise ValueError(f"Layer {index + 1} needs an image path")
        layer = dict(raw)
        layer["id"] = str(raw.get("id", f"layer-{index + 1}"))
        if layer["id"] in ids:
            raise ValueError("Layer IDs must be unique")
        ids.add(layer["id"])
        layer["name"] = str(raw.get("name", f"Layer {index + 1}"))[:100]
        for field, default in DEFAULTS.items():
            lo, hi = BOUNDS[field]
            layer[field] = _number(raw.get(field, default), field, lo, hi)
        frames = raw.get("keyframes", [])
        if not isinstance(frames, list) or len(frames) > 120:
            raise ValueError("Keyframes must be a list of at most 120 items")
        clean = []
        previous = -1.0
        for frame in frames:
            if not isinstance(frame, dict):
                raise ValueError("Keyframe must be an object")
            moment = _number(frame.get("time"), "time", 0.0, duration)
            if moment <= previous:
                raise ValueError("Keyframes must be ordered with unique times")
            previous = moment
            ease = frame.get("ease", "linear")
            if ease not in EASINGS:
                raise ValueError("Unsupported easing; use linear, smooth or hold")
            key = {"time": moment, "ease": ease}
            for field in ANIMATABLE:
                if field in frame:
                    lo, hi = BOUNDS[field]
                    key[field] = _number(frame[field], field, lo, hi)
            clean.append(key)
        layer["keyframes"] = clean
        normalized.append(layer)
    return normalized


def retime_layers(layers, old_duration, new_duration):
    """Preserve animation timing proportions when changing scene duration."""
    old_duration = _number(old_duration, "old duration", 0.5, 120.0)
    new_duration = _number(new_duration, "new duration", 0.5, 120.0)
    result = []
    for layer in validated_layers(layers, old_duration):
        copy = dict(layer)
        copy["keyframes"] = [
            {**key, "time": key["time"] * new_duration / old_duration}
            for key in layer["keyframes"]
        ]
        result.append(copy)
    return validated_layers(result, new_duration)


def layer_state(layer, seconds):
    """Interpolate a validated layer at an animation time in seconds."""
    if not math.isfinite(float(seconds)):
        raise ValueError("Invalid playback time")
    state = {name: layer[name] for name in DEFAULTS}
    for name in ANIMATABLE:
        points = [(0.0, layer[name], "linear")]
        for key in layer.get("keyframes", []):
            if name in key:
                point = (key["time"], key[name], key["ease"])
                if point[0] == points[-1][0]:
                    points[-1] = point
                else:
                    points.append(point)
        if seconds <= points[0][0]:
            state[name] = points[0][1]
            continue
        state[name] = points[-1][1]
        for first, second in zip(points, points[1:]):
            if first[0] <= seconds <= second[0]:
                u = (seconds - first[0]) / (second[0] - first[0])
                if second[2] == "smooth":
                    u = u * u * (3.0 - 2.0 * u)
                elif second[2] == "hold":
                    u = 0.0 if seconds < second[0] else 1.0
                state[name] = first[1] + (second[1] - first[1]) * u
                break
    return state
