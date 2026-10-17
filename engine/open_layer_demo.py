"""Open the local layer demonstration without saving over its source project."""
import tkinter as tk
import desktop_app as base
from editor_app import EditorApp


def main():
    path = base.ROOT/'projects'/'orbit-layers-v1'/'story.json'
    if not path.is_file():
        raise FileNotFoundError('Install the Orbit layer demo project under projects/orbit-layers-v1 first.')
    root = tk.Tk()
    app = EditorApp(root)
    app.load_from(path)
    app.project_path = None
    app.status.set('Orbit layer demo loaded. Select Animate layers; Save as makes your own copy.')
    root.mainloop()


if __name__ == '__main__':
    main()
