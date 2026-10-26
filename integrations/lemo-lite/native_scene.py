"""Pure-Pillow renderer for the cartoon scenes: no browser, same layout and motion as scene/scene.js.

The drawing code mirrors scene/characters.js and scene/scene.js shape by shape (Canvas2D calls become
affine-transformed polygons, antialiased by 2x supersampling). Motion math is shared with project.key_values.
"""
from __future__ import annotations

import math
from pathlib import Path
import os

from PIL import Image, ImageDraw, ImageFont

import project

TAU = math.tau
COLORS = {'meadow': ('#8cdeed', '#e1f5d0', '#75b896', '#98cf78'), 'sunset': ('#efb0b1', '#ffe0aa', '#bf91a3', '#d5b18c'),
          'night': ('#293e68', '#647fa2', '#526b80', '#749a91')}


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a+(b-a)*t


def seg(t, a, b):
    return clamp((t-a)/(b-a))


def ss(t):
    t = clamp(t)
    return t*t*(3-2*t)


def hash_(n):
    n = math.sin(n*127.1+311.7)*43758.5453
    return n-math.floor(n)


def color(value):
    """'#rrggbb', '#rrggbbaa' or 'white' → RGBA tuple."""
    if value == 'white':
        return (255, 255, 255, 255)
    value = value.lstrip('#')
    if len(value) == 6:
        value += 'ff'
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4, 6))


class Painter:
    """Canvas2D-like fills on a supersampled RGB image with a transform stack."""
    def __init__(self, image, scale):
        self.image = image
        self.draw = ImageDraw.Draw(image, 'RGBA')
        self.base = scale                              # logical unit → device pixels
        self.matrix = (scale, 0.0, 0.0, scale, 0.0, 0.0)
        self.stack = []

    def save(self):
        self.stack.append(self.matrix)

    def restore(self):
        self.matrix = self.stack.pop()

    def _mul(self, m):
        a, b, c, d, e, f = self.matrix
        p, q, r, s, t, u = m
        self.matrix = (a*p+c*q, b*p+d*q, a*r+c*s, b*r+d*s, a*t+c*u+e, b*t+d*u+f)

    def translate(self, x, y):
        self._mul((1, 0, 0, 1, x, y))

    def scale(self, sx, sy):
        self._mul((sx, 0, 0, sy, 0, 0))

    def rotate(self, angle):
        cos, sin = math.cos(angle), math.sin(angle)
        self._mul((cos, sin, -sin, cos, 0, 0))

    def point(self, x, y):
        a, b, c, d, e, f = self.matrix
        return (a*x+c*y+e, b*x+d*y+f)

    def factor(self):
        a, b, c, d, _, _ = self.matrix
        return math.sqrt(abs(a*d-b*c))

    def polygon(self, points, fill):
        if len(points) >= 3:
            self.draw.polygon([self.point(*p) for p in points], fill=color(fill))

    def ellipse(self, cx, cy, rx, ry, fill):
        steps = int(clamp(max(rx, ry)*self.factor()/2.2, 14, 120))
        self.polygon([(cx+rx*math.cos(TAU*i/steps), cy+ry*math.sin(TAU*i/steps)) for i in range(steps)], fill)

    def round_rect(self, x, y, w, h, r, fill):
        r = min(r, w/2, h/2)
        steps = max(3, int(r*self.factor()/3))
        pts = []
        for cx, cy, start in ((x+w-r, y+r, -90), (x+w-r, y+h-r, 0), (x+r, y+h-r, 90), (x+r, y+r, 180)):
            for i in range(steps+1):
                angle = math.radians(start+90*i/steps)
                pts.append((cx+r*math.cos(angle), cy+r*math.sin(angle)))
        self.polygon(pts, fill)

    def stroke(self, points, fill, width):
        """Round-capped polyline."""
        device = [self.point(*p) for p in points]
        w = max(1.0, width*self.factor())
        self.draw.line(device, fill=color(fill), width=round(w), joint='curve')
        for x, y in (device[0], device[-1]):
            self.draw.ellipse((x-w/2, y-w/2, x+w/2, y+w/2), fill=color(fill))


def pose_at(t, action='idle', speed=1.0):
    q = t*speed
    return dict(
        bob=abs(math.sin(q*7))*9 if action == 'walk' else math.sin(q*2)*2,
        jump=max(0, math.sin(q*3))*85 if action == 'jump' else 0,
        arm=-2.1+math.sin(q*8)*.4 if action == 'wave' else (-.2-.7*ss(seg(t, 3.3, 4.6)) if action == 'story' else -.2),
        leg=math.sin(q*7)*.35 if action == 'walk' else 0,
        blink=3.46 < q % 3.7 < 3.62,
        mouth=.3+.7*abs(math.sin(q*11)) if action == 'talk' else 0,
        tail=math.sin(q*4)*.12)


def draw_character(g, kind='fox', expression='happy', action='idle', speed=1.0, t=0.0, x=0.0, y=0.0, scale=1.0, tilt=0.0):
    p = pose_at(t, action, speed)
    fur = '#e98343' if kind == 'fox' else '#a97954' if kind == 'bear' else '#b5a1d5'
    dark = '#ac542f' if kind == 'fox' else '#76513e' if kind == 'bear' else '#8b78ac'
    cream = '#fff4ff' if kind == 'rabbit' else '#fff0d4'
    ellipse, path, rect = g.ellipse, g.polygon, g.round_rect
    g.save(); g.translate(x, y); g.scale(scale, scale)
    if tilt:
        g.translate(0, 100); g.rotate(tilt); g.translate(0, -100)
    ellipse(0, 102, 80-p['jump']*.3, 12, '#214e4429')
    g.translate(0, p['bob']-p['jump'])
    if kind == 'fox':
        g.save(); g.rotate(p['tail'])
        path([(35, 32), (108, -2), (138, -69), (166, -45), (151, 10), (100, 58), (45, 67)], fur)
        path([(138, -69), (166, -45), (151, 10), (121, 17), (128, -15)], cream); g.restore()
    else:
        ellipse(60, 49, 24 if kind == 'rabbit' else 17, 23, cream)
    for side in (-1, 1):
        g.save(); g.translate(side*28, 48); g.rotate(side*p['leg'])
        rect(-15, 0, 30, 52, 14, dark); ellipse(0, 51, 26, 13, cream); g.restore()
    ellipse(0, 16, 70, 78, fur); ellipse(0, 22, 42, 58, cream)
    for side in (-1, 1):
        g.save(); g.translate(side*51, -12); g.rotate(p['arm'] if side == 1 else .25-p['leg'])
        rect(-13, 0, 27, 69, 14, fur); ellipse(0, 64, 17, 16, cream); g.restore()
    if kind == 'fox':
        for s in (-1, 1):
            path([(s*72, -98), (s*81, -193), (s*8, -150)], dark)
            path([(s*59, -132), (s*68, -176), (s*27, -149)], '#eeb6a3')
    elif kind == 'rabbit':
        for s in (-1, 1):
            ellipse(s*44, -192, 25, 82, fur); ellipse(s*44, -194, 12, 58, '#f3c8d9')
    else:
        for s in (-1, 1):
            ellipse(s*70, -163, 34, 34, dark); ellipse(s*70, -163, 20, 20, '#eabda0')
    ellipse(0, -92, 92, 83, fur); ellipse(-52, -59, 40, 31, cream); ellipse(52, -59, 40, 31, cream)
    ellipse(0, -48, 39, 25, cream); ellipse(0, -62, 14, 10, '#c77f97' if kind == 'rabbit' else '#343b44')
    for s in (-1, 1):
        if p['blink']:
            rect(s*37-17, -105, 34, 5, 3, '#343b44')
        else:
            ellipse(s*37, -105, 8, 18 if expression == 'surprised' else 13, '#343b44')
            ellipse(s*37-2, -109, 2.5, 3.5, 'white')
        tilt_brow = s*8 if expression == 'sad' else -s*8 if expression == 'curious' else 0
        g.stroke([(s*37-14, -128+tilt_brow), (s*37+14, -128-tilt_brow)], dark, 4)
    if p['mouth'] or expression == 'surprised':
        ellipse(0, -38, 11 if expression == 'surprised' else 15, 8+p['mouth']*10, '#794740')
    else:
        sad = expression == 'sad'
        a0, a1 = (math.pi+.2, TAU-.2) if sad else (.2, math.pi-.2)
        cy = -27 if sad else -51
        g.stroke([(16*math.cos(a0+(a1-a0)*i/24), cy+16*math.sin(a0+(a1-a0)*i/24)) for i in range(25)], '#794740', 4)
    ellipse(-65, -77, 12, 6, '#f2a0a0'); ellipse(65, -77, 12, 6, '#f2a0a0')
    g.restore()


def _font(size):
    names = ['segoeuib.ttf', 'segoeui.ttf', 'DejaVuSans-Bold.ttf', 'arialbd.ttf', 'LiberationSans-Bold.ttf']
    folders = [Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts', Path('/usr/share/fonts/truetype/dejavu'), Path('/usr/share/fonts/truetype/liberation')]
    for name in names:
        for folder in folders:
            if (folder/name).is_file():
                return ImageFont.truetype(str(folder/name), size)
    return ImageFont.load_default()


def scene_at(t, scenes):
    start = 0.0
    for i, scene in enumerate(scenes):
        if t < start+scene['duration'] or i == len(scenes)-1:
            return scene, clamp(t-start, 0, scene['duration']), i
        start += scene['duration']


class NativeScene:
    """Renders ``document`` frames of ``width`` x ``height`` pixels. ``frame(t)`` returns an RGB image."""
    def __init__(self, document, width, height, supersample=2):
        self.doc = project.validate(document)
        self.width, self.height, self.ss = width, height, supersample
        self.portrait = self.doc['format'] == 'Shorts / TikTok 9:16'
        self.W, self.H = (720, 1280) if self.portrait else (1280, 720)
        self.scale = min(width/self.W, height/self.H)
        self.total = sum(s['duration'] for s in self.doc['scenes'])
        self.layers = {}                       # background name → (sky+sun image, hills overlay)

    def _layers(self, name):
        if name in self.layers:
            return self.layers[name]
        sky, light, far, near = (color(c) for c in COLORS[name])
        factor = self.scale*self.ss
        size = (round(self.W*factor), round(self.H*factor))
        base = Image.new('RGB', size)
        top, bottom = sky[:3], light[:3]
        d = ImageDraw.Draw(base)
        for row in range(size[1]):
            u = row/max(1, size[1]-1)
            d.line([(0, row), (size[0], row)], fill=tuple(round(lerp(top[i], bottom[i], u)) for i in range(3)))
        g = Painter(base, factor)
        g.ellipse(self.W*.82, self.H*.16, 58, 58, '#fff9db' if name == 'night' else '#fff1b7')
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        h = Painter.__new__(Painter)
        h.image = overlay; h.draw = ImageDraw.Draw(overlay); h.base = factor
        h.matrix = (factor, 0.0, 0.0, factor, 0.0, 0.0); h.stack = []
        h.ellipse(self.W*.24, self.H*.85, self.W*.75, self.H*.37, COLORS[name][2])
        h.ellipse(self.W*.9, self.H*.94, self.W*.8, self.H*.43, COLORS[name][3])
        for i in range(22):
            h.ellipse(hash_(i+1)*self.W, self.H*(.7+hash_(i+30)*.3), 4, 7, '#fff0b7')
        self.layers[name] = (base, overlay)
        return self.layers[name]

    def frame(self, t):
        t = clamp(t, 0, self.total)
        scene, local, _ = scene_at(t, self.doc['scenes'])
        W, H, portrait = self.W, self.H, self.portrait
        base, overlay = self._layers(scene['background'])
        image = base.copy()
        g = Painter(image, self.scale*self.ss)
        for i in range(4):
            x = (W*(i*.28+.08)+local*(i+1)*2) % (W+100)-40
            y = H*(.15+(i % 2)*.11)
            g.ellipse(x, y, 75, 22, '#ffffff85'); g.ellipse(x+24, y-13, 40, 30, '#ffffff85')
        image.paste(overlay, (0, 0), overlay)
        phase = local/scene['duration']*10
        k = project.key_values(scene, local/scene['duration'])
        action = k['action']
        base_x = W*(.29+k['x']*.45) if portrait else W*k['x']
        arrival = ss(seg(phase, .3, 2.1)) if action == 'story' else 1
        x = lerp(-150, base_x, arrival)
        walk = math.sin(local*.7*scene['speed'])*(45 if portrait else 110) if action == 'walk' else 0
        scale = (1.05 if portrait else 1.0)*k['size']
        y = (H*.64 if portrait else H*.63)-k['lift']
        jump = math.sin(math.pi*seg(phase, 5.15, 6.85))*80 if action == 'story' and 5.15 < phase < 6.85 else 0
        draw_character(g, kind=scene['character'], expression=k['expression'], action=action, speed=scene['speed'], t=local,
                       x=x+walk, y=y-jump, scale=scale, tilt=k['tilt'])
        sx = W*.76 if portrait else lerp(W*.82, W*.64, ss(seg(phase, 2.8, 5.4)))
        sy = (H*.29 if portrait else H*.33)+math.sin(local*3)*14
        g.ellipse(sx, sy, 65, 65, '#fff4bb42'); self.star(g, sx, sy, 48, '#ffe16c'); self.star(g, sx, sy-2, 36, '#fff3a0')
        g.ellipse(sx-10, sy-4, 3, 5, '#735f45'); g.ellipse(sx+10, sy-4, 3, 5, '#735f45')
        if scene['title'] and (action != 'story' or phase >= 7):
            self.caption(g, scene['title'])
        ratio = self.scale*self.ss
        picture = image.reduce(self.ss) if self.ss > 1 else image
        canvas = Image.new('RGB', (self.width, self.height), '#e7eee9')
        canvas.paste(picture, (round((self.width-picture.width)/2), round((self.height-picture.height)/2)))
        return canvas

    @staticmethod
    def star(g, x, y, r, fill):
        pts = []
        for i in range(10):
            angle = -math.pi/2+i*math.pi/5
            radius = r*.44 if i % 2 else r
            pts.append((x+math.cos(angle)*radius, y+math.sin(angle)*radius))
        g.polygon(pts, fill)

    def caption(self, g, text):
        size = 32 if self.portrait else 38
        font = _font(round(size*g.base))                       # measured in device pixels
        limit = self.W*.82*g.base
        lines, line = [], ''
        for ch in text:
            if font.getlength(line+ch) > limit:
                lines.append(line); line = ch
            else:
                line += ch
        if line:
            lines.append(line)
        height = len(lines)*(size+6)+30
        y = self.H*(.77 if self.portrait else .79)
        g.round_rect(self.W*.06, y, self.W*.88, height, 20, '#204e48ef')
        for i, text_line in enumerate(lines):
            x, top = g.point(self.W/2, y+15+i*(size+6))
            g.draw.text((x, top), text_line, font=font, fill=color('#fff9e9'), anchor='mt')


def preview_png(document, seconds, width, height):
    import io
    buffer = io.BytesIO()
    NativeScene(document, width, height).frame(seconds).save(buffer, 'PNG')
    return buffer.getvalue()
