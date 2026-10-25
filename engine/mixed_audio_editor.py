"""Modal editor for the shared mix: source level, music, ducking, narration and sound effects."""
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import mixed_audio as model

KINDS = {'Narration': 'narration', 'Sound effect': 'sfx'}
TYPES = [('Audio', ' '.join('*'+e for e in model.EXTENSIONS))]


class AudioEditor:
    def __init__(self, parent):
        self.parent = parent
        self.audio = model.validate_audio(parent.doc.get('audio')) or model.new_audio()
        self.window = tk.Toplevel(parent.root)
        self.window.title('Shared audio mix')
        self.window.geometry('860x600')
        self.window.minsize(780, 560)
        self.window.transient(parent.root)
        self.window.grab_set()
        body = ttk.Frame(self.window, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, wraplength=800, text='Source audio is the narration and sound already inside each section. Music loops under the whole '
                  'timeline and lowers automatically while anyone is speaking. Files stay on this computer and are never copied or changed.').pack(anchor='w')
        mix = ttk.LabelFrame(body, text='Levels (0 = silent, 1 = original, 2 = double)', padding=8)
        mix.pack(fill='x', pady=8)
        self.source_volume = tk.DoubleVar(value=self.audio['source_volume'])
        self.music_file = tk.StringVar(value=(self.audio['music'] or {}).get('file', ''))
        self.music_volume = tk.DoubleVar(value=(self.audio['music'] or {}).get('volume', .5))
        self.duck = tk.StringVar(value=self.audio['duck'])
        ttk.Label(mix, text='Source audio').grid(row=0, column=0, sticky='w')
        ttk.Scale(mix, from_=0, to=model.MAX_VOLUME, variable=self.source_volume, length=220).grid(row=0, column=1, padx=8)
        ttk.Label(mix, text='Music file').grid(row=1, column=0, sticky='w')
        ttk.Entry(mix, textvariable=self.music_file, width=48, state='readonly').grid(row=1, column=1, columnspan=2, padx=8, sticky='w')
        self.music_buttons = {}
        for column, (label, action) in enumerate([('Choose music…', self.choose_music), ('Clear music', self.clear_music)]):
            button = ttk.Button(mix, text=label, command=action)
            button.grid(row=1, column=3+column, padx=2)
            self.music_buttons[label] = button
        ttk.Label(mix, text='Music volume').grid(row=2, column=0, sticky='w')
        ttk.Scale(mix, from_=0, to=model.MAX_VOLUME, variable=self.music_volume, length=220).grid(row=2, column=1, padx=8)
        ttk.Label(mix, text='Lower music while speaking').grid(row=2, column=2, sticky='e')
        ttk.Combobox(mix, textvariable=self.duck, values=list(model.DUCKING), state='readonly', width=9).grid(row=2, column=3, sticky='w')
        clips = ttk.LabelFrame(body, text='Narration and sound-effect clips (times are from the start of the whole timeline)', padding=8)
        clips.pack(fill='both', expand=True)
        self.items = tk.Listbox(clips, height=6, exportselection=False)
        self.items.pack(fill='both', expand=True)
        self.items.bind('<<ListboxSelect>>', self.select)
        row = ttk.Frame(clips)
        row.pack(fill='x', pady=6)
        self.kind = tk.StringVar(value='Narration')
        self.file = tk.StringVar()
        self.start = tk.StringVar(value='0')
        self.volume = tk.StringVar(value='1')
        ttk.Combobox(row, textvariable=self.kind, values=list(KINDS), state='readonly', width=12).pack(side='left')
        ttk.Entry(row, textvariable=self.file, width=34, state='readonly').pack(side='left', padx=4)
        self.buttons = {}
        self.buttons['Browse'] = ttk.Button(row, text='Browse…', command=self.choose_clip)
        self.buttons['Browse'].pack(side='left')
        for label, variable in [('Start s', self.start), ('Volume', self.volume)]:
            ttk.Label(row, text=label).pack(side='left', padx=4)
            ttk.Entry(row, textvariable=variable, width=6).pack(side='left')
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

    def choose_music(self):
        path = filedialog.askopenfilename(parent=self.window, title='Choose music', filetypes=TYPES)
        if path:
            self.music_file.set(str(Path(path).resolve()))

    def clear_music(self):
        self.music_file.set('')

    def choose_clip(self):
        path = filedialog.askopenfilename(parent=self.window, title='Choose audio clip', filetypes=TYPES)
        if path:
            self.file.set(str(Path(path).resolve()))

    def current(self):
        try:
            clip = dict(file=self.file.get(), start=float(self.start.get()), volume=float(self.volume.get()))
        except ValueError:
            raise ValueError('Start and volume must be numbers') from None
        probe = {'narration': [], 'sfx': []}
        probe[KINDS[self.kind.get()]].append(clip)
        model.validate_audio(probe)
        return KINDS[self.kind.get()], clip

    def refresh(self):
        self.items.delete(0, 'end')
        for key, clip in self.entries:
            label = 'Narration' if key == 'narration' else 'Sound effect'
            self.items.insert('end', f'{clip["start"]:g}s · {label} · {Path(clip["file"]).name} · x{clip["volume"]:g}')

    def select(self, _=None):
        choice = self.items.curselection()
        if choice:
            key, clip = self.entries[choice[0]]
            self.kind.set('Narration' if key == 'narration' else 'Sound effect')
            self.file.set(clip['file']); self.start.set(str(clip['start'])); self.volume.set(str(clip['volume']))

    def change(self, replace=False):
        try:
            entry = self.current()
            candidate = list(self.entries)
            if replace:
                choice = self.items.curselection()
                if not choice:
                    raise ValueError('Select a clip to update')
                candidate[choice[0]] = entry
            else:
                candidate.append(entry)
            previous, self.entries = self.entries, candidate
            try:
                self.collect()
            except ValueError:
                self.entries = previous  # e.g. more clips than the timeline allows
                raise
            self.refresh()
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
        audio = dict(source_volume=round(float(self.source_volume.get()), 3), duck=self.duck.get(), narration=[], sfx=[],
                     music=dict(file=self.music_file.get(), volume=round(float(self.music_volume.get()), 3)) if self.music_file.get() else None)
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
