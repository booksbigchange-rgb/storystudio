"""Modal editor for the shared mix: levels, music, ducking and a draggable multi-lane clip timeline."""
import copy
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import mixed_audio as model
import mixed_durations as durations
from mixed_audio_timeline import AudioTimeline
from studio_hub import ROOT
from waveform import WaveformJob

KINDS = {'Narration': 'narration', 'Sound effect': 'sfx'}
TYPES = [('Audio', ' '.join('*'+e for e in model.EXTENSIONS))]


class AudioEditor:
    def __init__(self, parent):
        self.parent = parent
        self.audio = model.validate_audio(parent.doc.get('audio')) or model.new_audio()
        self.waves, self.requested, self.wave_events = {}, set(), queue.Queue()
        self.window = tk.Toplevel(parent.root)
        self.window.title('Shared audio mix')
        self.window.geometry('900x780')
        self.window.minsize(820, 700)
        self.window.transient(parent.root)
        self.window.grab_set()
        body = ttk.Frame(self.window, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, wraplength=840, text='Source audio is the narration and sound already inside each section. Music loops under the whole '
                  'timeline and lowers while anyone is speaking. Drag clips on the timeline to move them. Files stay on this computer and are never changed.').pack(anchor='w')
        mix = ttk.LabelFrame(body, text='Levels (0 = silent, 1 = original, 2 = double)', padding=8)
        mix.pack(fill='x', pady=8)
        music = self.audio['music'] or {}
        self.source_volume = tk.DoubleVar(value=self.audio['source_volume'])
        self.music_file = tk.StringVar(value=music.get('file', ''))
        self.music_volume = tk.DoubleVar(value=music.get('volume', .5))
        self.music_fade_in = tk.StringVar(value=f"{music.get('fade_in', .5):g}")
        self.music_fade_out = tk.StringVar(value=f"{music.get('fade_out', 1.5):g}")
        self.duck = tk.StringVar(value=self.audio['duck'])
        ttk.Label(mix, text='Source audio').grid(row=0, column=0, sticky='w')
        ttk.Scale(mix, from_=0, to=model.MAX_VOLUME, variable=self.source_volume, length=220, command=lambda _: self.redraw()).grid(row=0, column=1, padx=8)
        ttk.Label(mix, text='Music file').grid(row=1, column=0, sticky='w')
        ttk.Entry(mix, textvariable=self.music_file, width=48, state='readonly').grid(row=1, column=1, columnspan=2, padx=8, sticky='w')
        self.music_buttons = {}
        for column, (label, action) in enumerate([('Choose music…', self.choose_music), ('Clear music', self.clear_music)]):
            button = ttk.Button(mix, text=label, command=action)
            button.grid(row=1, column=3+column, padx=2)
            self.music_buttons[label] = button
        ttk.Label(mix, text='Music volume').grid(row=2, column=0, sticky='w')
        ttk.Scale(mix, from_=0, to=model.MAX_VOLUME, variable=self.music_volume, length=220, command=lambda _: self.redraw()).grid(row=2, column=1, padx=8)
        ttk.Label(mix, text='Lower music while speaking').grid(row=2, column=2, sticky='e')
        ttk.Combobox(mix, textvariable=self.duck, values=list(model.DUCKING), state='readonly', width=9).grid(row=2, column=3, sticky='w')
        ttk.Label(mix, text='Music fade in / out (s)').grid(row=3, column=0, sticky='w')
        fades = ttk.Frame(mix)
        fades.grid(row=3, column=1, sticky='w', padx=8)
        for variable in (self.music_fade_in, self.music_fade_out):
            entry = ttk.Entry(fades, textvariable=variable, width=6)
            entry.pack(side='left', padx=2)
            entry.bind('<FocusOut>', lambda _: self.redraw())
        self.timeline = AudioTimeline(body, self.timeline_selected, self.timeline_moved)
        self.timeline.pack(fill='x', pady=6)
        clips = ttk.LabelFrame(body, text='Narration and sound-effect clips (times are from the start of the whole timeline)', padding=8)
        clips.pack(fill='both', expand=True)
        self.items = tk.Listbox(clips, height=5, exportselection=False)
        self.items.pack(fill='both', expand=True)
        self.items.bind('<<ListboxSelect>>', self.select)
        row = ttk.Frame(clips)
        row.pack(fill='x', pady=6)
        self.kind = tk.StringVar(value='Narration')
        self.file = tk.StringVar()
        self.start = tk.StringVar(value='0')
        self.volume = tk.StringVar(value='1')
        self.fade_in = tk.StringVar(value='0')
        self.fade_out = tk.StringVar(value='0')
        ttk.Combobox(row, textvariable=self.kind, values=list(KINDS), state='readonly', width=12).pack(side='left')
        ttk.Entry(row, textvariable=self.file, width=28, state='readonly').pack(side='left', padx=4)
        self.buttons = {}
        self.buttons['Browse'] = ttk.Button(row, text='Browse…', command=self.choose_clip)
        self.buttons['Browse'].pack(side='left')
        for label, variable in [('Start s', self.start), ('Volume', self.volume), ('Fade in', self.fade_in), ('Fade out', self.fade_out)]:
            ttk.Label(row, text=label).pack(side='left', padx=3)
            ttk.Entry(row, textvariable=variable, width=5).pack(side='left')
        actions = ttk.Frame(clips)
        actions.pack(fill='x')
        for label, action in [('Add', self.add), ('Update', self.update), ('Remove', self.remove)]:
            self.buttons[label] = ttk.Button(actions, text=label, command=action, width=9)
            self.buttons[label].pack(side='left', padx=2)
        footer = ttk.Frame(body)
        footer.pack(fill='x', pady=(10, 0))
        ttk.Button(footer, text='Cancel', command=self.window.destroy).pack(side='right')
        self.apply_button = ttk.Button(footer, text='Apply to timeline', command=self.apply)
        self.apply_button.pack(side='right', padx=8)
        self.entries = [(k, c) for k in ('narration', 'sfx') for c in self.audio[k]]
        self.refresh()
        self.window.after(150, self.poll_waves)

    # --- waveforms: decoded off the UI thread, cached on disk, drawn when they arrive -----------------
    def request_wave(self, path):
        if not path or path in self.requested or not Path(path).is_file():
            return
        self.requested.add(path)
        import mixed_render
        job = WaveformJob(path, mixed_render.tool('ffmpeg'), ROOT/'cache'/'waveforms', lambda data, error, p=path: self.wave_events.put((p, data)))
        threading.Thread(target=job.run, daemon=True).start()

    def poll_waves(self):
        if not self.window.winfo_exists():
            return
        changed = False
        while not self.wave_events.empty():
            path, data = self.wave_events.get_nowait()
            if data:
                self.waves[path] = data
                changed = True
        if changed:
            self.redraw()
        self.window.after(150, self.poll_waves)

    # --- timeline ------------------------------------------------------------------------------------
    def total_seconds(self):
        return max(1.0, durations.timeline(self.parent.doc)[1]/durations.FPS)

    def redraw(self):
        for _, clip in self.entries:
            self.request_wave(clip['file'])
        self.request_wave(self.music_file.get())
        music = None
        if self.music_file.get():
            music = dict(file=self.music_file.get(), volume=self.music_volume.get())
            for name, variable in (('fade_in', self.music_fade_in), ('fade_out', self.music_fade_out)):
                try:
                    music[name] = float(variable.get())
                except ValueError:
                    music[name] = 0
        self.timeline.set_data(self.entries, music, self.total_seconds(), self.waves)

    def timeline_selected(self, index):
        self.items.selection_clear(0, 'end')
        self.items.selection_set(index)
        self.select()

    def timeline_moved(self, index, start):
        key, clip = self.entries[index]
        clip['start'] = start
        self.start.set(f'{start:g}')
        self.refresh(keep=index)

    # --- editing ---------------------------------------------------------------------------------------
    def choose_music(self):
        path = filedialog.askopenfilename(parent=self.window, title='Choose music', filetypes=TYPES)
        if path:
            self.music_file.set(str(Path(path).resolve()))
            self.redraw()

    def clear_music(self):
        self.music_file.set('')
        self.redraw()

    def choose_clip(self):
        path = filedialog.askopenfilename(parent=self.window, title='Choose audio clip', filetypes=TYPES)
        if path:
            self.file.set(str(Path(path).resolve()))

    def current(self):
        try:
            clip = dict(file=self.file.get(), start=float(self.start.get()), volume=float(self.volume.get()),
                        fade_in=float(self.fade_in.get()), fade_out=float(self.fade_out.get()))
        except ValueError:
            raise ValueError('Start, volume and fades must be numbers') from None
        probe = {'narration': [], 'sfx': []}
        probe[KINDS[self.kind.get()]].append(clip)
        model.validate_audio(probe)
        return KINDS[self.kind.get()], clip

    def refresh(self, keep=None):
        self.items.delete(0, 'end')
        for key, clip in self.entries:
            label = 'Narration' if key == 'narration' else 'Sound effect'
            self.items.insert('end', f'{clip["start"]:g}s · {label} · {Path(clip["file"]).name} · x{clip["volume"]:g}'
                              + (f' · fade {clip["fade_in"]:g}/{clip["fade_out"]:g}' if clip['fade_in'] or clip['fade_out'] else ''))
        if keep is not None and keep < len(self.entries):
            self.items.selection_set(keep)
        self.timeline.selected = keep
        self.redraw()

    def select(self, _=None):
        choice = self.items.curselection()
        if choice:
            key, clip = self.entries[choice[0]]
            self.kind.set('Narration' if key == 'narration' else 'Sound effect')
            self.file.set(clip['file']); self.start.set(f'{clip["start"]:g}'); self.volume.set(str(clip['volume']))
            self.fade_in.set(f'{clip["fade_in"]:g}'); self.fade_out.set(f'{clip["fade_out"]:g}')
            self.timeline.select(choice[0])

    def change(self, replace=False):
        try:
            entry = self.current()
            candidate = list(self.entries)
            chosen = self.items.curselection()
            if replace:
                if not chosen:
                    raise ValueError('Select a clip to update')
                candidate[chosen[0]] = entry
            else:
                candidate.append(entry)
            previous, self.entries = self.entries, candidate
            try:
                self.collect()
            except ValueError:
                self.entries = previous  # e.g. more clips than the timeline allows
                raise
            self.refresh(keep=chosen[0] if replace else len(candidate)-1)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Cannot change clip', str(exc), parent=self.window)

    def add(self):
        self.change()

    def update(self):
        self.change(replace=True)

    def remove(self):
        choice = self.items.curselection()
        if choice:
            del self.entries[choice[0]]
            self.refresh()

    def collect(self):
        music = None
        if self.music_file.get():
            try:
                fades = dict(fade_in=float(self.music_fade_in.get()), fade_out=float(self.music_fade_out.get()))
            except ValueError:
                raise ValueError('Music fades must be numbers') from None
            music = dict(file=self.music_file.get(), volume=round(float(self.music_volume.get()), 3), **fades)
        audio = dict(source_volume=round(float(self.source_volume.get()), 3), duck=self.duck.get(), narration=[], sfx=[], music=music)
        for key, clip in self.entries:
            audio[key].append(copy.deepcopy(clip))
        return model.validate_audio(audio)

    def apply(self):
        try:
            audio = self.collect()
            missing = [f'{label}: {name}' for label, name in model.media_files(audio) if not Path(name).is_file()]
            if missing:
                raise FileNotFoundError('Audio file not found — '+missing[0])
        except (ValueError, OSError) as exc:
            messagebox.showerror('Cannot apply audio', str(exc), parent=self.window)
            return
        stored = audio if model.active(audio) else None
        if stored != self.parent.doc.get('audio'):
            self.parent.checkpoint()
            if stored is None:
                self.parent.doc.pop('audio', None)
            else:
                self.parent.doc['audio'] = stored
            self.parent.dirty = True
            self.parent.status.set('Shared audio mix applied. Save the timeline to keep it.' if stored else 'Shared audio mix cleared. Section audio is unchanged.')
        self.window.destroy()
