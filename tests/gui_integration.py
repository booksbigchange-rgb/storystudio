"""Actual Tk widget/event-loop checks; run explicitly on a desktop with Pillow."""
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from PIL import Image
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp
from camera import camera_values


def main():
    with tempfile.TemporaryDirectory() as folder:
        directory = Path(folder)
        image = directory / "test.png"
        Image.new("RGB", (360, 640), "#70bca0").save(image)
        errors = []
        with mock.patch.object(base, "PROJECTS", directory), mock.patch.object(base, "EXPORTS", directory):
            root = tk.Tk()
            root.report_callback_exception = lambda *args: errors.append(str(args))
            app = EditorApp(root)
            root.update()
            root.geometry("1000x680")
            root.update()
            def buttons(widget):
                for child in widget.winfo_children():
                    if child.winfo_class() == "TButton":
                        yield child
                    yield from buttons(child)
            for button in buttons(root):
                assert button.winfo_rootx()+button.winfo_width() <= root.winfo_rootx()+root.winfo_width(), button.cget("text")
                assert button.winfo_rooty()+button.winfo_height() <= root.winfo_rooty()+root.winfo_height(), button.cget("text")
            with mock.patch("editor_app.filedialog.askopenfilenames", return_value=(str(image),)):
                app.add()
            root.update()
            assert app.selected() == 0 and app._preview_image is not None
            app.duration.set("1")
            app.apply_duration()
            app.endpoint.set("end")
            app.choose_endpoint()
            app.checkpoint()
            app.zoom.set(1.7)
            app.change_zoom()
            ox, oy, scale, sw, sh = app._preview_geometry
            x, y = ox+sw*scale/2, oy+sh*scale/2
            app.begin_drag(SimpleNamespace(x=x, y=y))
            app.drag_camera(SimpleNamespace(x=x+20, y=y+20))
            app.end_drag()
            assert app.scenes[0]["x_end"] > .5
            moved = app.scenes[0]["x_end"]
            app.undo()
            assert camera_values(app.scenes[0])["x_end"] == .5
            app.redo()
            assert app.scenes[0]["x_end"] == moved
            app.duplicate()
            assert len(app.scenes) == 2
            app.move(-1)
            assert app.selected() == 0
            app.seek(.5)
            app.add_keyframe()
            assert len(app.scenes[0]["keyframes"]) == 1
            app.checkpoint()
            app.zoom.set(1.95)
            app.change_zoom()
            assert app.scenes[0]["keyframes"][0]["zoom"] == 1.95
            marker = app._key_markers[0]
            app.seek(0)
            app.click_timeline(SimpleNamespace(x=marker[0], y=41))
            assert app.endpoint.get() == "key" and app.zoom.get() == 1.95
            original_at = app.key_at
            history_length = len(app.history)
            app.timeline.event_generate("<ButtonPress-1>", x=round(marker[0]), y=41)
            root.update()
            for delta in (20, 40, 60):
                app.timeline.event_generate("<B1-Motion>", x=round(marker[0])+delta, y=41)
                root.update()
            app.timeline.event_generate("<ButtonRelease-1>", x=round(marker[0])+60, y=41)
            root.update()
            dragged_at = app.scenes[0]["keyframes"][0]["at"]
            assert dragged_at > original_at
            assert app.scenes[0]["keyframes"][0]["zoom"] == 1.95
            assert len(app.history) == history_length+1
            app.undo()
            assert app.scenes[0]["keyframes"][0]["at"] == original_at
            app.redo()
            assert app.scenes[0]["keyframes"][0]["at"] == dragged_at
            app.undo()
            marker = app._key_markers[0]
            app.click_timeline(SimpleNamespace(x=marker[0], y=41))
            app.end_timeline_drag()
            app.remove_keyframe()
            assert not app.scenes[0]["keyframes"]
            app.undo()
            assert app.scenes[0]["keyframes"][0]["zoom"] == 1.95
            app.seek(.5)
            app.toggle_play()
            start = time.monotonic()
            while time.monotonic()-start < .25:
                root.update()
                time.sleep(.01)
            assert app.playhead > .5
            app.pause()
            saved = directory / "saved.json"
            with mock.patch("editor_app.filedialog.asksaveasfilename", return_value=str(saved)):
                assert app.save_as()
            original = json.loads(saved.read_text())
            app.scenes = []
            app.load_from(saved)
            assert len(app.scenes) == 2 and app.scenes[0]["zoom_end"] == 1.7
            assert app.scenes[0]["keyframes"][0]["zoom"] == 1.95
            assert original["scenes"][0]["image"] == "test.png"
            with mock.patch("editor_app.filedialog.askopenfilename", return_value=str(directory / "voice.wav")):
                app.add_audio()
            app.audio_inputs["volume"].set("0.4")
            app.audio_inputs["offset"].set("0.3")
            app.apply_audio()
            assert app.audio["volume"] == .4
            assert app.save()
            app.load_from(saved)
            assert app.audio["offset"] == .3
            preserved = app.document()
            bad = directory / "bad.json"
            bad.write_text('{"version":2,"scenes":[null]}')
            try:
                app.load_from(bad)
                raise AssertionError("Invalid project accepted")
            except ValueError:
                pass
            assert app.document() == preserved
            app.dirty = True
            with mock.patch("editor_app.messagebox.askyesnocancel", return_value=None):
                app.new()
            assert app.document() == preserved
            app.busy = True
            app.render_button.state(["disabled"])
            app.events.put(("error", "test export failure"))
            with mock.patch("editor_app.messagebox.showerror") as error:
                start = time.monotonic()
                while time.monotonic()-start < .2:
                    root.update()
                    time.sleep(.01)
                assert error.called and not app.busy and "disabled" not in app.render_button.state()
            app.seek(2)
            assert app.selected() == 1
            assert not errors, errors
            app.dirty = False
            app.close()
    print("PASS: Tk launch, 1000x680 control bounds, preview, duration, camera drag, timeline keyframe drag with one-step undo/redo, reorder, playback, project/audio roundtrip, malformed load retention, unsaved cancellation, export error recovery")


if __name__ == "__main__":
    main()
