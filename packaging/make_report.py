"""Write BUILD-REPORT.md for a portable build from the manifest and the compiled test results (stdlib only).

usage: make_report.py <build folder> <evidence folder>
"""
import json
from pathlib import Path
import sys


def load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def main(argv):
    root, evidence = Path(argv[1]), Path(argv[2])
    manifest = load(root/'MANIFEST.json')
    lines = [f"# StoryStudio Unified portable {manifest['version']} — build report", '',
             f"- Commit: `{manifest['commit']}`", f"- Built (UTC): {manifest['built_utc']} by {manifest['builder']}, run {manifest['build_run']}",
             '- The archive checksum is in the `.sha256` file published beside the zip (it cannot be stored inside the zip).',
             f"- Contents: {manifest['file_count']:,} files, {manifest['total_bytes']:,} bytes (see MANIFEST.json and SHA256SUMS.txt)", '',
             '## Programs', '']
    for entry in manifest['files']:
        if entry['path'].lower().endswith('.exe') and '_internal' not in entry['path']:
            lines.append(f"- `{entry['path']}` — {entry['bytes']:,} bytes — SHA-256 `{entry['sha256']}`")
    lines += ['', '## Tool provenance', '']
    for name, data in manifest['provenance'].items():
        if name == 'ffmpeg-provenance':
            lines.append(f"- FFmpeg: {data.get('version')} from {data.get('url')} (archive SHA-256 `{data.get('sha256')}` matched the publisher's checksum)")
        else:
            lines.append(f"- {name}: recorded in `provenance/{name}.json`")
    lines += ['', '## Automated validation of this exact build (compiled executables, GitHub Actions Windows runner)', '']
    selftest = load(evidence/'compiled-unified/results.json')
    if selftest:
        lines += [f"- Unified self-test: **{selftest['status']}**, output `{selftest['output']}`, {selftest['frames']} frames, SHA-256 `{selftest['sha256']}`"]
        lines += [f"  - {item}" for item in selftest['checks']]
    gui = load(evidence/'compiled-character-gui/gui-results.json')
    if gui:
        lines += [f"- Character editor compiled GUI test: **{gui['result']}** — " + ', '.join(gui['checks'])]
    for name in ('landscape', 'portrait'):
        details = load(evidence/f'compiled-character-{name}.json')
        if details:
            lines.append(f"- Character {name} self-test export: {details['summary']}")
    lines += ['', '## Not verified here', '',
              '- Everything above ran on a clean GitHub-hosted Windows runner, not on your computer.',
              '- Not tested: your hardware (Ryzen 3 / 12 GB / integrated graphics), your display scaling, long real projects, listening quality of mixes, Windows Defender/SmartScreen behavior (the executables are unsigned and may prompt).',
              '- The character editor and character export need Microsoft Edge or Google Chrome installed (existing browser; none is bundled).',
              '', '## Verify your download', '',
              'In PowerShell: `Get-FileHash -Algorithm SHA256 <zip>` and compare with the `.sha256` file, or use `Install-StoryStudio-Unified-Portable.cmd`, which checks it for you. After installing, every file can be re-checked against `SHA256SUMS.txt`.', '']
    (root/'BUILD-REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print('report written')


if __name__ == '__main__':
    main(sys.argv)
