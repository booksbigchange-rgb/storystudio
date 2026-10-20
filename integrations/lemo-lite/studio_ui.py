"""Lightweight Windows editor; all Tk updates run on the main event thread."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import traceback
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

import presets
import project
import renderer

BG = '#eef3ef'
INK = '#243e39'
MUTED = '#61766f'
GREEN = '#26776a'
WHITE = '#ffffff'


class StudioApp(tk.Tk):
    def __init__(self, workspace=None, auto_preview=True):
        if os.name == 'nt':
            # Match Tk/window/screenshot coordinates on scaled Windows displays.
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        super().__init__()
        self.workspace = Path(workspace or renderer.ROOT)
        self.title('StoryStudio 2.0 · My cartoon')
        self.geometry('1180x780')
        self.minsize(1000, 680)
        self.configure(bg=BG)
        self.document = project.new_project()
        self.project_path = None
        self.dirty = False
        self.busy = False
        self.preview_busy = False
        self.preview_pending = False
        self.preview_enabled = auto_preview
        self.cancel_event = threading.Event()
        self.events = queue.Queue()
        self.preview_server = None
        self.preview_process = None
        self.closing = False
        self.revision = 0
        self._photo = None
        self.time = tk.DoubleVar(value=0)
        self.status = tk.StringVar(value='Ready. Choose a character, add a scene, and make it move.')
        self.audio_label = tk.StringVar(value='Original chimes · no narration selected')
        self.format_var = tk.StringVar(value=self.document['format'])
        self.quality_var = tk.StringVar(value=self.document['quality'])
        self.fields = {k: tk.StringVar(value=str(v)) for k,v in project.new_scene().items()}
        self.key_fields = {k: tk.StringVar() for k in ('at', 'x', 'size', 'lift', 'tilt', 'expression', 'action')}
        self.key_fields['at'].set('50')
        self.preset_name = tk.StringVar()
        self.preset_choice = tk.StringVar()
        self.preset_path = self.workspace/'projects'/'character-presets.json'
        self._build()
        self.refresh(0)
        self.protocol('WM_DELETE_WINDOW', self.exit_app)
        self.bind('<Control-s>', lambda _: self.save_project())
        self.bind('<Control-o>', lambda _: self.open_project())
        self.bind('<Control-e>', lambda _: self.export_video())
        self.after(60, self.poll_events)
        if auto_preview:
            self.after(300, self.request_preview)

    def _build(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), foreground=INK, background=BG)
        style.configure('TButton', padding=(9,6), background='#dfe9e2', borderwidth=0)
        style.map('TButton', background=[('active','#cbded3')])
        style.configure('Small.TButton', padding=(3,6), font=('Segoe UI',9))
        style.configure('Accent.TButton', background=GREEN, foreground=WHITE, font=('Segoe UI',10,'bold'))
        style.map('Accent.TButton', background=[('active','#1d6055'),('disabled','#9ab6aa')])
        style.configure('TEntry', fieldbackground=WHITE, padding=5)
        style.configure('TCombobox', fieldbackground=WHITE, padding=5)
        style.map('TCombobox', fieldbackground=[('readonly',WHITE)], foreground=[('readonly',INK)])
        style.configure('TNotebook', tabmargins=0)
        style.configure('TNotebook.Tab', padding=(7,7))
        style.configure('Horizontal.TProgressbar', background=GREEN, troughcolor='#dce7df')
        header=ttk.Frame(self,padding=(20,14))
        header.pack(fill='x')
        ttk.Label(header,text='STORYSTUDIO  2.0',font=('Segoe UI',18,'bold'),foreground=GREEN).pack(side='left')
        ttk.Label(header,text='Your ideas, in motion.',foreground=MUTED).pack(side='left',padx=18)
        self.export_button=ttk.Button(header,text='Export MP4',style='Accent.TButton',command=self.export_video)
        self.export_button.pack(side='right')
        self.save_button=ttk.Button(header,text='Save project',command=self.save_project)
        self.save_button.pack(side='right',padx=6)
        ttk.Button(header,text='Open',command=self.open_project).pack(side='right')
        ttk.Button(header,text='New',command=self.new_project).pack(side='right',padx=6)

        # Pack footer first: export, transport and status stay visible on laptop displays.
        footer=ttk.Frame(self,padding=(20,6,20,12));footer.pack(side='bottom',fill='x')
        transport=ttk.Frame(footer);transport.pack(fill='x',pady=(0,6))
        ttk.Label(transport,text='STORY TIMELINE',font=('Segoe UI',9,'bold')).pack(side='left')
        self.time_label=ttk.Label(transport,text='0.0 / 10.0 s',foreground=MUTED)
        self.time_label.pack(side='right')
        self.timeline=tk.Canvas(footer,height=46,bg=WHITE,highlightthickness=0)
        self.timeline.pack(fill='x')
        self.timeline.bind('<Configure>',lambda _:self.draw_timeline())
        self.timeline.bind('<Button-1>',self.click_timeline)
        row=ttk.Frame(footer);row.pack(fill='x',pady=6)
        self.preview_button=ttk.Button(row,text='Refresh frame',command=self.request_preview)
        self.preview_button.pack(side='left')
        self.live_button=ttk.Button(row,text='Play live preview',command=self.open_preview)
        self.live_button.pack(side='left',padx=6)
        self.scrubber=ttk.Scale(row,from_=0,to=10,variable=self.time,command=self.scrub)
        self.scrubber.pack(side='left',fill='x',expand=True,padx=10)
        self.cancel_button=ttk.Button(row,text='Cancel export',command=self.cancel_export,state='disabled')
        self.cancel_button.pack(side='right')
        self.progress=ttk.Progressbar(footer,maximum=1)
        self.progress.pack(fill='x')
        ttk.Label(footer,textvariable=self.status,foreground=MUTED,wraplength=950).pack(anchor='w',pady=(6,0))

        body=ttk.Frame(self,padding=(20,0));body.pack(fill='both',expand=True)
        left=ttk.Frame(body,width=185);left.pack(side='left',fill='y',padx=(0,14));left.pack_propagate(False)
        ttk.Label(left,text='YOUR SCENES',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(6,10))
        self.scene_list=tk.Listbox(left,exportselection=False,relief='flat',borderwidth=0,
                                  bg=WHITE,fg=INK,selectbackground=GREEN,selectforeground=WHITE,
                                  font=('Segoe UI',11),activestyle='none')
        self.scene_list.pack(fill='both',expand=True)
        self.scene_list.bind('<<ListboxSelect>>',self.select_scene)
        self.add_button=ttk.Button(left,text='+ Add scene',command=self.add_scene)
        self.add_button.pack(fill='x',pady=(8,4))
        row=ttk.Frame(left);row.pack(fill='x')
        row.columnconfigure((0,1),weight=1,uniform='actions')
        self.duplicate_button=ttk.Button(row,text='Duplicate',style='Small.TButton',width=1,command=self.duplicate_scene)
        self.duplicate_button.grid(row=0,column=0,sticky='ew')
        self.delete_button=ttk.Button(row,text='Remove',style='Small.TButton',width=1,command=self.remove_scene)
        self.delete_button.grid(row=0,column=1,sticky='ew')
        row=ttk.Frame(left);row.pack(fill='x',pady=4)
        row.columnconfigure((0,1),weight=1,uniform='actions')
        ttk.Button(row,text='Move up',style='Small.TButton',width=1,command=lambda:self.move_scene(-1)).grid(row=0,column=0,sticky='ew')
        ttk.Button(row,text='Move down',style='Small.TButton',width=1,command=lambda:self.move_scene(1)).grid(row=0,column=1,sticky='ew')

        inspector=ttk.Frame(body,width=285);inspector.pack(side='right',fill='y',padx=(14,0));inspector.pack_propagate(False)
        ttk.Label(inspector,text='MAKE IT YOURS',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(6,10))
        self.tabs=ttk.Notebook(inspector);self.tabs.pack(fill='both',expand=True)
        scene_tab=ttk.Frame(self.tabs,padding=10);motion_tab=ttk.Frame(self.tabs,padding=10);anim_tab=ttk.Frame(self.tabs,padding=10);export_tab=ttk.Frame(self.tabs,padding=10)
        self.tabs.add(scene_tab,text='Scene');self.tabs.add(motion_tab,text='Character');self.tabs.add(export_tab,text='Output');self.tabs.add(anim_tab,text='Animate')
        preset_tab=ttk.Frame(self.tabs,padding=10);self.tabs.add(preset_tab,text='Presets')
        self._build_animate(anim_tab);self._build_presets(preset_tab)
        def field(parent,label,key,options=None):
            ttk.Label(parent,text=label,foreground=MUTED).pack(anchor='w',pady=(8,3))
            if options:
                widget=ttk.Combobox(parent,textvariable=self.fields[key],values=options,state='readonly')
                widget.bind('<<ComboboxSelected>>',lambda _:self.apply_scene())
            else:
                widget=ttk.Entry(parent,textvariable=self.fields[key])
                widget.bind('<Return>',lambda _:self.apply_scene())
            widget.pack(fill='x')
            return widget
        self.title_entry=field(scene_tab,'Caption · up to 60 characters','title')
        field(scene_tab,'Length · 1–30 seconds','duration')
        field(scene_tab,'Backdrop','background',project.BACKGROUNDS)
        self.apply_button=ttk.Button(scene_tab,text='Apply scene edits',style='Accent.TButton',command=self.apply_scene)
        self.apply_button.pack(fill='x',pady=14)
        ttk.Label(scene_tab,text='Add scenes to tell a longer story.\nSave a project to edit it again later.',foreground=MUTED,wraplength=240).pack(anchor='w')
        self.character_combo=field(motion_tab,'Character','character',project.CHARACTERS)
        self.expression_combo=field(motion_tab,'Expression','expression',project.EXPRESSIONS)
        self.action_combo=field(motion_tab,'Motion','action',project.ACTIONS)
        params=ttk.Frame(motion_tab);params.pack(fill='x',pady=(10,0))
        for col,(key,label) in enumerate([('x','Position'),('size','Size'),('speed','Speed')]):
            ttk.Label(params,text=label).grid(row=0,column=col,sticky='w')
            ttk.Entry(params,textvariable=self.fields[key],width=7).grid(row=1,column=col,padx=(0,6),pady=4)
        ttk.Label(motion_tab,text='Position .2–.7 · Size .6–1.25\nSpeed .5–2 · Blink is automatic',foreground=MUTED,wraplength=240).pack(anchor='w',pady=6)
        ttk.Button(motion_tab,text='Apply character edits',style='Accent.TButton',command=self.apply_scene).pack(fill='x',pady=8)
        ttk.Label(export_tab,text='Video format',foreground=MUTED).pack(anchor='w',pady=(8,3))
        self.format_combo=ttk.Combobox(export_tab,textvariable=self.format_var,values=list(project.FORMATS),state='readonly')
        self.format_combo.pack(fill='x');self.format_combo.bind('<<ComboboxSelected>>',self.apply_output)
        ttk.Label(export_tab,text='Quality',foreground=MUTED).pack(anchor='w',pady=(12,3))
        self.quality_combo=ttk.Combobox(export_tab,textvariable=self.quality_var,values=list(project.QUALITIES),state='readonly')
        self.quality_combo.pack(fill='x');self.quality_combo.bind('<<ComboboxSelected>>',self.apply_output)
        ttk.Label(export_tab,text='Soundtrack',foreground=MUTED).pack(anchor='w',pady=(18,4))
        ttk.Label(export_tab,textvariable=self.audio_label,wraplength=240).pack(anchor='w')
        ttk.Button(export_tab,text='Import narration / audio',command=self.import_audio).pack(fill='x',pady=(8,4))
        ttk.Button(export_tab,text='Use original chimes',command=self.clear_audio).pack(fill='x')
        ttk.Label(export_tab,text='Audio starts at 0s. Short audio is padded; long audio is trimmed. Live preview is silent.',foreground=MUTED,wraplength=240).pack(anchor='w',pady=12)
        ttk.Button(export_tab,text='Save project as…',command=lambda:self.save_project(save_as=True)).pack(fill='x')
        ttk.Button(export_tab,text='Open export folder',command=self.open_exports).pack(fill='x',pady=4)

        middle=ttk.Frame(body);middle.pack(fill='both',expand=True)
        self.preview_heading=ttk.Label(middle,text='STAGE  /  16:9',font=('Segoe UI',10,'bold'))
        self.preview_heading.pack(anchor='w',pady=(6,10))
        self.stage=tk.Canvas(middle,bg='#dce8e1',highlightthickness=0)
        self.stage.pack(fill='both',expand=True)
        self.stage.bind('<Configure>',lambda _:self.draw_snapshot())
        self.snapshot=None
        ttk.Label(middle,text='Frame preview · use Play live preview to watch motion',foreground=MUTED).pack(anchor='w',pady=8)

    def _build_animate(self,tab):
        ttk.Label(tab,text='Animation keys · time in % of this scene. Leave a box blank to keep the scene value.',foreground=MUTED,wraplength=250).pack(anchor='w')
        self.key_list=tk.Listbox(tab,height=4,exportselection=False,relief='flat',borderwidth=0,bg=WHITE,fg=INK,
                                 selectbackground=GREEN,selectforeground=WHITE,activestyle='none')
        self.key_list.pack(fill='x',pady=6)
        self.key_list.bind('<<ListboxSelect>>',self.select_key)
        grid=ttk.Frame(tab);grid.pack(fill='x')
        labels=[('at','Time %'),('x','Position'),('size','Size'),('lift','Lift'),('tilt','Tilt')]
        for col,(key,label) in enumerate(labels):
            ttk.Label(grid,text=label,foreground=MUTED).grid(row=0,column=col,sticky='w')
            ttk.Entry(grid,textvariable=self.key_fields[key],width=4).grid(row=1,column=col,padx=(0,4),pady=2)
        ttk.Combobox(tab,textvariable=self.key_fields['expression'],values=['']+list(project.EXPRESSIONS),state='readonly').pack(fill='x',pady=(6,2))
        ttk.Combobox(tab,textvariable=self.key_fields['action'],values=['']+list(project.ACTIONS),state='readonly').pack(fill='x',pady=2)
        ttk.Label(tab,text='Lift ±150 · Tilt ±0.6 radians · expression and motion switch at the key',foreground=MUTED,wraplength=250).pack(anchor='w')
        row=ttk.Frame(tab);row.pack(fill='x',pady=6)
        self.key_buttons={}
        for label,action in [('Add key',self.add_key),('Update',self.update_key),('Remove',self.remove_key)]:
            self.key_buttons[label]=ttk.Button(row,text=label,style='Small.TButton',width=1,command=action)
            self.key_buttons[label].pack(side='left',fill='x',expand=True,padx=1)

    def _build_presets(self,tab):
        ttk.Label(tab,text='A preset remembers a character, look, motion and animation keys so you can reuse it in any scene or project. Caption, length and backdrop are never changed.',foreground=MUTED,wraplength=250).pack(anchor='w')
        ttk.Label(tab,text='Preset name',foreground=MUTED).pack(anchor='w',pady=(10,2))
        ttk.Entry(tab,textvariable=self.preset_name).pack(fill='x',pady=2)
        self.preset_buttons={}
        self.preset_buttons['Save preset']=ttk.Button(tab,text='Save this character as preset',command=self.save_preset)
        self.preset_buttons['Save preset'].pack(fill='x',pady=2)
        ttk.Label(tab,text='Saved presets',foreground=MUTED).pack(anchor='w',pady=(12,2))
        self.preset_combo=ttk.Combobox(tab,textvariable=self.preset_choice,state='readonly')
        self.preset_combo.pack(fill='x',pady=2)
        row=ttk.Frame(tab);row.pack(fill='x')
        for label,action in [('Apply preset',self.apply_preset),('Delete preset',self.delete_preset)]:
            self.preset_buttons[label]=ttk.Button(row,text=label,style='Small.TButton',width=1,command=action)
            self.preset_buttons[label].pack(side='left',fill='x',expand=True,padx=1)
        self.refresh_presets()

    def scene_keys(self):
        return copy.deepcopy(self.document['scenes'][self.selected()].get('keys',[]))

    def refresh_keys(self):
        self.key_list.delete(0,'end')
        for key in self.scene_keys():
            parts=[f"{name} {key[name]:g}" for name in ('x','size','lift','tilt') if name in key]
            parts+=[str(key[name]) for name in ('expression','action') if name in key]
            self.key_list.insert('end',f"{key['at']*100:g}% · "+', '.join(parts))

    def key_from_fields(self):
        key={'at':float(self.key_fields['at'].get())/100}
        for name in ('x','size','lift','tilt'):
            if self.key_fields[name].get().strip():key[name]=float(self.key_fields[name].get())
        for name in ('expression','action'):
            if self.key_fields[name].get():key[name]=self.key_fields[name].get()
        return key

    def commit_keys(self,keys,select=None):
        index=self.selected();doc=copy.deepcopy(self.document)
        scene=doc['scenes'][index]
        if keys:scene['keys']=keys
        else:scene.pop('keys',None)
        try:doc=project.validate(doc)
        except ValueError as exc:
            self.status.set(str(exc));return False
        self.document=doc;self.mark_dirty();self.refresh(index);self.request_preview()
        if select is not None and select<self.key_list.size():
            self.key_list.selection_set(select)
        return True

    def change_key(self,replace=False):
        try:
            key=self.key_from_fields();keys=self.scene_keys()
            chosen=self.key_list.curselection()
            if replace:
                if not chosen:raise ValueError('Select a key to update')
                keys[chosen[0]]=key
            else:keys.append(key)
            keys.sort(key=lambda item:item['at'])
        except (ValueError,TypeError) as exc:
            self.status.set(str(exc));return False
        return self.commit_keys(keys,keys.index(key))

    def add_key(self):return self.change_key()

    def update_key(self):return self.change_key(replace=True)

    def remove_key(self):
        chosen=self.key_list.curselection()
        if chosen:
            keys=self.scene_keys();del keys[chosen[0]];self.commit_keys(keys)

    def select_key(self,_=None):
        chosen=self.key_list.curselection()
        if not chosen:return
        key=self.scene_keys()[chosen[0]]
        self.key_fields['at'].set(f"{key['at']*100:g}")
        for name in ('x','size','lift','tilt'):self.key_fields[name].set(f"{key[name]:g}" if name in key else '')
        for name in ('expression','action'):self.key_fields[name].set(key.get(name,''))
        index=self.selected();scenes=self.document['scenes']
        self.time.set(sum(s['duration'] for s in scenes[:index])+key['at']*scenes[index]['duration'])
        self.scrub()

    def refresh_presets(self):
        try:names=sorted(presets.load(self.preset_path))
        except (OSError,ValueError) as exc:
            names=[];self.status.set('Preset library could not be read: '+str(exc))
        self.preset_combo.configure(values=names)
        if self.preset_choice.get() not in names:self.preset_choice.set(names[0] if names else '')

    def save_preset(self):
        name=self.preset_name.get()
        try:
            scene=self.document['scenes'][self.selected()]
            try:presets.save(self.preset_path,name,scene)
            except FileExistsError:
                if not messagebox.askyesno('Replace preset',f'Replace the existing preset “{name.strip()}”?'):return
                presets.save(self.preset_path,name,scene,replace=True)
        except (OSError,ValueError) as exc:
            self.status.set(str(exc));return
        self.preset_choice.set(name.strip());self.refresh_presets();self.status.set(f'Saved preset “{name.strip()}”.')

    def apply_preset(self):
        try:
            preset=presets.load(self.preset_path)[self.preset_choice.get()]
        except (OSError,ValueError,KeyError):
            self.status.set('Choose a saved preset first.');return
        index=self.selected();doc=copy.deepcopy(self.document)
        doc['scenes'][index]=presets.apply(doc['scenes'][index],preset)
        try:doc=project.validate(doc)
        except ValueError as exc:
            self.status.set(str(exc));return
        self.document=doc;self.mark_dirty();self.refresh(index);self.request_preview()
        self.status.set(f'Applied preset “{self.preset_choice.get()}” to scene {index+1}. Caption, length and backdrop were kept.')

    def delete_preset(self):
        name=self.preset_choice.get()
        try:presets.delete(self.preset_path,name)
        except (OSError,ValueError,KeyError):
            self.status.set('Choose a saved preset first.');return
        self.refresh_presets();self.status.set(f'Deleted preset “{name}”.')

    def selected(self):
        selected=self.scene_list.curselection()
        return selected[0] if selected else 0

    def mark_dirty(self):
        self.dirty=True;self.revision+=1
        self.title('StoryStudio 2.0 · '+self.document['name']+' *')

    def refresh(self,index=0):
        self.scene_list.delete(0,'end')
        for i,scene in enumerate(self.document['scenes']):
            self.scene_list.insert('end',f"  {i+1:02d}  {scene['character'].title()}  ·  {scene['duration']:g}s")
        index=max(0,min(index,len(self.document['scenes'])-1))
        self.scene_list.selection_set(index);self.scene_list.see(index)
        for key,var in self.fields.items():var.set(str(self.document['scenes'][index][key]))
        self.format_var.set(self.document['format']);self.quality_var.set(self.document['quality'])
        audio=self.document['audio'];self.audio_label.set(Path(audio).name if audio else 'Original chimes · no narration selected')
        self.scrubber.configure(to=project.total_duration(self.document))
        self.time.set(min(self.time.get(),project.total_duration(self.document)))
        self.preview_heading.configure(text='STAGE  /  '+self.document['format'])
        self.refresh_keys();self.draw_timeline();self.draw_snapshot()

    def select_scene(self,_=None):
        index=self.selected()
        for key,var in self.fields.items():var.set(str(self.document['scenes'][index][key]))
        self.time.set(sum(s['duration'] for s in self.document['scenes'][:index]))
        self.refresh_keys();self.scrub();self.draw_timeline()

    def apply_scene(self):
        index=self.selected();doc=copy.deepcopy(self.document)
        scene={**doc['scenes'][index],**{key:var.get() for key,var in self.fields.items()}}  # keeps animation keys
        try:
            for key in ('duration','x','size','speed'):scene[key]=float(scene[key])
            doc['scenes'][index]=scene
            doc=project.validate(doc)
        except (ValueError,TypeError) as exc:
            self.status.set(str(exc));return False
        self.document=doc;self.mark_dirty();self.refresh(index);self.request_preview()
        return True

    def apply_output(self,_=None):
        self.document['format']=self.format_var.get();self.document['quality']=self.quality_var.get()
        self.mark_dirty();self.refresh(self.selected());self.request_preview()

    def add_scene(self):
        self._insert(project.new_scene())

    def duplicate_scene(self):
        self._insert(copy.deepcopy(self.document['scenes'][self.selected()]))

    def _insert(self,scene):
        doc=copy.deepcopy(self.document);index=self.selected()+1;doc['scenes'].insert(index,scene)
        try:doc=project.validate(doc)
        except ValueError as exc:self.status.set(str(exc));return
        self.document=doc;self.mark_dirty();self.refresh(index);self.select_scene()

    def remove_scene(self):
        if len(self.document['scenes'])==1:self.status.set('Keep at least one scene.');return
        index=self.selected();self.document['scenes'].pop(index)
        self.mark_dirty();self.refresh(index);self.select_scene()

    def move_scene(self,delta):
        index=self.selected();target=index+delta
        if 0<=target<len(self.document['scenes']):
            scenes=self.document['scenes'];scenes[index],scenes[target]=scenes[target],scenes[index]
            self.mark_dirty();self.refresh(target);self.select_scene()

    def scrub(self,_=None):
        self.time_label.configure(text=f'{self.time.get():.1f} / {project.total_duration(self.document):.1f} s')
        self.draw_timeline()
        self.status.set('Frame changed. Refresh frame, or play the live preview.')

    def draw_timeline(self):
        self.timeline.delete('all');width=max(1,self.timeline.winfo_width());total=project.total_duration(self.document);start=0
        for i,scene in enumerate(self.document['scenes']):
            end=start+scene['duration'];x1=start/total*width;x2=end/total*width
            self.timeline.create_rectangle(x1+2,3,x2-2,43,fill=GREEN if i==self.selected() else '#abcbbb',outline='')
            if x2-x1>60:self.timeline.create_text((x1+x2)/2,23,text=f"{i+1:02d} · {scene['duration']:g}s",fill=WHITE if i==self.selected() else INK)
            start=end
        x=self.time.get()/total*width;self.timeline.create_line(x,0,x,46,fill='#e8ab50',width=3)

    def click_timeline(self,event):
        moment=max(0,min(1,event.x/max(1,self.timeline.winfo_width())))*project.total_duration(self.document)
        start=0
        for index,scene in enumerate(self.document['scenes']):
            if moment<start+scene['duration'] or index==len(self.document['scenes'])-1:break
            start+=scene['duration']
        self.refresh(index);self.time.set(moment);self.scrub()

    def draw_snapshot(self):
        self.stage.delete('all');w=max(1,self.stage.winfo_width());h=max(1,self.stage.winfo_height())
        if self.snapshot:
            image=Image.open(io.BytesIO(self.snapshot));image.thumbnail((max(1,w-20),max(1,h-20)))
            self._photo=ImageTk.PhotoImage(image)
            self.stage.create_image(w/2,h/2,image=self._photo)
        else:
            self.stage.create_text(w/2,h/2,text='Your story starts here.\n\nChoose Refresh frame to see your cartoon.',fill=GREEN,font=('Segoe UI',13),justify='center',width=max(100,w-30))

    def request_preview(self):
        if not self.preview_enabled or self.closing:return
        if self.busy or self.preview_busy:self.preview_pending=True;return
        self.preview_busy=True;self.preview_pending=False
        doc=copy.deepcopy(self.document);moment=self.time.get();revision=self.revision
        self.status.set('Drawing preview frame…')
        def worker():
            try:self.events.put(('preview',renderer.preview_frame(doc,moment),revision))
            except Exception as exc:self.events.put(('preview_error',str(exc),revision))
        threading.Thread(target=worker,daemon=True).start()

    def poll_events(self):
        try:
            while True:
                event=self.events.get_nowait();kind=event[0]
                if kind=='progress':self.progress['value']=event[1];self.status.set(event[2])
                elif kind in ('preview','preview_error'):
                    self.preview_busy=False
                    if event[2]==self.revision:
                        if kind=='preview':self.snapshot=event[1];self.draw_snapshot();self.status.set('Preview ready. Edits are saved when you choose Save project.')
                        else:self.status.set('Preview unavailable: '+event[1])
                elif kind=='done':
                    self.busy=False;self.export_button.state(['!disabled']);self.cancel_button.state(['disabled'])
                    self.status.set(event[1])
        except queue.Empty:pass
        if self.closing:
            if not self.busy and not self.preview_busy:
                self._close_server();self.destroy();return
        elif self.preview_pending and not self.busy and not self.preview_busy:self.request_preview()
        self.after(60,self.poll_events)

    def _close_server(self):
        if self.preview_process:
            if self.preview_process.poll() is None:
                self.preview_process.terminate()
                try:self.preview_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.preview_process.kill();self.preview_process.wait(timeout=5)
            self.preview_process=None
        if self.preview_server:self.preview_server.__exit__(None,None,None);self.preview_server=None

    def open_preview(self):
        if not self.apply_scene():return
        try:
            self._close_server();self.preview_server=renderer.local_server(copy.deepcopy(self.document))
            address=self.preview_server.__enter__().replace('?capture=1','')
            # A separate profile keeps new browser caches beside this studio.
            # Never attach to or terminate the user's normal browser session.
            profile=self.workspace/'cache'/f'live-preview-{os.getpid()}'
            profile.mkdir(parents=True,exist_ok=True)
            self.preview_process=subprocess.Popen(
                [renderer.find_chrome(),f'--user-data-dir={profile}',f'--app={address}',
                 '--no-first-run','--no-default-browser-check','--disable-gpu'],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=renderer.NO_WINDOW)
            self.status.set('Live preview opened. Reopen it after edits. Audio is included in MP4 exports.')
        except Exception as exc:self.status.set(str(exc))

    def confirm_discard(self):
        return not self.dirty or messagebox.askyesno('Unsaved project','Discard unsaved changes?',parent=self)

    def new_project(self):
        if not self.confirm_discard():return
        self.document=project.new_project();self.project_path=None;self.dirty=False;self.revision+=1
        self.time.set(0);self.snapshot=None;self.refresh();self.title('StoryStudio 2.0 · My cartoon');self.request_preview()

    def open_project(self):
        if not self.confirm_discard():return
        path=filedialog.askopenfilename(parent=self,title='Open StoryStudio project',filetypes=[('StoryStudio project','*.json')])
        if path:
            try:
                doc=project.load(path)
                self.document=doc;self.project_path=Path(path);self.dirty=False;self.revision+=1;self.time.set(0)
                self.refresh();self.title('StoryStudio 2.0 · '+doc['name']);self.request_preview()
            except (ValueError,OSError) as exc:messagebox.showerror('Cannot open project',str(exc),parent=self)

    def save_project(self,save_as=False):
        if not self.apply_scene():return
        path=self.project_path
        if path is None or save_as:
            folder=self.workspace/'projects';folder.mkdir(parents=True,exist_ok=True)
            chosen=filedialog.asksaveasfilename(parent=self,title='Save project',initialdir=folder,
                                               initialfile='my-cartoon.json',defaultextension='.json',filetypes=[('StoryStudio project','*.json')])
            if not chosen:return
            path=Path(chosen)
        try:
            project.save(self.document,path);self.project_path=Path(path);self.dirty=False
            self.title('StoryStudio 2.0 · '+self.document['name']);self.status.set('Project saved: '+str(path))
        except (ValueError,OSError) as exc:messagebox.showerror('Cannot save project',str(exc),parent=self)

    def import_audio(self):
        path=filedialog.askopenfilename(parent=self,title='Import local narration or audio',filetypes=[('Audio','*.wav *.mp3 *.m4a *.flac *.ogg')])
        if path:self.document['audio']=str(Path(path).resolve());self.mark_dirty();self.refresh(self.selected())

    def clear_audio(self):
        self.document['audio']=None;self.mark_dirty();self.refresh(self.selected())

    def export_video(self):
        if self.busy:return
        if not self.apply_scene():return
        folder=self.workspace/'exports';folder.mkdir(parents=True,exist_ok=True)
        path=filedialog.asksaveasfilename(parent=self,title='Export verified MP4',initialdir=folder,
                                        initialfile='cartoon-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.mp4',
                                        defaultextension='.mp4',filetypes=[('MP4 video','*.mp4')])
        if path:self.start_export(path)

    def start_export(self,path):
        if self.busy:return
        doc=copy.deepcopy(self.document);w,h,fps=project.dimensions(doc)
        if self.project_path and Path(path).resolve()==self.project_path.resolve():
            self.status.set('Choose a different output path from the project file.');return
        self.busy=True;self.cancel_event.clear();self.progress['value']=0
        self.export_button.state(['disabled']);self.cancel_button.state(['!disabled'])
        self.status.set('Starting export. You may keep editing; export uses the current snapshot.')
        args=argparse.Namespace(document=doc,width=w,height=h,fps=fps,duration=project.total_duration(doc),audio=None,output=path,overwrite=True)
        def worker():
            try:
                out=renderer.export(args,lambda value,text:self.events.put(('progress',value,text)),self.cancel_event)
                self.events.put(('done','Verified MP4 saved: '+str(out)))
            except renderer.Cancelled as exc:self.events.put(('done',str(exc)))
            except Exception as exc:
                folder=self.workspace/'logs';folder.mkdir(parents=True,exist_ok=True)
                (folder/'last-export-error.log').write_text(traceback.format_exc(),encoding='utf-8')
                self.events.put(('done','Export failed: '+str(exc)[:200]))
        threading.Thread(target=worker,daemon=True).start()

    def cancel_export(self):
        self.cancel_event.set();self.status.set('Cancelling after the current frame…')

    def open_exports(self):
        path=self.workspace/'exports';path.mkdir(parents=True,exist_ok=True)
        if os.name=='nt':os.startfile(str(path))
        else:webbrowser.open(path.as_uri())

    def exit_app(self):
        if not self.confirm_discard():return
        self.closing=True;self.preview_pending=False;self.cancel_event.set()
        self.status.set('Closing browser and export workers…')
