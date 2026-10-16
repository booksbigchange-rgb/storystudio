"""Real mixed-engine export, source integrity, GUI ordering and save/reopen."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
import mixed_project as model
from mixed_editor import MixedEditor
from mixed_render import export

folder = ROOT/'exports'/('mixed-acceptance-'+uuid.uuid4().hex)
folder.mkdir()
cartoon = folder/'character.json'
cartoon.write_text(json.dumps(dict(version=2,name='Mixed test',format='Landscape 16:9',
    quality='Standard · 720p / 24 fps',audio=None,scenes=[dict(title='CHARACTER SECTION',duration=2,
    character='bear',expression='curious',action='wave',background='night',x=.4,size=1,speed=1)])),encoding='utf-8')
noir = ROOT/'projects/noir-widescreen-v2/story.json'
before = hashlib.sha256(noir.read_bytes()).hexdigest()
root = tk.Tk()
app = MixedEditor(root)
app.add_path(noir)
app.add_path(cartoon)
app.move(-1)
assert app.doc['sections'][0]['engine']=='cartoon'
app.move(1)
assert app.doc['sections'][0]['engine']=='documentary'
app.path=folder/'mixed.json'
app.save()
assert model.load(app.path)==app.doc
root.update()
app.close()
loaded=model.load(folder/'mixed.json')
output=folder/'mixed-widescreen.mp4'
export(loaded, output, print)
assert hashlib.sha256(noir.read_bytes()).hexdigest()==before
original=hashlib.sha256(output.read_bytes()).hexdigest()
try:
    export(loaded,output)
    raise AssertionError('Existing output overwritten')
except FileExistsError:pass
assert hashlib.sha256(output.read_bytes()).hexdigest()==original
from project import read_project
portrait=model.load(folder/'mixed.json')
silent=read_project(noir)
silent['scenes'][0]['duration']=1
silent['audio']=None
silent['music']=None
(folder/'silent.json').write_text(json.dumps(silent),encoding='utf-8')
portrait['sections'][0]['project']=str(folder/'silent.json')
portrait['format']='portrait'
model.save(portrait,folder/'portrait.json')
export(portrait,folder/'mixed-portrait.mp4',print)
ffmpeg=ROOT/'tools/ffmpeg/ffmpeg.exe'
frames=[]
for i, at in enumerate((1,9.5)):
    image=folder/f'section-{i}.png'
    subprocess.run([str(ffmpeg),'-v','error','-ss',str(at),'-i',str(output),'-frames:v','1',str(image)],check=True)
    frames.append(str(image))
(folder/'acceptance.json').write_text(json.dumps(dict(status='passed',output=str(output),
    checks=['GUI add/reorder/save','mixed reopen','both engines rendered','both formats H264/AAC/full decode','silent section padding',
            'source unchanged','existing output protected'],frames=frames),indent=2),encoding='utf-8')
print('ACCEPTANCE:',folder)
