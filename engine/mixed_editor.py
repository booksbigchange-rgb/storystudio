"""A shared section timeline for both established StoryStudio editors."""
import copy
import json
import math
from pathlib import Path
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import mixed_project as model
from mixed_control import MixedControl, RenderCancelled
from studio_hub import ROOT, command, project_kind


class MixedEditor:
    def __init__(self, root, path=None):
        self.root = root
        self.doc = model.load(path) if path else model.new_project()
        self.path = Path(path) if path else None
        self.dirty = False
        self.busy = False
        self.control = None
        self.events = queue.Queue()
        root.title('StoryStudio · Shared timeline')
        root.geometry('940x570')
        root.minsize(720, 420)
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='SHARED STORY TIMELINE', font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(frame, text='Arrange documentary and character projects as sections. Source scenes remain editable in their workspace.').pack(anchor='w', pady=10)
        footer = ttk.Frame(frame)
        footer.pack(side='bottom', fill='x')
        self.status = tk.StringVar(value='Add saved projects to begin. Linked source changes are included in the next export.')
        ttk.Label(footer, textvariable=self.status, wraplength=780).pack(fill='x', pady=8)
        controls = ttk.Frame(footer)
        controls.pack(fill='x')
        self.format = tk.StringVar(value=self.doc['format'])
        self.selector = ttk.Combobox(controls, textvariable=self.format, values=list(model.FORMATS), state='readonly', width=15)
        self.selector.pack(side='left')
        self.selector.bind('<<ComboboxSelected>>', self.change_format)
        self.buttons = []
        for label, action in [('Save timeline', self.save), ('Open timeline', self.open), ('Export MP4', self.export), ('Timed text', self.edit_titles), ('Audio mix', self.edit_audio)]:
            b = ttk.Button(controls, text=label, command=action)
            b.pack(side='right', padx=4)
            self.buttons.append(b)
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill='x', pady=6)
        self.cancel_button = ttk.Button(toolbar, text='Cancel export', command=self.cancel_export, state='disabled')
        self.cancel_button.pack(side='right', padx=3)
        for label, action in [('Add project', self.add), ('Edit source', self.edit), ('Move up', lambda:self.move(-1)),
                              ('Move down', lambda:self.move(1)), ('Remove', self.remove)]:
            b = ttk.Button(toolbar, text=label, command=action)
            b.pack(side='left', padx=3)
            self.buttons.append(b)
        self.items = tk.Listbox(frame, font=('Segoe UI',12), selectmode='browse')
        self.items.pack(fill='both', expand=True)
        self.timeline = tk.Canvas(frame, height=68, background='#11161c', highlightthickness=0)
        self.timeline.pack(fill='x', pady=8)
        self.timeline.bind('<Configure>', lambda _:self.draw_timeline())
        self.timeline.bind('<Button-1>', self.select_section)
        self.hitboxes = []
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_id = root.after(100, self.poll)

    def selected(self):
        choice = self.items.curselection()
        return choice[0] if choice else None

    def edit_titles(self):
        from mixed_titles_editor import TitlesEditor
        return TitlesEditor(self)

    def edit_audio(self):
        from mixed_audio_editor import AudioEditor
        return AudioEditor(self)

    def refresh(self, index=0):
        self.items.delete(0, 'end')
        for i, section in enumerate(self.doc['sections']):
            self.items.insert('end', f'{i+1:02d}  ·  {section["engine"]}  ·  {section["name"]}')
        if self.doc['sections']:
            self.items.selection_set(min(index, len(self.doc['sections'])-1))
        self.draw_timeline()

    def draw_timeline(self):
        self.timeline.delete('all')
        self.hitboxes = []
        durations = []
        for section in self.doc['sections']:
            try:
                path = Path(section['project'])
                if path.stat().st_size > 1024*1024:
                    raise ValueError('Source too large')
                source = json.loads(path.read_text(encoding='utf-8'))
                seconds = sum(float(s['duration']) for s in source['scenes'])
                if not math.isfinite(seconds) or seconds <= 0:
                    raise ValueError('Invalid duration')
                durations.append(seconds)
            except (OSError, ValueError, KeyError, TypeError):
                durations.append(None)
        total = sum(s or 1 for s in durations)
        if not total:
            return
        width = max(100,self.timeline.winfo_width())-16
        left = 8
        elapsed = 0
        for i, seconds in enumerate(durations):
            right = left+width*(seconds or 1)/total
            color = '#BA9155' if self.doc['sections'][i]['engine']=='documentary' else '#426a83'
            self.timeline.create_rectangle(left,8,right-2,44,fill=color,outline='')
            if right-left > 45:
                self.timeline.create_text((left+right)/2,25,text=f'{i+1} · {seconds:g}s' if seconds else f'{i+1} · missing',fill='white')
            self.timeline.create_text(left,55,text=f'{elapsed:g}s',anchor='w',fill='#D8D0BE')
            self.hitboxes.append((left,right,i))
            left = right
            elapsed += seconds or 0

    def select_section(self,event):
        for left,right,index in self.hitboxes:
            if left <= event.x <= right:
                self.items.selection_clear(0,'end')
                self.items.selection_set(index)
                break

    def add_path(self, path):
        kind = project_kind(path)
        if kind == 'mixed':
            raise ValueError('Add documentary or character projects, not a nested timeline')
        candidate = copy.deepcopy(self.doc)
        candidate['sections'].append(dict(engine=kind, project=str(Path(path).resolve()), name=Path(path).parent.name+' / '+Path(path).stem))
        self.doc = model.validate(candidate)
        self.dirty = True
        self.refresh(len(self.doc['sections'])-1)

    def add(self):
        path = filedialog.askopenfilename(parent=self.root, initialdir=ROOT/'projects', filetypes=[('StoryStudio project','*.json')])
        if path:
            try:
                self.add_path(path)
            except (ValueError,OSError) as exc:
                messagebox.showerror('Cannot add project', str(exc), parent=self.root)

    def move(self, delta):
        index = self.selected()
        if index is not None:
            target = model.move(self.doc, index, delta)
            self.dirty |= target != index
            self.refresh(target)

    def remove(self):
        index = self.selected()
        if index is not None:
            del self.doc['sections'][index]
            self.dirty = True
            self.refresh(max(0,index-1))

    def edit(self):
        index = self.selected()
        if index is not None:
            section = self.doc['sections'][index]
            subprocess.Popen(command(section['engine'], section['project']), cwd=ROOT)

    def change_format(self, _=None):
        self.doc['format'] = self.format.get()
        self.dirty = True

    def save(self):
        path = self.path or filedialog.asksaveasfilename(parent=self.root, initialdir=ROOT/'projects',
                initialfile='mixed-story.json', defaultextension='.json', filetypes=[('StoryStudio timeline','*.json')])
        if not path:
            return
        try:
            model.save(self.doc, path)
            self.path = Path(path)
            self.dirty = False
            self.status.set('Saved: '+str(path))
        except (ValueError,OSError) as exc:
            messagebox.showerror('Cannot save', str(exc), parent=self.root)

    def discard(self):
        return not self.dirty or messagebox.askyesno('Unsaved timeline', 'Discard unsaved timeline changes?', parent=self.root)

    def open(self):
        if not self.discard():
            return
        path = filedialog.askopenfilename(parent=self.root, initialdir=ROOT/'projects', filetypes=[('StoryStudio timeline','*.json')])
        if path:
            try:
                doc = model.load(path)
                self.doc, self.path, self.dirty = doc, Path(path), False
                self.format.set(doc['format'])
                self.refresh()
            except (ValueError,OSError) as exc:
                messagebox.showerror('Cannot open', str(exc), parent=self.root)

    def export(self):
        if not self.doc['sections']:
            self.status.set('Add at least one project first.')
            return
        path = filedialog.asksaveasfilename(parent=self.root, initialdir=ROOT/'exports', defaultextension='.mp4', filetypes=[('MP4 video','*.mp4')])
        if not path:
            return
        doc = copy.deepcopy(self.doc)
        self.busy = True
        self.control = MixedControl()
        self.cancel_button.state(['!disabled'])
        for button in self.buttons:
            button.state(['disabled'])
        self.selector.configure(state='disabled')
        self.status.set('Preparing source snapshots…')
        def worker():
            try:
                from mixed_render import export
                output = export(doc, path, lambda text:self.events.put(('status',text)), control=self.control)
                self.events.put(('done',str(output)))
            except RenderCancelled as exc:
                self.events.put(('cancelled',str(exc)))
            except Exception as exc:
                self.events.put(('error',str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def cancel_export(self):
        if self.busy and self.control:
            self.control.cancel()
            self.cancel_button.state(['disabled'])
            self.status.set('Canceling export and stopping its processes…')

    def poll(self):
        while not self.events.empty():
            kind, text = self.events.get_nowait()
            self.status.set(text)
            if kind != 'status':
                self.busy = False
                self.cancel_button.state(['disabled'])
                for button in self.buttons:
                    button.state(['!disabled'])
                self.selector.configure(state='readonly')
                if kind == 'error':
                    messagebox.showerror('Export failed', text, parent=self.root)
        self.poll_id = self.root.after(100,self.poll)

    def close(self):
        if self.busy:
            self.status.set('Cancel export or wait for it to finish before closing.')
        elif self.discard():
            self.root.after_cancel(self.poll_id)
            self.root.destroy()
