"""CPU-friendly, per-frame 2D sprite compositing for animated scenes.

Still-image scenes continue to use the existing FFmpeg zoompan path.
Pillow is needed only when a scene actually contains character layers.
"""
import math
import subprocess
from pathlib import Path

from animation import layer_state, validated_layers
from camera import camera_values


def render_scene_frame(scene, seconds, width, height):
    """Return a Pillow RGB frame; preview and export use this same function."""
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Pillow is required for character layers") from exc

    duration = float(scene["duration"])
    if not math.isfinite(seconds) or seconds < 0 or seconds > duration:
        raise ValueError("Playback time is outside the scene")
    if width < 1 or height < 1:
        raise ValueError("Invalid frame dimensions")
    layers = validated_layers(scene.get("layers", []), duration)
    with Image.open(scene["image"]) as background:
        stage = ImageOps.fit(background.convert("RGBA"), (width, height),
                             method=Image.Resampling.LANCZOS)
    for layer in layers:
        state = layer_state(layer, seconds)
        with Image.open(layer["image"]) as source:
            sprite = source.convert("RGBA")
        target_width = max(1, round(width * state["width"] * state["scale"]))
        target_height = max(1, round(target_width * sprite.height / sprite.width))
        # Prevent oversized source artwork from exhausting RAM on small PCs.
        reduction = min(1.0, (2 * width) / target_width, (2 * height) / target_height)
        if reduction < 1.0:
            target_width = max(1, round(target_width * reduction))
            target_height = max(1, round(target_height * reduction))
        sprite = sprite.resize((target_width, target_height), Image.Resampling.LANCZOS)
        if state["opacity"] != 1:
            alpha = sprite.getchannel("A").point(lambda a: round(a * state["opacity"]))
            sprite.putalpha(alpha)
        if state["rotation"]:
            sprite = sprite.rotate(-state["rotation"], Image.Resampling.BICUBIC, expand=True)
        left = round(state["x"] * width - sprite.width / 2)
        top = round(state["y"] * height - sprite.height / 2)
        # Crop first: Pillow's alpha_composite destination must be nonnegative.
        x1, y1 = max(0, left), max(0, top)
        x2, y2 = min(width, left + sprite.width), min(height, top + sprite.height)
        if x2 > x1 and y2 > y1:
            visible = sprite.crop((x1 - left, y1 - top, x2 - left, y2 - top))
            stage.alpha_composite(visible, (x1, y1))
    camera = camera_values(scene)
    u = seconds / duration
    zoom = camera["zoom_start"] + (camera["zoom_end"] - camera["zoom_start"]) * u
    pos_x = camera["x_start"] + (camera["x_end"] - camera["x_start"]) * u
    pos_y = camera["y_start"] + (camera["y_end"] - camera["y_start"]) * u
    crop_w, crop_h = max(1, round(width / zoom)), max(1, round(height / zoom))
    left = round((width - crop_w) * pos_x)
    top = round((height - crop_h) * pos_y)
    return stage.crop((left, top, left + crop_w, top + crop_h)).resize(
        (width, height), Image.Resampling.LANCZOS
    ).convert("RGB")


def render_layer_segment(scene, target, ffmpeg, width, height, fps):
    """Stream raw frames to the existing FFmpeg encoder; never cache frames."""
    duration = float(scene["duration"])
    validated_layers(scene.get("layers", []), duration)
    if not Path(scene["image"]).is_file():
        raise FileNotFoundError(scene["image"])
    for layer in scene["layers"]:
        if not Path(layer["image"]).is_file():
            raise FileNotFoundError(layer["image"])
    frames = round(duration * fps)
    if frames < 1:
        raise ValueError("Scene must contain at least one frame")
    cmd = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
           "-r", str(fps), "-i", "pipe:0", "-frames:v", str(frames),
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-pix_fmt", "yuv420p", str(target)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            for frame in range(frames):
                moment = duration * frame / max(1, frames - 1)
                frame_bytes = render_scene_frame(scene, moment, width, height).tobytes()
                process.stdin.write(frame_bytes)
        except BrokenPipeError:
            pass
        finally:
            process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        status = process.wait()
        if status:
            raise subprocess.CalledProcessError(status, cmd, stderr=stderr)
