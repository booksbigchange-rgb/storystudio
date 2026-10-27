"""Modal, non-destructive layer editor. Apply is one undoable scene edit."""
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from layers import POSE, EASINGS, layer_values, SceneCompositor, MOTION_PRESETS, motion_preset


class LayerEditor:
    def __init__(self, app):
        self.app = app
        self.index = app.selected()
        self.scene = copy.deepcopy(app.scenes[self.index])
        self.layers = layer_values(self.scene)
        self.current = None
        self.window = tk.Toplevel(app.root)
        self.window.title('Animate artwork layers')
        self.window.geometry('800x700')
        self.window.transient(app.root)
        self.window.grab_set()
        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Independent artwork motion', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Use transparent PNG artwork. Layers draw bottom to top. Background camera stays independent.').pack(anchor='w')
        self.items = tk.Listbox(frame, height=5, exportselection=False)
        self.items.pack(fill='x', pady=6)
        self.items.bind('<<ListboxSelect>>', self.select)
        bar = ttk.Frame(frame)
        bar.pack(fill='x')
        for label, command in [('Add artwork', self.add), ('Remove', self.remove),
                               ('Move behind', lambda: self.move(-1)), ('Move forward', lambda: self.move(1))]:
            ttk.Button(bar, text=label, command=command).pack(side='left', padx=2)
        ttk.Button(bar, text='Motion keys…', command=self.edit_keys).pack(side='left', padx=2)
        self.name = tk.StringVar(self.window)
        self.easing = tk.StringVar(self.window, 'smooth')
        metadata = ttk.Frame(frame)
        metadata.pack(fill='x', pady=8)
        ttk.Label(metadata, text='Name').pack(side='left')
        ttk.Entry(metadata, textvariable=self.name, width=30).pack(side='left', padx=6)
        ttk.Combobox(metadata, textvariable=self.easing, values=EASINGS, state='readonly', width=12).pack(side='left')
        poses = ttk.Frame(frame)
        poses.pack(fill='x')
        self.fields = {}
        for column, end in enumerate(('start', 'end')):
            box = ttk.LabelFrame(poses, text=end.title()+' pose', padding=8)
            box.grid(row=0, column=column, sticky='nsew', padx=4)
            poses.columnconfigure(column, weight=1)
            self.fields[end] = {}
            for row, (key, default) in enumerate(POSE.items()):
                variable = tk.StringVar(self.window, str(default))
                self.fields[end][key] = variable
                label = {'x':'X center (-1 to 2)', 'y':'Y center (-1 to 2)', 'size':'Width (0.01 to 3)',
                         'angle':'Rotation degrees', 'opacity':'Opacity (0 to 1)'}[key]
                ttk.Label(box, text=label).grid(row=row, column=0, sticky='w')
                ttk.Entry(box, textvariable=variable, width=10).grid(row=row, column=1, padx=8)
        ttk.Label(frame, text='X/Y: 0 = left/top, 1 = right/bottom. Width: 1 = full output width. Rotation is counterclockwise.').pack(anchor='w', pady=6)
        preview_bar = ttk.Frame(frame)
        preview_bar.pack(fill='x')
        for label, t in [('Preview start', 0), ('Preview middle', .5), ('Preview end', 1)]:
            ttk.Button(preview_bar, text=label, command=lambda t=t: self.preview(t)).pack(side='left', padx=3)
        self.preset = tk.StringVar(self.window, MOTION_PRESETS[0])
        ttk.Combobox(preview_bar, textvariable=self.preset, values=MOTION_PRESETS, state='readonly', width=16).pack(side='left', padx=3)
        ttk.Button(preview_bar, text='Use preset', command=self.apply_preset).pack(side='left')
        self.canvas = tk.Canvas(frame, height=185, bg='#e5eaf0', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, pady=6)
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        ttk.Button(actions, text='Cancel', command=self.window.destroy).pack(side='right')
        ttk.Button(actions, text='Apply to scene', command=self.apply).pack(side='right', padx=6)
        self.refresh(0 if self.layers else None)

    def store(self):
        if self.current is None:
            return True
        try:
            value = dict(self.layers[self.current], name=self.name.get(), easing=self.easing.get(),
                         **{end: {key: field.get() for key, field in fields.items()} for end, fields in self.fields.items()})
            self.layers[self.current] = layer_values({'layers': [value]})[0]
            return True
        except (ValueError, TypeError) as exc:
            messagebox.showerror('Invalid layer', str(exc), parent=self.window)
            return False

    def edit_keys(self):
        if self.current is not None and self.store():
            from layer_keys_editor import LayerKeysEditor
            return LayerKeysEditor(self)

    def refresh(self, selected):
        self.items.delete(0, 'end')
        for number, layer in enumerate(self.layers):
            self.items.insert('end', f'{number+1}. {layer["name"]}')
        self.current = selected
        if selected is not None:
            self.items.selection_set(selected)
            layer = self.layers[selected]
            self.name.set(layer['name'])
            self.easing.set(layer['easing'])
            for end, fields in self.fields.items():
                for key, field in fields.items():
                    field.set(str(layer[end][key]))

    def select(self, _event=None):
        selection = self.items.curselection()
        if not selection or selection[0] == self.current:
            return
        if self.store():
            self.refresh(selection[0])
        elif self.current is not None:
            self.items.selection_clear(0, 'end')
            self.items.selection_set(self.current)

    def add(self):
        if not self.store():
            return
        if len(self.layers) >= 8:
            messagebox.showinfo('Layer limit', 'Use at most eight artwork layers per scene.', parent=self.window)
            return
        path = filedialog.askopenfilename(parent=self.window, title='Add transparent artwork',
                                          filetypes=[('PNG artwork', '*.png'), ('Images', '*.png *.webp')])
        if path:
            try:
                from PIL import Image
                with Image.open(path) as image:
                    image.verify()
                self.layers.append(layer_values({'layers':[{'image':str(Path(path).resolve()),
                    'start':dict(POSE, x=.25), 'end':dict(POSE, x=.75)}]})[0])
                self.refresh(len(self.layers)-1)
                self.preview(.5)
            except (OSError, ValueError) as exc:
                messagebox.showerror('Artwork unavailable', str(exc), parent=self.window)

    def remove(self):
        if self.current is not None:
            del self.layers[self.current]
            self.refresh(min(self.current, len(self.layers)-1) if self.layers else None)

    def move(self, delta):
        if self.current is None or not self.store():
            return
        target = self.current+delta
        if 0 <= target < len(self.layers):
            self.layers[self.current], self.layers[target] = self.layers[target], self.layers[self.current]
            self.refresh(target)

    def preview(self, progress):
        if not self.store():
            return
        try:
            from PIL import ImageTk
            self.scene['layers'] = self.layers
            h = max(100, min(self.canvas.winfo_height()-6, (self.canvas.winfo_width()-12)/self.app.aspect))
            h = int(h)
            w = round(h*self.app.aspect)
            self.photo = ImageTk.PhotoImage(SceneCompositor(self.scene).frame(progress, w, h))
            self.canvas.delete('all')
            self.canvas.create_image(self.canvas.winfo_width()/2, self.canvas.winfo_height()/2, image=self.photo)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Preview unavailable', str(exc), parent=self.window)

    def apply(self):
        if self.store():
            self.app.checkpoint()
            self.app.scenes[self.index]['layers'] = copy.deepcopy(self.layers)
            self.app.changed()
            self.app.draw_preview()
            self.window.destroy()

    def apply_preset(self):
        if self.current is not None and self.store():
            self.layers[self.current] = motion_preset(self.layers[self.current], self.preset.get())
            self.refresh(self.current)
            self.preview(.5)
