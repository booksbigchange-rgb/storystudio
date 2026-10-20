"""Reusable visual regression project. Uses StoryStudio's actual project/renderer.

Run through Run-Video-Check.cmd. The master assets are generated once, hashed,
and reused. Every verification run gets its own export directory.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import soundfile as sf
import desktop_app as app
from camera import camera_at, crop_box
from project import read_project, write_project

MASTER = app.PROJECTS / "regression-master-v1"
SPECS = [
    ("Still picture", 4, "PNG · No movement", "One. A clear, still picture."),
    ("Steady zoom", 4, "PNG · Linear", "Two. A steady zoom toward the center."),
    ("Left to right", 4, "PNG · Smooth", "Three. Pan smoothly from A to B."),
    ("Top to bottom", 4, "PNG · Ease in", "Four. Move down, then speed up."),
    ("Three turns", 5, "PNG · Intermediate keyframes", "Five. Turn left, right, and return home."),
    ("Wide to tall", 5, "JPEG · Center crop", "Six. A wide image fills the tall frame."),
    ("Up and slow", 4, "BMP · Ease out", "Seven. Move up and slow down."),
    ("Check complete", 4, "PNG · Save and reopen", "Eight. Save, reopen, and export again."),
]


def font(size, bold=False):
    return ImageFont.truetype(str(Path(os.environ.get("WINDIR", "C:/Windows"))/"Fonts"/
                                  ("segoeuib.ttf" if bold else "segoeui.ttf")), size)


def centered(draw, text, xy, size=40, color="#183047", bold=False):
    draw.text(xy, text, font=font(size, bold), fill=color, anchor="mm")


def card(index, destination):
    wide = index == 5
    w, h = (1280, 720) if wide else (720, 1280)
    tint = [(25, 139, 109), (43, 104, 191), (179, 97, 30), (128, 78, 171),
            (6, 133, 157), (62, 111, 72), (172, 64, 102), (25, 139, 109)][index]
    y, x = np.mgrid[:h, :w]
    amount = (.05+.14*y/h+.035*np.sin(x/w*6))[:, :, None]
    pixels = np.clip(255*(1-amount)+np.array(tint)*amount, 0, 255).astype("uint8")
    image = Image.fromarray(pixels)
    draw = ImageDraw.Draw(image)
    for gx in range(0, w, 90):
        draw.line((gx, 0, gx, h), fill="#dae3e8", width=1)
    for gy in range(0, h, 90):
        draw.line((0, gy, w, gy), fill="#dae3e8", width=1)
    if wide:
        draw.rectangle((0, 0, 436, h), fill="#edcab9")
        draw.rectangle((844, 0, w, h), fill="#bdd7ed")
        centered(draw, "OUTSIDE", (215, 360), 48)
        centered(draw, "OUTSIDE", (1060, 360), 48)
        draw.rectangle((440, 60, 840, 660), outline=tint, width=6)
        centered(draw, "06", (640, 180), 92, tint, True)
        centered(draw, "WIDE TO TALL", (640, 315), 35, bold=True)
        centered(draw, "Keep this center", (640, 395), 27)
        centered(draw, "JPEG / center crop", (640, 460), 24)
    else:
        draw.rounded_rectangle((42, 46, 678, 134), radius=24, fill="white")
        draw.text((68, 69), "STORYSTUDIO / VIDEO CHECK", font=font(26, True), fill=tint)
        centered(draw, f"{index+1:02d}", (360, 255), 130, tint, True)
        centered(draw, SPECS[index][0], (360, 373), 48, bold=True)
        centered(draw, SPECS[index][2], (360, 434), 26)
        def target(cx, cy, label, color):
            draw.ellipse((cx-78, cy-78, cx+78, cy+78), fill="white", outline=color, width=7)
            draw.ellipse((cx-49, cy-49, cx+49, cy+49), fill=color)
            centered(draw, label, (cx, cy-3), 48, "white", True)
        if index in (2, 4):
            draw.line((180, 670, 540, 670), fill=tint, width=7)
            target(185, 670, "A", "#b85d1c")
            target(535, 670, "B", "#2368bb")
            centered(draw, "FOLLOW THE TARGETS", (360, 820), 28, bold=True)
        elif index in (3, 6):
            draw.line((360, 575, 360, 1010), fill=tint, width=7)
            target(360, 565, "A", "#26759f")
            target(360, 970, "B", "#a84671")
        elif index == 7:
            target(360, 670, "8", tint)
            centered(draw, "WATCH · EDIT · EXPORT", (360, 850), 32, bold=True)
            centered(draw, "One reference for every update", (360, 921), 27)
        else:
            for radius in (190, 140, 88):
                draw.ellipse((360-radius, 740-radius, 360+radius, 740+radius), outline=tint, width=6)
            target(360, 740, "+", tint)
        draw.rounded_rectangle((48, 1112, 672, 1220), radius=18, fill="white")
        centered(draw, f"SCENE {index+1}  /  {SPECS[index][1]} SECONDS", (360, 1148), 26, tint, True)
        centered(draw, "Technical test artwork", (360, 1188), 22)
    image.save(destination, **({"quality": 95} if destination.suffix == ".jpg" else {}))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze_expected_frames(folder):
    """Called only when creating a reference, never during normal verification."""
    expected_dir = folder / "expected"
    expected_dir.mkdir(exist_ok=False)
    document = read_project(folder / "story.json")
    reference_frames = []
    for i, scene in enumerate(document["scenes"]):
        with Image.open(scene["image"]) as source:
            source = source.convert("RGB")
            last = round(scene["duration"]*24)-1
            frames = sorted({0, round(last*.25), round(last*.5), round(last*.75), last} |
                            {round(key["at"]*last) for key in scene["keyframes"]})
            for frame in frames:
                name = f"expected/scene-{i+1:02d}-frame-{frame:04d}.png"
                source.resize((180, 320), Image.Resampling.BICUBIC,
                    box=crop_box(*source.size, camera_at(scene, frame/last))).save(folder / name)
                reference_frames.append({"scene": i+1, "frame": frame, "image": name})
    return reference_frames


def build_master():
    if MASTER.exists():
        verify_master()
        print("Reusing unchanged master project.", flush=True)
        return
    from narration import generate
    app.PROJECTS.mkdir(parents=True, exist_ok=True)
    draft = app.PROJECTS / ("regression-master-build-"+uuid.uuid4().hex[:8])
    draft.mkdir()
    assets = draft / "assets"
    assets.mkdir()
    scenes, schedule = [], []
    cursor = 0
    for i, (title, duration, detail, spoken) in enumerate(SPECS):
        extension = ".jpg" if i == 5 else ".bmp" if i == 6 else ".png"
        path = assets / (f"{i+1:02d}-scene"+extension)
        card(i, path)
        scene = {"image": str(path), "duration": duration, "zoom_start": 1, "zoom_end": 1}
        if i == 1:
            scene.update(zoom_end=1.6)
        elif i == 2:
            scene.update(zoom_start=1.7, zoom_end=1.7, x_start=0, x_end=1, easing="smooth")
        elif i == 3:
            scene.update(zoom_start=1.6, zoom_end=1.6, y_start=0, y_end=1, easing="ease-in")
        elif i == 4:
            scene.update(zoom_start=1.1, zoom_end=1.1, easing="smooth", keyframes=[
                {"at": .28, "zoom": 1.8, "x": 0, "y": .5},
                {"at": .68, "zoom": 1.8, "x": 1, "y": .5}])
        elif i == 5:
            scene.update(zoom_end=1.4, easing="ease-out")
        elif i == 6:
            scene.update(zoom_start=1.6, zoom_end=1.6, y_start=1, y_end=0, easing="ease-out")
        scenes.append(scene)
        schedule.append({"scene": i+1, "title": title, "start": cursor, "end": cursor+duration,
                         "check": detail, "spoken": spoken})
        cursor += duration
    rate = 24000
    track = np.zeros(int((cursor+1)*rate), dtype=np.float32)
    # A one-second calibration tone must disappear when source trim is applied.
    track[:rate] = .12*np.sin(2*np.pi*1000*np.arange(rate)/rate)
    chirp = .08*np.sin(2*np.pi*523.25*np.arange(int(.3*rate))/rate)
    track[rate:rate+len(chirp)] = chirp
    for i, chapter in enumerate(schedule):
        wav = assets / f"voice-{i+1:02d}.wav"
        print(f"Generating offline narration {i+1}/8…", flush=True)
        generate(chapter["spoken"], wav, speed=1.08)
        voice, actual_rate = sf.read(wav, dtype="float32")
        assert actual_rate == rate
        if len(voice)/rate > (chapter["end"]-chapter["start"])-.9:
            raise RuntimeError(f"Narration {i+1} exceeds its scene: {len(voice)/rate:.2f}s; draft preserved at {draft}")
        start = round((1+chapter["start"]+.35)*rate)
        track[start:start+len(voice)] += voice
    # A soft tail note makes the final global fade measurable.
    start = round((1+cursor-1)*rate)
    track[start:] += .06*np.sin(2*np.pi*392*np.arange(len(track)-start)/rate)
    audio_path = assets / "soundtrack.wav"
    sf.write(audio_path, track, rate, subtype="PCM_16")
    write_project(draft / "story.json", scenes, {"path": str(audio_path), "offset": .5,
                  "trim": 1, "volume": .75, "fade": .4})
    expected_frames = freeze_expected_frames(draft)
    hashes = {p.relative_to(draft).as_posix(): sha(p) for p in sorted(draft.rglob("*")) if p.is_file()}
    (draft / "reference.json").write_text(json.dumps({"fixture_version": 1, "duration": cursor,
          "schedule": schedule, "sha256": hashes, "expected_frames": expected_frames}, indent=2), encoding="utf-8")
    # Both resolved paths stay inside this studio's project directory.
    assert draft.resolve().is_relative_to(app.PROJECTS.resolve())
    assert MASTER.resolve().is_relative_to(app.PROJECTS.resolve()) and not MASTER.exists()
    draft.rename(MASTER)
    print(f"Created master: {MASTER / 'story.json'}", flush=True)


def verify_master():
    reference = json.loads((MASTER / "reference.json").read_text(encoding="utf-8"))
    if not reference.get("expected_frames"):
        raise RuntimeError("This master lacks frozen reference frames; do not silently regenerate a baseline after an update.")
    for name, expected in reference["sha256"].items():
        path = (MASTER / name).resolve()
        if not path.is_relative_to(MASTER.resolve()) or not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"Reference changed: {name}. Keep the master unchanged; edit a saved copy.")
    return reference


def tk_check(document):
    import tkinter as tk
    from editor_app import EditorApp
    root = tk.Tk()
    root.withdraw()
    errors = []
    root.report_callback_exception = lambda *args: errors.append(str(args))
    editor = EditorApp(root)
    try:
        editor.load_from(MASTER / "story.json")
        assert editor.document()[0] == document["scenes"]
        assert editor.audio == document["audio"]
        for i in range(len(editor.scenes)):
            editor.refresh(i)
            root.update()
            assert editor._preview_image is not None, f"Scene {i+1} preview failed"
        assert not errors, errors
    finally:
        editor.dirty = False
        editor.close()


def verify_export(folder, document, reference, gui=False):
    output = folder / "StoryStudio-Master-Check.mp4"
    binary = app.ffmpeg_binary()
    probe = Path(binary).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    data = json.loads(subprocess.check_output([str(probe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)]))
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next(s for s in data["streams"] if s["codec_type"] == "audio")
    duration = reference["duration"]
    assert (video["width"], video["height"], video["codec_name"], video["r_frame_rate"]) == (1080, 1920, "h264", "24/1")
    assert int(video["nb_frames"]) == duration*24
    assert audio["codec_name"] == "aac" and abs(float(data["format"]["duration"])-duration) < .1
    subprocess.run([binary, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True, capture_output=True)
    frame_metadata = json.loads(subprocess.check_output([str(probe), "-v", "error", "-select_streams", "v:0",
        "-show_frames", "-show_entries", "frame=pts_time,color_range,color_space,color_primaries,color_transfer",
        "-of", "json", str(output)]))["frames"]
    assert len(frame_metadata) == duration*24
    for n, frame in enumerate(frame_metadata):
        assert abs(float(frame["pts_time"])-n/24) < .001, (n, frame)
        assert (frame.get("color_range"), frame.get("color_space"), frame.get("color_primaries"),
                frame.get("color_transfer")) == ("tv", "bt709", "bt709", "bt709"), (n, frame)
    selected_frames = []
    for item in reference["expected_frames"]:
        chapter = reference["schedule"][item["scene"]-1]
        selected_frames.append(round(chapter["start"]*24)+item["frame"])
    selection = "+".join(f"eq(n,{n})" for n in selected_frames)
    raw_frames = subprocess.check_output([binary, "-v", "error", "-i", str(output), "-an",
        "-vf", f"select='{selection}',scale=180:320", "-fps_mode", "vfr", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    assert len(raw_frames) == len(selected_frames)*180*320*3, "Exact-frame extraction count changed"
    decoded_frames = np.frombuffer(raw_frames, dtype="uint8").reshape(len(selected_frames), 320, 180, 3)
    frame_lookup = dict(zip(selected_frames, decoded_frames))
    samples = []
    thumbs = []
    for i, (scene, chapter) in enumerate(zip(document["scenes"], reference["schedule"])):
        with Image.open(scene["image"]) as source:
            source = source.convert("RGB")
            last = round(scene["duration"]*24)-1
            baseline = [item for item in reference["expected_frames"] if item["scene"] == i+1]
            for item in baseline:
                frame = item["frame"]
                moment = chapter["start"]+frame/24
                actual = frame_lookup[round(chapter["start"]*24)+frame]
                with Image.open(MASTER / item["image"]) as reference_image:
                    expected = np.asarray(reference_image.convert("RGB"))
                error = float(np.mean(np.abs(actual.astype(float)-expected.astype(float))))
                samples.append({"scene": i+1, "frame": frame, "time": round(moment, 4), "mean_rgb_error": round(error, 4)})
                assert error < 12, samples[-1]
                if frame == round(last*.5):
                    thumbs.append(Image.fromarray(actual))
            print(f"Verified camera and crop: scene {i+1}/8", flush=True)
    raw_audio = subprocess.check_output([binary, "-v", "error", "-i", str(output), "-map", "0:a:0",
                    "-f", "f32le", "-ac", "1", "-ar", "24000", "-"])
    actual = np.frombuffer(raw_audio, dtype="float32")[:duration*24000]
    source, rate = sf.read(document["audio"]["path"], dtype="float32")
    delay, trim = round(.5*rate), rate
    expected = np.zeros(duration*rate, dtype="float32")
    expected[delay:] = source[trim:trim+len(expected)-delay]*.75
    timeline = np.arange(len(expected))/rate
    expected *= np.clip((timeline-.5)/.4, 0, 1) * np.clip((duration-timeline)/.4, 0, 1)
    assert len(actual) == len(expected)
    correlation = float(np.corrcoef(actual, expected)[0, 1])
    rms_error = float(np.sqrt(np.mean((actual-expected)**2)))
    assert correlation > .98 and rms_error < .01, (correlation, rms_error)
    assert np.max(np.abs(actual[:int(.4*rate)])) < .002
    # This checks audible speech in every chapter, not just one nonzero sample.
    for chapter in reference["schedule"]:
        segment = actual[int((chapter["start"]+1)*rate):int((chapter["end"]-.2)*rate)]
        assert float(np.sqrt(np.mean(segment**2))) > .002, chapter["title"]
    before_fade = actual[int((duration-.6)*rate):int((duration-.4)*rate)]
    end_fade = actual[int((duration-.08)*rate):int((duration-.02)*rate)]
    fade_ratio = float(np.sqrt(np.mean(end_fade**2))/np.sqrt(np.mean(before_fade**2)))
    assert fade_ratio < .35, fade_ratio
    # Saving and reopening must retain every camera/audio setting.
    roundtrip = folder / "roundtrip.json"
    write_project(roundtrip, document["scenes"], document["audio"])
    assert read_project(roundtrip) == document
    if gui:
        tk_check(document)
    # Exercise current narration code as well as the frozen soundtrack.
    from narration import generate
    fresh_narration = generate("Story Studio narration check.", folder / "fresh-narration-check.wav")
    speech, speech_rate = sf.read(fresh_narration["output"])
    assert speech_rate == 24000 and .5 < len(speech)/speech_rate < 15
    assert np.max(np.abs(speech)) > .01
    sheet = Image.new("RGB", (840, 820), "#edf2f6")
    draw = ImageDraw.Draw(sheet)
    centered(draw, "STORYSTUDIO / MASTER VIDEO CHECK", (420, 35), 25, bold=True)
    for i, thumbnail in enumerate(thumbs):
        left, top = 20+(i%4)*205, 70+(i//4)*375
        sheet.paste(thumbnail, (left, top))
        draw.text((left, top+325), f"{i+1:02d}  {SPECS[i][0]}", font=font(16, True), fill="#183047")
        chapter = reference["schedule"][i]
        draw.text((left, top+347), f"{chapter['start']:02d}–{chapter['end']:02d} seconds", font=font(15), fill="#526878")
    sheet.save(folder / "contact-sheet.png")
    verify_master()
    return {"status": "PASS", "output": str(output), "project": str(MASTER / "story.json"),
            "duration_seconds": duration, "frames": int(video["nb_frames"]), "resolution": [1080, 1920],
            "codecs": ["h264", "aac"], "fps": 24, "sampled_video_frames": len(samples),
            "maximum_rgb_error": max(p["mean_rgb_error"] for p in samples),
            "audio_correlation": correlation, "audio_rms_error": rms_error, "fade_ratio": fade_ratio,
            "reference_sha256": sha(MASTER / "reference.json"),
            "checks": {"complete_decode": "PASS", "scene_order_and_timing": "PASS", "camera_and_image_formats": "PASS",
                       "consistent_color_metadata": "PASS",
                       "audio_offset_trim_volume_fade": "PASS", "speech_in_all_scenes": "PASS",
                       "project_roundtrip": "PASS", "master_unchanged": "PASS",
                       "fresh_offline_narration": "PASS",
                       "tk_project_and_previews": "PASS" if gui else "NOT RUN"},
            "frame_comparisons": samples,
            "limitations": "Does not replace manual GUI, listening, performance, packaging or CI checks."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open the master as an unsaved copy in the desktop editor")
    parser.add_argument("--gui", action="store_true", help="Also load the project and all previews into real Tk widgets")
    args = parser.parse_args()
    build_master()
    reference = verify_master()
    if args.open:
        import tkinter as tk
        from editor_app import EditorApp
        root = tk.Tk()
        editor = EditorApp(root)
        editor.load_from(MASTER / "story.json")
        editor.project_path = None  # Save always asks for a copy; protect the master.
        editor.status.set("Master test loaded. Save as creates your own copy.")
        root.mainloop()
        return
    folder = app.EXPORTS / "video-checks" / (time.strftime("run-%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    report = {"status": "FAIL", "project": str(MASTER / "story.json")}
    try:
        document = read_project(MASTER / "story.json")
        app.render_scenes(document["scenes"], folder / "StoryStudio-Master-Check.mp4", print, audio=document["audio"])
        report = verify_export(folder, document, reference, gui=args.gui)
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        report["source_sha256"] = {p.name: sha(p) for p in sorted((app.ROOT / "engine").glob("*.py"))}
        (folder / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"{report['status']}: {folder / 'report.json'}", flush=True)


if __name__ == "__main__":
    main()
