"""Validated start/end camera keyframes for still-image scenes.

The FFmpeg zoompan filter uses output-frame index 'on' for interpolation.
Coordinates are normalized crop positions: 0=left/top, 1=right/bottom.
"""
import math

DEFAULT = {"zoom_start": 1.0, "zoom_end": 1.08,
           "x_start": 0.5, "x_end": 0.5,
           "y_start": 0.5, "y_end": 0.5}


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
    def lerp(start, end):
        return f"({values[start]:.6f}+({values[end]:.6f}-{values[start]:.6f})*{t})"
    zoom = lerp("zoom_start", "zoom_end")
    x = lerp("x_start", "x_end")
    y = lerp("y_start", "y_end")
    return (
        f"zoompan=z='{zoom}':"
        f"x='(iw-iw/zoom)*{x}':"
        f"y='(ih-ih/zoom)*{y}':"
        f"d=1:s={width}x{height}:fps={fps}"
    )
