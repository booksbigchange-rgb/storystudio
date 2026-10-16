"""Modal title editor with literal-text layout preview."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageTk
from mixed_titles import KINDS, validate_titles, preview
from mixed_project import FORMATS


class TitlesEditor:
    def __init__(self, parent):
        self.parent = parent
        self.titles = copy.deepcopy(parent.doc.get('titles', []))
        self.window = tk.Toplevel(parent.root)
        self.window.title('Timed titles and captions')
        self.window.geometry('820x560')
        self.window.minsize(760, 520)
        self.window.transient(parent.root)
        self.window.grab_set()
        body = ttk.Frame(self.window, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Enter text → Add or Update → Apply to timeline. Times start at the beginning of the whole timeline.', wraplength=740).pack(anchor='w')
        ttk.Label(body, text='Title / Date appear at the top. Source / Caption appear at the bottom. Same-position items cannot overlap.', wraplength=740).pack(anchor='w', pady=6)
        columns = ttk.Frame(body)
        columns.pack(fill='both', expand=True)
        left = ttk.Frame(columns)
        left.pack(side='left', fill='both', expand=True)
        self.items = tk.Listbox(left, height=7, exportselection=False)
        self.items.pack(fill='x')
        self.items.bind('<<ListboxSelect>>', self.select)
        row = ttk.Frame(left)
        row.pack(fill='x', pady=8)
        self.kind = tk.StringVar(value='Title')
        self.start = tk.StringVar(value='0')
        self.end = tk.StringVar(value='2')
        ttk.Combobox(row, textvariable=self.kind, values=KINDS, state='readonly', width=9).pack(side='left')
        for label, variable in [('Start', self.start), ('End', self.end)]:
            ttk.Label(row, text=label).pack(side='left', padx=4)
            ttk.Entry(row, textvariable=variable, width=7).pack(side='left')
        self.text = tk.Text(left, height=5, width=35, wrap='word', font=('Segoe UI', 11))
        self.text.pack(fill='both', expand=True)
        actions = ttk.Frame(left)
        actions.pack(fill='x', pady=8)
        self.buttons = {}
        for label, action in [('Add', self.add), ('Update', self.update), ('Remove', self.remove), ('Preview', self.show_preview)]:
            button = ttk.Button(actions, text=label, command=action, width=8)
            button.pack(side='left', padx=2)
            self.buttons[label] = button
        right = ttk.Frame(columns, width=350)
        right.pack(side='right', fill='both', padx=(16, 0))
        ttk.Label(right, text='Text layout preview', font=('Segoe UI', 11, 'bold')).pack()
        self.picture = ttk.Label(right)
        self.picture.pack(expand=True)
        ttk.Label(right, text='Neutral background; source footage is shown in the export.', wraplength=320).pack()
        footer = ttk.Frame(body)
        footer.pack(fill='x', pady=(12, 0))
        ttk.Button(footer, text='Cancel', command=self.window.destroy).pack(side='right')
        ttk.Button(footer, text='Apply to timeline', command=self.apply).pack(side='right', padx=8)
        self.refresh()

    def value(self):
        item = dict(kind=self.kind.get(), text=self.text.get('1.0', 'end-1c'), start=float(self.start.get()), end=float(self.end.get()))
        validate_titles([item])
        return item

    def refresh(self):
        self.items.delete(0, 'end')
        for item in self.titles:
            self.items.insert('end', f'{item["start"]:g}–{item["end"]:g}s · {item["kind"]} · {item["text"][:30]}')

    def select(self, _=None):
        choice = self.items.curselection()
        if choice:
            item = self.titles[choice[0]]
            self.kind.set(item['kind']); self.start.set(str(item['start'])); self.end.set(str(item['end']))
            self.text.delete('1.0', 'end'); self.text.insert('1.0', item['text'])
            self.show_preview()

    def change(self, replace=False):
        try:
            candidate = copy.deepcopy(self.titles)
            item = self.value()
            if replace:
                choice = self.items.curselection()
                if not choice:
                    raise ValueError('Select an item to update')
                candidate[choice[0]] = item
            else:
                candidate.append(item)
            validate_titles(candidate)
            self.render_preview(item)
            self.titles = candidate
            self.refresh()
        except (ValueError, OSError) as exc:
            messagebox.showerror('Cannot change text', str(exc), parent=self.window)

    def add(self):
        self.change()

    def update(self):
        self.change(replace=True)

    def remove(self):
        choice = self.items.curselection()
        if choice:
            del self.titles[choice[0]]
            self.refresh()

    def render_preview(self, item):
        self.photo = ImageTk.PhotoImage(preview(item, *FORMATS[self.parent.doc['format']]))
        self.picture.configure(image=self.photo)

    def show_preview(self):
        try:
            self.render_preview(self.value())
        except (ValueError, OSError) as exc:
            messagebox.showerror('Cannot preview text', str(exc), parent=self.window)

    def apply(self):
        if self.titles != self.parent.doc.get('titles', []):
            self.parent.doc['titles'] = copy.deepcopy(self.titles)
            self.parent.dirty = True
            self.parent.status.set(f'{len(self.titles)} timed text items applied. Save the timeline to keep them.')
        self.window.destroy()
