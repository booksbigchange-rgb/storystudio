"""Shared audio mix: validation, persistence, media checks and measured FFmpeg output."""
import array
import copy
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
import mixed_audio as audio
import mixed_project as model

from mixed_render import tool
FFMPEG, FFPROBE = tool('ffmpeg'), tool('ffprobe')
RATE = 48000


def tone(path, hertz, seconds, amplitude=.5, delay=0.0):
    frames = array.array('h')
    for n in range(round(RATE*(delay+seconds))):
        t = n/RATE
        frames.append(round(32767*amplitude*math.sin(2*math.pi*hertz*t)) if t >= delay else 0)
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(RATE)
        handle.writeframes(frames.tobytes())
    return path


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-500:])
    return result.stdout


def goertzel(samples, hertz):
    k = 2*math.cos(2*math.pi*hertz/RATE)
    a = b = 0.0
    for x in samples:
        a, b = x + k*a - b, a
    return math.sqrt(max(a*a + b*b - k*a*b, 0))/len(samples)*2


def decode(path):
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    return [x/32768 for x in array.array('h', raw)]


def window(samples, start, end):
    return samples[round(start*RATE):round(end*RATE)]


class Validation(unittest.TestCase):
    def test_defaults_and_inactive(self):
        self.assertIsNone(audio.validate_audio(None))
        normal = audio.validate_audio({})
        self.assertFalse(audio.active(normal))
        self.assertTrue(audio.active(audio.validate_audio({'source_volume': .5})))

    def test_rejects_bad_settings(self):
        bad = [{'music': {'file': 'a.txt'}}, {'music': {'file': 'https://x/a.wav'}}, {'music': {'file': '//server/a.wav'}},
               {'music': {'file': 'a.wav', 'volume': 3}}, {'music': {'file': 'a.wav', 'volume': float('nan')}},
               {'music': {'file': 'a.wav', 'volume': True}}, {'duck': 'extreme'}, {'surprise': 1}, {'source_volume': -1},
               {'narration': [{'file': 'a.wav', 'start': -1}]}, {'narration': [{'file': 'a.wav', 'start': float('inf')}]},
               {'sfx': [{'file': 'a.wav'}]*33}, {'narration': [{'file': 'a.wav'}]*17}, {'sfx': 'x'}, [], {'music': 'a.wav'}]
        for settings in bad:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                audio.validate_audio(settings)

    def test_does_not_mutate(self):
        original = {'music': {'file': 'm.wav'}, 'sfx': [{'file': 's.wav', 'start': 1}]}
        before = copy.deepcopy(original)
        audio.validate_audio(original)
        self.assertEqual(original, before)

    def test_old_timelines_unchanged(self):
        doc = model.new_project()
        self.assertNotIn('audio', model.validate(doc))

    def test_relative_roundtrip_and_stable_order(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder).resolve()
            (folder/'media').mkdir()
            doc = model.new_project()
            doc['audio'] = {'music': {'file': str(folder/'media/m.wav'), 'volume': .3}, 'duck': 'strong',
                            'narration': [{'file': str(folder/'media/b.wav'), 'start': 5}, {'file': str(folder/'media/a.wav'), 'start': 1}],
                            'sfx': [{'file': str(folder/'media/s.wav'), 'start': 2, 'volume': 1.5}]}
            path = folder/'timeline.json'
            model.save(doc, path)
            stored = json.loads(path.read_text())['audio']
            self.assertEqual(stored['music']['file'], str(Path('media/m.wav')))
            self.assertEqual([c['file'] for c in stored['narration']], [str(Path('media/b.wav')), str(Path('media/a.wav'))])
            loaded = model.load(path)
            self.assertEqual(loaded['audio'], model.validate(doc)['audio'])


class Media(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def check(self, settings, duration=10):
        return audio.check_media(audio.validate_audio(settings), duration, run, FFMPEG, FFPROBE)

    def test_valid_media(self):
        music = tone(self.folder/'m.wav', 220, 1)
        lengths = self.check({'music': {'file': str(music)}})
        self.assertAlmostEqual(lengths[str(music)], 1, places=1)

    def test_missing_file(self):
        with self.assertRaisesRegex(FileNotFoundError, 'Music file is missing'):
            self.check({'music': {'file': str(self.folder/'gone.wav')}})

    def test_empty_text_and_corrupt_files(self):
        empty = self.folder/'empty.wav'; empty.write_bytes(b'')
        text = self.folder/'text.mp3'; text.write_text('not audio at all')
        good = tone(self.folder/'good.wav', 440, 1)
        damaged = self.folder/'damaged.wav'
        damaged.write_bytes(good.read_bytes()[:60]+b'\xff'*2000)
        for path, message in [(empty, 'between 1 byte'), (text, 'not readable audio')]:
            with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, message):
                self.check({'sfx': [{'file': str(path)}]})
        with self.assertRaises(ValueError):
            self.check({'sfx': [{'file': str(damaged)}]})

    def test_video_only_file_is_not_audio(self):
        silent = self.folder/'video.mp4'
        run([FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x64:d=1:r=24', '-pix_fmt', 'yuv420p', str(silent)])
        silent.rename(silent.with_suffix('.m4a'))
        with self.assertRaisesRegex(ValueError, 'not readable audio'):
            self.check({'music': {'file': str(silent.with_suffix('.m4a'))}})

    def test_clip_starting_after_timeline(self):
        sfx = tone(self.folder/'s.wav', 900, .5)
        with self.assertRaisesRegex(ValueError, 'after the 10s timeline ends'):
            self.check({'sfx': [{'file': str(sfx), 'start': 10}]})
        self.check({'sfx': [{'file': str(sfx), 'start': 9.9}]})


class Mix(unittest.TestCase):
    """Measure the real FFmpeg graph with distinct frequencies for each layer."""
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.voice = tone(cls.folder/'voice.wav', 1000, 3, .4, delay=2)        # source speech 2–5 s
        cls.base = cls.folder/'base.mp4'
        run([FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x223344:s=160x90:d=10:r=24', '-i', str(cls.voice),
             '-map', '0:v', '-map', '1:a', '-af', 'apad', '-t', '10', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le',
             str(cls.base.with_suffix('.mov'))])
        cls.base = cls.base.with_suffix('.mov')
        cls.music = tone(cls.folder/'music.wav', 220, 3, .5)                  # shorter than the video: must loop
        cls.narration = tone(cls.folder/'narration.wav', 1500, 1, .4)
        cls.sfx = tone(cls.folder/'sfx.wav', 3000, .5, .5)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def render(self, settings, name):
        settings = audio.validate_audio(settings)
        inputs, graph, label = audio.build(settings, 10)
        out = self.folder/(name+'.mp4')
        run([FFMPEG, '-v', 'error', '-nostdin', '-i', str(self.base), *inputs, '-filter_complex', graph,
             '-map', '0:v:0', '-map', label, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', '10', str(out)])
        run([FFMPEG, '-v', 'error', '-xerror', '-i', str(out), '-f', 'null', '-'])
        return decode(out)

    def test_layers_timing_loop_and_ducking(self):
        settings = {'music': {'file': str(self.music), 'volume': .6}, 'duck': 'strong',
                    'narration': [{'file': str(self.narration), 'start': 6, 'volume': 1}],
                    'sfx': [{'file': str(self.sfx), 'start': 8, 'volume': 1}]}
        mixed = self.render(settings, 'mix')
        self.assertAlmostEqual(len(mixed)/RATE, 10, delta=.1)
        self.assertGreater(goertzel(window(mixed, 2.5, 4.5), 1000), .2)               # source speech preserved
        self.assertGreater(goertzel(window(mixed, 6.2, 6.9), 1500), .2)               # shared narration at 6 s
        self.assertLess(goertzel(window(mixed, 5.2, 5.8), 1500), .01)
        self.assertGreater(goertzel(window(mixed, 8.05, 8.45), 3000), .2)             # SFX at 8 s
        self.assertLess(goertzel(window(mixed, 7.0, 7.8), 3000), .01)
        free = goertzel(window(mixed, 0.8, 1.8), 220)                                # music alone
        looped = goertzel(window(mixed, 3.3, 3.4), 220)
        self.assertGreater(free, .15)
        under_source = goertzel(window(mixed, 3.0, 4.0), 220)
        under_narration = goertzel(window(mixed, 6.2, 6.9), 220)
        self.assertLess(under_source, free*.5)                                         # ducked under source speech
        self.assertLess(under_narration, free*.5)                                      # and shared narration
        recovered = goertzel(window(mixed, 7.5, 7.95), 220)
        self.assertGreater(recovered, free*.7)                                         # looped music returns afterward
        self.assertGreater(max(abs(x) for x in mixed), .05)
        self.assertLess(max(abs(x) for x in mixed), .99)

    def test_duck_off_leaves_music_level(self):
        mixed = self.render({'music': {'file': str(self.music), 'volume': .6}, 'duck': 'off'}, 'noduck')
        free = goertzel(window(mixed, 0.8, 1.8), 220)
        self.assertAlmostEqual(goertzel(window(mixed, 3.0, 4.0), 220), free, delta=free*.2)

    def test_volume_controls(self):
        loud = goertzel(window(self.render({'source_volume': 1}, 'v1'), 2.5, 4.5), 1000)
        half = goertzel(window(self.render({'source_volume': .5}, 'v05'), 2.5, 4.5), 1000)
        mute = goertzel(window(self.render({'source_volume': 0, 'sfx': [{'file': str(self.sfx), 'start': 9}]}, 'v0'), 2.5, 4.5), 1000)
        self.assertAlmostEqual(half/loud, .5, delta=.08)
        self.assertLess(mute, .005)

    def test_limiter_prevents_clipping(self):
        loud = tone(self.folder/'loud.wav', 700, 3, 1.0)
        settings = {'music': {'file': str(loud), 'volume': 2}, 'duck': 'off',
                    'narration': [{'file': str(loud), 'start': 0, 'volume': 2}], 'sfx': [{'file': str(loud), 'start': 0, 'volume': 2}]}
        peak = max(abs(x) for x in self.render(settings, 'loud'))
        self.assertLess(peak, .99)

    def test_clip_past_end_is_trimmed(self):
        mixed = self.render({'sfx': [{'file': str(self.sfx), 'start': 9.8}]}, 'tail')
        self.assertAlmostEqual(len(mixed)/RATE, 10, delta=.1)


if __name__ == '__main__':
    unittest.main()
