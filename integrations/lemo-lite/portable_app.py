"""StoryStudio Portable beta: browse, preview and export a real MP4.

Runs as a plain Python script during development or as a PyInstaller onedir
executable on Windows. Uses only stdlib for the UI and renderer for export.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys
import threading
import traceback
import webbrowser

import renderer

APP_DIR = renderer.ROOT
LOG_DIR = APP_DIR / 'logs'
EXPORT_DIR = APP_DIR / 'exports'

def ensure_folders():
    for folder in (LOG_DIR, EXPORT_DIR, APP_DIR / 'temp'):
        folder.mkdir(exist_ok=True, parents=True)
    # Scope Playwright's disposable browser profile and temp files to this
    # portable folder rather than filling the user's system drive.
    if renderer.FROZEN:
        os.environ['TEMP'] = str(APP_DIR / 'temp')
        os.environ['TMP'] = str(APP_DIR / 'temp')
        os.environ['TMPDIR'] = str(APP_DIR / 'temp')

def diagnostics():
    problems = []
    try:
        ff = renderer.find_ffmpeg()
        if not ff:
            problems.append('FFmpeg is missing (bin/ffmpeg.exe).')
    except Exception as e:
        problems.append(str(e))
    try:
        renderer.find_chrome()
    except Exception as e:
        problems.append(str(e))
    return problems

def smoke_test(args):
    ensure_folders()
    log = LOG_DIR / 'portable-self-test.log'
    output = Path(args.output).resolve() if args.output else EXPORT_DIR / 'portable-self-test.mp4'
    render_args = argparse.Namespace(
        output=str(output), duration=args.duration,
        fps=args.fps, width=args.width, height=args.height,
        audio=None, overwrite=True)
    try:
        renderer.export(render_args)
        log.write_text('PASS: ' + str(output) + '\n', encoding='utf-8')
        return 0
    except Exception:
        log.write_text('FAIL\n' + traceback.format_exc(), encoding='utf-8')
        return 1

def start_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    ensure_folders()
    DARK = '#101b30'
    MID = '#1b2e46'
    WHITE = '#f3f8fc'
    MUTED = '#b9cbdf'
    ACCENT = '#51d1bc'
    BUTTON = '#2b8e8a'
    OUTLINE = '#41566a'

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title('StoryStudio 2.0 — Portable Beta')
            self.geometry('840x590')
            self.minsize(720, 540)
            self.configure(bg=DARK)
            self.preview_server = None
            self.busy = False
            self.option = tk.StringVar(value='720p • 24 fps')
            self.status = tk.StringVar(value='Checking your animation tools…')
            self.make_ui()
            self.after(300, self.check_tools)
            self.protocol('WM_DELETE_WINDOW', self.exit_app)

        def label(self, parent, txt, size=12, color=WHITE, bold=False, **kwargs):
            font = ('Segoe UI', size, 'bold' if bold else 'normal')
            return tk.Label(parent, text=txt, font=font, fg=color, bg=kwargs.get('bg', DARK),
                            anchor=kwargs.get('anchor', 'w'), justify='left', wraplength=kwargs.get('wraplength', 700))

        def button(self, parent, text, callback, primary=False):
            btn = tk.Button(parent, text=text, command=callback, cursor='hand2',
                            bg=BUTTON if primary else MID,
                            fg='white', activebackground=ACCENT,
                            activeforeground=DARK, relief='flat', bd=0,
                            font=('Segoe UI', 11, 'bold'), padx=20, pady=13)
            return btn

        def make_ui(self):
            header = tk.Frame(self, bg=DARK)
            header.pack(fill='x', padx=36, pady=(30, 19))
            self.label(header, 'STORYSTUDIO', 13, ACCENT, True).pack(anchor='w')
            self.label(header, 'Make your story move.', 26, WHITE, True).pack(anchor='w', pady=(5, 5))
            self.label(header, 'Create, preview and export your first cartoon. No paid credits or Docker.',
                       11, MUTED).pack(anchor='w')

            top = tk.Frame(self, bg=DARK)
            top.pack(fill='both', expand=True, padx=36)
            left = tk.Frame(top, bg=MID, highlightthickness=1, highlightbackground=OUTLINE)
            right = tk.Frame(top, bg=MID, highlightthickness=1, highlightbackground=OUTLINE)
            left.pack(side='left', fill='both', expand=True, padx=(0, 10))
            right.pack(side='left', fill='both', expand=True, padx=(10, 0))

            for card, count, heading, desc in [
                (left,'01','Preview the cartoon','Watch Pip the fox meet a friendly little star.\nUse the play and timeline controls in your browser.'),
                (right,'02','Export a real MP4','Render the story with original sound effects.\nSave the file wherever you choose.')
            ]:
                self.label(card, count, 12, ACCENT, True, bg=MID).pack(anchor='w', padx=22, pady=(23, 6))
                self.label(card, heading, 17, WHITE, True, bg=MID).pack(anchor='w', padx=22, pady=(0, 9))
                self.label(card, desc, 11, MUTED, bg=MID, wraplength=310).pack(anchor='w', padx=22)

            self.preview_button = self.button(left, '▶  Open Live Preview', self.open_preview, True)
            self.preview_button.pack(anchor='w', padx=22, pady=(26, 20))
            self.label(right, 'RENDER QUALITY', 9, MUTED, True, bg=MID).pack(anchor='w', padx=22, pady=(16, 4))
            quality = ttk.Combobox(right, textvariable=self.option, state='readonly',
                                   values=['720p • 24 fps','360p • 12 fps'], width=20, font=('Segoe UI',10))
            quality.pack(anchor='w', padx=22, pady=(0, 14))
            self.export_button = self.button(right, '⬇  Export MP4', self.export, True)
            self.export_button.pack(anchor='w', padx=22, pady=(0, 20))

            foot = tk.Frame(self, bg=DARK)
            foot.pack(fill='x', padx=36, pady=(20, 28))
            self.label(foot, 'RENDER STATUS', 9, MUTED, True).pack(anchor='w')
            self.status_view = self.label(foot, '', 11, WHITE, wraplength=760)
            self.status_view.pack(anchor='w', pady=(5, 13))
            self.status.trace_add('write', lambda *_: self.status_view.config(text=self.status.get()))
            actions = tk.Frame(foot, bg=DARK)
            actions.pack(anchor='w')
            self.button(actions, 'Open Export Folder', self.open_exports).pack(side='left', padx=(0, 10))
            self.button(actions, 'Check Tools', self.check_tools).pack(side='left')

        def check_tools(self):
            if self.busy:
                return
            issues = diagnostics()
            if issues:
                self.status.set('Setup needed: ' + ' '.join(issues))
                self.export_button.config(state='disabled')
            else:
                self.status.set('Ready: browser and FFmpeg found. Choose Preview or Export MP4.')
                self.export_button.config(state='normal')

        def open_preview(self):
            try:
                if self.preview_server is None:
                    ctx = renderer.local_server()
                    address = ctx.__enter__()
                    self.preview_server = ctx
                    self.preview_address = address.replace('?capture=1','')
                webbrowser.open(self.preview_address)
                self.status.set('Preview opened in your browser. Return here to export MP4.')
            except Exception as e:
                messagebox.showerror('Preview failed', str(e))

        def export(self):
            if self.busy:
                return
            issues = diagnostics()
            if issues:
                messagebox.showerror('Missing tools','\n'.join(issues))
                return
            high = self.option.get().startswith('720p')
            width, height, fps, duration = (1280,720,24,10) if high else (640,360,12,10)
            suggest = 'pip-and-the-star-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.mp4'
            target = filedialog.asksaveasfilename(
                title='Export your StoryStudio video',
                initialdir=str(EXPORT_DIR), initialfile=suggest,
                defaultextension='.mp4', filetypes=[('MP4 video','*.mp4')])
            if not target:
                return
            self.busy = True
            self.export_button.config(state='disabled')
            self.status.set('Rendering video… this can take some time on a small laptop.')
            def run():
                try:
                    args = argparse.Namespace(output=target,duration=duration,fps=fps,width=width,
                                             height=height,audio=None,overwrite=True)
                    file = renderer.export(args)
                    self.after(0,lambda: self.complete(True,'MP4 verified and saved: '+str(file)))
                except Exception:
                    err = traceback.format_exc()
                    LOG_DIR.mkdir(exist_ok=True, parents=True)
                    (LOG_DIR / 'last-export-error.log').write_text(err, encoding='utf-8')
                    self.after(0,lambda: self.complete(False,'Export failed. Check logs/last-export-error.log'))
            threading.Thread(target=run,daemon=True).start()

        def complete(self,ok,message):
            self.busy=False
            self.status.set(message)
            self.export_button.config(state='normal' if not diagnostics() else 'disabled')
            if ok:
                messagebox.showinfo('Export complete', message)
            else:
                messagebox.showerror('Export failed', message)

        def open_exports(self):
            EXPORT_DIR.mkdir(parents=True,exist_ok=True)
            if os.name=='nt':
                os.startfile(str(EXPORT_DIR))
            else:
                import subprocess
                subprocess.Popen(['xdg-open',str(EXPORT_DIR)])

        def exit_app(self):
            if self.busy:
                from tkinter import messagebox
                if not messagebox.askyesno('Render running','Rendering is still active. Quit and interrupt export?'):
                    return
            if self.preview_server:
                self.preview_server.__exit__(None,None,None)
            self.destroy()

    App().mainloop()


def main():
    p = argparse.ArgumentParser(description='StoryStudio Portable beta')
    p.add_argument('--self-test',action='store_true',help='Render a small MP4 without opening the interface')
    p.add_argument('--output',help='MP4 output path for --self-test')
    p.add_argument('--duration',type=float,default=2)
    p.add_argument('--fps',type=int,default=12)
    p.add_argument('--width',type=int,default=640)
    p.add_argument('--height',type=int,default=360)
    args=p.parse_args()
    if args.self_test:
        return smoke_test(args)
    start_gui()
    return 0

if __name__=='__main__':
    sys.exit(main())
