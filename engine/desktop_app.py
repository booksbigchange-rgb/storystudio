"""StoryStudio desktop MVP: image scene sequencing and local FFmpeg rendering.

Run with the D: Python runtime. No cloud services or extra UI dependencies.
"""
import json
import math
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from timeline import scene_at, scene_ranges, total_duration
from camera import DEFAULT as CAMERA_DEFAULT, camera_values, zoompan_filter
from animation import validated_layers, retime_layers, upsert_keyframe, move_keyframe, delete_keyframe, layer_state, ANIMATABLE
from layer_render import render_layer_segment
from stage import DEFAULT as CANVAS_DEFAULT, PRESETS, validate_canvas
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    tk = None
    filedialog = messagebox = ttk = None

ROOT = Path(os.environ.get("STORY_STUDIO", Path(__file__).resolve().parents[1])).expanduser().resolve()
PROJECTS = ROOT / "projects"
EXPORTS = ROOT / "exports"
TEMP = ROOT / "temp"
FFMPEG = ROOT / "tools" / "ffmpeg" / "ffmpeg.exe"
FPS = 24
WIDTH, HEIGHT = 1080, 1920


def ffmpeg_binary():
    configured = os.environ.get("STORY_STUDIO_FFMPEG")
    if configured:
        return configured if Path(configured).is_file() else None
    return str(FFMPEG) if FFMPEG.is_file() else shutil.which("ffmpeg")


def render_scenes(scenes, output, progress=None, canvas=None):
    """Render still-image scenes into a vertical H.264 MP4, with no shell calls."""
    if not scenes:
        raise ValueError("Add at least one scene before rendering")
    binary = ffmpeg_binary()
    if not binary:
        raise RuntimeError("FFmpeg not found in tools/ffmpeg or PATH")
    settings = validate_canvas(canvas) if canvas is not None else {
        "width": WIDTH, "height": HEIGHT, "fit": "fill"}
    frame_width, frame_height, frame_fit = (
        settings["width"], settings["height"], settings["fit"])
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    job = TEMP / ("render-" + uuid.uuid4().hex)
    job.mkdir(parents=True, exist_ok=False)
    try:
        segments = []
        for index, scene in enumerate(scenes):
            image = Path(scene["image"]).resolve()
            if not image.is_file():
                raise FileNotFoundError(str(image))
            duration = float(scene["duration"])
            if not math.isfinite(duration) or not 0.5 <= duration <= 120:
                raise ValueError("Scene duration must be between 0.5 and 120 seconds")
            frames = round(duration * FPS)
            segment = job / f"scene_{index:04d}.mp4"
            if scene.get("layers"):
                render_layer_segment(scene, segment, binary, frame_width, frame_height, FPS, frame_fit)
            else:
                # Scale/crop to fill a vertical frame; subtle movement without
                # fabricating character animation from a single illustration.
                if frame_fit == "fit":
                    background_filter = (
                        f"scale={frame_width}:{frame_height}:force_original_aspect_ratio=decrease,"
                        f"pad={frame_width}:{frame_height}:(ow-iw)/2:(oh-ih)/2:color=0x141820,"
                    )
                else:
                    background_filter = (
                        f"scale={frame_width}:{frame_height}:force_original_aspect_ratio=increase,"
                        f"crop={frame_width}:{frame_height},"
                    )
                vf = (background_filter
                      + zoompan_filter(scene, frames, frame_width, frame_height, FPS)
                      + ",format=yuv420p")
                cmd = [
                    binary, "-hide_banner", "-loglevel", "error", "-y",
                    "-loop", "1", "-i", str(image), "-vf", vf,
                    "-frames:v", str(frames), "-an",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-pix_fmt", "yuv420p", str(segment)
                ]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            segments.append(segment)
            if progress:
                progress(f"Rendered scene {index + 1}/{len(scenes)}")
        # concat demuxer reads a local list of sanitized generated filenames.
        listing = job / "scenes.txt"
        listing.write_text(
            "".join(f"file 'scene_{i:04d}.mp4'\n" for i in range(len(segments))),
            encoding="utf-8",
        )
        cmd = [
            binary, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", "-movflags", "+faststart", str(output)
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        if progress:
            progress("Export complete")
        return output
    finally:
        shutil.rmtree(job, ignore_errors=True)


class StoryStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StoryStudio — 2D Animation Studio")
        self.root.geometry("1440x900")
        self.root.minsize(1000, 690)
        self._preview_image = None
        self._stage_rect = None
        self.preview_end = False
        self.playhead = 0.0
        self.playing = False
        self._play_clock = None
        self._play_from = 0.0
        self._play_job = None
        self._sync_scrubber = False
        self.canvas_settings = dict(CANVAS_DEFAULT)
        self.canvas_preset = tk.StringVar(value="Portrait 9:16")
        self.fit_mode = tk.StringVar(value="fill")
        self.time_readout = tk.StringVar(value="0.00 / 0.00 s")
        self.scenes = []
        self.project_path = PROJECTS / "desktop-mvp" / "story.json"
        self.status = tk.StringVar(value="Add illustrated scenes to begin.")
        self.duration = tk.StringVar(value="5")
        self.camera_inputs = {key: tk.StringVar(value=str(value)) for key, value in CAMERA_DEFAULT.items()}
        self.build()
        if self.project_path.exists():
            try:
                self.load_from(self.project_path)
            except (OSError, ValueError, KeyError) as exc:
                self.status.set(f"Project not loaded: {exc}")

    def build(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="StoryStudio", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            frame, text="Create animated scenes with characters, keyframes and local MP4 export."
        ).pack(anchor="w", pady=(0, 8))
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=4)
        ttk.Button(toolbar, text="Add image", command=self.add).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Remove", command=self.remove).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Move up", command=lambda: self.move(-1)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Move down", command=lambda: self.move(1)).pack(side="left", padx=2)
        ttk.Label(toolbar, text="Seconds:").pack(side="left", padx=(16, 4))
        ttk.Entry(toolbar, textvariable=self.duration, width=6).pack(side="left")
        ttk.Button(toolbar, text="Apply duration", command=self.apply_duration).pack(side="left", padx=4)
        canvas_row = ttk.Frame(frame)
        canvas_row.pack(fill="x", pady=(5, 2))
        ttk.Label(canvas_row, text="CANVAS").pack(side="left", padx=(0, 8))
        ttk.Combobox(canvas_row, textvariable=self.canvas_preset,
                     values=list(PRESETS), width=19, state="readonly").pack(side="left", padx=3)
        ttk.Label(canvas_row, text="Image framing").pack(side="left", padx=(12, 3))
        ttk.Combobox(canvas_row, textvariable=self.fit_mode,
                     values=("fill", "fit"), width=7, state="readonly").pack(side="left", padx=3)
        ttk.Button(canvas_row, text="Apply canvas", command=self.apply_canvas).pack(side="left", padx=6)
        ttk.Label(canvas_row, text="Fit = entire image, Fill = crop to stage").pack(side="left", padx=8)
        camera_row = ttk.Frame(frame)
        camera_row.pack(fill="x", pady=(6, 2))
        ttk.Label(camera_row, text="CAMERA KEYFRAMES").pack(side="left", padx=(0, 8))
        for key in CAMERA_DEFAULT:
            ttk.Label(camera_row, text=key.replace("_", " ")).pack(side="left", padx=(6, 2))
            ttk.Entry(camera_row, textvariable=self.camera_inputs[key], width=5).pack(side="left")
        ttk.Button(camera_row, text="Apply camera", command=self.apply_camera).pack(side="left", padx=8)
        workspace = ttk.Panedwindow(frame, orient="horizontal")
        workspace.pack(fill="both", expand=True, pady=12)
        scenes_panel = ttk.Frame(workspace)
        workspace.add(scenes_panel, weight=2)
        preview_panel = ttk.Frame(workspace)
        workspace.add(preview_panel, weight=3)
        ttk.Label(scenes_panel, text="SCENES").pack(anchor="w")
        self.items = tk.Listbox(scenes_panel, font=("Segoe UI", 11), height=9, exportselection=False)
        self.items.pack(fill="both", expand=True)
        self.items.bind("<<ListboxSelect>>", self.on_select)
        ttk.Label(scenes_panel, text="CHARACTER / PROP LAYERS").pack(anchor="w", pady=(10, 2))
        self.layer_items = tk.Listbox(scenes_panel, font=("Segoe UI", 10), height=5,
                                      exportselection=False)
        self.layer_items.pack(fill="x")
        self.layer_items.bind("<<ListboxSelect>>", self.on_layer_select)
        layer_actions = ttk.Frame(scenes_panel)
        layer_actions.pack(fill="x", pady=3)
        ttk.Button(layer_actions, text="Add PNG", command=self.add_layer).pack(side="left", padx=2)
        ttk.Button(layer_actions, text="Remove", command=self.remove_layer).pack(side="left", padx=2)
        ttk.Button(layer_actions, text="Animate right", command=self.animate_layer).pack(side="left", padx=2)
        ttk.Button(layer_actions, text="Clear motion", command=self.clear_motion).pack(side="left", padx=2)
        ttk.Label(preview_panel, text="SCENE PREVIEW — drag selected character to position it").pack(anchor="w")
        preview_actions = ttk.Frame(preview_panel)
        preview_actions.pack(fill="x")
        ttk.Button(preview_actions, text="Start frame", command=lambda: self.show_pose(False)).pack(side="left", padx=2)
        ttk.Button(preview_actions, text="End frame", command=lambda: self.show_pose(True)).pack(side="left", padx=2)
        self.play_button = ttk.Button(preview_actions, text="Play", command=self.toggle_play)
        self.play_button.pack(side="left", padx=7)
        self.scrubber = ttk.Scale(preview_actions, from_=0, to=5,
                                  command=self.scrub_changed, length=180)
        self.scrubber.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(preview_actions, textvariable=self.time_readout).pack(side="left", padx=3)
        self.preview = tk.Canvas(preview_panel, width=300, height=420, bg="#20232b", highlightthickness=0)
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", lambda _event: self.draw_preview())
        self.preview.bind("<Button-1>", self.drag_selected_layer)
        self.preview.bind("<B1-Motion>", self.drag_selected_layer)
        ttk.Label(frame, text="SCENE TIMELINE — click to select scene and time").pack(anchor="w")
        self.timeline = tk.Canvas(frame, height=62, bg="#20232b", highlightthickness=0)
        self.timeline.pack(fill="x", pady=(3, 8))
        self.timeline.bind("<Configure>", lambda _event: self.draw_timeline())
        self.timeline.bind("<Button-1>", self.click_timeline)
        self.timeline_info = ttk.Label(frame, text="Total: 0.0s")
        self.timeline_info.pack(anchor="w")
        # A second local timeline for animated layers is added separately.
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(actions, text="Save project", command=self.save).pack(side="left", padx=2)
        ttk.Button(actions, text="Open project", command=self.open_project).pack(side="left", padx=2)
        self.render_button = ttk.Button(actions, text="Export MP4", command=self.export)
        self.render_button.pack(side="right", padx=2)
        ttk.Label(frame, textvariable=self.status, wraplength=790).pack(anchor="w", pady=12)
        ttk.Label(
            frame,
            text="MVP: image sequencing + gentle camera zoom. Character rigs, audio and lip-sync come later.",
            foreground="#666666",
        ).pack(anchor="w")

    def refresh(self, index=None):
        self.items.delete(0, "end")
        for n, scene in enumerate(self.scenes, 1):
            self.items.insert("end", f"{n:02d}   {Path(scene['image']).name}   —   {scene['duration']:g} seconds")
        if index is not None and 0 <= index < len(self.scenes):
            self.items.selection_set(index)
        self.refresh_layers()
        self.draw_timeline()
        self.set_playhead(0)

    def selected(self):
        selection = self.items.curselection()
        return selection[0] if selection else None

    def add(self):
        images = filedialog.askopenfilenames(
            title="Add scene illustrations",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        for image in images:
            self.scenes.append({"image": str(Path(image).resolve()), "duration": 5.0})
        self.refresh(len(self.scenes) - 1)

    def remove(self):
        index = self.selected()
        if index is not None:
            self.scenes.pop(index)
            self.refresh(min(index, len(self.scenes) - 1))

    def move(self, delta):
        index = self.selected()
        if index is None or not 0 <= index + delta < len(self.scenes):
            return
        self.scenes[index], self.scenes[index + delta] = (
            self.scenes[index + delta], self.scenes[index]
        )
        self.refresh(index + delta)

    def on_select(self, _event=None):
        self.stop_playback()
        index = self.selected()
        if index is not None:
            self.duration.set(str(self.scenes[index]["duration"]))
            for key, value in camera_values(self.scenes[index]).items():
                self.camera_inputs[key].set(str(value))
        self.preview_end = False
        self.playhead = 0.0
        self.refresh_layers()
        self.draw_timeline()
        self.set_playhead(0)

    def draw_preview(self):
        self.preview.delete("all")
        self._preview_image = None
        self._stage_rect = None
        w, h = max(self.preview.winfo_width(), 100), max(self.preview.winfo_height(), 100)
        index = self.selected()
        if index is None:
            self.preview.create_text(w // 2, h // 2, text="Select a scene to preview", fill="white")
            return
        scene = self.scenes[index]
        path = Path(scene["image"])
        if not path.is_file():
            self.preview.create_text(w // 2, h // 2, text="Image not found", fill="#ffb3b3")
            return
        try:
            from PIL import ImageTk
            from layer_render import render_scene_frame
            full_width = self.canvas_settings["width"]
            full_height = self.canvas_settings["height"]
            scale = min((w - 20) / full_width, (h - 20) / full_height)
            pw = max(1, round(full_width * scale))
            ph = max(1, round(full_height * scale))
            at = min(max(self.playhead, 0), scene["duration"])
            # Render at on-screen size so playback stays CPU-friendly.
            output = render_scene_frame(
                scene, at, pw, ph, self.canvas_settings["fit"])
            self._preview_image = ImageTk.PhotoImage(output)
            left, top = (w - pw) // 2, (h - ph) // 2
            self._stage_rect = (left, top, pw, ph)
            self.preview.create_image(w // 2, h // 2, image=self._preview_image)
        except (OSError, ValueError, RuntimeError, tk.TclError) as exc:
            self.preview.create_text(w // 2, h // 2, fill="#ffb3b3",
                                     text=f"Preview unavailable: {exc}", width=w - 20)

    def set_playhead(self, seconds, update_slider=True):
        index = self.selected()
        if index is None:
            self.playhead = 0.0
            self.time_readout.set("0.00 / 0.00 s")
            return
        duration = float(self.scenes[index]["duration"])
        self.playhead = max(0.0, min(float(seconds), duration))
        self.time_readout.set(f"{self.playhead:.2f} / {duration:.2f} s")
        if update_slider:
            self._sync_scrubber = True
            try:
                self.scrubber.configure(to=duration)
                self.scrubber.set(self.playhead)
            finally:
                self._sync_scrubber = False
        self.draw_preview()
        self.draw_motion_timeline()
        self.refresh_transform_fields()

    def scrub_changed(self, value):
        if self._sync_scrubber:
            return
        self.stop_playback()
        if self.selected() is not None:
            self.set_playhead(float(value), update_slider=False)

    def toggle_play(self):
        if self.playing:
            self.stop_playback()
            return
        index = self.selected()
        if index is None:
            return
        duration = float(self.scenes[index]["duration"])
        if self.playhead >= duration:
            self.set_playhead(0)
        self.playing = True
        self._play_from = self.playhead
        self._play_clock = time.monotonic()
        self.play_button.configure(text="Pause")
        self.tick_playback()

    def tick_playback(self):
        if not self.playing:
            return
        index = self.selected()
        if index is None:
            self.stop_playback()
            return
        duration = float(self.scenes[index]["duration"])
        seconds = self._play_from + (time.monotonic() - self._play_clock)
        self.set_playhead(min(seconds, duration))
        if seconds >= duration:
            self.stop_playback()
        else:
            # Preview is approximate 10 fps, while the final MP4 remains 24 fps.
            self._play_job = self.root.after(100, self.tick_playback)

    def stop_playback(self):
        self.playing = False
        if self._play_job is not None:
            self.root.after_cancel(self._play_job)
            self._play_job = None
        if hasattr(self, "play_button"):
            self.play_button.configure(text="Play")

    def apply_canvas(self):
        preset = self.canvas_preset.get()
        if preset not in PRESETS:
            messagebox.showerror("Canvas", "Choose a supported canvas preset")
            return
        width, height = PRESETS[preset]
        try:
            updated = validate_canvas(
                {"width": width, "height": height, "fit": self.fit_mode.get()})
        except ValueError as exc:
            messagebox.showerror("Canvas", str(exc))
            return
        self.stop_playback()
        self.canvas_settings = updated
        self.draw_preview()
        self.status.set(f"Canvas set to {width}x{height}, {updated['fit']} mode.")

    def draw_motion_timeline(self):
        # Populated by the editable-keyframe timeline milestone.
        pass

    def refresh_transform_fields(self):
        # Populated by the editable-keyframe timeline milestone.
        pass

    def on_layer_select(self, _event=None):
        self.refresh_transform_fields()
        self.draw_preview()

    def selected_layer(self):
        selected = self.layer_items.curselection()
        return selected[0] if selected else None

    def refresh_layers(self, index=None):
        self.layer_items.delete(0, "end")
        scene_index = self.selected()
        if scene_index is None:
            return
        layers = self.scenes[scene_index].get("layers", [])
        for layer in layers:
            motion = "  • animated" if layer.get("keyframes") else ""
            self.layer_items.insert("end", f"{layer.get('name', 'Character')}{motion}")
        if layers:
            position = min(index if index is not None else 0, len(layers) - 1)
            self.layer_items.selection_set(position)

    def add_layer(self):
        scene_index = self.selected()
        if scene_index is None:
            messagebox.showwarning("Choose a scene", "Select a scene before adding a character.")
            return
        path = filedialog.askopenfilename(title="Choose a character or prop with transparency",
                                          filetypes=[("PNG artwork", "*.png")])
        if not path:
            return
        layer = {"id": uuid.uuid4().hex, "name": Path(path).stem, "image": str(Path(path).resolve()),
                 "x": 0.3, "y": 0.55, "width": 0.32, "scale": 1.0,
                 "rotation": 0.0, "opacity": 1.0, "keyframes": []}
        layers = self.scenes[scene_index].setdefault("layers", [])
        if len(layers) >= 32:
            messagebox.showerror("Layer limit", "A scene supports up to 32 layers.")
            return
        layers.append(layer)
        self.preview_end = False
        self.refresh_layers(len(layers) - 1)
        self.draw_preview()
        self.status.set("Character added. Drag the selected layer inside the preview to position it.")

    def remove_layer(self):
        scene_index, layer_index = self.selected(), self.selected_layer()
        if scene_index is None or layer_index is None:
            return
        self.scenes[scene_index]["layers"].pop(layer_index)
        self.refresh_layers()
        self.draw_preview()

    def animate_layer(self):
        scene_index, layer_index = self.selected(), self.selected_layer()
        if scene_index is None or layer_index is None:
            self.status.set("Select a character layer to animate.")
            return
        scene = self.scenes[scene_index]
        layer = scene["layers"][layer_index]
        x, y = float(layer.get("x", 0.5)), float(layer.get("y", 0.5))
        layer["keyframes"] = [
            {"time": 0.0, "x": x, "y": y},
            {"time": float(scene["duration"]), "x": min(x + 0.35, 2.0),
             "y": y, "ease": "smooth"},
        ]
        self.refresh_layers(layer_index)
        self.set_playhead(scene["duration"])
        self.status.set("Motion created. Click Play or scrub to preview the full movement.")

    def clear_motion(self):
        scene_index, layer_index = self.selected(), self.selected_layer()
        if scene_index is None or layer_index is None:
            return
        self.scenes[scene_index]["layers"][layer_index]["keyframes"] = []
        self.refresh_layers(layer_index)
        self.set_playhead(0)

    def show_pose(self, end):
        self.stop_playback()
        index = self.selected()
        if index is not None:
            self.set_playhead(self.scenes[index]["duration"] if end else 0)

    def drag_selected_layer(self, event):
        scene_index, layer_index = self.selected(), self.selected_layer()
        if scene_index is None or layer_index is None or self._stage_rect is None:
            return
        left, top, width, height = self._stage_rect
        if not (left <= event.x <= left + width and top <= event.y <= top + height):
            return
        # The layer is translated together with its keyframes. That preserves
        # existing motion rather than silently discarding the animation.
        layer = self.scenes[scene_index]["layers"][layer_index]
        x = (event.x - left) / width
        y = (event.y - top) / height
        old_x, old_y = float(layer.get("x", 0.5)), float(layer.get("y", 0.5))
        dx, dy = x - old_x, y - old_y
        layer["x"], layer["y"] = x, y
        for key in layer.get("keyframes", []):
            if "x" in key:
                key["x"] = max(-1.0, min(2.0, key["x"] + dx))
            if "y" in key:
                key["y"] = max(-1.0, min(2.0, key["y"] + dy))
        self.draw_preview()

    def draw_timeline(self):
        self.timeline.delete("all")
        total = total_duration(self.scenes)
        self.timeline_info.configure(text=f"Total: {total:.1f}s  •  {len(self.scenes)} scenes")
        if not self.scenes:
            self.timeline.create_text(12, 38, anchor="w", text="Add images to build your timeline", fill="white")
            return
        width = max(self.timeline.winfo_width() - 16, 1)
        selected = self.selected()
        for i, (start, end) in enumerate(scene_ranges(self.scenes)):
            x1 = 8 + start / total * width
            x2 = 8 + end / total * width
            fill = "#57a4e9" if i == selected else "#53617b"
            self.timeline.create_rectangle(x1, 12, x2, 64, fill=fill, outline="#20232b", width=2)
            if x2 - x1 > 45:
                self.timeline.create_text((x1 + x2) / 2, 30, text=f"Scene {i + 1}", fill="white")
                self.timeline.create_text((x1 + x2) / 2, 48, text=f"{end - start:g}s", fill="white")

    def click_timeline(self, event):
        if not self.scenes:
            return
        width = max(self.timeline.winfo_width() - 16, 1)
        position = min(max((event.x - 8) / width, 0), 1) * total_duration(self.scenes)
        index = scene_at(self.scenes, position)
        if index is not None:
            start = scene_ranges(self.scenes)[index][0]
            self.items.selection_clear(0, "end")
            self.items.selection_set(index)
            self.items.see(index)
            self.on_select()
            self.set_playhead(position - start)

    def apply_camera(self):
        index = self.selected()
        if index is None:
            self.status.set("Select a scene before applying camera keyframes.")
            return
        try:
            values = camera_values({key: field.get() for key, field in self.camera_inputs.items()})
        except (TypeError, ValueError) as exc:
            messagebox.showerror("Invalid camera keyframes", str(exc))
            return
        self.scenes[index].update(values)
        self.status.set(f"Camera keyframes updated for scene {index + 1}.")
        self.draw_preview()

    def apply_duration(self):
        index = self.selected()
        if index is None:
            return
        try:
            seconds = float(self.duration.get())
            if not math.isfinite(seconds) or not 0.5 <= seconds <= 120:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid duration", "Use 0.5 to 120 seconds.")
            return
        scene = self.scenes[index]
        if scene.get("layers"):
            scene["layers"] = retime_layers(scene["layers"], scene["duration"], seconds)
        scene["duration"] = seconds
        self.refresh(index)

    def save(self):
        self.project_path.parent.mkdir(parents=True, exist_ok=True)
        self.project_path.write_text(
            json.dumps({"version": 1, "canvas": self.canvas_settings,
                        "scenes": self.scenes}, indent=2), encoding="utf-8"
        )
        self.status.set(f"Saved {self.project_path}")

    def load_from(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("version") != 1 or not isinstance(data.get("scenes"), list):
            raise ValueError("Unsupported project format")
        scenes = []
        for scene in data["scenes"]:
            image = scene["image"]
            duration = float(scene["duration"])
            if not isinstance(image, str) or not math.isfinite(duration) or not 0.5 <= duration <= 120:
                raise ValueError("Invalid scene data")
            scenes.append({**scene, "image": image, "duration": duration,
                           **camera_values(scene),
                           "layers": validated_layers(scene.get("layers", []), duration)})
        self.stop_playback()
        self.canvas_settings = validate_canvas(data.get("canvas"))
        self.fit_mode.set(self.canvas_settings["fit"])
        self.canvas_preset.set(next(
            (name for name, size in PRESETS.items()
             if size == (self.canvas_settings["width"], self.canvas_settings["height"])),
            "Portrait 9:16"))
        self.scenes = scenes
        self.project_path = Path(path)
        self.refresh(0 if self.scenes else None)
        self.status.set(f"Opened {path}")

    def open_project(self):
        path = filedialog.askopenfilename(
            title="Open StoryStudio project", filetypes=[("StoryStudio JSON", "*.json")]
        )
        if path:
            try:
                self.load_from(path)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                messagebox.showerror("Cannot open project", str(exc))

    def export(self):
        if not self.scenes:
            messagebox.showwarning("No scenes", "Add at least one image.")
            return
        EXPORTS.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save MP4", initialdir=str(EXPORTS),
            initialfile="story.mp4", defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
        )
        if not path:
            return
        # Snapshot scene data before a background worker reads it.
        scenes = [dict(s) for s in self.scenes]
        canvas_settings = dict(self.canvas_settings)
        self.render_button.state(["disabled"])
        self.status.set("Rendering video...")
        def report(message):
            self.root.after(0, lambda m=message: self.status.set(m))
        def worker():
            try:
                output = render_scenes(scenes, path, report, canvas=canvas_settings)
                self.root.after(0, lambda: messagebox.showinfo("Export complete", str(output)))
            except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
                detail = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
                self.root.after(0, lambda d=detail: messagebox.showerror("Render failed", d[-1500:]))
            finally:
                self.root.after(0, lambda: self.render_button.state(["!disabled"]))
        threading.Thread(target=worker, daemon=True).start()


def main():
    if tk is None:
        raise RuntimeError("Tkinter is required to launch the desktop GUI; headless rendering remains available")
    for path in (PROJECTS, EXPORTS, TEMP):
        path.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    StoryStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
