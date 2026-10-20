"""Real PCM preparation plus Tk transport lifecycle checks."""
import sys, time, wave, math, struct, tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"engine"))
import tkinter as tk
import _tkinter
from PIL import Image
import desktop_app as base
from editor_app import EditorApp
from preview_audio import PreviewAudio

with tempfile.TemporaryDirectory() as folder:
    folder=Path(folder)
    source=folder/'tone.wav'
    with wave.open(str(source), 'wb') as wav:
        wav.setparams((1,2,48000,0,'NONE','not compressed'))
        wav.writeframes(b''.join(struct.pack('<h', int(12000*math.sin(i*2*math.pi*440/48000))) for i in range(96000)))
    audio=dict(path=str(source), trim=.25, offset=.5, volume=.5, fade=.2)
    results=[]
    job=PreviewAudio(base.ffmpeg_binary(),folder,lambda *args:results.append(args))
    job.run(audio, 2, .25)
    assert results and results[0][1] is None, results
    with wave.open(str(job.path),'rb') as wav:
        assert wav.getnframes()==84000
        samples=struct.unpack('<'+'h'*(84000*2),wav.readframes(84000))
    assert max(map(abs,samples[:20000]))==0
    assert 4100 < max(map(abs,samples[48000:96000])) < 4400
    assert max(map(abs,samples[-100:])) < 100
    image=folder/'scene.png'; Image.new('RGB',(180,320)).save(image)
    root=tk.Tk(); app=EditorApp(root); root.update()
    app.scenes=[dict(image=str(image), duration=2)]
    app.audio=audio
    with mock.patch('editor_app.winsound.PlaySound') as sound:
        app.toggle_play()
        deadline=time.monotonic()+10
        while app._audio_pending and time.monotonic()<deadline:
            root.tk.dooneevent(_tkinter.DONT_WAIT); time.sleep(.001)
        assert app.playing and sound.called
        app.seek(.8)
        assert not app.playing and app._audio_preview is None
        app.toggle_play(); app.pause()
        for _ in range(30): root.update(); time.sleep(.01)
        assert not app.playing and not app._audio_pending
        app.toggle_play()
        deadline=time.monotonic()+10
        while app._audio_pending and time.monotonic()<deadline: root.tk.dooneevent(_tkinter.DONT_WAIT); time.sleep(.001)
        assert app.playing, (app.status.get(), app._audio_pending, app.playhead)
        # Isolate the manually advanced clock from an already queued Tk tick.
        if app._tick_job:
            root.after_cancel(app._tick_job)
            app._tick_job = None
        app.loop.set(True)
        app._clock_start=time.monotonic()-2.1
        app.tick()
        assert app._audio_pending and app.playhead==0, (app.playing, app._audio_pending, app.playhead, app.status.get())
        app.pause()
    # A failed preparation must reset the transport, rather than stay pending.
    failed = PreviewAudio(base.ffmpeg_binary(), folder, lambda *_: None)
    app._audio_preview = failed
    app._audio_pending = True
    app.play_button.configure(text="Cancel audio")
    app.events.put(("preview-audio", (failed, "Audio preparation timed out. Try a shorter story.")))
    app._poll_events()
    assert not app._audio_pending and not app.playing
    assert app._audio_preview is None and app.play_button.cget("text") == "Play"
    assert "timed out" in app.status.get()
    app.dirty = False
    app.close()
print('PASS: real PCM duration, delay, gain, fades and seek; Tk play, seek/pause, canceled preparation, loop restart (sound-device calls mocked).')
