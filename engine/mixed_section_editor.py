"""Modal editor for one section: trim, split and the transition into it."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
import mixed_durations as durations
import mixed_edit
import mixed_project as model

FPS = durations.FPS
KINDS = {'Cut': None, 'Dissolve (overlap)': 'dissolve', 'Dip to black': 'fade'}


class SectionEditor:
    def __init__(self, parent, index):
        self.parent, self.index = parent, index
        self.section = parent.doc['sections'][index]
        source = durations.section_frames(self.section)
        self.window = tk.Toplevel(parent.root)
        self.window.title('Section: trim, split and transition')
        self.window.geometry('560x420')
        self.window.transient(parent.root)
        self.window.grab_set()
        body = ttk.Frame(self.window, padding=16)
        body.pack(fill='both', expand=True)
        self.message = tk.StringVar()
        if source is None:
            self.message.set('The source project is missing or unreadable, so trimming is unavailable.')
        ttk.Label(body, text=f'“{self.section["name"]}” — {source or "?"} source frames ({(source or 0)/FPS:.2f} s).', wraplength=520).pack(anchor='w')
        grid = ttk.LabelFrame(body, text='Trim (seconds in the source; leave end blank for the whole rest)', padding=8)
        grid.pack(fill='x', pady=8)
        self.source = source
        self.first = tk.StringVar(value=f'{self.section.get("trim_in", 0)/FPS:g}')
        self.end = tk.StringVar(value=f'{self.section["trim_out"]/FPS:g}' if 'trim_out' in self.section else '')
        ttk.Label(grid, text='Start').grid(row=0, column=0)
        ttk.Entry(grid, textvariable=self.first, width=9).grid(row=0, column=1, padx=6)
        ttk.Label(grid, text='End').grid(row=0, column=2)
        ttk.Entry(grid, textvariable=self.end, width=9).grid(row=0, column=3, padx=6)
        transition = self.section.get('transition') or {}
        label = next((k for k, v in KINDS.items() if v == transition.get('kind')), 'Cut')
        self.kind = tk.StringVar(value=label)
        self.length = tk.StringVar(value=f'{transition.get("frames", 12)/FPS:g}')
        box = ttk.LabelFrame(body, text='Transition from the previous section (not used on the first section)', padding=8)
        box.pack(fill='x', pady=8)
        ttk.Combobox(box, textvariable=self.kind, values=list(KINDS), state='readonly', width=20).grid(row=0, column=0)
        ttk.Label(box, text='Seconds').grid(row=0, column=1, padx=6)
        ttk.Entry(box, textvariable=self.length, width=7).grid(row=0, column=2)
        ttk.Label(box, text='Dissolve overlaps the two sections, so the story gets shorter by that time.\n'
                  'Dip to black fades the previous section out and this one in without changing the length.', foreground='#61766f').grid(row=1, column=0, columnspan=4, sticky='w', pady=4)
        split = ttk.LabelFrame(body, text='Split this section in two (seconds from its current start)', padding=8)
        split.pack(fill='x', pady=8)
        self.at = tk.StringVar(value='1')
        ttk.Entry(split, textvariable=self.at, width=9).pack(side='left')
        self.buttons = {}
        self.buttons['Split'] = ttk.Button(split, text='Split here', command=self.split)
        self.buttons['Split'].pack(side='left', padx=8)
        ttk.Label(body, textvariable=self.message, foreground='#a02535', wraplength=520).pack(anchor='w')
        footer = ttk.Frame(body)
        footer.pack(side='bottom', fill='x')
        ttk.Button(footer, text='Cancel', command=self.window.destroy).pack(side='right')
        self.apply_button = ttk.Button(footer, text='Apply', command=self.apply)
        self.apply_button.pack(side='right', padx=8)

    def frames(self, text, label):
        try:
            seconds = float(text)
        except ValueError:
            raise ValueError(f'{label} must be a number of seconds') from None
        if seconds < 0 or seconds != seconds:
            raise ValueError(f'{label} cannot be negative')
        return round(seconds*FPS)

    def candidate(self):
        section = copy.deepcopy(self.section)
        for key in ('trim_in', 'trim_out', 'transition'):
            section.pop(key, None)
        first = self.frames(self.first.get(), 'Trim start')
        if first:
            section['trim_in'] = first
        if self.end.get().strip():
            section['trim_out'] = self.frames(self.end.get(), 'Trim end')
        kind = KINDS[self.kind.get()]
        if kind and self.index:
            section['transition'] = dict(kind=kind, frames=self.frames(self.length.get(), 'Transition length'))
        if self.source:
            mixed_edit.window(section, self.source)
        return section

    def commit(self, sections, select):
        doc = copy.deepcopy(self.parent.doc)
        doc['sections'] = sections
        doc = model.validate(doc)
        self.parent.checkpoint()
        self.parent.doc = doc
        self.parent.dirty = True
        self.parent.refresh(select)

    def apply(self):
        try:
            section = self.candidate()
            sections = copy.deepcopy(self.parent.doc['sections'])
            sections[self.index] = section
            known = [durations.section_frames(s) for s in sections]
            if all(known):
                mixed_edit.plan(sections, known)  # reject impossible trim/transition combinations now, not at export
            if section != self.section:
                self.commit(sections, self.index)
        except ValueError as exc:
            self.message.set(str(exc))
            messagebox.showerror('Cannot apply', str(exc), parent=self.window)
            return
        self.window.destroy()

    def split(self):
        try:
            if not self.source:
                raise ValueError('The source project is missing, so it cannot be split.')
            current = self.candidate()
            left, right = mixed_edit.split(current, self.frames(self.at.get(), 'Split time'), self.source)
            sections = copy.deepcopy(self.parent.doc['sections'])
            sections[self.index:self.index+1] = [left, right]
            self.commit(sections, self.index+1)
        except ValueError as exc:
            self.message.set(str(exc))
            messagebox.showerror('Cannot split', str(exc), parent=self.window)
            return
        self.window.destroy()
