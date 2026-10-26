"""One isolated legacy renderer per process; snapshots contain resolved asset paths."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]  # source checkouts only; frozen builds import bundled modules


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['snapshot', 'render', 'verify'])
    parser.add_argument('engine', choices=['cartoon', 'documentary'])
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    if args.engine == 'cartoon' or args.action == 'verify':
        sys.path.insert(0, str(ROOT/'integrations/lemo-lite'))
        import cartoon_project as project
        import renderer
        if args.action == 'verify':
            expected = json.loads(Path(args.source).read_text(encoding='utf-8'))
            renderer.verify(Path(args.output), expected['duration'], expected['width'], expected['height'], 24)
            return
        doc = project.load(args.source)
        frames = round(project.total_duration(doc)*24)
        duration = frames/24
        if args.action == 'render':
            width, height = project.FORMATS[doc['format']]
            renderer.export(argparse.Namespace(document=doc, width=width, height=height, fps=24,
                duration=project.total_duration(doc), audio=None, output=args.output, overwrite=False))
    else:
        import project
        doc = project.read_project(args.source)
        frames = sum(round(s['duration']*24) for s in doc['scenes'])
        duration = frames/24
        if args.action == 'render':
            from desktop_app import render_scenes
            render_scenes(doc['scenes'], args.output, audio=doc['audio'], music=doc['music'], output_format=doc['format'])
    if args.action == 'snapshot':
        if duration <= 0:
            raise ValueError('A section must contain scenes')
        Path(args.output).write_text(json.dumps(doc, allow_nan=False), encoding='utf-8')
        print(json.dumps({'duration': duration, 'frames': frames}))


if __name__ == '__main__':
    main()
