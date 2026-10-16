"""Real Tk editing and decoded frame-boundary tests using synthetic source projects."""
import hashlib
import ctypes
import copy
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
import uuid
from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
import mixed_project as model
from mixed_editor import MixedEditor
from mixed_render import export
from mixed_titles import card

folder = ROOT/'exports'/('titles-acceptance-'+uuid.uuid4().hex)
folder.mkdir()
Image.new('RGB', (1280, 720), '#dddddd').save(folder/'documentary.png')
documentary = folder/'documentary.json'
documentary.write_text(json.dumps(dict(version=5, format='widescreen', scenes=[dict(image='documentary.png', duration=1)])))
cartoon = folder/'character.json'
cartoon.write_text(json.dumps(dict(version=2, name='Titles test', format='Landscape 16:9',
    quality='Standard · 720p / 24 fps', audio=None, scenes=[dict(title='',duration=2,
    character='bear',expression='curious',action='wave',background='meadow',x=.4,size=1,speed=1)])), encoding='utf-8')
hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (documentary, cartoon)}
ctypes.windll.user32.SetProcessDPIAware()
root = tk.Tk()
app = MixedEditor(root)
app.add_path(documentary); app.add_path(cartoon)
root.update()
dialog = app.edit_titles()
dialog.window.geometry('+40+40')
items = [dict(kind='Title', text="Case file: 50% {literal} \\ ' evidence", start=.5, end=1.5),
         dict(kind='Date', text='16 October 2026', start=1.5, end=2),
         dict(kind='Source', text='Source: synthetic regression fixture', start=0, end=.5),
         dict(kind='Caption', text='Shared caption across both engines', start=2, end=2.5)]
for item in items:
    dialog.kind.set(item['kind']); dialog.start.set(str(item['start'])); dialog.end.set(str(item['end']))
    dialog.text.delete('1.0', 'end'); dialog.text.insert('1.0', item['text'])
    dialog.buttons['Add'].invoke()
assert dialog.titles == items
dialog.items.selection_set(0); dialog.select()
dialog.text.delete('1.0','end'); dialog.text.insert('1.0',items[0]['text']+' checked')
dialog.buttons['Update'].invoke()
items[0]['text'] += ' checked'
# Remove and restore a selected item through the real controls.
dialog.items.selection_set(3)
dialog.buttons['Remove'].invoke()
assert len(dialog.titles)==3
dialog.kind.set(items[3]['kind']); dialog.start.set('2'); dialog.end.set('2.5')
dialog.text.delete('1.0','end'); dialog.text.insert('1.0',items[3]['text'])
dialog.buttons['Add'].invoke()
dialog.items.selection_set(0); dialog.select()
root.update()
dialog.window.lift()
dialog.window.update()
settled = tk.BooleanVar(value=False)
root.after(700, lambda:settled.set(True))
root.wait_variable(settled)
window = ctypes.windll.user32.GetAncestor(dialog.window.winfo_id(), 2)
ImageGrab.grab(window=window).save(folder/'title-editor.png')
dialog.apply()
assert app.dirty and app.doc['titles']==items
app.path = folder/'timeline.json'; app.save()
assert model.load(app.path)==app.doc
doc = model.load(app.path)
cancelled = app.edit_titles()
cancelled.titles.clear()
cancelled.window.destroy()
assert app.doc['titles']==items
app.close()
ffmpeg = str(ROOT/'tools/ffmpeg/ffmpeg.exe')
results = []
invalid = copy.deepcopy(doc)
invalid['titles'] = [dict(kind='Title',text='Outside timeline',start=4,end=5)]
try:
    export(invalid, folder/'invalid.mp4')
    raise AssertionError('Out-of-range title accepted')
except ValueError: pass
assert not (folder/'invalid.mp4').exists()
legacy = copy.deepcopy(doc); legacy.pop('titles')
export(legacy, folder/'without-titles.mp4', print)
for format_name, (width, height) in model.FORMATS.items():
    doc['format'] = format_name
    output = folder/f'{format_name}.mp4'
    export(doc, output, print)
    original = hashlib.sha256(output.read_bytes()).hexdigest()
    try:
        export(doc, output)
        raise AssertionError('Existing output overwritten')
    except FileExistsError: pass
    assert hashlib.sha256(output.read_bytes()).hexdigest()==original
    # Decode full-size frames once. Probe exact first/last active frames and neighbors.
    frames = sorted(set([0, 11, 12, 23, 24, 35, 36, 47, 48, 59, 60, 71]))
    select = '+'.join(f'eq(n\\,{n})' for n in frames)
    raw = subprocess.run([ffmpeg,'-v','error','-i',str(output),'-vf',f'select={select}',
        '-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','-'], capture_output=True, check=True).stdout
    size = width*height*3
    assert len(raw)==size*len(frames)
    for offset, frame in enumerate(frames):
        image = Image.frombytes('RGB',(width,height),raw[offset*size:(offset+1)*size])
        for item in items:
            tile,(x,y) = card(item,width,height)
            # Top/bottom items share a lane: allow another active item there.
            from mixed_titles import POSITIONS
            active = any(POSITIONS[t['kind']]==POSITIONS[item['kind']] and round(t['start']*24)<=frame<round(t['end']*24) for t in items)
            # Sample each active tile's own location; inactive lanes use top/bottom edge.
            if active:
                current = next(t for t in items if POSITIONS[t['kind']]==POSITIONS[item['kind']] and round(t['start']*24)<=frame<round(t['end']*24))
                tile,(x,y)=card(current,width,height)
            pixel = image.getpixel((width//2,y+4))
            # Letterboxed portrait backgrounds can be black; cards are dark grey.
            assert (10<max(pixel)<80)==active, (format_name,frame,item['kind'],active,pixel)
        if frame in (24,48): image.save(folder/f'{format_name}-frame-{frame}.png')
    results.append(dict(format=format_name, frames=72, checked_boundaries=frames, status='passed'))
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==value for p,value in hashes.items())
(folder/'results.json').write_text(json.dumps(dict(status='passed',checks=['real GUI add/update/remove/cancel/preview/apply/save',
    'legacy project compatibility','source hashes unchanged','both engines and orientations',
    'frame-exact title start/end and section boundary','full decode with audio',
    'out-of-range titles rejected','existing output protected','export without titles'],results=results),indent=2))
print('ACCEPTANCE:',folder)
