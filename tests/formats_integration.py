"""Widescreen camera/layer concat, frame fidelity and real editor format changes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from PIL import Image,ImageDraw,ImageChops,ImageStat
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp
from formats import LABELS
from layers import SceneCompositor
from project import write_project,read_project

with tempfile.TemporaryDirectory() as temp:
    folder=Path(temp)
    background=Image.new('RGB',(800,800),'#23405e')
    draw=ImageDraw.Draw(background)
    draw.rectangle((50,50,350,350),fill='#c7a96d')
    draw.rectangle((450,450,750,750),fill='#a25a52')
    draw.line((0,400,800,400),fill='white',width=8)
    image=folder/'background.png';background.save(image)
    sprite=folder/'art.png';art=Image.new('RGBA',(120,80));ImageDraw.Draw(art).ellipse((5,5,115,75),fill='#d8ccac');art.save(sprite)
    first=dict(image=str(image),duration=1,zoom_start=1.2,zoom_end=1.5,x_start=.2,x_end=.8,y_start=.3,y_end=.7)
    second=dict(first,layers=[dict(image=str(sprite),start=dict(x=.2,y=.3,angle=-10),end=dict(x=.8,y=.6,angle=20))])
    scenes=[first,second]
    output=base.render_scenes(scenes,folder/'wide.mp4',output_format='widescreen')
    probe=json.loads(subprocess.run([str(base.ROOT/'tools'/'ffmpeg'/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(output)],capture_output=True,text=True,check=True).stdout)
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'])==(1920,1080)
    assert video['r_frame_rate']=='24/1' and int(video['nb_frames'])==48
    raw=subprocess.run([base.ffmpeg_binary(),'-v','error','-i',str(output),'-vf',
        "select='eq(n,0)+eq(n,23)+eq(n,24)+eq(n,47)'",'-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
    count=1920*1080*3;assert len(raw)==count*4
    errors=[]
    for i,n in enumerate([0,23,24,47]):
        expected=SceneCompositor(scenes[n//24]).frame((n%24)/23,1920,1080)
        actual=Image.frombytes('RGB',(1920,1080),raw[i*count:(i+1)*count])
        error=sum(ImageStat.Stat(ImageChops.difference(expected,actual)).mean)/3
        assert error<5,error
        errors.append(round(error,3))
    subprocess.run([base.ffmpeg_binary(),'-v','error','-i',str(output),'-f','null','-'],check=True)
    project=folder/'wide.json';write_project(project,scenes,output_format='widescreen')
    assert read_project(project)['format']=='widescreen'
    root=tk.Tk();app=EditorApp(root);root.update();app.load_from(project);root.update()
    assert app.output_format=='widescreen' and app.aspect==16/9
    assert abs(app._preview_image.width()/app._preview_image.height()-16/9)<.03
    app.format_choice.set(LABELS['portrait']);app.change_format();assert app.output_format=='portrait'
    app.undo();assert app.output_format=='widescreen'
    app.redo();assert app.output_format=='portrait'
    assert app.save() and read_project(project)['format']=='portrait'
    app.dirty=False;app.close()
print('PASS: 1920x1080/24fps, legacy camera plus layered concat, four decoded frames '+str(errors)+', full decode, format persistence and Tk preview/change/undo/redo/save.')
