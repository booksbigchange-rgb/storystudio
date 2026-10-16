"""Interactive camera editor built on the existing scene editor and renderer."""
import copy
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path

import desktop_app as base
from desktop_app import tk, ttk, filedialog, messagebox
from formats import LABELS, output_size
from layers import SceneCompositor
from camera import DEFAULT, EASINGS, MAX_INTERIOR_KEYS, camera_at, camera_values, crop_box, keyframe_values
from project import audio_values, read_project, write_project
from timeline import scene_at, scene_ranges, total_duration, keyframe_target_time
from render_control import RenderControl, RenderCancelled
from preview_audio import PreviewAudio
import winsound
from waveform import WaveformJob, source_key, waveform_columns


class EditorApp(base.StoryStudioApp):
    def __init__(self, root):
        self._audio_preview = None
        self._audio_pending = False
        self.output_format = "portrait"
        self.music = None
        self.audio = None
        self.playhead = 0.0
        self.playing = False
        self._render_control = None
        self.busy = False
        self.dirty = False
        self.history = []
        self.future = []
        self.events = queue.Queue()
        self._wave_key = None
        self._wave_data = None
        self._wave_job = None
        self._wave_state = ""
        self._wave_plot = None
        self._layer_preview_key = None
        self._layer_compositor = None
        self._source_key = None
        self._source_image = None
        self._preview_geometry = None
        self._drag = None
        self.key_at = None
        self._key_markers = []
        self._timeline_drag = None
        self._tick_job = None
        self._poll_job = None
        self._loading = True
        self.format_choice = tk.StringVar(root, LABELS[self.output_format])
        self.format_info = tk.StringVar(root)
        self.endpoint = tk.StringVar(root, "start")
        self.easing = tk.StringVar(root, "linear")
        self.loop = tk.BooleanVar(root, False)
        self.zoom = tk.DoubleVar(root, 1.0)
        self.audio_track = tk.StringVar(root, "Narration")
        self.audio_repeat = tk.BooleanVar(root, False)
        self.audio_label = tk.StringVar(root, "No soundtrack")
        self.audio_inputs = {k: tk.StringVar(root, str(v)) for k, v in
                             {"volume": 1, "offset": 0, "trim": 0, "fade": 0}.items()}
        super().__init__(root)
        self._loading = False
        root.title("StoryStudio — Camera & Audio Editor")
        root.minsize(1000, 680)
        root.geometry("1240x820")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<Control-z>", lambda _e: self.undo())
        root.bind("<Control-y>", lambda _e: self.redo())
        root.bind("<Control-s>", lambda _e: self.save())
        self._poll_events()

    def build(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        header = ttk.Frame(frame)
        header.pack(fill="x")
        ttk.Label(header, text="StoryStudio", font=("Segoe UI", 22, "bold")).pack(side="left")
        for label, command in (("New", self.new), ("Open", self.open_project), ("Save", self.save),
                               ("Save as", self.save_as), ("Undo", self.undo), ("Redo", self.redo)):
            ttk.Button(header, text=label, command=command).pack(side="left", padx=3)
        format_selector = ttk.Combobox(header, textvariable=self.format_choice, values=tuple(LABELS.values()), state="readonly", width=18)
        format_selector.pack(side="right")
        format_selector.bind("<<ComboboxSelected>>", lambda _e: self.change_format())
        self.sync_format()
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=8)
        for label, command in (("Add image", self.add), ("Relink", self.relink),
                               ("Duplicate", self.duplicate), ("Remove", self.remove),
                               ("Move up", lambda: self.move(-1)), ("Move down", lambda: self.move(1))):
            ttk.Button(toolbar, text=label, command=command).pack(side="left", padx=2)
        ttk.Label(toolbar, text="Seconds").pack(side="left", padx=(10, 3))
        ttk.Entry(toolbar, textvariable=self.duration, width=6).pack(side="left")
        ttk.Button(toolbar, text="Apply", command=self.apply_duration).pack(side="left", padx=3)
        workspace = ttk.Panedwindow(frame, orient="horizontal")
        workspace.pack(fill="both", expand=True)
        left = ttk.Frame(workspace)
        workspace.add(left, weight=1)
        right = ttk.Frame(workspace)
        workspace.add(right, weight=3)
        ttk.Label(left, text="SCENES").pack(anchor="w")
        self.items = tk.Listbox(left, font=("Segoe UI", 11), width=30, exportselection=False)
        self.items.pack(fill="both", expand=True)
        self.items.bind("<<ListboxSelect>>", self.on_select)
        ttk.Label(right, text="CAMERA FRAME — drag the colored box; resize with Zoom").pack(anchor="w")
        self.preview = tk.Canvas(right, bg="#e5eaf0", height=250, highlightthickness=0)
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", lambda _e: self.draw_preview())
        self.preview.bind("<Button-1>", self.begin_drag)
        self.preview.bind("<B1-Motion>", self.drag_camera)
        self.preview.bind("<ButtonRelease-1>", self.end_drag)
        camera_bar = ttk.Frame(right)
        camera_bar.pack(fill="x", pady=4)
        for end in ("start", "end"):
            ttk.Radiobutton(camera_bar, text=end.title() + " frame", variable=self.endpoint,
                            value=end, command=self.choose_endpoint).pack(side="left")
        ttk.Label(camera_bar, text="Zoom").pack(side="left", padx=8)
        self.zoom_scale = ttk.Scale(camera_bar, from_=1, to=2, variable=self.zoom, command=self.change_zoom)
        self.zoom_scale.pack(side="left", fill="x", expand=True)
        self.zoom_scale.bind("<ButtonPress-1>", lambda _e: self.checkpoint())
        self.zoom_scale.bind("<KeyPress>", lambda _e: self.checkpoint())
        ttk.Combobox(camera_bar, textvariable=self.easing, values=EASINGS, state="readonly", width=10).pack(side="left", padx=4)
        ttk.Button(camera_bar, text="Apply easing", command=self.apply_easing).pack(side="left")
        keys_bar = ttk.Frame(right)
        keys_bar.pack(fill="x", pady=3)
        ttk.Button(keys_bar, text="Add keyframe here", command=self.add_keyframe).pack(side="left")
        ttk.Button(keys_bar, text="Remove keyframe", command=self.remove_keyframe).pack(side="left", padx=4)
        ttk.Button(keys_bar, text="Animate layers", command=self.edit_layers).pack(side="right")
        self.key_label = ttk.Label(keys_bar, text="Click a blue timeline diamond to edit it.")
        self.key_label.pack(side="left", padx=4)
        numbers = ttk.Frame(frame)
        numbers.pack(fill="x", pady=5)
        for key in DEFAULT:
            ttk.Label(numbers, text=key.replace("_", " ")).pack(side="left", padx=(4, 2))
            ttk.Entry(numbers, textvariable=self.camera_inputs[key], width=5).pack(side="left")
        ttk.Button(numbers, text="Apply camera", command=self.apply_camera).pack(side="left", padx=5)
        transport = ttk.Frame(frame)
        transport.pack(fill="x", pady=3)
        self.play_button = ttk.Button(transport, text="Play", command=self.toggle_play)
        self.play_button.pack(side="left")
        ttk.Button(transport, text="Stop", command=lambda: self.seek(0)).pack(side="left")
        ttk.Button(transport, text="< Frame", command=lambda: self.seek(self.playhead-1/base.FPS)).pack(side="left")
        ttk.Button(transport, text="Frame >", command=lambda: self.seek(self.playhead+1/base.FPS)).pack(side="left")
        ttk.Checkbutton(transport, text="Loop", variable=self.loop).pack(side="left")
        self.timeline_info = ttk.Label(transport, text="0.00s / 0.00s")
        self.timeline_info.pack(side="left", padx=12)
        ttk.Label(transport, text="Audio plays after preparation; Pause stops sound.").pack(side="right")
        self.timeline = tk.Canvas(frame, height=82, bg="#eef2f6", highlightthickness=0)
        self.timeline.pack(fill="x", pady=4)
        self.timeline.bind("<Configure>", lambda _e: self.draw_timeline())
        self.timeline.bind("<Button-1>", self.click_timeline)
        self.timeline.bind("<B1-Motion>", self.drag_timeline)
        self.timeline.bind("<ButtonRelease-1>", self.end_timeline_drag)
        audio_bar = ttk.Frame(frame)
        audio_bar.pack(fill="x", pady=4)
        selector = ttk.Combobox(audio_bar, textvariable=self.audio_track, values=("Narration", "Music"), state="readonly", width=10)
        selector.pack(side="left", padx=3)
        selector.bind("<<ComboboxSelected>>", lambda _e: self.select_audio_track())
        ttk.Button(audio_bar, text="Add audio", command=self.add_audio).pack(side="left")
        ttk.Button(audio_bar, text="Remove audio", command=self.remove_audio).pack(side="left")
        ttk.Button(audio_bar, text="Create narration", command=self.narration_dialog).pack(side="left")
        ttk.Label(audio_bar, textvariable=self.audio_label).pack(side="left", padx=8)
        audio_settings = ttk.Frame(frame)
        audio_settings.pack(fill="x", pady=4)
        for key, label in (("volume", "Volume 0–2"), ("offset", "Start at (s)"),
                           ("trim", "Skip source (s)"), ("fade", "Fade (s)")):
            ttk.Label(audio_settings, text=label).pack(side="left", padx=(6, 3))
            ttk.Entry(audio_settings, textvariable=self.audio_inputs[key], width=6).pack(side="left")
        ttk.Button(audio_settings, text="Apply audio", command=self.apply_audio).pack(side="left", padx=5)
        ttk.Checkbutton(audio_settings, text="Repeat audio", variable=self.audio_repeat).pack(side="left", padx=4)
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=6)
        ttk.Button(actions, text="Preview MP4", command=self.preview_movie).pack(side="left")
        self.render_button = ttk.Button(actions, text="Export MP4", command=self.export)
        self.render_button.pack(side="right")
        self.cancel_button = ttk.Button(actions, text="Cancel export", command=self.cancel_export, state="disabled")
        self.cancel_button.pack(side="right", padx=5)
        ttk.Label(frame, textvariable=self.status, wraplength=1120).pack(anchor="w")
        ttk.Label(frame, textvariable=self.format_info,
                  foreground="#596779").pack(anchor="w", pady=(4, 0))

    @property
    def selected_audio(self):
        return self.music if self.audio_track.get() == "Music" else self.audio

    @selected_audio.setter
    def selected_audio(self, value):
        if self.audio_track.get() == "Music":
            self.music = value
        else:
            self.audio = value

    def select_audio_track(self):
        self.pause()
        self.sync_audio()
        self.draw_timeline()

    @property
    def aspect(self):
        width, height = output_size(self.output_format)
        return width/height

    def sync_format(self):
        self.format_choice.set(LABELS[self.output_format])
        width, height = output_size(self.output_format)
        self.format_info.set(f"Camera and artwork animation • {width} × {height} • 24 fps • Local export")
        self._layer_preview_key = None

    def change_format(self):
        requested = next(key for key, label in LABELS.items() if label == self.format_choice.get())
        if self.busy:
            self.sync_format()
            self.status.set('Wait for the current worker before changing format.')
            return
        if requested != self.output_format:
            self.checkpoint()
            self.output_format = requested
            self.sync_format()
            self.draw_preview()
            self.changed()

    def edit_layers(self):
        if self.selected() is None:
            self.status.set('Select a scene before adding artwork layers.')
            return
        self.pause()
        from layer_editor import LayerEditor
        LayerEditor(self)

    def document(self):
        return copy.deepcopy((self.scenes, self.audio, self.music, self.output_format))

    def checkpoint(self):
        if self._loading:
            return
        self.pause()
        state = self.document()
        if not self.history or self.history[-1] != state:
            self.history.append(state)
            self.history = self.history[-50:]
        self.future.clear()

    def changed(self):
        if not self._loading:
            self.dirty = True
        self.status.set("Unsaved changes" if self.dirty else "Ready")

    def restore(self, source, target):
        if not source:
            return
        self.pause()
        self._timeline_drag = None
        target.append(self.document())
        self.scenes, self.audio, self.music, self.output_format = source.pop()
        self.sync_format()
        self.playhead = min(self.playhead, total_duration(self.scenes))
        self.sync_audio()
        self.refresh(0 if self.scenes else None)
        self.changed()

    def undo(self):
        self.restore(self.history, self.future)

    def redo(self):
        self.restore(self.future, self.history)

    def refresh(self, index=None):
        super().refresh(index)
        self.sync_camera()

    def sync_camera(self):
        index = self.selected()
        if index is not None:
            scene = self.scenes[index]
            self.duration.set(str(scene["duration"]))
            for key, value in camera_values(scene).items():
                self.camera_inputs[key].set(f"{value:.4g}")
            self.zoom.set(self.active_camera()["zoom"])
            self.easing.set(scene.get("easing", "linear"))
            self.key_label.configure(text="Editing intermediate keyframe" if self.endpoint.get() == "key" else "Click a blue timeline diamond to edit it.")

    def active_camera(self):
        scene = self.scenes[self.selected()]
        if self.endpoint.get() == "key":
            for key in scene.get("keyframes", []):
                if key["at"] == self.key_at:
                    return {k: key[k] for k in ("zoom", "x", "y")}
            self.endpoint.set("start")
            self.key_at = None
        values = camera_values(scene)
        return {key: values[key+"_"+self.endpoint.get()] for key in ("zoom", "x", "y")}

    def set_active_camera(self, key, value):
        scene = self.scenes[self.selected()]
        if self.endpoint.get() == "key":
            for point in scene.get("keyframes", []):
                if point["at"] == self.key_at:
                    point[key] = value
                    return
        else:
            scene[key+"_"+self.endpoint.get()] = value

    def add_keyframe(self):
        index = self.selected()
        if index is None:
            return
        scene = self.scenes[index]
        start = scene_ranges(self.scenes)[index][0]
        last = max(1, round(scene["duration"]*base.FPS)-1)
        at = round((self.playhead-start)*base.FPS)/last
        if not 0 < at < 1:
            self.status.set("Move the playhead inside this scene, away from its first and last frames.")
            return
        points = keyframe_values(scene)
        existing = next((p for p in points if abs(p["at"]-at) < 1e-6), None)
        if existing:
            self.select_keyframe(index, existing["at"])
            return
        if len(points) >= MAX_INTERIOR_KEYS:
            self.status.set(f"This scene already has {MAX_INTERIOR_KEYS} intermediate keyframes.")
            return
        self.checkpoint()
        points.append({"at": at, **camera_at(scene, at)})
        scene["keyframes"] = sorted(points, key=lambda point: point["at"])
        self.select_keyframe(index, at)
        self.changed()

    def remove_keyframe(self):
        index = self.selected()
        if index is None or self.endpoint.get() != "key":
            self.status.set("Select a blue timeline diamond first. Start/end frames cannot be removed.")
            return
        self.checkpoint()
        self.scenes[index]["keyframes"] = [p for p in self.scenes[index].get("keyframes", []) if p["at"] != self.key_at]
        self.key_at = None
        self.endpoint.set("start")
        self.sync_camera()
        self.draw_preview()
        self.draw_timeline()
        self.changed()

    def select_keyframe(self, index, at):
        self.pause()
        self.items.selection_clear(0, "end")
        self.items.selection_set(index)
        self.items.see(index)
        self.key_at = at
        self.endpoint.set("key")
        self.choose_endpoint()

    def on_select(self, _event=None):
        index = self.selected()
        if index is not None:
            self.pause()
            self.playhead = scene_ranges(self.scenes)[index][0]
            self.endpoint.set("start")
            self.key_at = None
        self.sync_camera()
        self.draw_preview()
        self.draw_timeline()

    def add(self):
        self.checkpoint()
        before = self.document()
        super().add()
        if before != self.document():
            self.changed()
            self.on_select()

    def remove(self):
        if self.selected() is not None:
            self.checkpoint()
            super().remove()
            self.playhead = min(self.playhead, total_duration(self.scenes))
            self.changed()
            self.on_select()

    def move(self, delta):
        index = self.selected()
        if index is not None and 0 <= index + delta < len(self.scenes):
            self.checkpoint()
            super().move(delta)
            self.changed()
            self.on_select()

    def duplicate(self):
        index = self.selected()
        if index is not None:
            self.checkpoint()
            self.scenes.insert(index+1, copy.deepcopy(self.scenes[index]))
            self.refresh(index+1)
            self.changed()
            self.on_select()

    def relink(self):
        index = self.selected()
        if index is None:
            return
        path = filedialog.askopenfilename(title="Relink scene image", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self.checkpoint()
            self.scenes[index]["image"] = str(Path(path).resolve())
            self.refresh(index)
            self.changed()

    def apply_duration(self):
        self.checkpoint()
        before = self.document()
        super().apply_duration()
        if before != self.document():
            index = self.selected()
            self.scenes[index]["duration"] = round(self.scenes[index]["duration"] * base.FPS) / base.FPS
            self.playhead = min(self.playhead, total_duration(self.scenes))
            self.refresh(index)
            self.changed()

    def apply_camera(self):
        self.checkpoint()
        before = self.document()
        super().apply_camera()
        if before != self.document():
            self.changed()
            self.sync_camera()
            self.draw_preview()

    def apply_easing(self):
        index = self.selected()
        if index is not None:
            self.checkpoint()
            self.scenes[index]["easing"] = self.easing.get()
            self.changed()
            self.draw_preview()

    def choose_endpoint(self):
        self.pause()
        index = self.selected()
        if index is not None:
            start, end = scene_ranges(self.scenes)[index]
            if self.endpoint.get() == "key" and self.key_at is not None:
                self.playhead = start+self.key_at*(end-start-1/base.FPS)
            else:
                self.playhead = start if self.endpoint.get() == "start" else end - 1/base.FPS
            self.sync_camera()
            self.draw_preview()
            self.draw_timeline()

    def change_zoom(self, _value=None):
        index = self.selected()
        if index is None or self._loading:
            return
        self.pause()
        self.set_active_camera("zoom", round(self.zoom.get(), 4))
        self.choose_endpoint()
        self.changed()

    def source_image(self, path):
        from PIL import Image
        path = Path(path)
        key = (str(path), path.stat().st_mtime_ns)
        if key != self._source_key:
            with Image.open(path) as image:
                source = image.convert("RGB")
                source.thumbnail((1600, 1600))
                self._source_image = source.copy()
            self._source_key = key
        return self._source_image

    def draw_preview(self):
        self.preview.delete("all")
        self._preview_geometry = None
        index = self.selected()
        w, h = max(100, self.preview.winfo_width()), max(100, self.preview.winfo_height())
        if index is None:
            self.preview.create_text(w/2, h/2, text="Add or select an image", fill="#42546a")
            return
        try:
            from PIL import Image, ImageTk
            scene = self.scenes[index]
            source = self.source_image(scene["image"])
            sw, sh = source.size
            scale = min((w*.57-20)/sw, (h-40)/sh)
            dw, dh = max(1, int(sw*scale)), max(1, int(sh*scale))
            ox, oy = 10+(w*.57-20-dw)/2, (h-dh)/2
            self._overview = ImageTk.PhotoImage(source.resize((dw, dh)))
            self.preview.create_image(ox, oy, anchor="nw", image=self._overview)
            self._preview_geometry = (ox, oy, scale, sw, sh)
            outlines = [("start", "#16865e"), ("end", "#bd6417")]
            if self.endpoint.get() == "key":
                outlines.append(("key", "#1266c9"))
            for endpoint, color in outlines:
                values = camera_values(scene)
                camera = self.active_camera() if endpoint == "key" else {k: values[k+"_"+endpoint] for k in ("zoom", "x", "y")}
                box = crop_box(sw, sh, camera, aspect=self.aspect)
                coords = (ox+box[0]*scale, oy+box[1]*scale, ox+box[2]*scale, oy+box[3]*scale)
                self.preview.create_rectangle(*coords, outline=color, width=3 if endpoint == self.endpoint.get() else 1)
                self.preview.create_text(coords[0]+4, coords[1]+10, anchor="w", text=endpoint.upper(), fill=color)
            start = scene_ranges(self.scenes)[index][0]
            frames = max(1, round(scene["duration"] * base.FPS))
            frame = min(frames-1, max(0, round((self.playhead-start)*base.FPS)))
            camera = camera_at(scene, frame / max(1, frames-1))
            box = crop_box(sw, sh, camera, aspect=self.aspect)
            ph = max(1, min(h-36, int((w*.4-12)/self.aspect)))
            pw = max(1, round(ph*self.aspect))
            if scene.get('layers'):
                import json
                paths = [scene['image']] + [layer['image'] for layer in scene['layers']]
                signature = (json.dumps(scene, sort_keys=True), tuple((p, Path(p).stat().st_mtime_ns) for p in paths))
                if signature != self._layer_preview_key:
                    self._layer_compositor = SceneCompositor(scene, source)
                    self._layer_preview_key = signature
                output_frame = self._layer_compositor.frame(frame/max(1,frames-1), pw, ph)
            else:
                output_frame = source.resize((pw, ph), Image.Resampling.BICUBIC, box=box)
            self._preview_image = ImageTk.PhotoImage(output_frame)
            self.preview.create_image(w*.79, h/2, image=self._preview_image)
            self.preview.create_text(w*.79, h-10, text="OUTPUT PREVIEW", fill="#42546a")
        except (OSError, ValueError, ImportError, tk.TclError) as exc:
            self.preview.create_text(w/2, h/2, text=f"Preview unavailable: {exc}\nUse Relink for missing images.", width=w-20, fill="#993b3b")

    def begin_drag(self, event):
        if not self._preview_geometry or self.selected() is None:
            return
        ox, oy, scale, sw, sh = self._preview_geometry
        scene = self.scenes[self.selected()]
        values = self.active_camera()
        end = self.endpoint.get()
        box = crop_box(sw, sh, values, aspect=self.aspect)
        if not (ox+box[0]*scale <= event.x <= ox+box[2]*scale and oy+box[1]*scale <= event.y <= oy+box[3]*scale):
            return
        self.checkpoint()
        self._drag = (event.x, event.y, values, self._preview_geometry, end)

    def drag_camera(self, event):
        if self._drag is None:
            return
        x, y, values, geometry, end = self._drag
        _ox, _oy, scale, sw, sh = geometry
        scene = self.scenes[self.selected()]
        bw, bh = min(sw, sh*self.aspect), min(sh, sw/self.aspect)
        zoom = values["zoom"]
        for key, delta, length in (("x", event.x-x, bw), ("y", event.y-y, bh)):
            travel = length*(1-1/zoom)*scale
            if travel > .001:
                self.set_active_camera(key, max(0, min(1, values[key]+delta/travel)))
        self.choose_endpoint()
        self.changed()

    def end_drag(self, _event=None):
        self._drag = None

    def draw_timeline(self):
        self.timeline.delete("all")
        self._key_markers = []
        total = total_duration(self.scenes)
        self.ensure_waveform(bool(total))
        self.timeline_info.configure(text=f"{self.playhead:.2f}s / {total:.2f}s")
        if not total:
            return
        width = max(1, self.timeline.winfo_width()-16)
        for i, (start, end) in enumerate(scene_ranges(self.scenes)):
            x1, x2 = 8+start/total*width, 8+end/total*width
            self.timeline.create_rectangle(x1, 6, x2, 48, fill="#16865e" if i == self.selected() else "#617991", outline="white")
            if x2-x1 > 45:
                self.timeline.create_text((x1+x2)/2, 26, text=f"{i+1} · {end-start:g}s", fill="white")
            for x, color in ((x1+4, "#83ebbc"), (x2-4, "#ffbc79")):
                self.timeline.create_polygon(x, 36, x+4, 41, x, 46, x-4, 41, fill=color)
            for point in self.scenes[i].get("keyframes", []):
                x = 8+(start+point["at"]*(end-start-1/base.FPS))/total*width
                self._key_markers.append((x, i, point["at"]))
                selected = i == self.selected() and self.endpoint.get() == "key" and self.key_at == point["at"]
                self.timeline.create_polygon(x, 33, x+6, 41, x, 49, x-6, 41, fill="#1266c9", outline="white" if selected else "#b7d6fb", width=2)
        if self.selected_audio:
            start_x = 8+min(self.selected_audio["offset"], total)/total*width
            self.timeline.create_rectangle(start_x, 54, 8+width, 74, fill="#e5ddef", outline="")
            self.timeline.create_line(start_x, 64, 8+width, 64, fill="#b1a0c7")
            if self._wave_data:
                plot_key = (self._wave_key, tuple(sorted(self.selected_audio.items())), total, int(width))
                if self._wave_plot is None or self._wave_plot[0] != plot_key:
                    self._wave_plot = (plot_key, waveform_columns(self._wave_data, self.selected_audio, total, int(width)))
                for column, peak in enumerate(self._wave_plot[1]):
                    if peak > 0:
                        x = 8+column
                        self.timeline.create_line(x, 64-peak*9, x, 64+peak*9, fill="#684195", tags="audio-waveform")
            else:
                self.timeline.create_text(start_x+6, 64, anchor="w", text=self._wave_state, fill="#624786")
        x = 8+min(self.playhead, total)/total*width
        self.timeline.create_line(x, 0, x, 80, fill="#d43a48", width=2)

    def ensure_waveform(self, has_scenes):
        if not self.selected_audio or not has_scenes:
            if self._wave_job:
                self._wave_job.cancel()
            self._wave_key, self._wave_data, self._wave_job, self._wave_plot = None, None, None, None
            return
        try:
            key = source_key(self.selected_audio["path"])
        except OSError:
            key = "missing:"+self.selected_audio["path"]
            if self._wave_job:
                self._wave_job.cancel()
            self._wave_key, self._wave_data, self._wave_job, self._wave_plot = key, None, None, None
            self._wave_state = "Audio file missing — add it again to relink"
            return
        if key == self._wave_key:
            return
        if self._wave_job:
            self._wave_job.cancel()
        self._wave_key, self._wave_data, self._wave_plot = key, None, None
        self._wave_state = "Reading waveform…"
        self._wave_job = WaveformJob(self.selected_audio["path"], base.ffmpeg_binary(), base.ROOT / "cache" / "waveforms",
            lambda data, error: self.events.put(("waveform", (key, data, error))))
        threading.Thread(target=self._wave_job.run, daemon=True).start()

    def click_timeline(self, event):
        self._timeline_drag = None
        if 32 <= event.y <= 50:
            nearby = [marker for marker in self._key_markers if abs(marker[0]-event.x) <= 7]
            if nearby:
                _x, index, at = min(nearby, key=lambda marker: abs(marker[0]-event.x))
                self.select_keyframe(index, at)
                point = next(point for point in self.scenes[index]["keyframes"] if point["at"] == at)
                self._timeline_drag = {"scene": self.scenes[index], "index": index, "point": point,
                    "at": at, "x": event.x, "started": False, "before": self.document(),
                    "history": list(self.history), "future": list(self.future), "dirty": self.dirty}
                return
        self.scrub_timeline(event)

    def scrub_timeline(self, event):
        width = max(1, self.timeline.winfo_width()-16)
        self.seek(max(0, min(1, (event.x-8)/width))*total_duration(self.scenes))

    def drag_timeline(self, event):
        drag = self._timeline_drag
        if drag is None:
            self.scrub_timeline(event)
            return
        if abs(event.x-drag["x"]) < 3 and not drag["started"]:
            return
        if drag["index"] >= len(self.scenes) or self.scenes[drag["index"]] is not drag["scene"]:
            self._timeline_drag = None
            return
        width = max(1, self.timeline.winfo_width()-16)
        last = round(drag["scene"]["duration"]*base.FPS)-1
        seconds = drag["at"]*last/base.FPS + (event.x-drag["x"])/width*total_duration(self.scenes)
        at = keyframe_target_time(drag["scene"], drag["point"]["at"], seconds, base.FPS)
        if at == drag["point"]["at"]:
            return
        if not drag["started"]:
            self.checkpoint()
            drag["started"] = True
        drag["point"]["at"] = at
        self.select_keyframe(drag["index"], at)
        self.changed()
        self.status.set(f"Scene {drag['index']+1}: keyframe at {at*last/base.FPS:.2f}s — unsaved")

    def end_timeline_drag(self, _event=None):
        drag = self._timeline_drag
        self._timeline_drag = None
        if drag and drag["started"] and self.document() == drag["before"]:
            self.history, self.future, self.dirty = drag["history"], drag["future"], drag["dirty"]
            self.status.set("Unsaved changes" if self.dirty else "Ready")

    def seek(self, seconds, pause=True):
        if pause:
            self.pause()
        total = total_duration(self.scenes)
        self.playhead = max(0, min(round(seconds*base.FPS)/base.FPS, total))
        index = scene_at(self.scenes, self.playhead)
        if index is not None:
            if pause or index != self.selected():
                self.endpoint.set("start")
                self.key_at = None
            self.items.selection_clear(0, "end")
            self.items.selection_set(index)
            self.items.see(index)
            self.sync_camera()
        self.draw_preview()
        self.draw_timeline()

    def pause(self):
        self.playing = False
        self._audio_pending = False
        if self._audio_preview:
            job, self._audio_preview = self._audio_preview, None
            job.cancel()
            winsound.PlaySound(None, 0)
            try:
                job.path.unlink(missing_ok=True)
            except OSError:
                pass
        if self._tick_job:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None
        if hasattr(self, "play_button"):
            self.play_button.configure(text="Play")

    def toggle_play(self):
        if self.playing or self._audio_pending:
            self.pause()
        elif self.scenes:
            if self.playhead >= total_duration(self.scenes):
                self.seek(0)
            if self.audio or self.music:
                self._audio_pending = True
                self.play_button.configure(text="Cancel audio")
                self.status.set("Preparing preview audio…")
                job = PreviewAudio(base.ffmpeg_binary(), base.TEMP,
                                   lambda job, error: self.events.put(("preview-audio", (job, error))))
                self._audio_preview = job
                threading.Thread(target=job.run,
                                 args=(copy.deepcopy([t for t in (self.audio, self.music) if t]), total_duration(self.scenes), self.playhead),
                                 daemon=True).start()
            else:
                self.start_preview()

    def start_preview(self):
        self._audio_pending = False
        self.playing = True
        self.play_button.configure(text="Pause")
        self._clock_start = time.monotonic()-self.playhead
        self.tick()

    def tick(self):
        self._tick_job = None
        if not self.playing:
            return
        seconds = time.monotonic()-self._clock_start
        total = total_duration(self.scenes)
        if seconds >= total:
            if self.loop.get():
                self.seek(0)
                self.toggle_play()
                return
            else:
                self.seek(total)
                return
        self.seek(seconds, pause=False)
        self._tick_job = self.root.after(40, self.tick)

    def sync_audio(self):
        self.audio_repeat.set(self.selected_audio.get('repeat', False) if self.selected_audio else False)
        labels = [name for name, track in (("Narration", self.audio), ("Music", self.music)) if track]
        selected = Path(self.selected_audio["path"]).name if self.selected_audio else "No audio on this track"
        self.audio_label.set(selected + " | Mix: " + (" + ".join(labels) if labels else "empty"))
        for key, field in self.audio_inputs.items():
            field.set(str(self.selected_audio[key] if self.selected_audio else (1 if key == "volume" else 0)))

    def narration_dialog(self):
        if self.busy:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Create offline narration")
        ttk.Label(dialog, text="English narration · Local Kokoro voice · No network required", padding=10).pack()
        script = tk.Text(dialog, width=65, height=12, wrap="word")
        script.pack(padx=12, pady=6)
        options = ttk.Frame(dialog)
        options.pack(fill="x", padx=12)
        voice = tk.StringVar(dialog, "am_michael")
        speed = tk.StringVar(dialog, "1.0")
        ttk.Label(options, text="Voice").pack(side="left")
        ttk.Combobox(options, textvariable=voice, values=("am_michael", "af_heart"), state="readonly").pack(side="left", padx=5)
        ttk.Label(options, text="Speed 0.5–2").pack(side="left")
        ttk.Entry(options, textvariable=speed, width=7).pack(side="left", padx=5)
        def generate():
            if self.busy:
                return
            text = script.get("1.0", "end").strip()
            try:
                rate = float(speed.get())
                if not text or len(text) > 10000 or not .5 <= rate <= 2:
                    raise ValueError("Use 1–10,000 characters and a speed of 0.5–2.")
            except ValueError as exc:
                messagebox.showerror("Check narration", str(exc), parent=dialog)
                return
            selected_voice = voice.get()
            self.pause()
            self.busy = True
            self.render_button.state(["disabled"])
            self.status.set("Generating offline narration…")
            destination = base.EXPORTS / ("narration-"+uuid.uuid4().hex+".wav")
            dialog.destroy()
            def worker():
                try:
                    from narration import generate
                    generate(text, destination, voice=selected_voice, speed=rate)
                    self.events.put(("narration", str(destination)))
                except Exception as exc:
                    self.events.put(("error", str(exc)))
            threading.Thread(target=worker, daemon=True).start()
        ttk.Button(dialog, text="Generate WAV", command=generate).pack(pady=10)

    def add_audio(self):
        path = filedialog.askopenfilename(title="Add soundtrack or narration", filetypes=[("Audio", "*.wav *.mp3 *.m4a *.aac *.ogg *.flac")])
        if path:
            self.checkpoint()
            self.selected_audio = audio_values({"path": str(Path(path).resolve())})
            self.sync_audio()
            self.draw_timeline()
            self.changed()

    def remove_audio(self):
        if self.selected_audio:
            self.checkpoint()
            self.selected_audio = None
            self.sync_audio()
            self.draw_timeline()
            self.changed()

    def apply_audio(self):
        if not self.selected_audio:
            self.status.set("Add audio first.")
            return
        try:
            audio = audio_values({"path": self.selected_audio["path"], "repeat": self.audio_repeat.get(), **{k: v.get() for k, v in self.audio_inputs.items()}})
        except ValueError as exc:
            messagebox.showerror("Invalid audio settings", str(exc))
            return
        self.checkpoint()
        self.selected_audio = audio
        self.changed()
        self.draw_timeline()

    def discard_ok(self):
        if not self.dirty:
            return True
        result = messagebox.askyesnocancel("Unsaved changes", "Save this project before continuing?")
        return self.save() if result else result is False

    def new(self):
        if self.busy:
            self.status.set("Wait for the current export or narration to finish.")
            return
        if not self.discard_ok():
            return
        self.pause()
        self.scenes, self.audio, self.music = [], None, None
        self.output_format = "portrait"
        self.sync_format()
        self.project_path = None
        self.playhead = 0
        self.history.clear()
        self.future.clear()
        self.dirty = False
        self.sync_audio()
        self.refresh()
        self.status.set("New project")

    def load_from(self, path):
        doc = read_project(path)
        self.pause()
        self.endpoint.set("start")
        self.key_at = None
        self.scenes, self.audio, self.music = doc["scenes"], doc["audio"], doc["music"]
        self.output_format = doc["format"]
        self.sync_format()
        self.project_path = Path(path)
        self.playhead = 0
        self.history.clear()
        self.future.clear()
        self.dirty = False
        self.sync_audio()
        self.refresh(0 if self.scenes else None)
        self.status.set(f"Opened {path}")

    def open_project(self):
        if self.busy:
            self.status.set("Wait for the current export or narration to finish.")
            return
        if self.discard_ok():
            super().open_project()

    def save(self):
        if not self.project_path or not self.project_path.exists():
            return self.save_as()
        try:
            self.check_output_drive(self.project_path)
            write_project(self.project_path, self.scenes, self.audio, self.music, self.output_format)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("Cannot save", str(exc))
            return False
        self.dirty = False
        self.status.set(f"Saved {self.project_path}")
        return True

    def save_as(self):
        path = filedialog.asksaveasfilename(title="Save StoryStudio project", initialdir=str(base.PROJECTS),
                                          defaultextension=".json", filetypes=[("StoryStudio project", "*.json")])
        if not path:
            return False
        if Path(path).exists():
            messagebox.showerror("File protected", "Choose a new project filename. Use Save to update the open project.")
            return False
        try:
            self.check_output_drive(path)
            write_project(path, self.scenes, self.audio, self.music, self.output_format)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("Cannot save", str(exc))
            return False
        self.project_path = Path(path)
        self.dirty = False
        self.status.set(f"Saved {path}")
        return True

    def export(self):
        if self.busy:
            return
        if not self.scenes:
            messagebox.showwarning("No scenes", "Add at least one image.")
            return
        path = filedialog.asksaveasfilename(title="Export MP4 (choose a new filename)", initialdir=str(base.EXPORTS),
                                          initialfile="story.mp4", defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if path:
            self.render(path)

    def preview_movie(self):
        if not self.busy and self.scenes:
            self.render(base.TEMP / ("preview-"+uuid.uuid4().hex+".mp4"))

    def cancel_export(self):
        if self._render_control:
            self._render_control.cancel()
            self.cancel_button.state(["disabled"])
            self.status.set("Canceling export…")

    def render(self, path):
        if self.busy:
            return
        try:
            self.check_output_drive(path)
        except ValueError as exc:
            messagebox.showerror("Choose a D: destination", str(exc))
            return
        self.pause()
        scenes, audio, music, output_format = self.document()
        self.busy = True
        self.render_button.state(["disabled"])
        control = self._render_control = RenderControl()
        self.cancel_button.state(["!disabled"])
        self.status.set("Starting export…")
        def worker():
            try:
                output = base.render_scenes(scenes, path, lambda msg: self.events.put(("progress", msg)), audio=audio, music=music, control=control, output_format=output_format)
                self.events.put(("done", str(output)))
            except RenderCancelled as exc:
                self.events.put(("canceled", str(exc)))
            except Exception as exc:
                detail = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
                self.events.put(("error", str(detail)[-1500:]))
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def check_output_drive(path):
        import os
        if os.name == "nt" and Path(path).resolve().drive.lower() != base.ROOT.drive.lower():
            raise ValueError(f"Keep projects and exports on {base.ROOT.drive}. Use Save as for projects opened elsewhere.")

    def _poll_events(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "preview-audio":
                job, error = value
                if job is not self._audio_preview:
                    job.path.unlink(missing_ok=True)
                    continue
                if error:
                    self.pause()
                    self.status.set(error)
                    continue
                try:
                    winsound.PlaySound(str(job.path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                except RuntimeError as exc:
                    self.pause()
                    self.status.set(f"Audio device unavailable: {exc}")
                    continue
                self.status.set("Playing with audio")
                self.start_preview()
                continue
            if kind == "waveform":
                key, data, error = value
                if key == self._wave_key:
                    self._wave_data = data
                    self._wave_state = "Waveform unavailable" if error else ""
                    self._wave_plot = None
                    self.draw_timeline()
                continue
            if kind == "progress" and self._render_control and self._render_control.event.is_set():
                continue
            self.status.set(value)
            if kind in ("done", "error", "narration", "canceled"):
                self.busy = False
                self.render_button.state(["!disabled"])
                self.cancel_button.state(["disabled"])
                self._render_control = None
                if kind == "canceled":
                    continue
                if kind == "error":
                    messagebox.showerror("Render failed", value)
                elif kind == "narration":
                    if self.audio and not messagebox.askyesno("Narration ready", "Use the generated narration instead of the current soundtrack? The original audio file will be kept."):
                        continue
                    self.checkpoint()
                    self.audio = audio_values({"path": value})
                    self.audio_track.set("Narration")
                    self.sync_audio()
                    self.draw_timeline()
                    self.changed()
                    self.status.set(f"Narration ready: {value}")
                else:
                    # An explicit button allows playback with the user's usual player.
                    dialog = tk.Toplevel(self.root)
                    dialog.title("Export complete")
                    ttk.Label(dialog, text=value, wraplength=600, padding=15).pack()
                    def play():
                        import os
                        os.startfile(value)
                    ttk.Button(dialog, text="Play video", command=play).pack(pady=10)
        self._poll_job = self.root.after(100, self._poll_events)

    def close(self):
        if self.busy:
            messagebox.showinfo("Export in progress", "Wait for the export to finish before closing StoryStudio.")
            return
        if self.discard_ok():
            self.pause()
            if self._wave_job:
                self._wave_job.cancel()
            if self._poll_job:
                self.root.after_cancel(self._poll_job)
            self.root.destroy()
