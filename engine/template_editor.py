"""Documentary template inputs; generated projects remain ordinary editable layers."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk
from documentary_templates import KINDS, SIZES, create, load_recipe
from layers import SceneCompositor
from project import read_project


class TemplateEditor:
    def __init__(self, root, destination, on_open):
        self.destination=destination; self.on_open=on_open; self.created=None
        self.window=tk.Toplevel(root); self.window.title('Documentary templates')
        self.window.geometry('900x650'); self.window.minsize(820,600)
        body=ttk.Frame(self.window,padding=18);body.pack(fill='both',expand=True)
        ttk.Label(body,text='DOCUMENTARY TEMPLATES',font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(body,text='Use your own text and images. Each creation saves a new project; existing projects stay unchanged.',wraplength=800).pack(anchor='w',pady=8)
        footer=ttk.Frame(body);footer.pack(side='bottom',fill='x')
        row=ttk.Frame(body);row.pack(fill='x')
        self.kind=tk.StringVar(value=KINDS[0]);self.format=tk.StringVar(value='widescreen')
        ttk.Combobox(row,textvariable=self.kind,values=KINDS,state='readonly',width=20).pack(side='left')
        ttk.Combobox(row,textvariable=self.format,values=list(SIZES),state='readonly',width=15).pack(side='left',padx=8)
        self.seconds=tk.StringVar(value='4')
        ttk.Label(row,text='Seconds').pack(side='left');ttk.Entry(row,textvariable=self.seconds,width=6).pack(side='left',padx=5)
        self.title=tk.StringVar();self.source=tk.StringVar();self.image=tk.StringVar()
        for label,var in [('Title',self.title),('Source / credit (required)',self.source),('Evidence or map image (not needed for chronology)',self.image)]:
            ttk.Label(body,text=label).pack(anchor='w',pady=(8,0))
            ttk.Entry(body,textvariable=var).pack(fill='x')
        ttk.Button(body,text='Choose image…',command=self.browse).pack(anchor='w',pady=5)
        ttk.Label(body,text='Notes, or 1–4 chronology lines: date | event description').pack(anchor='w')
        middle=ttk.Frame(body);middle.pack(fill='both',expand=True)
        self.detail=tk.Text(middle,height=6,width=40,wrap='word',font=('Segoe UI',11));self.detail.pack(side='left',fill='both',expand=True)
        self.preview=ttk.Label(middle);self.preview.pack(side='right',padx=12)
        focus=ttk.Frame(footer);focus.pack(fill='x',pady=8)
        ttk.Label(focus,text='Map point (0–1 across/down the image):').pack(side='left')
        self.x=tk.StringVar(value='.5');self.y=tk.StringVar(value='.5')
        for label,var in [('X',self.x),('Y',self.y)]:
            ttk.Label(focus,text=label).pack(side='left',padx=5);ttk.Entry(focus,textvariable=var,width=6).pack(side='left')
        self.status=tk.StringVar(value='Map focus marks the point you choose; it does not geocode locations.')
        ttk.Label(footer,textvariable=self.status,wraplength=800).pack(fill='x',pady=6)
        buttons=ttk.Frame(footer);buttons.pack(fill='x')
        ttk.Button(buttons,text='Load template inputs…',command=self.load).pack(side='left')
        self.create_button=ttk.Button(buttons,text='Create new project',command=self.generate);self.create_button.pack(side='left',padx=8)
        self.open_button=ttk.Button(buttons,text='Open generated project',command=self.open,state='disabled');self.open_button.pack(side='right')

    def browse(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('Images','*.png *.jpg *.jpeg *.webp')])
        if path:self.image.set(path)

    def recipe(self):
        return dict(kind=self.kind.get(),format=self.format.get(),title=self.title.get(),source=self.source.get(),image=self.image.get(),
                    detail=self.detail.get('1.0','end-1c'),seconds=float(self.seconds.get()),focus_x=float(self.x.get()),focus_y=float(self.y.get()))

    def generate(self):
        try:
            self.created=create(self.recipe(),self.destination)
            doc=read_project(self.created); width,height=SIZES[doc['format']]
            image=SceneCompositor(doc['scenes'][0]).frame(1,width,height);image.thumbnail((250,170))
            self.photo=ImageTk.PhotoImage(image);self.preview.configure(image=self.photo)
            self.open_button.state(['!disabled']);self.status.set('Created: '+str(self.created))
        except (ValueError,OSError) as exc:
            messagebox.showerror('Cannot create template',str(exc),parent=self.window)

    def load(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('Template inputs','template.json')])
        if path:
            try:
                value=load_recipe(path)
                for key,var in [('kind',self.kind),('format',self.format),('title',self.title),('source',self.source),('image',self.image),('seconds',self.seconds),('focus_x',self.x),('focus_y',self.y)]:
                    var.set(value.get(key,''))
                self.detail.delete('1.0','end');self.detail.insert('1.0',value['detail'])
                self.status.set('Inputs loaded. Create saves a new version, leaving the original intact.')
            except (ValueError,OSError) as exc:
                messagebox.showerror('Cannot load inputs',str(exc),parent=self.window)

    def open(self):
        if self.created:self.on_open('documentary',self.created)
