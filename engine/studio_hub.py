"""Shared entry point; isolate legacy engines and never convert projects implicitly."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import runtime

ROOT = runtime.app_root(__file__)


def project_kind(path):
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Project exceeds 1 MB')
    doc = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(doc, dict) and doc.get('kind') == 'storystudio-mixed':
        from mixed_project import validate
        validate(doc)
        return 'mixed'
    if not isinstance(doc, dict) or not isinstance(doc.get('scenes'), list):
        raise ValueError('Not a StoryStudio project')
    scenes = doc['scenes']
    # Version 2 occurs in both formats. Inspect the scene contract as well.
    documentary = all(isinstance(s, dict) and 'image' in s and 'character' not in s for s in scenes)
    cartoon = bool(scenes) and all(isinstance(s, dict) and 'character' in s and 'image' not in s for s in scenes)
    if documentary and type(doc.get('version')) is int and doc['version'] in range(1, 6):
        return 'documentary'
    if cartoon and type(doc.get('version')) is int and doc['version'] == 2:
        return 'cartoon'
    raise ValueError('Unknown or mixed project format; the original file has not been changed')


def command(kind, path=None):
    if kind not in ('documentary', 'cartoon', 'mixed'):
        raise ValueError('Unknown editor')
    if runtime.FROZEN:
        result = [str(runtime.helper('hub')), '--editor', kind]
        if path:
            result += ['--project', str(Path(path).resolve())]
        return result
    result = [sys.executable, str(Path(__file__).resolve()), '--editor', kind]
    if path:
        result += ['--project', str(Path(path).resolve())]
    return result


def run_editor(kind, path=None, smoke=False):
    if path and project_kind(path) != kind:
        raise ValueError('Project belongs to the other editor')
    if kind == 'mixed':
        import tkinter as tk
        from mixed_editor import MixedEditor
        root = tk.Tk()
        app = MixedEditor(root, path)
        if smoke:
            root.update()
            app.close()
        else:
            root.mainloop()
    elif kind == 'cartoon':
        # The character project model is cartoon_project (the documentary one is project), so both editors can share a process.
        sys.path.insert(0, str(ROOT / 'integrations/lemo-lite'))
        import cartoon_project as project
        from studio_ui import StudioApp
        doc = project.load(path) if path else None
        app = StudioApp(auto_preview=not smoke)
        if doc:
            app.document = doc
            app.project_path = Path(path)
            app.refresh()
            app.title('StoryStudio · ' + doc['name'])
        if smoke:
            app.update()
            app.destroy()
        else:
            app.mainloop()
    else:
        import tkinter as tk
        from editor_app import EditorApp
        from project import read_project
        if path:
            read_project(path)  # Validate before constructing the window.
        root = tk.Tk()
        app = EditorApp(root)
        if path:
            app.load_from(path)
        if smoke:
            root.update()
            app.close()
        else:
            root.mainloop()


def main():
    parser = argparse.ArgumentParser(description='StoryStudio project launcher')
    parser.add_argument('--editor', choices=('documentary', 'cartoon', 'mixed'))
    parser.add_argument('--project')
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if args.editor:
        try:
            run_editor(args.editor, args.project, args.smoke)
        except (ValueError, OSError) as exc:
            if args.smoke:
                raise
            from tkinter import messagebox
            messagebox.showerror('Cannot open StoryStudio project', str(exc))
        return
    if args.project:
        subprocess.Popen(command(project_kind(args.project), args.project), cwd=ROOT)
        return
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    root = tk.Tk()
    root.title('StoryStudio · Choose your workspace')
    root.geometry('620x440')
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='STORYSTUDIO', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Choose a workspace or open an existing project.', padding=(0,12)).pack(anchor='w')
    def launch(kind, path=None):
        subprocess.Popen(command(kind, path), cwd=ROOT)
    def templates():
        from template_editor import TemplateEditor
        TemplateEditor(root, ROOT/'projects', launch)
    ttk.Button(frame, text='Documentary templates · evidence, chronology and map focus',
               command=templates).pack(fill='x', pady=6)
    ttk.Button(frame, text='Shared timeline · combine documentary and character sections',
               command=lambda: launch('mixed')).pack(fill='x', pady=6)
    ttk.Button(frame, text='Dark documentary · artwork, camera, layers and audio',
               command=lambda: launch('documentary')).pack(fill='x', pady=6)
    ttk.Button(frame, text='Character animation · reusable rigs and actions',
               command=lambda: launch('cartoon')).pack(fill='x', pady=6)
    def open_project():
        path = filedialog.askopenfilename(parent=root, initialdir=ROOT/'projects', filetypes=[('StoryStudio projects', '*.json')])
        if path:
            try:
                launch(project_kind(path), path)
            except (ValueError, OSError) as exc:
                messagebox.showerror('Cannot open project', str(exc), parent=root)
    ttk.Button(frame, text='Open project…', command=open_project).pack(fill='x', pady=6)
    if args.smoke:
        root.update()
        root.destroy()
    else:
        root.mainloop()


if __name__ == '__main__':
    main()
