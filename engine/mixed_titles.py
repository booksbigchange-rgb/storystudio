"""Small, deterministic title cards shared by both timeline renderers."""
import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

KINDS = ('Title', 'Date', 'Source', 'Caption')
POSITIONS = {'Title': 'top', 'Date': 'top', 'Source': 'bottom', 'Caption': 'bottom'}


def validate_titles(titles, duration=600):
    if not isinstance(titles, list) or len(titles) > 32:
        raise ValueError('Use at most 32 timed text items')
    for item in titles:
        if not isinstance(item, dict) or item.get('kind') not in KINDS:
            raise ValueError('Choose Title, Date, Source or Caption')
        text = item.get('text')
        if not isinstance(text, str) or not text.strip() or len(text) > 240:
            raise ValueError('Text must contain 1–240 characters')
        if any(ord(c) < 32 and c != '\n' for c in text):
            raise ValueError('Text contains unsupported control characters')
        start, end = item.get('start'), item.get('end')
        if any(type(t) not in (int, float) or not math.isfinite(t) for t in (start, end)):
            raise ValueError('Start and end must be finite seconds')
        if not 0 <= start < end <= duration or round(end*24) <= round(start*24):
            raise ValueError(f'Text must last at least one frame and fit within {duration:g} seconds')
    for i, item in enumerate(titles):
        for other in titles[:i]:
            if POSITIONS[item['kind']] == POSITIONS[other['kind']] and max(round(item['start']*24), round(other['start']*24)) < min(round(item['end']*24), round(other['end']*24)):
                raise ValueError('Text items in the same top or bottom position cannot overlap')
    return titles


def card(item, width, height):
    """Wrap literal text into a bounded RGBA card; no text reaches FFmpeg syntax."""
    font_path = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts/segoeui.ttf'
    margin = round(width*.06)
    pad = round(width*.025)
    limit = width-2*margin-2*pad
    size = round(min(width, height) * (.055 if item['kind']=='Title' else .038))
    probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    while size >= 12:
        font = ImageFont.truetype(str(font_path), size)
        lines = []
        for paragraph in item['text'].split('\n'):
            line = ''
            # Character wrapping also handles long URLs without clipping.
            for char in paragraph:
                if line and probe.textlength(line+char, font=font) > limit:
                    lines.append(line); line = ''
                line += char
            lines.append(line)
        spacing = round(size*.25)
        box = probe.multiline_textbbox((0, 0), '\n'.join(lines), font=font, spacing=spacing)
        if box[3]-box[1]+2*pad <= height*.30:
            break
        size -= 1
    else:
        raise ValueError('Text is too long for this format; shorten it or split it into separate items')
    image = Image.new('RGBA', (width-2*margin, box[3]-box[1]+2*pad), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, image.width-1, image.height-1), radius=pad, fill=(17, 22, 28, 232))
    draw.multiline_text((pad, pad-box[1]), '\n'.join(lines), font=font, spacing=spacing,
                        fill='#F5D28D' if item['kind']=='Date' else 'white')
    y = round(height*.05) if POSITIONS[item['kind']]=='top' else height-round(height*.08)-image.height
    return image, (margin, y)


def preview(item, width, height):
    image = Image.new('RGBA', (width, height), '#426a83')
    tile, xy = card(item, width, height)
    image.alpha_composite(tile, xy)
    image.thumbnail((340, 260))
    return image
