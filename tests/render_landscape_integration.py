"""Small landscape Fit render test, with and without an animated sprite."""
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
    with tempfile.TemporaryDirectory(prefix="storystudio-landscape-") as path:
        root = Path(path)
        desktop_app.TEMP = root / "tmp"
        desktop_app.TEMP.mkdir()
        source = root / "portrait.png"
        ball = root / "sprite.png"
        Image.new("RGB", (90, 160), (220, 90, 30)).save(source)
        Image.new("RGBA", (30, 30), (0, 220, 0, 255)).save(ball)
        frames = [{"image": str(source), "duration": 0.5},
                  {"image": str(source), "duration": 0.5, "layers": [
                      {"image": str(ball), "id": "ball", "width": 0.3,
                       "keyframes": [{"time": 0.5, "x": 0.75}]}
                  ]}]
        fitted = render_scene_frame(frames[1], 0, 160, 90, fit="fit")
        assert fitted.getpixel((1, 1)) == (20, 24, 32), "Fit matte is missing"
        filled = render_scene_frame(frames[1], 0, 160, 90, fit="fill")
        assert filled.getpixel((1, 1)) == (220, 90, 30), "Fill must crop edge to edge"
        target = root / "landscape.mp4"
        desktop_app.render_scenes(
            frames, target, canvas={"width": 160, "height": 90, "fit": "fit"})
        probe = subprocess.run(["ffprobe", "-v", "error", "-of", "json",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height:format=duration", str(target)],
            capture_output=True, text=True, check=True)
        result = json.loads(probe.stdout)
        assert result["streams"][0]["width"] == 160
        assert result["streams"][0]["height"] == 90
        assert result["streams"][0]["codec_name"] == "h264"
        assert 0.9 <= float(result["format"]["duration"]) <= 1.1
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(target),
                        "-f", "null", "-"], capture_output=True, text=True, check=True)
        print("PASS: landscape canvas, fitted still + animated layer, decoded MP4")


if __name__ == "__main__":
    main()
