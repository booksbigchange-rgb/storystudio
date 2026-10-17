"""Local documentary starters producing ordinary version-5 layer projects."""
import copy
import json
import math
import os
from pathlib import Path
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageOps
from project import write_project

KINDS = ('Evidence desk', 'Chronology', 'Map focus')
SIZES = {'widescreen': (1280, 720), 'portrait': (720, 1280)}


def validate(recipe):
    if not isinstance(recipe, dict) or recipe.get('kind') not in KINDS or recipe.get('format') not in SIZES:
        raise ValueError('Choose a documentary template and output format')
    result = copy.deepcopy(recipe)
    for key, limit in [('title', 100), ('detail', 400), ('source', 180)]:
        text = result.get(key)
        if not isinstance(text, str) or not text.strip() or len(text) > limit:
            raise ValueError(f'{key.title()} needs 1–{limit} characters')
        if any(ord(c)<32 and c!='\n' for c in text):
            raise ValueError('Text contains unsupported control characters')
    for key, default, low, high in [('seconds', 4, 1, 30), ('focus_x', .5, 0, 1), ('focus_y', .5, 0, 1)]:
        value = result.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError(f'{key} must be {low}–{high}')
        result[key] = value
    if result['kind']=='Chronology':
        events = [line.strip() for line in result['detail'].splitlines() if line.strip()]
        if not 1<=len(events)<=4 or any('|' not in line or not all(p.strip() for p in line.split('|',1)) for line in events):
            raise ValueError('Enter 1–4 events, one per line: date | description')
        result['detail'] = '\n'.join(events)
    elif not isinstance(result.get('image'), str) or not result['image']:
        raise ValueError('Choose your evidence image or map image')
    return result


def text_card(text, width, height, size, gold=False):
    font_path = Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/segoeui.ttf'
    image = Image.new('RGBA',(width,height),'#202A32')
    draw = ImageDraw.Draw(image)
    padding = max(12,round(min(width,height)*.12))
    for pixels in range(size,11,-1):
        font = ImageFont.truetype(str(font_path),pixels)
        lines = []
        for paragraph in text.splitlines():
            line = ''
            for word in paragraph.split(' '):
                proposed = (line+' '+word).strip()
                if draw.textlength(proposed,font=font)<=width-2*padding:
                    line=proposed
                else:
                    if line: lines.append(line)
                    line=''
                    for char in word:
                        if line and draw.textlength(line+char,font=font)>width-2*padding:
                            lines.append(line);line=''
                        line+=char
            lines.append(line)
        spacing=round(pixels*.25)
        box=draw.multiline_textbbox((0,0),'\n'.join(lines),font=font,spacing=spacing)
        if box[3]-box[1]<=height-2*padding:
            draw.rectangle((0,0,5,height),fill='#CDA76D')
            draw.multiline_text((padding,padding-box[1]),'\n'.join(lines),font=font,spacing=spacing,fill='#F1CF96' if gold else '#EFF2F4')
            return image
    raise ValueError('Text does not fit this layout; shorten it or use fewer events')


def create(recipe, parent):
    recipe = validate(recipe)
    width,height=SIZES[recipe['format']]
    portrait=height>width
    art=None
    if recipe['kind']!='Chronology':
        source=Path(recipe['image']).resolve()
        if source.stat().st_size>50*1024*1024:
            raise ValueError('Image must be under 50 MB')
        with Image.open(source) as raw:
            if raw.width*raw.height>25_000_000:
                raise ValueError('Image must be at most 25 megapixels')
            art=ImageOps.exif_transpose(raw).convert('RGB')
        recipe['image']=str(source)
    # Unique folder, exclusive creation; never write into an existing project.
    parent=Path(parent).resolve(); parent.mkdir(parents=True,exist_ok=True)
    folder=parent/('documentary-'+uuid.uuid4().hex)
    folder.mkdir()
    assets=folder/'assets'; assets.mkdir()
    bg=Image.new('RGB',(width,height),'#11191F')
    grid=ImageDraw.Draw(bg)
    for x in range(0,width,48): grid.line((x,0,x,height),fill='#172129')
    for y in range(0,height,48): grid.line((0,y,width,y),fill='#172129')
    bg.save(assets/'background.png')
    layers=[]
    def layer(image, name, box, reveal=False):
        x,y,w,h=box
        image.save(assets/(name+'.png'))
        pose=dict(x=(x+w/2)/width,y=(y+h/2)/height,size=w/width,angle=0,opacity=1)
        layers.append(dict(image=str(assets/(name+'.png')),name=name,easing='smooth',
                           start=dict(pose,opacity=.3 if reveal else 1),end=pose))
    margin=round(width*.06); content=width-2*margin
    header=(margin,round(height*.05),content,round(height*.14))
    layer(text_card(recipe['title'],header[2],header[3],38,True),'Title',header)
    footer=(margin,round(height*.87),content,round(height*.08))
    layer(text_card('SOURCE · '+recipe['source'],footer[2],footer[3],21),'Source',footer)
    if recipe['kind']=='Chronology':
        events=recipe['detail'].splitlines()
        gap=round(height*.025)
        card_h=round((height*.61-gap*(len(events)-1))/len(events))
        for i,event in enumerate(events):
            date,description=event.split('|',1)
            box=(margin,round(height*.23)+i*(card_h+gap),content,card_h)
            layer(text_card(f'{i+1:02d}   {date.strip()}\n{description.strip()}',content,card_h,30),'Event-'+str(i+1),box,True)
    else:
        if portrait:
            image_box=(margin,round(height*.23),content,round(height*.37))
            detail_box=(margin,round(height*.63),content,round(height*.20))
        else:
            image_box=(margin,round(height*.23),round(content*.60),round(height*.60))
            detail_box=(round(width*.64),round(height*.23),round(width*.30),round(height*.60))
        panel=Image.new('RGB',image_box[2:],'#25323A')
        fitted=ImageOps.contain(art,image_box[2:],Image.Resampling.LANCZOS)
        ox=(panel.width-fitted.width)//2;oy=(panel.height-fitted.height)//2
        panel.paste(fitted,(ox,oy))
        layer(panel,'Map' if recipe['kind']=='Map focus' else 'Evidence',image_box)
        # Store the displayed, orientation-correct source inside the new project.
        art.save(assets/'input.png'); recipe['image']='assets/input.png'
        if recipe['kind']=='Map focus':
            marker=Image.new('RGBA',(64,64)); draw=ImageDraw.Draw(marker)
            draw.ellipse((10,10,54,54),outline='#F5C778',width=5)
            draw.ellipse((27,27,37,37),fill='#F5C778')
            marker_size=round(min(width,height)*.07)
            cx=image_box[0]+ox+recipe['focus_x']*(fitted.width-1)
            cy=image_box[1]+oy+recipe['focus_y']*(fitted.height-1)
            layer(marker,'Focus marker',(cx-marker_size/2,cy-marker_size/2,marker_size,marker_size),True)
        layer(text_card(recipe['detail'],detail_box[2],detail_box[3],30),'Notes',detail_box,True)
    scene=dict(image=str(assets/'background.png'),duration=recipe['seconds'],layers=layers)
    path=folder/'story.json'
    write_project(path,[scene],output_format=recipe['format'])
    (folder/'template.json').write_text(json.dumps({**recipe,'template_version':1},indent=2,ensure_ascii=False),encoding='utf-8')
    return path


def load_recipe(path):
    path=Path(path).resolve()
    if path.stat().st_size>16384: raise ValueError('Template input exceeds 16 KB')
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict) or type(value.get('template_version')) is not int or value['template_version']!=1:
        raise ValueError('Unsupported template inputs')
    if value.get('image'): value['image']=str((path.parent/value['image']).resolve())
    return validate(value)
