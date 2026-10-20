"""Real 1080p MP4/audio acceptance; keeps synthetic evidence in a new folder."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import numpy as np
from PIL import Image, ImageDraw
import soundfile as sf
import desktop_app as base
from camera import EASINGS, camera_at, crop_box
from narration import generate


def main():
    folder = base.ROOT / "exports" / ("acceptance-"+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    y, x = np.mgrid[0:640, 0:360]
    pixels = np.stack((30+x*200//360, 30+y*200//640, np.full_like(x, 110)), axis=2).astype("uint8")
    image = Image.fromarray(pixels)
    draw = ImageDraw.Draw(image)
    for v in range(0, 640, 80):
        draw.line((0, v, 360, v), fill="white", width=2)
    for u in range(0, 360, 60):
        draw.line((u, 0, u, 640), fill="white", width=2)
    path = folder / "camera-grid.png"
    image.save(path)
    scenes = [{"image": str(path), "duration": 1, "zoom_start": 1, "zoom_end": 2,
               "x_start": 0, "x_end": 1, "y_start": 0, "y_end": 1, "easing": easing,
               "keyframes": [{"at": .3, "zoom": 1.8, "x": .8, "y": .2},
                             {"at": .65, "zoom": 1.25, "x": .2, "y": .8}]} for easing in EASINGS]
    narration = folder / "narration.wav"
    metadata = generate("Story Studio brings your pictures to life.", narration)
    samples, rate = sf.read(narration)
    assert len(samples)/rate > 1 and np.max(np.abs(samples)) > .01
    output = folder / "camera-and-narration.mp4"
    base.render_scenes(scenes, output, print, audio={"path": str(narration), "offset": .4, "volume": .6, "fade": .1})
    binary = base.ffmpeg_binary()
    ffprobe = str(Path(binary).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe"))
    probe = json.loads(subprocess.check_output([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)]))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    assert (video["width"], video["height"], video["codec_name"], video["r_frame_rate"]) == (1080, 1920, "h264", "24/1")
    assert audio["codec_name"] == "aac"
    assert abs(float(probe["format"]["duration"])-4) < .1
    subprocess.run([binary, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True, capture_output=True)
    pcm = subprocess.check_output([binary, "-v", "error", "-i", str(output), "-map", "0:a:0", "-f", "f32le", "-ac", "1", "-ar", "24000", "-"])
    decoded_audio = np.frombuffer(pcm, dtype="float32")
    assert np.max(np.abs(decoded_audio[:int(.3*24000)])) < .002
    assert np.max(np.abs(decoded_audio[int(.6*24000):])) > .01
    comparisons = []
    for index, scene in enumerate(scenes):
        for frame in (0, 6, 12, 18, 23):
            moment = index+frame/24
            raw = subprocess.check_output([binary, "-v", "error", "-ss", str(moment), "-i", str(output),
                                           "-frames:v", "1", "-vf", "scale=180:320", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
            actual = np.frombuffer(raw, dtype="uint8").reshape(320, 180, 3)
            expected = np.asarray(image.resize((180, 320), Image.Resampling.BICUBIC,
                                               box=crop_box(360, 640, camera_at(scene, frame/23))))
            mae = float(np.mean(np.abs(actual.astype(float)-expected.astype(float))))
            comparisons.append({"easing": scene["easing"], "frame": frame, "mean_pixel_error": round(mae, 3)})
            assert mae < 12, comparisons[-1]
            if index == 0:
                Image.fromarray(actual).save(folder / f"decoded-frame-{frame}.png")
    result = {"output": str(output), "video": {k: video[k] for k in ("width", "height", "codec_name", "r_frame_rate", "nb_frames")},
              "audio_codec": audio["codec_name"], "duration": probe["format"]["duration"],
              "narration": metadata, "camera_comparisons": comparisons, "full_decode": "passed", "audio_delay": "passed"}
    (folder / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
