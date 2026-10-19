"""Pure helpers for animating horizontal character positions over time."""
from __future__ import annotations


def position_at(time: float, duration: float, base_x: float, keyframes: list[dict]) -> float:
    """Return a clamped horizontal position, interpolating between time-sorted keys.

    With no keyframes, preserve the scene's existing static position.
    Before the first key and after the last key, hold the nearest keyed value.
    """
    if not keyframes:
        return base_x
    keys = sorted(keyframes, key=lambda item: item["time"])
    if time <= keys[0]["time"]:
        return keys[0]["x"]
    if time >= keys[-1]["time"]:
        return keys[-1]["x"]
    for left, right in zip(keys, keys[1:]):
        if left["time"] <= time <= right["time"]:
            span = right["time"] - left["time"]
            if span <= 0:
                return right["x"]
            amount = (time - left["time"]) / span
            return left["x"] + (right["x"] - left["x"]) * amount
    return base_x
