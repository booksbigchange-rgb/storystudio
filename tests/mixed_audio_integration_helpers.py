"""Shared decoded-output helpers for mixed audio acceptance tests."""
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from mixed_render import tool


def probe_streams(path):
    details = json.loads(subprocess.run([tool('ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-count_frames', '-of', 'json', str(path)],
                                        capture_output=True, text=True, check=True).stdout)
    video = next(s for s in details['streams'] if s['codec_type'] == 'video')
    return video, [s for s in details['streams'] if s['codec_type'] == 'audio'], float(details['format']['duration'])
