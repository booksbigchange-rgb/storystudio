"""One window for the whole studio: every editor opens as a tab in the same process.

The editors were written for their own top-level windows. ``Host`` is a frame that answers the few
window-manager calls they make (title, geometry, close handler, keyboard shortcuts), so they run unchanged
inside a tab. Keyboard shortcuts only reach the editor in the visible tab.
"""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import runtime
from studio_hub import ROOT, project_kind

LABELS = {'mixed': 'Shared timeline', 'documentary': 'Documentary', 'cartoon': 'Character'}


class Host(ttk.Frame):
    """A tab that behaves like the window an editor expects."""
    def __init__(self, master=None, shell=None, **options):
        super().__init__(master, **options)
        self.shell = shell
        self._close = None
        self._title = ''
        self.app = None

    # --- window-manager calls the editors make -----------------------------------------------------
    def title(self, text=None):
        if text is None:
            return self._title
        self._title = text
        if self.shell:
            self.shell.retitle(self, text)

    def geometry(self, *_):
        return ''

    def minsize(self, *_):
        return None

    def protocol(self, name=None, func=None):
        if name == 'WM_DELETE_WINDOW' and func is not None:
            self._close = func

    def bind(self, sequence=None, func=None, add=None):
        """Shortcuts are bound on the main window but only act while this tab is showing."""
        if func is None or self.shell is None:
            return super().bind(sequence, func, add)

        def guarded(event, host=self, handler=func):
            if host.winfo_exists() and host.shell.current() is host:
                return handler(event)
        return self.shell.root.bind(sequence, guarded, add='+')

    def open_editor(self, kind, path=None):
        """Lets an editor open another project as a tab (shared timeline: Edit source)."""
        return self.shell.open(kind, path)

    def close_request(self):
        if self._close:
            self._close()            # the editor asks about unsaved work, then destroys itself
        else:
            self.destroy()

    def destroy(self):
        shell = self.shell
        self.shell = None
        if shell:
            shell.forget(self)
        super().destroy()


class StudioShell:
    def __init__(self, root):
        self.root = root
        self.hosts = []
        root.title('StoryStudio')
        root.geometry('1360x860')
        root.minsize(1100, 720)
        side = ttk.Frame(root, padding=(14, 14, 8, 14), width=220)
        side.pack(side='left', fill='y')
        side.pack_propagate(False)
        ttk.Label(side, text='STORYSTUDIO', font=('Segoe UI', 16, 'bold')).pack(anchor='w', pady=(0, 12))
        self.buttons = {}
        for label, action in [('Shared timeline', lambda: self.open('mixed')), ('Documentary', lambda: self.open('documentary')),
                              ('Character', lambda: self.open('cartoon')), ('Documentary templates…', self.templates),
                              ('Open project…', self.open_project), ('Close tab', self.close_tab)]:
            self.buttons[label] = ttk.Button(side, text=label, command=action)
            self.buttons[label].pack(fill='x', pady=3)
        ttk.Label(side, text='Each workspace opens as a tab. Close a tab to finish with it; unsaved work is asked about first.',
                  wraplength=190, foreground='#61766f').pack(anchor='w', pady=12)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(side='left', fill='both', expand=True, padx=(0, 8), pady=8)
        home = ttk.Frame(self.notebook, padding=24)
        ttk.Label(home, text='Welcome', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(home, wraplength=760, text='Choose a workspace on the left. Projects open in tabs here, so you can keep a shared timeline, '
                  'its documentary sections and its characters open side by side. Shortcuts such as Ctrl+S and Ctrl+Z act on the tab you are looking at.').pack(anchor='w', pady=10)
        self.notebook.add(home, text='Home')
        self.home = home
        root.protocol('WM_DELETE_WINDOW', self.close_all)
        self.status = tk.StringVar()
        ttk.Label(side, textvariable=self.status, wraplength=190, foreground='#a02535').pack(side='bottom', anchor='w')

    # --- tabs ------------------------------------------------------------------------------------------
    def current(self):
        name = self.notebook.select()
        return next((h for h in self.hosts if str(h) == name), None)

    def retitle(self, host, text):
        if str(host) in self.notebook.tabs():
            short = text.replace('StoryStudio 2.0 · ', '').replace('StoryStudio · ', '').replace('StoryStudio — ', '')
            self.notebook.tab(host, text=short[:40])

    def forget(self, host):
        if host in self.hosts:
            self.hosts.remove(host)
        if str(host) in self.notebook.tabs():
            self.notebook.forget(host)

    def open(self, kind, path=None):
        """Open a workspace (optionally a saved project) in a new tab; returns its host."""
        if path:
            found = project_kind(path)
            if found != kind:
                raise ValueError('That project belongs to the other editor')
        if kind == 'cartoon':
            if not runtime.FROZEN:
                sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
            from studio_ui import StudioCore
            import cartoon_project

            class CharacterTab(StudioCore, Host):
                embedded = True
            host = CharacterTab(auto_preview=True, master=self.notebook, shell=self)
            host.app = host
            self.notebook.add(host, text=LABELS[kind])
            self.hosts.append(host)
            if path:
                host.document = cartoon_project.load(path)
                host.project_path = Path(path)
                host.refresh()
                host.title('StoryStudio · '+host.document['name'])
        else:
            host = Host(self.notebook, shell=self)
            self.notebook.add(host, text=LABELS[kind])
            self.hosts.append(host)
            try:
                if kind == 'mixed':
                    from mixed_editor import MixedEditor
                    host.app = MixedEditor(host, path)
                else:
                    from editor_app import EditorApp
                    from project import read_project
                    if path:
                        read_project(path)
                    host.app = EditorApp(host)
                    if path:
                        host.app.load_from(path)
            except Exception:
                host.destroy()
                raise
        self.notebook.select(host)
        return host

    def open_project(self):
        path = filedialog.askopenfilename(parent=self.root, initialdir=ROOT/'projects', filetypes=[('StoryStudio projects', '*.json')])
        if path:
            try:
                self.open(project_kind(path), path)
            except (ValueError, OSError) as exc:
                messagebox.showerror('Cannot open project', str(exc), parent=self.root)

    def templates(self):
        from template_editor import TemplateEditor
        return TemplateEditor(self.root, ROOT/'projects', lambda kind, path=None: self.open(kind, path))

    def close_tab(self):
        host = self.current()
        if host is None:
            self.status.set('The Home tab stays open.')
            return
        host.close_request()

    def close_all(self):
        """Ask every tab to close (each asks about its own unsaved work); quit when all are gone."""
        for host in list(self.hosts):
            host.close_request()
        self._finish_close(0)

    def _finish_close(self, waited):
        self.hosts = [h for h in self.hosts if h.winfo_exists()]
        if not self.hosts:
            self.root.destroy()
            return
        waiting = [h for h in self.hosts if getattr(h.app, 'closing', False)]
        if waiting and len(waiting) == len(self.hosts) and waited < 300:
            self.root.after(100, lambda: self._finish_close(waited+1))    # character tabs stop their workers first
        else:
            self.status.set('Some tabs are still open (unsaved work kept or an export is running).')


def main(smoke=False):
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    shell = StudioShell(root)
    if smoke:
        root.update()
        root.destroy()
    else:
        root.mainloop()
    return shell
