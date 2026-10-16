"""Real repeated PCM/MP4 and independent Tk repeat controls."""
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import wave
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from PIL import Image
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp
from preview_audio import PreviewAudio
from project import audio_values, read_project, write_project

with tempfile.TemporaryDirectory() as temp:
    folder = Path(temp)
    source = folder/'short.wav'
    with wave.open(str(source), 'wb') as wav:
        wav.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
        wav.writeframes(b''.join(struct.pack('<h', int(8000*math.sin(i*2*math.pi*440/48000))) for i in range(24000)))
    track = audio_values(dict(path=str(source), repeat=True, offset=.25, trim=.1, fade=.1))
    def pcm(path):
        with wave.open(str(path), 'rb') as wav:
            count, channels = wav.getnframes(), wav.getnchannels()
            assert count == 96000
            return struct.unpack('<'+'h'*(count*channels), wav.readframes(count))[::channels]
    results = []
    job = PreviewAudio(base.ffmpeg_binary(), folder, lambda *args: results.append(args))
    job.run(track, 2, 0)
    assert results[0][1] is None, results
    samples = pcm(job.path)
    assert max(map(abs, samples[:12000])) == 0
    assert max(map(abs, samples[72000:84000])) > 4000
    assert max(map(abs, samples[-20:])) < 100
    # Compare the same source without repetition: its tail must be silent.
    plain = dict(track, repeat=False)
    other = PreviewAudio(base.ffmpeg_binary(), folder, lambda *_: None)
    other.run(plain, 2, 0)
    assert max(map(abs, pcm(other.path)[72000:84000])) == 0
    image = folder/'scene.png'
    Image.new('RGB', (180,320), 'teal').save(image)
    scenes = [dict(image=str(image), duration=2)]
    project = folder/'story.json'
    write_project(project, scenes, music=track)
    assert read_project(project)['music']['repeat'] is True
    output = base.render_scenes(scenes, folder/'repeat.mp4', music=track)
    decoded = folder/'decoded.wav'
    subprocess.run([base.ffmpeg_binary(), '-v', 'error', '-i', str(output), '-vn', '-ar', '48000',
                    '-t', '2', '-c:a', 'pcm_s16le', str(decoded)], check=True)
    assert max(map(abs, pcm(decoded)[72000:84000])) > 3500
    subprocess.run([base.ffmpeg_binary(), '-v', 'error', '-i', str(output), '-f', 'null', '-'], check=True)
    root = tk.Tk()
    app = EditorApp(root)
    root.update()
    app.scenes, app.music = scenes, plain
    app.audio_track.set('Music')
    app.select_audio_track()
    app.audio_repeat.set(True)
    app.apply_audio()
    assert app.music['repeat'] and app.audio is None
    app.undo()
    assert not app.music['repeat']
    app.redo()
    assert app.music['repeat']
    app.audio_track.set('Narration')
    app.select_audio_track()
    assert not app.audio_repeat.get()
    app.dirty = False
    app.close()
print('PASS: repeat/default PCM tail, delay/fade, save/reopen, repeated music in decoded MP4, Tk independent settings and undo/redo.')
