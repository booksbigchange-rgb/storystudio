"""Actual key editing, parent undo/redo and decoded motion fidelity in both formats."""
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from unittest.mock import patch
import uuid
from PIL import Image,ImageDraw,ImageGrab,ImageChops,ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
from editor_app import EditorApp
from layer_editor import LayerEditor
from layers import SceneCompositor
from project import write_project,read_project
from mixed_render import export

folder=ROOT/'exports'/('layer-keys-acceptance-'+uuid.uuid4().hex);folder.mkdir()
bg=folder/'background.png';Image.new('RGB',(1280,720),'#204060').save(bg)
art=Image.new('RGBA',(180,180));ImageDraw.Draw(art).rounded_rectangle((8,8,172,172),radius=25,fill='#ffb030')
sprite=folder/'artwork.png';art.save(sprite)
scene=dict(image=str(bg),duration=2,layers=[dict(image=str(sprite),name='Evidence marker',easing='linear',
    start=dict(x=.2,y=.5,size=.2),end=dict(x=.2,y=.5,size=.2))])
ctypes.windll.user32.SetProcessDPIAware()
root=tk.Tk();app=EditorApp(root);root.update()
app.scenes=[scene];app.items.delete(0,'end');app.items.insert('end','Key test');app.items.selection_set(0)
dialog=LayerEditor(app);root.update();keys=dialog.edit_keys();keys.window.geometry('+30+30');root.update()
errors=[]
with patch('layer_keys_editor.messagebox.showerror',side_effect=lambda title,text,**kwargs:errors.append(text)):
    keys.time.set('50');keys.fields['x'].set('.8');keys.fields['angle'].set('45');keys.fields['opacity'].set('.7')
    keys.buttons['Add key'].invoke();assert len(keys.layer['keyframes'])==1
    keys.items.selection_set(0);keys.select();keys.fields['x'].set('.7');keys.buttons['Update key'].invoke()
    assert keys.layer['keyframes'][0]['pose']['x']==.7
    keys.time.set('75');keys.sample_button.invoke();keys.buttons['Add key'].invoke()
    keys.items.selection_set(1);keys.select();keys.buttons['Remove key'].invoke();assert len(keys.layer['keyframes'])==1
    keys.time.set('50');keys.buttons['Preview'].invoke();root.update()
    assert keys.canvas.find_all() and not errors,errors
    for button in [keys.apply_button,*keys.buttons.values()]:
        assert button.winfo_viewable() and button.winfo_rooty()+button.winfo_height()<=keys.window.winfo_rooty()+keys.window.winfo_height()
    keys.window.lift();root.update();settled=tk.BooleanVar(value=False)
    root.after(500,lambda:settled.set(True));root.wait_variable(settled)
    ImageGrab.grab(window=ctypes.windll.user32.GetAncestor(keys.window.winfo_id(),2)).save(folder/'motion-keys.png')
    keys.apply_button.invoke()
    assert len(dialog.layers[0]['keyframes'])==1
    cancelled=dialog.edit_keys();cancelled.time.set('25');cancelled.buttons['Add key'].invoke();cancelled.close()
    assert len(dialog.layers[0]['keyframes'])==1
dialog.apply();assert app.scenes[0]['layers'][0]['keyframes']
app.undo();assert not app.scenes[0]['layers'][0].get('keyframes')
app.redo();scene=app.scenes[0]
app.dirty=False;app.close()
results=[]
for format,width,height in [('widescreen',1280,720),('portrait',720,1280)]:
    path=folder/(format+'.json');write_project(path,[scene],output_format=format)
    doc=read_project(path);assert doc['scenes'][0]['layers'][0]['keyframes']==scene['layers'][0]['keyframes']
    output=folder/(format+'.mp4')
    export(dict(kind='storystudio-mixed',version=1,format=format,sections=[dict(engine='documentary',project=str(path),name='Layer keys')]),output,print)
    frames=[0,12,24,36,47]
    select='+'.join(f'eq(n\\,{n})' for n in frames)
    raw=subprocess.run([str(ROOT/'tools/ffmpeg/ffmpeg.exe'),'-v','error','-i',str(output),'-vf','select='+select,
        '-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
    size=width*height*3;assert len(raw)==size*len(frames)
    compositor=SceneCompositor(doc['scenes'][0]);means=[]
    for i,n in enumerate(frames):
        decoded=Image.frombytes('RGB',(width,height),raw[i*size:(i+1)*size])
        expected=compositor.frame(n/47,width,height)
        error=sum(ImageStat.Stat(ImageChops.difference(decoded,expected)).mean)/3
        assert error<5,(format,n,error)
        means.append(round(error,3))
        if n==24:decoded.save(folder/(format+'-middle.png'))
    results.append(dict(format=format,decoded_frame_mean_errors=means,status='passed'))
(folder/'results.json').write_text(json.dumps(dict(status='passed',checks=['real GUI add/update/remove/preview/cancel',
    'apply keys','single parent undo/redo','save/reopen','both MP4 orientations fully decoded','five decoded poses match compositor'],results=results),indent=2))
print('ACCEPTANCE:',folder)
