"""Shared, offline audio mix for mixed timelines: source audio, narration, music, SFX.

The mix is optional. A timeline without an ``audio`` block keeps the exact audio
behavior of its source projects. Media files are local only and are validated
(existence, type, decodability, duration) before any rendering starts.
"""
import copy
import json
import math
from pathlib import Path

EXTENSIONS = ('.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac')
MAX_BYTES = 200*1024*1024
MAX_SECONDS = 3600
MAX_NARRATION = 16
MAX_SFX = 32
MAX_VOLUME = 2.0
# threshold (linear), ratio: heavier presets pull music further under speech.
DUCKING = {'off': None, 'light': (0.06, 3), 'medium': (0.03, 6), 'strong': (0.02, 12)}
RATE = 48000
FORMAT = 'aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo'


def new_audio():
    return dict(source_volume=1.0, music=None, duck='medium', narration=[], sfx=[])


def _volume(value, label, default=None):
    if value is None and default is not None:
        return default
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= MAX_VOLUME:
        raise ValueError(f'{label} volume must be between 0 and {MAX_VOLUME:g}')
    return float(value)


def _file(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 500 or '\0' in value:
        raise ValueError(f'{label} needs a local audio file')
    if '://' in value or value.startswith(('\\\\', '//')):
        raise ValueError(f'{label} must be a local file; network and web locations are not used')
    if Path(value).suffix.lower() not in EXTENSIONS:
        raise ValueError(f'{label} must be one of: ' + ', '.join(EXTENSIONS))
    return value


def _clip(item, label):
    if not isinstance(item, dict):
        raise ValueError(f'{label} is not a valid clip')
    start = item.get('start', 0)
    if type(start) not in (int, float) or not math.isfinite(start) or not 0 <= start <= 600:
        raise ValueError(f'{label} start must be 0–600 seconds')
    return dict(file=_file(item.get('file'), label), start=float(start), volume=_volume(item.get('volume'), label, 1.0))


def validate_audio(audio):
    """Return a normalized copy of the structural audio settings (no file access)."""
    if audio is None:
        return None
    if not isinstance(audio, dict):
        raise ValueError('Audio settings must be an object')
    unknown = set(audio) - {'source_volume', 'music', 'duck', 'narration', 'sfx'}
    if unknown:
        raise ValueError('Unknown audio setting: '+sorted(unknown)[0])
    result = new_audio()
    result['source_volume'] = _volume(audio.get('source_volume'), 'Source audio', 1.0)
    if audio.get('duck', 'medium') not in DUCKING:
        raise ValueError('Ducking must be off, light, medium or strong')
    result['duck'] = audio.get('duck', 'medium')
    music = audio.get('music')
    if music is not None:
        if not isinstance(music, dict):
            raise ValueError('Music is not a valid track')
        result['music'] = dict(file=_file(music.get('file'), 'Music'), volume=_volume(music.get('volume'), 'Music', .5))
    for key, limit, label in (('narration', MAX_NARRATION, 'narration'), ('sfx', MAX_SFX, 'sound effect')):
        clips = audio.get(key, [])
        if not isinstance(clips, list) or len(clips) > limit:
            raise ValueError(f'Use at most {limit} {label} clips')
        result[key] = [_clip(c, f'{label.capitalize()} {i+1}') for i, c in enumerate(clips)]
    return result


def active(audio):
    return bool(audio) and bool(audio['music'] or audio['narration'] or audio['sfx'] or audio['source_volume'] != 1.0)


def map_files(audio, function):
    """Copy of ``audio`` with ``function`` applied to every media path (relative/absolute)."""
    audio = copy.deepcopy(audio)
    if audio.get('music'):
        audio['music']['file'] = function(audio['music']['file'])
    for key in ('narration', 'sfx'):
        for clip in audio.get(key, []):
            clip['file'] = function(clip['file'])
    return audio


def media_files(audio):
    if not audio:
        return []
    named = [('Music', audio['music']['file'])] if audio.get('music') else []
    named += [(f'Narration {i+1}', c['file']) for i, c in enumerate(audio.get('narration', []))]
    named += [(f'Sound effect {i+1}', c['file']) for i, c in enumerate(audio.get('sfx', []))]
    return named


def check_media(audio, duration, run, ffmpeg='ffmpeg', ffprobe='ffprobe'):
    """Fail early and clearly on missing, unreadable, non-audio or corrupt media.

    ``run`` executes a command list and returns stdout; it raises on failure.
    Returns {path: seconds}.
    """
    lengths = {}
    starts = {}
    for key, label in (('narration', 'Narration'), ('sfx', 'Sound effect')):
        for i, clip in enumerate(audio.get(key, [])):
            starts[f'{label} {i+1}'] = clip['start']
    for label, name in media_files(audio):
        path = Path(name)
        if not path.is_file():
            raise FileNotFoundError(f'{label} file is missing: {path}')
        size = path.stat().st_size
        if size == 0 or size > MAX_BYTES:
            raise ValueError(f'{label} file must be between 1 byte and {MAX_BYTES//1024//1024} MB: {path.name}')
        try:
            info = json.loads(run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
            stream = next(s for s in info['streams'] if s.get('codec_type') == 'audio')
            seconds = float(info['format'].get('duration') or stream.get('duration'))
        except (RuntimeError, ValueError, KeyError, StopIteration, TypeError, json.JSONDecodeError):
            raise ValueError(f'{label} is not readable audio: {path.name}') from None
        if not math.isfinite(seconds) or not .05 <= seconds <= MAX_SECONDS:
            raise ValueError(f'{label} must last 0.05 seconds to {MAX_SECONDS//60} minutes: {path.name}')
        try:
            run([ffmpeg, '-v', 'error', '-xerror', '-nostdin', '-i', str(path), '-f', 'null', '-'])
        except RuntimeError:
            raise ValueError(f'{label} is damaged and cannot be decoded: {path.name}') from None
        lengths[name] = seconds
        if label in starts and starts[label] >= duration:
            raise ValueError(f'{label} starts at {starts[label]:g}s, after the {duration:g}s timeline ends')
    return lengths


def build(audio, duration):
    """Return (input arguments, filter_complex, output label).

    Input 0 is the joined section video/audio. Further inputs follow in the order
    music, narration clips, sound-effect clips.
    """
    inputs, parts = [], []
    index = 0

    def add(name, loop=False):
        nonlocal index
        index += 1
        inputs.extend((['-stream_loop', '-1'] if loop else []) + ['-i', str(name)])
        return index
    parts.append(f'[0:a]{FORMAT},volume={audio["source_volume"]:g}[src]')
    music = None
    if audio['music']:
        m = add(audio['music']['file'], loop=True)
        fade = min(1.5, duration/4)
        parts.append(f'[{m}:a]{FORMAT},atrim=duration={duration:.6f},asetpts=PTS-STARTPTS,volume={audio["music"]["volume"]:g},'
                     f'afade=t=in:d={min(.5, duration/8):.3f},afade=t=out:st={duration-fade:.6f}:d={fade:.3f}[music]')
        music = 'music'
    voice = ['src']
    for i, clip in enumerate(audio['narration']):
        n = add(clip['file'])
        parts.append(f'[{n}:a]{FORMAT},volume={clip["volume"]:g},adelay={round(clip["start"]*1000)}:all=1[nar{i}]')
        voice.append(f'nar{i}')
    if len(voice) > 1:
        parts.append(''.join(f'[{v}]' for v in voice)+f'amix=inputs={len(voice)}:normalize=0:duration=longest[voice]')
    else:
        parts.append('[src]anull[voice]')
    ducking = DUCKING[audio['duck']]
    final = []
    if music and ducking:
        threshold, ratio = ducking
        parts.append('[voice]asplit=2[voicemix][voicekey]')
        parts.append(f'[music][voicekey]sidechaincompress=threshold={threshold}:ratio={ratio}:attack=20:release=500:makeup=1[bed]')
        final += ['voicemix', 'bed']
    else:
        final += ['voice'] + ([music] if music else [])
    for i, clip in enumerate(audio['sfx']):
        s = add(clip['file'])
        parts.append(f'[{s}:a]{FORMAT},volume={clip["volume"]:g},adelay={round(clip["start"]*1000)}:all=1[sfx{i}]')
        final.append(f'sfx{i}')
    tail = f'atrim=duration={duration:.6f},alimiter=limit=0.89:level=0,aresample={RATE}'
    if len(final) > 1:
        parts.append(''.join(f'[{f}]' for f in final)+f'amix=inputs={len(final)}:normalize=0:duration=longest,{tail}[aout]')
    else:
        parts.append(f'[{final[0]}]{tail}[aout]')
    return inputs, ';'.join(parts), '[aout]'
