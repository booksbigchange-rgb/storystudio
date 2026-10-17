"""Actual transparent layering, decoded-frame fidelity, Tk editing and cancellation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from PIL import Image, ImageDraw, ImageChops, ImageStat
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp
from layer_editor import LayerEditor
from layers import SceneCompositor, layer_values
from project import read_project, write_project
from render_control import RenderControl, RenderCancelled

with tempfile.TemporaryDirectory() as temp:
    folder = Path(temp)
    background = folder/'background.png'
    Image.new('RGB', (360,640), '#204060').save(background)
    art = Image.new('RGBA', (120,160))
    ImageDraw.Draw(art).rounded_rectangle((5,5,115,155), radius=20, fill='#ffb030')
    sprite = folder/'actor.png';art.save(sprite)
    scene = dict(image=str(background), duration=1, zoom_start=1, zoom_end=1,
                 layers=[dict(image=str(sprite),start=dict(x=.2,y=.3,size=.3,angle=-25,opacity=.3),
                              end=dict(x=.8,y=.7,size=.5,angle=35,opacity=1),easing='smooth')])
    compositor = SceneCompositor(scene)
    assert compositor.frame(0,180,320).getpixel((179,319)) == (32,64,96)
    project=folder/'story.json';write_project(project,[scene])
    doc=read_project(project)
    assert doc['version']==5 and doc['scenes'][0]['layers'][0]['image']==str(sprite)
    assert json.loads(project.read_text())['scenes'][0]['layers'][0]['image']=='actor.png'
    output = base.render_scenes([scene],folder/'layers.mp4')
    raw=subprocess.run([base.ffmpeg_binary(),'-v','error','-i',str(output),'-vf',
        "select='eq(n,0)+eq(n,12)+eq(n,23)'",'-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
        capture_output=True,check=True).stdout
    count=1080*1920*3;assert len(raw)==count*3
    errors=[]
    for i,n in enumerate([0,12,23]):
        decoded=Image.frombytes('RGB',(1080,1920),raw[i*count:(i+1)*count])
        expected=compositor.frame(n/23,1080,1920)
        error=sum(ImageStat.Stat(ImageChops.difference(decoded,expected)).mean)/3
        assert error<4,error
        errors.append(round(error,3))
    subprocess.run([base.ffmpeg_binary(),'-v','error','-i',str(output),'-f','null','-'],check=True)
    # Cancellation during streaming must leave no published output.
    control=RenderControl();timer=threading.Timer(.3,control.cancel);timer.start()
    try:
        base.render_scenes([dict(scene,duration=120)],folder/'canceled.mp4',control=control)
    except RenderCancelled:pass
    else:raise AssertionError('Layer export ignored cancellation')
    timer.join();assert not (folder/'canceled.mp4').exists()
    root=tk.Tk();app=EditorApp(root);root.update()
    app.scenes=[dict(image=str(background),duration=1)]
    app.items.delete(0,'end');app.items.insert('end','test');app.items.selection_set(0)
    dialog=LayerEditor(app);root.update()
    with mock.patch('layer_editor.filedialog.askopenfilename',return_value=str(sprite)):
        dialog.add()
    dialog.fields['end']['angle'].set('45');dialog.preview(.5)
    assert len(dialog.canvas.find_all())==1
    dialog.apply();assert app.scenes[0]['layers'][0]['end']['angle']==45
    app.undo();assert not app.scenes[0].get('layers')
    app.redo();assert app.scenes[0]['layers']
    app.dirty=False;app.close()
print('PASS: RGBA transparency, version5 relative links, three decoded transform frames (RGB mean errors '+str(errors)+'), full decode, streaming cancellation, Tk add/pose/preview/apply/undo/redo.')
