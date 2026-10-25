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
import mixed_durations as durations
from mixed_history import History
from mixed_control import MixedControl, RenderCancelled
from studio_hub import ROOT, command, project_kind


def marks(section):
    """Short list markers for trims and transitions."""
    text = ''
    if 'trim_in' in section or 'trim_out' in section:
        text += '  ✂'
    transition = section.get('transition')
    if transition:
        text += f'  ⇄ {transition["kind"]} {transition["frames"]}f'
    return text


class MixedEditor:
    def __init__(self, root, path=None):
        self.root = root
        self.doc = model.load(path) if path else model.new_project()
        self.path = Path(path) if path else None
        self.dirty = False
        self.history = History()
        self.busy = False
        self.control = None
        self.events = queue.Queue()
        root.title('StoryStudio · Shared timeline')
        root.geometry('1120x620')
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
                              ('Move down', lambda:self.move(1)), ('To top', lambda:self.move_to(0)),
                              ('To bottom', lambda:self.move_to(10**6)), ('Duplicate', self.duplicate), ('Remove', self.remove),
                              ('Trim · split · transition', self.edit_section), ('Undo', self.undo), ('Redo', self.redo)]:
            b = ttk.Button(toolbar, text=label, command=action)
            b.pack(side='left', padx=3)
            self.buttons.append(b)
        self.summary = tk.StringVar()
        ttk.Label(frame, textvariable=self.summary).pack(anchor='w')
        lister = ttk.Frame(frame)
        lister.pack(fill='both', expand=True)
        scroll = ttk.Scrollbar(lister, orient='vertical')
        scroll.pack(side='right', fill='y')
        self.items = tk.Listbox(lister, font=('Segoe UI',12), selectmode='browse', exportselection=False, yscrollcommand=scroll.set)
        self.items.pack(side='left', fill='both', expand=True)
        scroll.configure(command=self.items.yview)
        self.timeline = tk.Canvas(frame, height=68, background='#11161c', highlightthickness=0)
        self.timeline.pack(fill='x', pady=8)
        self.timeline.bind('<Configure>', lambda _:self.draw_timeline())
        self.timeline.bind('<Button-1>', self.select_section)
        self.hitboxes = []
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Control-z>', lambda _: self.undo())
        root.bind('<Control-y>', lambda _: self.redo())
        self.poll_id = root.after(100, self.poll)

    def selected(self):
        choice = self.items.curselection()
        return choice[0] if choice else None

    def checkpoint(self):
        """Remember the timeline before a change so Undo can restore it."""
        self.history.checkpoint(self.doc)

    def restore(self, doc, index):
        self.doc = doc
        self.dirty = True
        self.format.set(doc['format'])
        self.refresh(index)

    def undo(self):
        if self.busy:
            return
        doc = self.history.undo(self.doc)
        if doc is None:
            self.status.set('Nothing to undo.')
        else:
            self.restore(doc, self.selected() or 0)
            self.status.set('Undid the last change.')

    def redo(self):
        if self.busy:
            return
        doc = self.history.redo(self.doc)
        if doc is None:
            self.status.set('Nothing to redo.')
        else:
            self.restore(doc, self.selected() or 0)
            self.status.set('Redid the change.')

    def edit_section(self):
        index = self.selected()
        if index is not None:
            from mixed_section_editor import SectionEditor
            return SectionEditor(self, index)

    def edit_titles(self):
        from mixed_titles_editor import TitlesEditor
        return TitlesEditor(self)

    def edit_audio(self):
        from mixed_audio_editor import AudioEditor
        return AudioEditor(self)

    def refresh(self, index=0):
        self.items.delete(0, 'end')
        rows, total = durations.timeline(self.doc)
        for i, (section, (start, count)) in enumerate(zip(self.doc['sections'], rows)):
            length = durations.clock(count) if count else 'missing'
            self.items.insert('end', f'{i+1:03d}  ·  {section["engine"]}  ·  {section["name"]}{marks(section)}  ·  {length}  ·  starts {durations.clock(start)}')
        if self.doc['sections']:
            self.items.selection_set(min(index, len(self.doc['sections'])-1))
            self.items.see(min(index, len(self.doc['sections'])-1))
        broken = sum(1 for _, count in rows if not count)
        self.summary.set(f'{len(self.doc["sections"])} of {model.MAX_SECTIONS} sections · total {durations.clock(total)}'
                         + (f' · {broken} source(s) missing or invalid' if broken else ''))
        self.draw_timeline()

    def draw_timeline(self):
        self.timeline.delete('all')
        self.hitboxes = []
        rows, total = durations.timeline(self.doc)
        if not rows:
            return
        weight = sum((count or 24) for _, count in rows)
        width = max(100,self.timeline.winfo_width())-16
        left = 8
        for i, (start, count) in enumerate(rows):
            right = left+width*(count or 24)/weight
            color = '#BA9155' if self.doc['sections'][i]['engine']=='documentary' else '#426a83'
            self.timeline.create_rectangle(left,8,max(left+1,right-(2 if right-left > 4 else 0)),44,fill=color if count else '#7a3030',outline='')
            if right-left > 45:
                self.timeline.create_text((left+right)/2,25,text=f'{i+1} · {count/24:g}s' if count else f'{i+1} · missing',fill='white')
                self.timeline.create_text(left,55,text=durations.clock(start),anchor='w',fill='#D8D0BE')
            self.hitboxes.append((left,right,i))
            left = right

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
        checked = model.validate(candidate)
        self.checkpoint()
        self.doc = checked
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
            self.checkpoint()
            target = model.move(self.doc, index, delta)
            self.dirty |= target != index
            self.refresh(target)

    def move_to(self, target):
        index = self.selected()
        if index is not None:
            self.checkpoint()
            new = model.move_to(self.doc, index, target)
            self.dirty |= new != index
            self.refresh(new)

    def duplicate(self):
        index = self.selected()
        if index is not None:
            before = copy.deepcopy(self.doc)
            try:
                new = model.duplicate(self.doc, index)
            except ValueError as exc:
                messagebox.showerror('Cannot duplicate', str(exc), parent=self.root)
                return
            self.history.checkpoint(before)
            self.dirty = True
            self.refresh(new)

    def remove(self):
        index = self.selected()
        if index is not None:
            self.checkpoint()
            del self.doc['sections'][index]
            self.dirty = True
            self.refresh(max(0,index-1))

    def edit(self):
        index = self.selected()
        if index is not None:
            section = self.doc['sections'][index]
            subprocess.Popen(command(section['engine'], section['project']), cwd=ROOT)

    def change_format(self, _=None):
        self.checkpoint()
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
                self.history.clear()
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
