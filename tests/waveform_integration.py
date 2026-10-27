"""Real audio decode/cache and Tk timeline checks; explicit local test."""
import math
from pathlib import Path
import struct
import sys
import time
import uuid
import wave
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from PIL import Image
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp
from waveform import WaveformJob, source_key


def main():
    folder = base.TEMP / ("waveform-check-"+uuid.uuid4().hex[:8])
    folder.mkdir()
    path = folder / "speech-pattern.wav"
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        samples = []
        for i in range(16000):
            t = i/8000
            amplitude = .5 if .5 <= t < 1 else .25 if 1.5 <= t else 0
            samples.append(round(amplitude*32767*math.sin(2*math.pi*440*t)))
        audio.writeframes(struct.pack("<"+"h"*len(samples), *samples))
    data = WaveformJob(path, base.ffmpeg_binary(), folder / "cache", lambda *_args: None).analyze()
    assert abs(data["duration"]-2) < .001 and len(data["peaks"]) == 100
    assert data["peaks"][10] == 0 and .45 < data["peaks"][35] < .55
    assert data["peaks"][60] == 0 and .2 < data["peaks"][85] < .3
    with mock.patch("waveform.subprocess.Popen", side_effect=AssertionError("Cache hit must not decode")):
        assert WaveformJob(path, "unused", folder / "cache", lambda *_args: None).analyze() == data
    (folder / "cache" / (source_key(path)+".json")).write_text("[]")
    assert WaveformJob(path, base.ffmpeg_binary(), folder / "cache", lambda *_args: None).analyze() == data
    image = folder / "image.png"
    Image.new("RGB", (180,320), "#88bb99").save(image)
    root = tk.Tk()
    editor = EditorApp(root)
    editor.scenes = [{"image":str(image),"duration":3}]
    editor.audio = {"path":str(path),"offset":.5,"trim":.25,"volume":.75,"fade":.1}
    editor.sync_audio()
    editor.refresh(0)
    until = time.monotonic()+10
    while editor._wave_data is None and time.monotonic() < until:
        root.update()
        time.sleep(.02)
    assert editor._wave_data is not None, editor._wave_state
    root.update()
    assert editor.timeline.find_withtag("audio-waveform")
    key = editor._wave_key
    editor.audio_inputs["volume"].set("0")
    editor.apply_audio()
    root.update()
    assert editor._wave_key == key and not editor.timeline.find_withtag("audio-waveform")
    editor.audio = None
    editor.sync_audio()
    editor.draw_timeline()
    editor.events.put(("waveform", (key, data, None)))
    until = time.monotonic()+.25
    while time.monotonic() < until:
        root.update()
        time.sleep(.01)
    assert editor._wave_data is None and not editor.timeline.find_withtag("audio-waveform")
    editor.dirty = False
    editor.close()
    print("PASS: real PCM decode, silence/loudness, cache hit, corrupt-cache recovery, Tk waveform drawing, volume adjustment without re-decode, stale-result rejection")


if __name__ == "__main__":
    main()
