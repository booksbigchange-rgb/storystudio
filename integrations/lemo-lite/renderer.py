"""Deterministic Canvas2D renderer with bounded memory and atomic verified output."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from fractions import Fraction
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import uuid
import wave

import project

BASE = Path(__file__).resolve().parent
FROZEN = bool(getattr(sys, 'frozen', False))
ROOT = Path(sys.executable).resolve().parent if FROZEN else BASE.parents[1]
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
BROWSER_LOCK = threading.Lock()


class Cancelled(Exception):
    pass


def report(message):
    if sys.stdout is not None:
        print(message, flush=True)


def find_ffmpeg():
    override = os.getenv('STORYSTUDIO_FFMPEG')
    if override:
        if not Path(override).is_file():
            raise RuntimeError('STORYSTUDIO_FFMPEG not found: ' + override)
        return override
    return next((str(p) for p in [ROOT/'bin/ffmpeg.exe', ROOT/'tools/ffmpeg/ffmpeg.exe',
                ROOT/'tools/ffmpeg/bin/ffmpeg.exe'] if p.is_file()), shutil.which('ffmpeg'))


def find_ffprobe():
    ff = find_ffmpeg()
    sibling = Path(ff).with_name('ffprobe.exe' if os.name == 'nt' else 'ffprobe') if ff else None
    found = str(sibling) if sibling and sibling.is_file() else shutil.which('ffprobe')
    if not found:
        raise RuntimeError('Cannot verify export: FFprobe missing')
    return found


def find_chrome():
    override = os.getenv('STORYSTUDIO_CHROME')
    if override:
        if not Path(override).is_file():
            raise RuntimeError('STORYSTUDIO_CHROME does not exist: ' + override)
        return override
    for base in [os.getenv('PROGRAMFILES', r'C:\Program Files'),
                 os.getenv('PROGRAMFILES(X86)', r'C:\Program Files (x86)'),
                 os.getenv('LOCALAPPDATA', '')]:
        for sub in ['Microsoft/Edge/Application/msedge.exe', 'Google/Chrome/Application/chrome.exe']:
            path = Path(base)/sub
            if path.is_file():
                return str(path)
    for cmd in ('chromium', 'google-chrome', 'microsoft-edge'):
        if shutil.which(cmd):
            return shutil.which(cmd)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            if Path(pw.chromium.executable_path).is_file():
                return pw.chromium.executable_path
    except ImportError:
        pass
    raise RuntimeError('Install Edge or Chrome, or set STORYSTUDIO_CHROME to its executable.')


@contextmanager
def local_server(document=None):
    # Serve only renderer assets, never arbitrary project files or directory listings.
    document = project.validate(document or project.new_project())
    payload = json.dumps(document, ensure_ascii=False).encode('utf-8')
    class Quiet(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(BASE), **kwargs)
        def log_message(self, *args):
            pass
        def do_GET(self):
            from urllib.parse import urlsplit
            path = urlsplit(self.path).path
            if path == '/project.json':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(payload)
            elif path in ('/scene/index.html', '/scene/scene.js', '/scene/characters.js', '/vendor/lemo-lib.js'):
                super().do_GET()
            else:
                self.send_error(404)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/scene/index.html?capture=1'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@contextmanager
def scene_page(document, width, height):
    from playwright.sync_api import sync_playwright
    with BROWSER_LOCK, local_server(document) as url, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=find_chrome(), headless=True,
                                    args=['--disable-gpu'])
        try:
            page = browser.new_page(viewport=dict(width=width, height=height), device_scale_factor=1)
            errors = []
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.goto(url, wait_until='load')
            page.wait_for_function('window.READY === true', timeout=15000)
            yield page, errors
        finally:
            browser.close()


def preview_frame(document, seconds=0):
    width, height, _ = project.dimensions(document)
    scale = min(640/width, 400/height)
    with scene_page(document, round(width*scale), round(height*scale)) as (page, errors):
        page.evaluate('(t) => window.render(t)', seconds)
        if errors:
            raise RuntimeError(errors[-1])
        return page.screenshot(type='png')


def chime_wav(path, duration):
    rate = 24000
    notes = ((.15, 523.25), (3.1, 659.25), (5.25, 784.0), (7.1, 1046.5))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for start in range(0, math.ceil(duration*rate), 2048):
            samples = []
            for i in range(start, min(start+2048, math.ceil(duration*rate))):
                t, signal = i/rate, 0.0
                for at, freq in notes:
                    age = t-at
                    if 0 <= age < .55:
                        signal += .13*math.sin(2*math.pi*freq*age)*(1-age/.55)**2
                samples.append(struct.pack('<h', int(max(-1, min(1, signal))*32767)))
            w.writeframesraw(b''.join(samples))


def validate_args(args, document):
    for value in (args.width, args.height, args.fps):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError('Dimensions and FPS must be integers')
    if (args.width % 2 or args.height % 2 or min(args.width, args.height) < 16
            or max(args.width, args.height) > 1920 or args.width*args.height > 1920*1080):
        raise ValueError('Use even dimensions from 16 to 1920, at most Full HD')
    if not math.isfinite(args.duration) or not 0 < args.duration <= project.total_duration(document):
        raise ValueError('Duration must be positive and no longer than the project')
    if not 1 <= args.fps <= 60 or round(args.duration*args.fps) < 1:
        raise ValueError('Use 1–60 FPS and at least one frame')


def export(args, progress=None, cancel=None):
    document = project.validate(getattr(args, 'document', None) or
                                (project.load(args.project) if getattr(args, 'project', None) else project.new_project()))
    validate_args(args, document)
    cancelled = cancel or threading.Event()
    def check_cancel():
        if cancelled.is_set():
            raise Cancelled('Export cancelled. Existing files were preserved.')
    check_cancel()
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError('FFmpeg missing. Load launchers/environment.ps1 or set STORYSTUDIO_FFMPEG.')
    find_ffprobe()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f'{output} already exists. Choose another filename.')
    audio_path = getattr(args, 'audio', None) or document['audio']
    if audio_path and Path(audio_path).resolve() == output:
        raise ValueError('Output cannot replace source audio')
    # Same-directory staging makes the final replace atomic, even on another drive.
    pending = output.with_name('.'+output.stem+'-'+uuid.uuid4().hex+'.partial.mp4')
    temp_root = Path(os.getenv('STORYSTUDIO_TEMP') or ROOT/'temp')
    temp_root.mkdir(parents=True, exist_ok=True)
    frame_count = round(args.duration*args.fps)
    actual_duration = frame_count/args.fps
    try:
        with tempfile.TemporaryDirectory(prefix='render-', dir=temp_root) as td:
            audio = Path(audio_path).resolve() if audio_path else Path(td)/'chimes.wav'
            if audio_path and not audio.is_file():
                raise FileNotFoundError(f'Audio not found: {audio}')
            if not audio_path:
                chime_wav(audio, actual_duration)
            with scene_page(document, args.width, args.height) as (page, errors):
                ffargs = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                          '-f', 'image2pipe', '-framerate', str(args.fps), '-vcodec', 'mjpeg', '-i', 'pipe:0',
                          '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0', '-af', 'apad',
                          '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '22',
                          '-vf', 'scale=in_range=pc:out_range=tv,format=yuv420p',
                          '-pix_fmt', 'yuv420p', '-color_range', 'tv',
                          '-c:a', 'aac', '-b:a', '128k', '-t', str(actual_duration),
                          '-movflags', '+faststart', str(pending)]
                # File-backed stderr avoids pipe deadlocks during a long encode.
                with open(Path(td)/'ffmpeg.log', 'w+b') as errlog:
                    proc = subprocess.Popen(ffargs, stdin=subprocess.PIPE, stderr=errlog,
                                            stdout=subprocess.DEVNULL, creationflags=NO_WINDOW)
                    try:
                        for i in range(frame_count):
                            check_cancel()
                            page.evaluate('(t) => window.render(t)', i/args.fps)
                            if errors:
                                raise RuntimeError('Scene JavaScript error: '+errors[-1])
                            proc.stdin.write(page.screenshot(type='jpeg', quality=90, animations='disabled'))
                            if progress:
                                progress((i+1)/frame_count*.9, f'Rendering frame {i+1} / {frame_count}')
                        proc.stdin.close()
                        proc.wait(timeout=90)
                        errlog.seek(0)
                        if proc.returncode:
                            raise RuntimeError('FFmpeg failed: '+errlog.read().decode(errors='replace')[-2000:])
                    finally:
                        if proc.poll() is None:
                            proc.kill()
                        if not proc.stdin.closed:
                            try:
                                proc.stdin.close()
                            except BrokenPipeError:
                                pass
                        proc.wait(timeout=10)
        check_cancel()
        if progress:
            progress(.95, 'Checking video, audio and full MP4 decode…')
        verify(pending, actual_duration, args.width, args.height, args.fps)
        check_cancel()
        if args.overwrite:
            os.replace(pending, output)
        else:
            # Atomic no-clobber publication: a concurrent writer wins safely.
            os.link(pending, output)
            pending.unlink()
        if progress:
            progress(1, 'Verified export saved')
        report('VERIFIED: '+str(output))
        return output
    finally:
        pending.unlink(missing_ok=True)


def verify(file, duration, width, height, fps):
    result = subprocess.run([find_ffprobe(), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(file)],
                            capture_output=True, text=True, check=True, timeout=30, creationflags=NO_WINDOW)
    details = json.loads(result.stdout)
    video = next((s for s in details['streams'] if s['codec_type'] == 'video'), None)
    audio = next((s for s in details['streams'] if s['codec_type'] == 'audio'), None)
    checks = [(video is not None and audio is not None, 'Video and audio required')]
    if video and audio:
        checks += [(video['codec_name'] == 'h264' and audio['codec_name'] == 'aac', 'Expected H.264/AAC'),
                   (video['pix_fmt'] == 'yuv420p', 'Expected compatible yuv420p'),
                   ((video['width'], video['height']) == (width, height), 'Wrong dimensions'),
                   (abs(float(details['format']['duration'])-duration) <= .12, 'Wrong duration'),
                   (abs(eval_fraction(video['avg_frame_rate'])-fps) < .01, 'Wrong frame rate'),
                   (int(video.get('nb_frames', -1)) == round(duration*fps), 'Wrong frame count'),
                   (abs(float(audio.get('duration', 0))-duration) <= .12, 'Audio does not span the story')]
    for ok, message in checks:
        if not ok:
            raise RuntimeError('Verification failed: '+message)
    check = subprocess.run([find_ffmpeg(), '-v', 'error', '-xerror', '-i', str(file), '-f', 'null', '-'],
                           capture_output=True, text=True, timeout=180, creationflags=NO_WINDOW)
    if check.returncode or check.stderr.strip():
        raise RuntimeError('Decode failed: '+check.stderr[-900:])
    return details


def eval_fraction(value):
    return float(Fraction(value))


def main():
    p = argparse.ArgumentParser(description='Render an offline StoryStudio cartoon')
    p.add_argument('--project')
    p.add_argument('--output', default=str(ROOT/'exports/lemo-pip-test.mp4'))
    p.add_argument('--duration', type=float, default=10)
    p.add_argument('--fps', type=int, default=24)
    p.add_argument('--width', type=int, default=1280)
    p.add_argument('--height', type=int, default=720)
    p.add_argument('--audio')
    p.add_argument('--overwrite', action='store_true')
    try:
        export(p.parse_args())
    except Exception as exc:
        p.exit(1, 'EXPORT FAILED: '+str(exc)+'\n')


if __name__ == '__main__':
    main()
