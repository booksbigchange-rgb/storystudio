"""Multi-lane audio timeline: music, narration and sound-effect clips drawn with waveforms and dragged in time."""
import tkinter as tk

LABEL = 78
LANES = (('music', 'Music', 22), ('narration', 'Narration', 68), ('sfx', 'Sound effects', 114))
LANE_HEIGHT = 40
COLORS = {'music': '#426a83', 'narration': '#BA9155', 'sfx': '#7a9f6a'}
FPS = 24


class AudioTimeline(tk.Canvas):
    """Draws ``entries`` [(kind, clip)] and ``music`` against a timeline of ``total`` seconds.

    ``on_select(index)`` and ``on_move(index, start_seconds)`` are called as the user clicks and drags.
    """
    def __init__(self, parent, on_select, on_move, **options):
        super().__init__(parent, height=162, background='#11161c', highlightthickness=0, **options)
        self.on_select, self.on_move = on_select, on_move
        self.entries, self.music, self.total, self.waves = [], None, 10.0, {}
        self.selected = None
        self.hitboxes = []
        self.grab = 0.0
        self.dragging = None
        self.bind('<Configure>', lambda _: self.redraw())
        self.bind('<ButtonPress-1>', lambda e: self.press(e.x, e.y))
        self.bind('<B1-Motion>', lambda e: self.drag(e.x))
        self.bind('<ButtonRelease-1>', lambda _: self.release())

    @property
    def scale(self):
        return max(40, self.winfo_width()-LABEL-10)/self.total

    def time_at(self, x):
        return (x-LABEL)/self.scale

    def set_data(self, entries, music, total, waves):
        self.entries, self.music, self.total, self.waves = entries, music, max(1.0, total), waves
        self.redraw()

    def select(self, index):
        self.selected = index
        self.redraw()

    def length(self, clip):
        wave = self.waves.get(clip['file'])
        return wave['duration'] if wave else 1.0

    def redraw(self):
        self.delete('all')
        self.hitboxes = []
        width = max(100, self.winfo_width())
        scale = self.scale
        step = 1 if self.total <= 30 else 5 if self.total <= 150 else 30 if self.total <= 900 else 120
        t = 0
        while t <= self.total:
            x = LABEL+t*scale
            self.create_line(x, 12, x, 156, fill='#232c36')
            self.create_text(x+2, 6, text=f'{int(t//60)}:{int(t%60):02d}', anchor='w', fill='#8fa09a', font=('Segoe UI', 8))
            t += step
        for kind, label, top in LANES:
            self.create_rectangle(LABEL, top, width-10, top+LANE_HEIGHT, outline='#232c36', fill='#161d25')
            self.create_text(6, top+LANE_HEIGHT/2, text=label, anchor='w', fill='#D8D0BE', font=('Segoe UI', 9))
        if self.music:
            top = LANES[0][2]
            self.bar(None, 'music', 0, self.total, self.music, top, loop=True)
        for index, (kind, clip) in enumerate(self.entries):
            top = next(t for k, _, t in LANES if k == kind)
            length = min(self.length(clip), max(.05, self.total-clip['start']))
            self.bar(index, kind, clip['start'], length, clip, top)

    def bar(self, index, kind, start, length, clip, top, loop=False):
        scale = self.scale
        x0, x1 = LABEL+start*scale, LABEL+(start+length)*scale
        x1 = max(x1, x0+6)
        chosen = index is not None and index == self.selected
        self.create_rectangle(x0, top+2, x1, top+LANE_HEIGHT-2, fill=COLORS[kind], outline='white' if chosen else '', width=2 if chosen else 0, stipple='' )
        wave = self.waves.get(clip['file'])
        middle = top+LANE_HEIGHT/2
        if wave:
            peaks, step = wave['peaks'], wave['step']
            gain = clip.get('volume', 1.0)
            for pixel in range(int(x0), int(min(x1, self.winfo_width()-10)), 2):
                moment = (pixel-x0)/scale
                if loop:
                    moment %= wave['duration']
                first = int(moment/step)
                last = max(first+1, int((moment+2/scale)/step))
                amplitude = min(1, max(peaks[first:last] or [0])*gain)
                self.create_line(pixel, middle-amplitude*(LANE_HEIGHT/2-5), pixel, middle+amplitude*(LANE_HEIGHT/2-5), fill='#f4efe2')
        else:
            self.create_text((x0+x1)/2, middle, text='…', fill='white')
        fade_in, fade_out = clip.get('fade_in', 0), clip.get('fade_out', 0)
        if fade_in:
            self.create_line(x0, top+LANE_HEIGHT-2, min(x1, x0+fade_in*scale), top+3, fill='#ffd166', width=2)
        if fade_out:
            self.create_line(max(x0, x1-fade_out*scale), top+3, x1, top+LANE_HEIGHT-2, fill='#ffd166', width=2)
        if index is not None:
            self.hitboxes.append((x0, top, x1, top+LANE_HEIGHT, index))

    def press(self, x, y):
        for x0, y0, x1, y1, index in reversed(self.hitboxes):
            if x0 <= x <= x1 and y0 <= y <= y1:
                self.selected = index
                self.grab = self.time_at(x)-self.entries[index][1]['start']
                self.dragging = index
                self.on_select(index)
                self.redraw()
                return index
        self.dragging = None
        return None

    def drag(self, x):
        if self.dragging is None:
            return None
        clip = self.entries[self.dragging][1]
        start = self.time_at(x)-self.grab
        latest = max(0, int((self.total-.1)*FPS))/FPS            # last whole frame that still leaves 0.1 s inside the story
        start = min(max(0, round(start*FPS)/FPS), latest)
        if start != clip['start']:
            self.on_move(self.dragging, start)
        return start

    def release(self):
        self.dragging = None
