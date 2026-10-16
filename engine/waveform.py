"""Small cached audio envelopes, decoded locally without loading whole files."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import threading
import uuid

RATE, BUCKET = 8000, 160
MAX_SECONDS = 7200


def source_key(path):
    path = Path(path).resolve()
    stat = path.stat()
    return hashlib.sha256(f"v1|{path}|{stat.st_size}|{stat.st_mtime_ns}".encode()).hexdigest()


def read_cache(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid waveform cache")
    if data.get("version") != 1 or data.get("step") != BUCKET / RATE:
        raise ValueError("Unsupported waveform cache")
    if not isinstance(data.get("peaks"), list) or len(data["peaks"]) > MAX_SECONDS * RATE // BUCKET:
        raise ValueError("Invalid waveform cache")
    duration = float(data["duration"])
    if not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS:
        raise ValueError("Invalid waveform duration")
    if any(not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1 for p in data["peaks"]):
        raise ValueError("Invalid waveform peaks")
    if abs(len(data["peaks"])*data["step"]-duration) > data["step"]+.0001:
        raise ValueError("Waveform length mismatch")
    return data


class WaveformJob:
    def __init__(self, path, binary, cache_dir, callback):
        self.path, self.binary, self.cache_dir = Path(path), binary, Path(cache_dir)
        self.callback = callback
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.process = None
        self.timed_out = False

    def cancel(self):
        self.stop.set()
        with self.lock:
            if self.process and self.process.poll() is None:
                try:
                    self.process.terminate()
                except OSError:
                    pass

    def run(self):
        try:
            data = self.analyze()
            if not self.stop.is_set():
                self.callback(data, None)
        except Exception as exc:
            if not self.stop.is_set() or self.timed_out:
                self.callback(None, str(exc))

    def analyze(self):
        key = source_key(self.path)
        cached = self.cache_dir / (key + ".json")
        if cached.exists():
            try:
                return read_cache(cached)
            except (OSError, ValueError, KeyError, TypeError):
                pass  # Rebuild this derived cache, never the source media.
        if self.stop.is_set():
            raise RuntimeError("Waveform canceled")
        if not self.binary:
            raise RuntimeError("FFmpeg unavailable")
        command = [self.binary, "-v", "error", "-nostdin", "-i", str(self.path), "-map", "0:a:0",
                   "-t", str(MAX_SECONDS), "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"]
        peaks, sample_count = [], 0
        with self.lock:
            if self.stop.is_set():
                raise RuntimeError("Waveform canceled")
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        def timeout():
            self.timed_out = True
            self.cancel()
        timer = threading.Timer(60, timeout)
        timer.daemon = True
        timer.start()
        try:
            pending = b""
            while True:
                chunk = self.process.stdout.read(RATE * 2)
                if self.stop.is_set():
                    raise RuntimeError("Waveform analysis canceled or timed out")
                if not chunk:
                    break
                pending += chunk
                available = len(pending) // (BUCKET*2) * (BUCKET*2)
                for offset in range(0, available, BUCKET*2):
                    samples = array("h", pending[offset:offset+BUCKET*2])
                    if sys.byteorder != "little":
                        samples.byteswap()
                    peaks.append(round(max(abs(n) for n in samples)/32768, 5))
                    sample_count += len(samples)
                pending = pending[available:]
            if pending:
                samples = array("h", pending)
                if sys.byteorder != "little":
                    samples.byteswap()
                peaks.append(round(max(abs(n) for n in samples)/32768, 5))
                sample_count += len(samples)
            if self.process.wait(timeout=3) != 0 or not sample_count:
                raise ValueError("Cannot read an audio stream from this file")
        finally:
            timer.cancel()
            self.process.stdout.close()
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait()
        data = {"version": 1, "step": BUCKET/RATE, "duration": sample_count/RATE, "peaks": peaks,
                "analysis_limit_seconds": MAX_SECONDS}
        if self.stop.is_set() or source_key(self.path) != key:
            raise RuntimeError("Audio changed during waveform analysis")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary = cached.with_name(key + "." + uuid.uuid4().hex + ".tmp")
        try:
            temporary.write_text(json.dumps(data), encoding="utf-8")
            temporary.replace(cached)
        finally:
            temporary.unlink(missing_ok=True)
        return data


def waveform_columns(data, settings, duration, width):
    """Map the source envelope to timeline pixels with trim, delay, gain and fade."""
    width = int(width)
    if width <= 0 or duration <= 0:
        return []
    peaks, step = data["peaks"], data["step"]
    scale = max(max(peaks, default=0), .05)
    offset, trim, gain = (settings[key] for key in ("offset", "trim", "volume"))
    fade = min(settings["fade"], max(0, duration-offset))
    result = []
    for column in range(width):
        start, end = column/width*duration, (column+1)/width*duration
        left, right = max(0, start-offset), max(0, end-offset)
        source_start, source_end = left+trim, right+trim
        repeating = settings.get('repeat', False) and data['duration'] > 0
        if end <= offset or (not repeating and source_start >= data['duration']):
            result.append(0.0)
            continue
        if repeating:
            length = data['duration']
            span = source_end-source_start
            source_start %= length
            source_end = source_start+span
            if span >= length:
                ranges = [(0, length)]
            elif source_end > length:
                ranges = [(source_start, length), (0, source_end-length)]
            else:
                ranges = [(source_start, source_end)]
        else:
            ranges = [(source_start, source_end)]
        peak = 0
        for start_time, end_time in ranges:
            first = max(0, math.floor(start_time/step))
            last = min(len(peaks), math.ceil(end_time/step))
            peak = max(peak, max(peaks[first:last], default=0))
        amplitude = peak/scale*gain
        center = max(offset, (start+end)/2)
        if fade:
            amplitude *= min(1, max(0, (center-offset)/fade), max(0, (duration-center)/fade))
        result.append(min(1, amplitude))
    return result
