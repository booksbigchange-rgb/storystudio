"""Edit a copy of one layer's interior poses; parent Apply remains one undo step."""
import copy
import tkinter as tk
from tkinter import ttk,messagebox
from layers import POSE,layer_values,pose_at,SceneCompositor


class LayerKeysEditor:
    def __init__(self,parent):
        self.parent=parent
        self.layer=copy.deepcopy(parent.layers[parent.current])
        self.selected=None
        self.window=tk.Toplevel(parent.window)
        self.window.title('Layer motion keys');self.window.geometry('640x620')
        self.window.transient(parent.window);self.window.grab_set()
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        frame=ttk.Frame(self.window,padding=16);frame.pack(fill='both',expand=True)
        footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x')
        ttk.Button(footer,text='Cancel',command=self.close).pack(side='right')
        self.apply_button=ttk.Button(footer,text='Apply keys',command=self.apply);self.apply_button.pack(side='right',padx=6)
        ttk.Label(frame,text='Motion inside the scene',font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Edit fields → Add/Update → Apply keys → Apply to scene.\nTime is a percentage of scene duration. Keys follow layer easing.\nPresets change endpoints and preserve these keys.',wraplength=600).pack(anchor='w',pady=8)
        self.items=tk.Listbox(frame,height=5,exportselection=False);self.items.pack(fill='x')
        self.items.bind('<<ListboxSelect>>',self.select)
        row=ttk.Frame(frame);row.pack(fill='x',pady=8)
        self.time=tk.StringVar(value='50')
        ttk.Label(row,text='Time % (0–100, exclusive)').pack(side='left')
        ttk.Entry(row,textvariable=self.time,width=8).pack(side='left',padx=8)
        self.sample_button=ttk.Button(row,text='Sample pose here',command=self.sample);self.sample_button.pack(side='left')
        fields=ttk.Frame(frame);fields.pack(fill='x');self.fields={}
        for i,name in enumerate(POSE):
            variable=tk.StringVar();self.fields[name]=variable
            ttk.Label(fields,text=name.title()).grid(row=0,column=i,padx=5)
            ttk.Entry(fields,textvariable=variable,width=10).grid(row=1,column=i,padx=5)
        bar=ttk.Frame(frame);bar.pack(fill='x',pady=8)
        self.buttons={}
        for label,action in [('Add key',self.add),('Update key',self.update),('Remove key',self.remove),('Preview',self.preview)]:
            b=ttk.Button(bar,text=label,command=action);b.pack(side='left',padx=3);self.buttons[label]=b
        self.canvas=tk.Canvas(frame,height=180,bg='#e5eaf0',highlightthickness=0);self.canvas.pack(fill='both',expand=True,pady=6)
        self.refresh();self.sample()

    def fraction(self):
        t=float(self.time.get())/100
        if not 0<t<1:raise ValueError('Choose a time strictly between 0% and 100%')
        return t

    def refresh(self):
        self.items.delete(0,'end');self.selected=None
        for key in self.layer['keyframes']:
            self.items.insert('end',f'{key["t"]*100:g}% · x {key["pose"]["x"]:g}, y {key["pose"]["y"]:g}, opacity {key["pose"]["opacity"]:g}')

    def select(self,_=None):
        choice=self.items.curselection()
        if choice:
            self.selected=choice[0];key=self.layer['keyframes'][self.selected]
            self.time.set(f'{key["t"]*100:g}')
            for name,value in self.fields.items():value.set(f'{key["pose"][name]:.6g}')

    def sample(self):
        try:
            pose=pose_at(self.layer,self.fraction())
            for name,value in self.fields.items():value.set(f'{pose[name]:.6g}')
        except ValueError as exc:messagebox.showerror('Invalid time',str(exc),parent=self.window)

    def candidate(self,replace=False):
        value=copy.deepcopy(self.layer)
        if replace:
            if self.selected is None:raise ValueError('Select a key to update')
            del value['keyframes'][self.selected]
        value['keyframes'].append(dict(t=self.fraction(),pose={name:field.get() for name,field in self.fields.items()}))
        value['keyframes'].sort(key=lambda item:item['t'])
        return layer_values({'layers':[value]})[0]

    def change(self,replace=False):
        try:
            self.layer=self.candidate(replace);self.refresh();self.preview()
        except (ValueError,TypeError) as exc:messagebox.showerror('Invalid key',str(exc),parent=self.window)

    def add(self):self.change()
    def update(self):self.change(True)

    def remove(self):
        if self.selected is not None:
            del self.layer['keyframes'][self.selected];self.refresh();self.preview()

    def preview(self):
        try:
            from PIL import ImageTk
            scene=copy.deepcopy(self.parent.scene);scene['layers']=copy.deepcopy(self.parent.layers)
            scene['layers'][self.parent.current]=self.layer
            aspect=self.parent.app.aspect
            height=max(50,min(180,(max(200,self.canvas.winfo_width())-10)/aspect));height=int(height)
            image=SceneCompositor(scene).frame(self.fraction(),round(height*aspect),height)
            self.photo=ImageTk.PhotoImage(image);self.canvas.delete('all')
            self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.photo)
        except (ValueError,OSError) as exc:messagebox.showerror('Preview unavailable',str(exc),parent=self.window)

    def apply(self):
        self.parent.layers[self.parent.current]=copy.deepcopy(self.layer)
        self.parent.refresh(self.parent.current);self.parent.preview(.5);self.close()

    def close(self):
        self.window.destroy();self.parent.window.grab_set()
