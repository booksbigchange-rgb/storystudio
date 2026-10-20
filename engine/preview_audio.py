"""Prepare timeline-aligned PCM for Windows preview without changing source media."""
import subprocess
import threading
import time
import uuid
from pathlib import Path


def audio_filter(audio, duration):
    fade = min(audio['fade'], max(0, duration-audio['offset']))
    filters = (f"aresample=48000,atrim=start={audio['trim']},asetpts=N/SR/TB,"
               f"volume={audio['volume']},adelay={round(audio['offset']*48000)}S:all=1,"
               f"asetpts=N/SR/TB,apad,atrim=end_sample={round(duration*48000)},asetpts=N/SR/TB")
    if fade:
        filters += (f",afade=t=in:st={audio['offset']}:d={fade},"
                    f"afade=t=out:st={max(audio['offset'], duration-fade)}:d={fade}")
    return filters


def mix_arguments(tracks, duration, position=0, first_input=0):
    inputs, chains, labels = [], [], []
    for index, track in enumerate(tracks):
        if track.get('repeat', False):
            inputs += ['-stream_loop', '-1']
        inputs += ['-i', track['path']]
        label = f'track{index}'
        chains.append(f'[{first_input+index}:a]'+audio_filter(track, duration)+f'[{label}]')
        labels.append(f'[{label}]')
    if not labels:
        raise ValueError('Add an audio track first')
    chains.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0:duration=longest,'
                  f'alimiter=limit=1:level=false:latency=true,atrim=start_sample={round(position*48000)},asetpts=N/SR/TB[mix]')
    return inputs, ';'.join(chains)


class PreviewAudio:
    timeout = 60

    def __init__(self, binary, directory, callback):
        self.binary, self.directory, self.callback = binary, Path(directory), callback
        self.cancelled = threading.Event()
        self.lock = threading.Lock()
        self.process = None
        self.path = self.directory / ('preview-audio-'+uuid.uuid4().hex+'.wav')

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()

    def run(self, audio, duration, position):
        error = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            inputs, filters = mix_arguments(audio if isinstance(audio, list) else [audio], duration, position)
            with self.lock:
                if self.cancelled.is_set():
                    return
                self.process = subprocess.Popen(
                    [str(self.binary), '-nostdin', '-v', 'error', *inputs,
                     '-vn', '-filter_complex', filters, '-map', '[mix]', '-ac', '2', '-c:a', 'pcm_s16le', str(self.path)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + self.timeout
            while True:
                if self.cancelled.is_set() or time.monotonic() >= deadline:
                    timed_out = not self.cancelled.is_set()
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=3)
                    if timed_out:
                        raise RuntimeError('Audio preparation timed out. Try a shorter story.')
                    return
                try:
                    code = self.process.wait(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    pass
            if code:
                raise RuntimeError('Could not decode preview audio. Check the soundtrack file.')
        except Exception as exc:
            error = str(exc)
        finally:
            if self.cancelled.is_set() or error:
                self.path.unlink(missing_ok=True)
            if not self.cancelled.is_set():
                self.callback(self, error)
