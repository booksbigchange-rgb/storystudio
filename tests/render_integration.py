"""End-to-end StoryStudio FFmpeg test with generated local images.

Uses only Python standard library and the FFmpeg/FFprobe on PATH.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import desktop_app


def make_ppm(path, rgb):
    width, height = 24, 24
    path.write_bytes(
        f"P6\n{width} {height}\n255\n".encode("ascii")
        + bytes(rgb) * (width * height)
    )


def main():
    with tempfile.TemporaryDirectory(prefix="storystudio-ci-") as folder:
        root = Path(folder)
        desktop_app.TEMP = root / "temp"
        desktop_app.TEMP.mkdir()
        # Small output makes this end-to-end smoke test inexpensive.
        desktop_app.WIDTH = 160
        desktop_app.HEIGHT = 288
        first, second = root / "first.ppm", root / "second.ppm"
        make_ppm(first, (220, 45, 65))
        make_ppm(second, (30, 120, 210))
        output = root / "story.mp4"
        desktop_app.render_scenes(
            [
                {"image": str(first), "duration": 0.5,
                 "zoom_start": 1.0, "zoom_end": 1.3,
                 "x_start": 0.0, "x_end": 1.0,
                 "y_start": 0.0, "y_end": 1.0},
                {"image": str(second), "duration": 0.5},
            ],
            output,
        )
        if not output.is_file() or output.stat().st_size == 0:
            raise AssertionError("MP4 not created")
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration:stream=codec_name,width,height",
                "-select_streams", "v:0", "-of", "json", str(output)
            ],
            capture_output=True, text=True, check=True
        )
        data = json.loads(probe.stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
        assert stream["codec_name"] == "h264", stream
        assert (stream["width"], stream["height"]) == (160, 288), stream
        assert 0.9 <= duration <= 1.1, duration
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"],
            check=True, capture_output=True, text=True,
        )
        print("PASS: two scenes rendered, H.264 160x288, 1s, decoded successfully")


if __name__ == "__main__":
    main()
