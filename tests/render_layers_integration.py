"""Small, automated layered-render test; CI installs Pillow and FFmpeg."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import desktop_app
from layer_render import render_scene_frame


def main():
    with tempfile.TemporaryDirectory(prefix="storystudio-layers-") as directory:
        root = Path(directory)
        desktop_app.TEMP = root / "tmp"
        desktop_app.TEMP.mkdir()
        desktop_app.WIDTH, desktop_app.HEIGHT = 160, 288
        background = root / "background.png"
        sprite = root / "sprite.png"
        Image.new("RGB", (160, 288), (15, 35, 55)).save(background)
        artwork = Image.new("RGBA", (40, 60), (0, 0, 0, 0))
        ImageDraw.Draw(artwork).ellipse((4, 4, 36, 56), fill=(240, 100, 40, 255))
        artwork.save(sprite)
        scene = {"image": str(background), "duration": 1.0,
                 "zoom_start": 1, "zoom_end": 1, "layers": [{
                     "image": str(sprite), "id": "hero", "width": 0.2,
                     "x": 0.2, "y": 0.5,
                     "keyframes": [{"time": 1, "x": 0.8}]
                 }]}
        a = render_scene_frame(scene, 0, 160, 288)
        b = render_scene_frame(scene, 1, 160, 288)
        if a.tobytes() == b.tobytes():
            raise AssertionError("Character did not move between keyframes")
        output = root / "movie.mp4"
        # Mix layered and old-format still image scenes in the existing exporter.
        desktop_app.render_scenes([scene, {"image": str(background), "duration": 0.5}], output)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "format=duration:stream=codec_name,width,height",
             "-of", "json", str(output)],
            check=True, capture_output=True, text=True)
        payload = json.loads(probe.stdout)
        video = payload["streams"][0]
        assert video["codec_name"] == "h264", video
        assert (video["width"], video["height"]) == (160, 288), video
        assert 1.4 <= float(payload["format"]["duration"]) <= 1.6, payload
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"],
                       check=True, capture_output=True, text=True)
        print("PASS: keyframed layered character + legacy scene export, 1.5s H.264 decoded")


if __name__ == "__main__":
    main()
