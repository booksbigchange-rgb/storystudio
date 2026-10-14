"""Small native-Windows-friendly deterministic Canvas-to-MP4 renderer.

Uses Lemo OpusCar's render(t) convention and licensed motion helpers,
without its Unix setup script, 3D dependencies or cloud models.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from contextlib import contextmanager

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]  # StoryStudio root


def find_ffmpeg():
    override = os.getenv('STORYSTUDIO_FFMPEG')
    paths = ([Path(override)] if override else []) + [
        ROOT / 'tools' / 'ffmpeg' / 'ffmpeg.exe',
        ROOT / 'tools' / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
    ]
    return next((str(p) for p in paths if p.is_file()), shutil.which('ffmpeg'))


def find_chrome():
    override = os.getenv('STORYSTUDIO_CHROME')
    if override:
        if not Path(override).is_file():
            raise RuntimeError('STORYSTUDIO_CHROME does not exist: ' + override)
        return override
    paths = [
        Path(os.getenv('PROGRAMFILES', r'C:\Program Files')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
        Path(os.getenv('PROGRAMFILES(X86)', r'C:\Program Files (x86)')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
        Path(os.getenv('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
        Path(os.getenv('PROGRAMFILES', r'C:\Program Files')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
        Path(os.getenv('PROGRAMFILES(X86)', r'C:\Program Files (x86)')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
    ]
    for p in paths:
        if p.is_file():
            return str(p)
    for cmd in ('chromium', 'google-chrome', 'microsoft-edge'):
        result = shutil.which(cmd)
        if result:
            return result
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            bundled = pw.chromium.executable_path
            if Path(bundled).is_file():
                return bundled
    except ImportError:
        pass
    raise RuntimeError('Chrome, Edge or Chromium not found. Set STORYSTUDIO_CHROME to the full executable path.')


@contextmanager
def local_server():
    class Quiet(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(BASE), **kw)
        def log_message(self, fmt, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port) + '/scene/index.html?capture=1'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def chime_wav(path, duration):
    """Create low-volume original cue tones, no third-party audio or model."""
    rate = 24000
    notes = ((0.65, 523.25), (3.1, 659.25), (5.25, 784.0), (7.1, 1046.5))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        block = 2048
        for start in range(0, math.ceil(duration * rate), block):
            frames = []
            for i in range(start, min(start + block, math.ceil(duration * rate))):
                t = i / rate
                signal = 0.0
                for at, freq in notes:
                    age = t - at
                    if 0 <= age < .55:
                        signal += .13 * math.sin(2 * math.pi * freq * age) * (1 - age / .55) ** 2
                frames.append(struct.pack('<h', int(max(-1, min(1, signal)) * 32767)))
            w.writeframesraw(b''.join(frames))


def export(args):
    if args.width % 2 or args.height % 2 or min(args.width, args.height) < 16:
        raise ValueError('Width and height must be even and at least 16 pixels (H.264 requirement)')
    if not (0 < args.duration <= 600 and 1 <= args.fps <= 60):
        raise ValueError('Choose duration 0–600 seconds and fps 1–60')
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError('FFmpeg not found; load launchers/environment.ps1 or set STORYSTUDIO_FFMPEG')
    chrome = find_chrome()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError('Missing free dependency: install playwright in the existing D: StoryStudio Python environment') from e
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_file() and not args.overwrite:
        raise FileExistsError(str(output) + ' already exists. Choose another path or use --overwrite.')
    with tempfile.TemporaryDirectory(prefix='story-studio-', dir=os.getenv('STORYSTUDIO_TEMP') or None) as td:
        audio = Path(args.audio).resolve() if args.audio else Path(td) / 'chimes.wav'
        if args.audio and not audio.is_file():
            raise FileNotFoundError(audio)
        if not args.audio:
            chime_wav(audio, args.duration)
        with local_server() as url, sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=chrome, headless=True, args=['--disable-gpu'])
            page = browser.new_page(viewport={'width': args.width, 'height': args.height}, device_scale_factor=1)
            page_errors = []
            page.on('pageerror', lambda e: page_errors.append(str(e)))
            page.goto(url, wait_until='load')
            page.wait_for_function('window.READY === true', timeout=15000)
            duration = float(page.evaluate('window.DUR'))
            if args.duration > duration:
                raise ValueError('Requested %ss exceeds scene duration %ss' % (args.duration, duration))
            ffargs = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y' if args.overwrite else '-n',
                      '-f', 'image2pipe', '-framerate', str(args.fps), '-vcodec', 'mjpeg', '-i', 'pipe:0',
                      '-i', str(audio), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                      '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-t', str(args.duration),
                      '-movflags', '+faststart', str(output)]
            proc = subprocess.Popen(ffargs, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for i in range(round(args.duration * args.fps)):
                    if page_errors:
                        raise RuntimeError('Scene JavaScript error: ' + page_errors[-1])
                    page.evaluate('(t) => window.render(t)', i / args.fps)
                    image = page.screenshot(type='jpeg', quality=84, animations='disabled')
                    proc.stdin.write(image)
                    if i % args.fps == 0:
                        print('Rendering %d/%gs' % (i / args.fps, args.duration), flush=True)
            except Exception:
                proc.kill()
                raise
            finally:
                proc.stdin.close()
                browser.close()
            msg = proc.stderr.read().decode(errors='replace')
            ret = proc.wait()
            if ret:
                output.unlink(missing_ok=True)
                raise RuntimeError('FFmpeg failed (code %s): %s' % (ret, msg[-2000:]))
    verify(output, args.duration, args.width, args.height, args.fps)
    print('VERIFIED:', output)
    return output


def verify(file, duration, width, height, fps):
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        ff = find_ffmpeg()
        ffprobe = str(Path(ff).with_name('ffprobe.exe')) if ff and Path(ff).with_name('ffprobe.exe').is_file() else None
    if not ffprobe:
        raise RuntimeError('Cannot verify export: ffprobe missing')
    result = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(file)],
                            capture_output=True, text=True, check=True)
    details = json.loads(result.stdout)
    streams = details['streams']
    video = next((x for x in streams if x['codec_type']=='video'), None)
    audio = next((x for x in streams if x['codec_type']=='audio'), None)
    assert video and audio, 'Video and audio streams required'
    assert (video['width'], video['height']) == (width, height), 'Wrong dimensions'
    assert abs(float(details['format']['duration'])-duration) < .2, 'Wrong duration'
    assert abs(eval_fraction(video.get('avg_frame_rate', '0/1'))-fps) < .2, 'Wrong frame rate'
    check = subprocess.run([find_ffmpeg(), '-v', 'error', '-i', str(file), '-f', 'null', '-'],
                           capture_output=True, text=True)
    assert check.returncode == 0, 'Decode check failed: ' + check.stderr[-900:]


def eval_fraction(s):
    a,b = s.split('/')
    return float(a)/float(b)


def main():
    p = argparse.ArgumentParser(description='Render 2D Lemo-style test scene to MP4 with original sound cues')
    p.add_argument('--output', default=str(ROOT/'exports'/'lemo-pip-test.mp4'))
    p.add_argument('--duration', type=float, default=10)
    p.add_argument('--fps', type=int, default=24)
    p.add_argument('--width', type=int, default=1280)
    p.add_argument('--height', type=int, default=720)
    p.add_argument('--audio', help='Optional WAV narration/music; uses original chimes by default')
    p.add_argument('--overwrite', action='store_true')
    a = p.parse_args()
    try:
        export(a)
    except Exception as e:
        p.exit(1, 'EXPORT FAILED: ' + str(e) + '\n')


if __name__ == '__main__':
    main()
