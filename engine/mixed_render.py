"""Render immutable source snapshots, normalize sections and publish verified MP4."""
import json
import os
from pathlib import Path
import shutil
import sys
import uuid
from mixed_project import validate, FORMATS, MAX_SECONDS
from mixed_durations import estimated_bytes
from studio_hub import project_kind
from mixed_titles import validate_titles, card
from mixed_control import MixedControl
import mixed_audio
import runtime

ROOT = runtime.app_root(__file__)
WORKER = Path(__file__).with_name('mixed_worker.py')


def tool(name):
    """Bundled Windows FFmpeg tools first; PATH only as a development fallback."""
    for folder in ('tools/ffmpeg', 'bin'):
        bundled = ROOT/folder/(name+'.exe')
        if bundled.is_file():
            return str(bundled)
    return shutil.which(name) or str(ROOT/'tools/ffmpeg'/(name+'.exe'))


def worker(kind):
    """Command prefix for one export worker process ('documentary' or 'cartoon')."""
    if runtime.FROZEN:
        return [str(runtime.helper(kind))]
    return [sys.executable, str(WORKER)]


MEDIA = ('*.mp4', '*.mov', '*.png')


def clean(work):
    """Drop bulky intermediates (gigabytes for long stories); logs, snapshots and results stay."""
    for pattern in MEDIA:
        for path in Path(work).glob(pattern):
            try:
                path.unlink()
            except OSError:
                pass  # Still locked by a stopping process; safe to delete later.
    for path in Path(work).glob('.*.partial.mp4'):
        try:
            path.unlink()
        except OSError:
            pass


def export(doc, output, progress=lambda _: None, control=None, keep_intermediates=None):
    control = control or MixedControl()
    control.check()
    if keep_intermediates is None:
        keep_intermediates = os.environ.get('STORYSTUDIO_KEEP_INTERMEDIATES') == '1'
    run = control.run
    doc = validate(doc)
    if not doc['sections']:
        raise ValueError('Add at least one section')
    output = Path(output).resolve()
    if output.suffix.lower() != '.mp4':
        raise ValueError('Choose an MP4 output')
    if output.exists():
        raise FileExistsError('Choose a new export name; existing files are protected')
    output.parent.mkdir(parents=True, exist_ok=True)
    work = ROOT/'exports'/('mixed-run-'+uuid.uuid4().hex)
    work.mkdir(parents=True)
    try:
        log = work/'render.log'
        ffmpeg = tool('ffmpeg')
        probe = tool('ffprobe')
        width, height = FORMATS[doc['format']]
        sections = []
        total_frames = 0
        # Snapshot every source before any rendering so editing during an export
        # cannot change scene settings halfway through this render.
        for i, section in enumerate(doc['sections']):
            if project_kind(section['project']) != section['engine']:
                raise ValueError('Source project no longer matches its section editor')
            snapshot = work/f'source-{i}.json'
            info = json.loads(run([*worker(section['engine']), 'snapshot', section['engine'], section['project'], str(snapshot)], log))
            sections.append((section, snapshot, info['duration']))
            total_frames += info['frames']
        duration = total_frames/24
        if duration > MAX_SECONDS:
            raise ValueError(f'Mixed timelines support up to {MAX_SECONDS//60} minutes')
        need = estimated_bytes(duration)
        for folder in {work, output.parent}:
            free = shutil.disk_usage(folder).free
            if free < need:
                raise OSError(f'Not enough free disk space on {folder.anchor or folder}: about {need//10**9+1} GB needed, {free//10**9} GB free')
        titles = validate_titles(doc.get('titles', []), duration)
        mix = doc.get('audio') if mixed_audio.active(doc.get('audio')) else None
        if mix:
            # Media problems must stop the export before any section is rendered.
            mixed_audio.check_media(mix, duration, lambda command: run(command, log), ffmpeg, probe)
        cards = []
        for i, item in enumerate(titles):
            image, xy = card(item, width, height)
            image.save(work/f'title-{i}.png')
            cards.append(xy)
        (work/'expected.json').write_text(json.dumps(dict(duration=duration, width=width, height=height)), encoding='utf-8')
        for i, (section, snapshot, seconds) in enumerate(sections):
            progress(f'Rendering section {i+1}/{len(sections)}: {section["name"]}')
            raw = work/f'raw-{i}.mp4'
            run([*worker(section['engine']), 'render', section['engine'], str(snapshot), str(raw)], log)
            details = json.loads(run([probe, '-v', 'error', '-show_streams', '-of', 'json', str(raw)], log))
            has_audio = any(s['codec_type'] == 'audio' for s in details['streams'])
            args = [ffmpeg, '-v', 'error', '-nostdin', '-n', '-i', str(raw)]
            if not has_audio:
                args += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
            args += ['-map', '0:v:0', '-map', '0:a:0' if has_audio else '1:a:0',
                     '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease:out_color_matrix=bt709:out_range=tv,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,format=yuv420p',
                     '-af', 'aresample=48000,apad', '-ac', '2', '-ar', '48000',
                     '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-threads', '2',
                     '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
                     '-c:a', 'pcm_s16le', '-video_track_timescale', '24000', '-t', str(seconds), str(work/f'section-{i}.mov')]
            run(args, log)
        concat = work/'sections.txt'
        concat.write_text(''.join(f"file 'section-{i}.mov'\n" for i in range(len(sections))), encoding='utf-8')
        pending = output.with_name('.'+output.stem+'.'+uuid.uuid4().hex+'.partial.mp4')
        try:
            progress('Joining sections and checking the complete video…')
            joined = work/'joined.mp4' if titles else pending
            join = [ffmpeg, '-v', 'error', '-nostdin', '-n', '-f', 'concat', '-safe', '1', '-i', str(concat)]
            if mix:
                progress('Mixing narration, music and sound effects…')
                inputs, graph, label = mixed_audio.build(mix, duration)
                join += inputs + ['-filter_complex', graph, '-map', '0:v:0', '-map', label]
            join += ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(duration), '-movflags', '+faststart', str(joined)]
            run(join, log)
            if titles:
                progress('Adding timed titles and captions…')
                args = [ffmpeg, '-v', 'error', '-nostdin', '-n', '-i', str(joined)]
                filters = []
                previous = '0:v'
                for i, (item, (x, y)) in enumerate(zip(titles, cards)):
                    args += ['-i', str(work/f'title-{i}.png')]
                    start, end = round(item['start']*24), round(item['end']*24)
                    filters.append(f'[{previous}][{i+1}:v]overlay={x}:{y}:enable=\'gte(n,{start})*lt(n,{end})\'[v{i}]')
                    previous = f'v{i}'
                args += ['-filter_complex_threads', '1', '-filter_complex', ';'.join(filters),
                         '-map', f'[{previous}]', '-map', '0:a:0', '-c:v', 'libx264', '-preset', 'veryfast',
                         '-crf', '20', '-threads', '2', '-pix_fmt', 'yuv420p', '-c:a', 'copy',
                         '-movflags', '+faststart', str(pending)]
                run(args, log)
            run([*worker('cartoon'), 'verify', 'cartoon', str(work/'expected.json'), str(pending)], log)
            # Atomic no-overwrite publication on the output volume (Windows NTFS).
            control.publish(pending, output)
            (work/'result.json').write_text(json.dumps(dict(status='passed', output=str(output), duration=duration,
                width=width, height=height, sections=len(sections)), indent=2), encoding='utf-8')
        finally:
            pending.unlink(missing_ok=True)
        progress(f'Export verified: {output}')
        return output
    finally:
        if not keep_intermediates:
            clean(work)
