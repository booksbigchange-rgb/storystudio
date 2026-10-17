"""Validated project documents and non-destructive persistence."""
import json
import math
import os
import uuid
from pathlib import Path
from layers import layer_values
from formats import format_value
from camera import camera_values, easing_value, keyframe_values


def audio_values(audio):
    if audio is None:
        return None
    if not isinstance(audio, dict) or not isinstance(audio.get("path"), str) or not audio["path"]:
        raise ValueError("Audio must contain a file path")
    result = {"path": audio["path"]}
    if not isinstance(audio.get('repeat', False), bool):
        raise ValueError('Audio repeat must be true or false')
    result['repeat'] = audio.get('repeat', False)
    for key, default, low, high in (("volume", 1, 0, 2), ("offset", 0, 0, 86400),
                                    ("trim", 0, 0, 86400), ("fade", 0, 0, 30)):
        value = float(audio.get(key, default))
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Audio {key} must be {low}–{high}")
        result[key] = value
    return result


def validate_document(data):
    if not isinstance(data, dict) or data.get("version") not in (1, 2, 3, 4, 5) or not isinstance(data.get("scenes"), list):
        raise ValueError("Unsupported project format")
    scenes = []
    for scene in data["scenes"]:
        if not isinstance(scene, dict) or not isinstance(scene.get("image"), str) or not scene["image"]:
            raise ValueError("Each scene needs an image path")
        duration = float(scene["duration"])
        if not math.isfinite(duration) or not .5 <= duration <= 120:
            raise ValueError("Scene duration must be 0.5–120 seconds")
        scenes.append({"image": scene["image"], "duration": round(duration * 24) / 24,
                       **camera_values(scene), "easing": easing_value(scene),
                       "keyframes": keyframe_values(scene), "layers": layer_values(scene)})
    return {"version": 5, "format": format_value(data.get('format', 'portrait')), "scenes": scenes, "audio": audio_values(data.get("audio")), "music": audio_values(data.get("music"))}


def read_project(path):
    path = Path(path).resolve()
    doc = validate_document(json.loads(path.read_text(encoding="utf-8")))
    for scene in doc["scenes"]:
        scene["image"] = str((path.parent / scene["image"]).resolve())
        for layer in scene["layers"]:
            layer["image"] = str((path.parent / layer["image"]).resolve())
    for track in (doc["audio"], doc["music"]):
        if track:
            track["path"] = str((path.parent / track["path"]).resolve())
    return doc


def write_project(path, scenes, audio=None, music=None, output_format='portrait'):
    path = Path(path).resolve()
    doc = validate_document({"version": 5, "format": output_format, "scenes": scenes, "audio": audio, "music": music})
    path.parent.mkdir(parents=True, exist_ok=True)
    # Relative media links survive moving a project and its assets together.
    for item, key in [(s, "image") for s in doc["scenes"]] + [(layer, "image") for s in doc["scenes"] for layer in s["layers"]] + [(t, "path") for t in (doc["audio"], doc["music"]) if t]:
        try:
            item[key] = os.path.relpath(Path(item[key]).resolve(), path.parent)
        except ValueError:  # Different Windows volumes.
            pass
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
