"""Cancellation during real encoding, between stages, and through Tk."""
import sys, tempfile, threading, time
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from PIL import Image
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp
from render_control import RenderControl, RenderCancelled
with tempfile.TemporaryDirectory() as folder:
    folder=Path(folder);image=folder/'image.png'
    Image.new('RGB',(360,640),'teal').save(image)
    scenes=[dict(image=str(image),duration=120)]
    with mock.patch.object(base,'TEMP',folder):
        # Timer fires while FFmpeg is encoding a long scene.
        control=RenderControl(); timer=threading.Timer(.4,control.cancel);timer.start()
        started=time.monotonic()
        try:base.render_scenes(scenes,folder/'canceled.mp4',control=control)
        except RenderCancelled:pass
        else:raise AssertionError('Cancellation ignored')
        timer.join();assert time.monotonic()-started<8
        assert not (folder/'canceled.mp4').exists()
        assert not list(folder.glob('render-*')) and not list(folder.glob('*.partial'))
        # Cancellation immediately before publishing must preserve destination.
        control=RenderControl()
        def progress(message):
            if message=='Finalizing MP4':control.cancel()
        try:base.render_scenes([dict(image=str(image),duration=.5)],folder/'late.mp4',progress,control=control)
        except RenderCancelled:pass
        else:raise AssertionError('Late cancellation ignored')
        assert not (folder/'late.mp4').exists() and not list(folder.glob('render-*'))
        # Successful publication wins over a subsequent cancel request.
        staged=folder/'stage';staged.write_bytes(b'complete');output=folder/'published'
        control=RenderControl();control.publish(staged,output);control.cancel()
        assert not control.event.is_set() and output.read_bytes()==b'complete'
        root=tk.Tk();app=EditorApp(root);app.scenes=scenes
        with mock.patch('editor_app.messagebox.showerror') as error:
            app.render(folder/'gui.mp4');app.cancel_button.invoke()
            deadline=time.monotonic()+8
            while app.busy and time.monotonic()<deadline:root.update();time.sleep(.01)
            assert not app.busy and not error.called and 'canceled' in app.status.get()
            assert app.cancel_button.instate(['disabled']) and not app.render_button.instate(['disabled'])
            assert not (folder/'gui.mp4').exists()
            # Can immediately export again after canceling.
            app.scenes=[dict(image=str(image),duration=.5)];app.render(folder/'retry.mp4')
            deadline=time.monotonic()+15
            while app.busy and time.monotonic()<deadline:root.update();time.sleep(.01)
            assert not app.busy and (folder/'retry.mp4').exists() and not error.called
        app.dirty=False;app.close()
print('PASS: real FFmpeg cancellation under 8s, no partial output/job residue, late cancel, publication race semantics, Tk cancel and successful retry.')
