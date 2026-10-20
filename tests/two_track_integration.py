"""Two-track persistence, actual mixed PCM/MP4, and Tk editing regression."""
import sys, wave, math, struct, tempfile, subprocess, time
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from PIL import Image
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp
from project import write_project, read_project, audio_values
from preview_audio import PreviewAudio
with tempfile.TemporaryDirectory() as temp:
    folder=Path(temp)
    def tone(name,frequency):
        path=folder/name
        with wave.open(str(path),'wb') as w:
            w.setparams((1,2,48000,0,'NONE','not compressed'))
            w.writeframes(b''.join(struct.pack('<h',int(5000*math.sin(i*2*math.pi*frequency/48000))) for i in range(96000)))
        return audio_values(dict(path=str(path),volume=.5))
    voice=tone('voice.wav',440); music=tone('music.wav',880)
    music['offset']=.25
    image=folder/'scene.png'; Image.new('RGB',(180,320),'teal').save(image)
    scenes=[dict(image=str(image),duration=2)]
    path=folder/'project.json';write_project(path,scenes,voice,music)
    doc=read_project(path);assert doc['audio']==voice and doc['music']==music
    calls=[]; job=PreviewAudio(base.ffmpeg_binary(),folder,lambda *args:calls.append(args))
    job.run([voice,music],2,0);assert calls[0][1] is None,calls
    def strengths(path):
        with wave.open(str(path),'rb') as w:
            channels=w.getnchannels(); values=struct.unpack('<'+'h'*(w.getnframes()*channels),w.readframes(w.getnframes()))[::channels]
        segment=values[24000:48000]
        return [abs(sum(v*complex(math.cos(i*2*math.pi*f/48000),math.sin(i*2*math.pi*f/48000)) for i,v in enumerate(segment)))/len(segment) for f in (440,880)]
    assert min(strengths(job.path))>700
    output=base.render_scenes(scenes,folder/'mixed.mp4',audio=voice,music=music)
    decoded=folder/'decoded.wav'
    subprocess.run([base.ffmpeg_binary(),'-v','error','-i',str(output),'-vn','-ar','48000','-c:a','pcm_s16le',str(decoded)],check=True)
    assert min(strengths(decoded))>650
    subprocess.run([base.ffmpeg_binary(),'-v','error','-i',str(output),'-f','null','-'],check=True)
    root=tk.Tk();app=EditorApp(root);app.scenes=scenes;app.audio=voice
    app.audio_track.set('Music');app.select_audio_track()
    with mock.patch('editor_app.filedialog.askopenfilename',return_value=music['path']):app.add_audio()
    assert app.audio==voice and app.music['path']==music['path']
    app.audio_inputs['volume'].set('.2');app.apply_audio();assert app.music['volume']==.2 and app.audio['volume']==.5
    app.undo();assert app.music['volume']==1;app.redo();assert app.music['volume']==.2
    app.remove_audio();assert app.music is None and app.audio==voice
    app.undo();assert app.music['volume']==.2
    app.project_path=path;assert app.save()
    assert read_project(path)['music']['volume']==.2
    for _ in range(10):root.update();time.sleep(.01)
    app.dirty=False;app.close()
print('PASS: two-track relative-path roundtrip, both frequencies in real preview PCM and decoded MP4, full decode, Tk track selection/edit/remove/undo/redo/save.')
