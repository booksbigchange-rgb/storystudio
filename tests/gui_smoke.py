"""GUI smoke test: use Xvfb+system Tkinter on Linux CI.

Verifies that the actual desktop interface starts and that canvas, pose controls,
project saving and time scrubbing are wired up. No FFmpeg work in this test.
"""
import tempfile
import sys
from pathlib import Path

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import desktop_app


def main():
    with tempfile.TemporaryDirectory(prefix="storystudio-gui-") as folder:
        rootpath = Path(folder)
        desktop_app.PROJECTS = rootpath / "projects"
        bg = rootpath / "background.png"
        png = rootpath / "character.png"
        Image.new("RGB", (320, 180), (28, 45, 80)).save(bg)
        Image.new("RGBA", (100, 80), (235, 95, 35, 200)).save(png)
        root = desktop_app.tk.Tk()
        try:
            app = desktop_app.StoryStudioApp(root)
            root.update_idletasks()
            app.scenes = [{"image": str(bg), "duration": 2.0, "layers": [{
                "id": "character", "name": "Character", "image": str(png),
                "x": 0.25, "y": 0.55, "width": 0.3, "keyframes": []}]}]
            app.refresh(0)
            app.canvas_preset.set("Landscape 16:9")
            app.fit_mode.set("fit")
            app.apply_canvas()
            assert app.canvas_settings == {"width": 1920, "height": 1080, "fit": "fit"}
            app.set_playhead(1.0)
            app.transform_inputs["x"].set("0.75")
            app.commit_keyframe()
            assert app.scenes[0]["layers"][0]["keyframes"], "No keyframe stored"
            app.show_pose(False)
            assert app.playhead == 0.0
            app.show_pose(True)
            assert app.playhead == 2.0
            app.save()
            path = app.project_path
            assert path.exists()
            app.load_from(path)
            assert app.canvas_settings["fit"] == "fit"
            assert app.scenes[0]["layers"][0]["keyframes"]
            app.set_playhead(1)
            app.toggle_play()
            assert app.playing
            app.stop_playback()
            assert not app.playing
            root.update_idletasks()
            print("PASS: Tk window, landscape Fit, keyframes, save/load, playback wiring")
        finally:
            root.destroy()


if __name__ == "__main__":
    main()
