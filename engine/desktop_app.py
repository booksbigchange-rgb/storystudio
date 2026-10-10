"""StoryStudio desktop MVP: image scene sequencing and local FFmpeg rendering.

Run with the D: Python runtime. No cloud services or extra UI dependencies.
"""
import json
import math
import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from timeline import scene_at, scene_ranges, total_duration
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


def render_scenes(scenes, output, progress=None):
    """Render still-image scenes into a vertical H.264 MP4, with no shell calls."""
    if not scenes:
        raise ValueError("Add at least one scene before rendering")
    binary = ffmpeg_binary()
    if not binary:
        raise RuntimeError("FFmpeg not found in tools/ffmpeg or PATH")
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
            # Scale/crop to fill a vertical frame; subtle movement without
            # fabricating character animation from a single illustration.
            vf = (
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{HEIGHT},"
                f"zoompan=z='min(zoom+0.0006,1.08)':"
                f"d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
                "format=yuv420p"
            )
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
        self.root.title("StoryStudio — Desktop MVP")
        self.root.geometry("1060x760")
        self._preview_image = None
        self.scenes = []
        self.project_path = PROJECTS / "desktop-mvp" / "story.json"
        self.status = tk.StringVar(value="Add illustrated scenes to begin.")
        self.duration = tk.StringVar(value="5")
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
            frame, text="Create vertical moving-storybook videos from still images."
        ).pack(anchor="w", pady=(0, 12))
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=4)
        ttk.Button(toolbar, text="Add image", command=self.add).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Remove", command=self.remove).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Move up", command=lambda: self.move(-1)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Move down", command=lambda: self.move(1)).pack(side="left", padx=2)
        ttk.Label(toolbar, text="Seconds:").pack(side="left", padx=(16, 4))
        ttk.Entry(toolbar, textvariable=self.duration, width=6).pack(side="left")
        ttk.Button(toolbar, text="Apply duration", command=self.apply_duration).pack(side="left", padx=4)
        workspace = ttk.Panedwindow(frame, orient="horizontal")
        workspace.pack(fill="both", expand=True, pady=12)
        scenes_panel = ttk.Frame(workspace)
        workspace.add(scenes_panel, weight=2)
        preview_panel = ttk.Frame(workspace)
        workspace.add(preview_panel, weight=3)
        ttk.Label(scenes_panel, text="SCENES").pack(anchor="w")
        self.items = tk.Listbox(scenes_panel, font=("Segoe UI", 11), height=13, exportselection=False)
        self.items.pack(fill="both", expand=True)
        self.items.bind("<<ListboxSelect>>", self.on_select)
        ttk.Label(preview_panel, text="SCENE PREVIEW (still image)").pack(anchor="w")
        self.preview = tk.Canvas(preview_panel, width=300, height=420, bg="#20232b", highlightthickness=0)
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", lambda _event: self.draw_preview())
        ttk.Label(frame, text="TIMELINE — click a scene to select it").pack(anchor="w")
        self.timeline = tk.Canvas(frame, height=76, bg="#20232b", highlightthickness=0)
        self.timeline.pack(fill="x", pady=(4, 12))
        self.timeline.bind("<Configure>", lambda _event: self.draw_timeline())
        self.timeline.bind("<Button-1>", self.click_timeline)
        self.timeline_info = ttk.Label(frame, text="Total: 0.0s")
        self.timeline_info.pack(anchor="w")
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
        self.draw_timeline()
        self.draw_preview()

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
        index = self.selected()
        if index is not None:
            self.duration.set(str(self.scenes[index]["duration"]))
        self.draw_timeline()
        self.draw_preview()

    def draw_preview(self):
        self.preview.delete("all")
        self._preview_image = None
        w, h = max(self.preview.winfo_width(), 100), max(self.preview.winfo_height(), 100)
        index = self.selected()
        if index is None:
            self.preview.create_text(w // 2, h // 2, text="Select a scene to preview", fill="white")
            return
        path = Path(self.scenes[index]["image"])
        if not path.is_file():
            self.preview.create_text(w // 2, h // 2, text="Image not found", fill="#ffb3b3")
            return
        try:
            # Pillow supports JPEG, PNG, and BMP with aspect-preserving scaling.
            from PIL import Image, ImageTk
            with Image.open(path) as image:
                image.thumbnail((max(w - 16, 1), max(h - 16, 1)))
                self._preview_image = ImageTk.PhotoImage(image.copy())
        except ImportError:
            try:
                self._preview_image = tk.PhotoImage(file=str(path))
                factor = max(1, (self._preview_image.width() + w - 1) // w,
                             (self._preview_image.height() + h - 1) // h)
                self._preview_image = self._preview_image.subsample(factor)
            except tk.TclError:
                self.preview.create_text(w // 2, h // 2,
                    text="Install Pillow to preview this format", fill="white")
                return
        except (OSError, ValueError, tk.TclError) as exc:
            self.preview.create_text(w // 2, h // 2, text=f"Preview unavailable: {exc}", fill="white", width=w - 20)
            return
        self.preview.create_image(w // 2, h // 2, image=self._preview_image)

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
            self.items.selection_clear(0, "end")
            self.items.selection_set(index)
            self.items.see(index)
            self.on_select()

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
        self.scenes[index]["duration"] = seconds
        self.refresh(index)

    def save(self):
        self.project_path.parent.mkdir(parents=True, exist_ok=True)
        self.project_path.write_text(
            json.dumps({"version": 1, "scenes": self.scenes}, indent=2), encoding="utf-8"
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
            scenes.append({"image": image, "duration": duration})
        self.scenes = scenes
        self.project_path = Path(path)
        self.refresh()
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
        self.render_button.state(["disabled"])
        self.status.set("Rendering video...")
        def report(message):
            self.root.after(0, lambda m=message: self.status.set(m))
        def worker():
            try:
                output = render_scenes(scenes, path, report)
                self.root.after(0, lambda: messagebox.showinfo("Export complete", str(output)))
            except (OSError, ValueError, subprocess.CalledProcessError) as exc:
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
