"""Real template controls, reusable inputs, rendered layer projects and MP4 checks."""
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from unittest.mock import patch
import uuid
from PIL import Image,ImageDraw,ImageGrab,ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
from documentary_templates import KINDS,SIZES
from template_editor import TemplateEditor
from project import read_project
from layers import SceneCompositor
from mixed_render import export

folder=ROOT/'exports'/('templates-acceptance-'+uuid.uuid4().hex);folder.mkdir()
image=folder/'synthetic-diagram.png'
canvas=Image.new('RGB',(800,600),'#607F90');draw=ImageDraw.Draw(canvas)
for x in range(0,800,100):draw.line((x,0,x,600),fill='#95B1BD',width=2)
for y in range(0,600,100):draw.line((0,y,800,y),fill='#95B1BD',width=2)
draw.rectangle((120,120,340,280),fill='#B08C59');draw.ellipse((500,300,680,480),fill='#AEC4B1')
canvas.save(image);original=hashlib.sha256(image.read_bytes()).hexdigest()
ctypes.windll.user32.SetProcessDPIAware()
root=tk.Tk();root.geometry('400x120+20+20');root.update()
opened=[];errors=[]
app=TemplateEditor(root,folder/'projects',lambda kind,path:opened.append((kind,path)))
app.window.geometry('+30+30')
outputs=[]
with patch('template_editor.messagebox.showerror',side_effect=lambda title,text,**kwargs:errors.append(text)):
    for format,(width,height) in SIZES.items():
        sections=[]
        for kind in KINDS:
            app.kind.set(kind);app.format.set(format);app.seconds.set('1')
            app.title.set({'Evidence desk':'EVIDENCE / 01','Chronology':'CHRONOLOGY / 02','Map focus':'DIAGRAM FOCUS / 03'}[kind])
            app.source.set('Synthetic regression diagram — not a real place')
            app.image.set(str(image));app.x.set('.25');app.y.set('.65')
            app.detail.delete('1.0','end');app.detail.insert('1.0','2001 | First recorded event\n2003 | Follow-up recorded' if kind=='Chronology' else 'Only the supplied information appears here. Replace this test content with your own source material.')
            app.created=None;app.create_button.invoke();root.update()
            assert not errors,errors
            for button in (app.create_button,app.open_button):
                assert button.winfo_viewable()
                assert button.winfo_rooty()+button.winfo_height()<=app.window.winfo_rooty()+app.window.winfo_height()
            assert app.created and app.created.is_file()
            app.open_button.invoke();assert opened[-1]==('documentary',app.created)
            doc=read_project(app.created)
            frame=SceneCompositor(doc['scenes'][0]).frame(.8,width,height)
            assert max(ImageStat.Stat(frame).stddev)>15
            frame.save(folder/(format+'-'+kind.replace(' ','-')+'.png'))
            sections.append(dict(engine='documentary',project=str(app.created),name=kind))
        with patch('template_editor.filedialog.askopenfilename',return_value=str(app.created.parent/'template.json')):
            app.load()
        assert app.title.get()=='DIAGRAM FOCUS / 03' and Path(app.image.get()).is_file()
        output=folder/(format+'.mp4')
        export(dict(kind='storystudio-mixed',version=1,format=format,sections=sections),output,print)
        # One decoded frame from each section must be distinct and nonblank.
        raw=subprocess.run([str(ROOT/'tools/ffmpeg/ffmpeg.exe'),'-v','error','-i',str(output),
            '-vf',r'select=eq(n\,12)+eq(n\,36)+eq(n\,60),scale=160:160:force_original_aspect_ratio=decrease,pad=160:160:(ow-iw)/2:(oh-ih)/2','-fps_mode','passthrough',
            '-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
        # Save a directly decoded evidence frame for human inspection too.
        subprocess.run([str(ROOT/'tools/ffmpeg/ffmpeg.exe'),'-v','error','-ss','2.5','-i',str(output),
            '-frames:v','1',str(folder/(format+'-decoded-map.png'))],check=True)
        size=160*160*3
        assert len(raw)==3*size
        samples=[raw[i*size:(i+1)*size] for i in range(3)]
        assert len({hashlib.sha256(sample).hexdigest() for sample in samples})==3
        assert all(max(ImageStat.Stat(Image.frombytes('RGB',(160,160),sample)).stddev)>15 for sample in samples)
        outputs.append(str(output))
    app.window.lift();app.window.update()
    settled=tk.BooleanVar(value=False);root.after(500,lambda:settled.set(True));root.wait_variable(settled)
    ImageGrab.grab(window=ctypes.windll.user32.GetAncestor(app.window.winfo_id(),2)).save(folder/'template-window.png')
app.window.destroy();root.destroy()
assert hashlib.sha256(image.read_bytes()).hexdigest()==original
(folder/'results.json').write_text(json.dumps(dict(status='passed',outputs=outputs,
    checks=['six real GUI creations','input reload','open-project dispatch','editable layer documents',
            'source unchanged','six layer previews','both MP4 formats fully decoded','three section samples per MP4']),indent=2))
print('ACCEPTANCE:',folder)
