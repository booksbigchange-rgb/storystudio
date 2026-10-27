"""Portable Windows entrypoint. Source mode reuses the existing D: installation."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
import traceback
import renderer
import cartoon_project as project

APP_DIR=renderer.ROOT


def ensure_folders():
    for name in ('logs','exports','temp','projects','cache'):
        (APP_DIR/name).mkdir(exist_ok=True,parents=True)
    if renderer.FROZEN:
        for key in ('TEMP','TMP','TMPDIR'):os.environ[key]=str(APP_DIR/'temp')


def diagnostics():
    problems=[]
    for operation in (renderer.find_ffmpeg,renderer.find_ffprobe,renderer.find_chrome):
        try:
            if not operation():problems.append('A required tool is missing')
        except Exception as exc:problems.append(str(exc))
    return problems


def main():
    parser=argparse.ArgumentParser(description='StoryStudio 2.0 Portable')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--gui-test',action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--project')
    parser.add_argument('--open', help='Open this saved project in the editor')
    parser.add_argument('--audio')
    parser.add_argument('--duration',type=float,default=2)
    parser.add_argument('--fps',type=int,default=12)
    parser.add_argument('--width',type=int,default=640)
    parser.add_argument('--height',type=int,default=360)
    args=parser.parse_args()
    ensure_folders()
    log=APP_DIR/'logs/portable-self-test.log'
    try:
        if args.gui_test:
            from gui_regression import run
            run(Path(args.output or APP_DIR/'exports/gui-regression'))
        elif args.self_test:
            args.output=args.output or str(APP_DIR/'exports/portable-self-test.mp4')
            args.overwrite=False
            args.document=project.load(args.project) if args.project else project.new_project()
            if args.height>args.width:args.document['format']='Shorts / TikTok 9:16'
            renderer.export(args)
            log.write_text('PASS: '+args.output+'\n',encoding='utf-8')
        else:
            from studio_ui import StudioApp
            app=StudioApp()
            if args.open:
                doc=project.load(args.open)
                app.document=doc;app.project_path=Path(args.open);app.refresh();app.title('StoryStudio 2.0 · '+doc['name'])
            app.mainloop()
        return 0
    except Exception:
        log.write_text(traceback.format_exc(),encoding='utf-8')
        if sys.stderr:traceback.print_exc()
        return 1


if __name__=='__main__':
    sys.exit(main())
