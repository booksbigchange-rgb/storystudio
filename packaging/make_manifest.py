"""Write MANIFEST.json and SHA256SUMS.txt for a finished portable build folder (stdlib only).

usage: make_manifest.py <build folder> <version> <commit> [provenance.json ...]
       make_manifest.py --sums-only <build folder>   (rewrite SHA256SUMS.txt after adding BUILD-REPORT.md)
SHA256SUMS.txt lists every file except itself, in `sha256sum -c` format. MANIFEST.json describes
the build and is itself listed in SHA256SUMS.txt.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_sums(root):
    files = sorted(p for p in root.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    lines = sorted((f"{digest(p)}  {p.relative_to(root).as_posix()}" for p in files), key=lambda l: l.split('  ', 1)[1])
    (root/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return len(lines)


def main(argv):
    if argv[1] == '--sums-only':
        print(write_sums(Path(argv[2]).resolve()), 'files summed')
        return
    root, version, commit = Path(argv[1]).resolve(), argv[2], argv[3]
    provenance = {}
    for name in argv[4:]:
        provenance[Path(name).stem] = json.loads(Path(name).read_text(encoding='utf-8-sig'))
    files = sorted(p for p in root.rglob('*') if p.is_file() and p.name not in ('MANIFEST.json', 'SHA256SUMS.txt'))
    entries = [dict(path=p.relative_to(root).as_posix(), bytes=p.stat().st_size, sha256=digest(p)) for p in files]
    manifest = dict(
        product='StoryStudio Unified portable', version=version, commit=commit,
        built_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        build_run=os.environ.get('GITHUB_RUN_ID'), builder='GitHub Actions windows-latest',
        executables=[e['path'] for e in entries if e['path'].lower().endswith('.exe') and e['path'].count('/') <= 1 and '_internal' not in e['path']],
        longest_relative_path=max(len(e['path']) for e in entries), file_count=len(entries), total_bytes=sum(e['bytes'] for e in entries), provenance=provenance, files=entries)
    (root/'MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    write_sums(root)
    print(f'{len(entries)} files, {manifest["total_bytes"]} bytes, longest relative path {manifest["longest_relative_path"]}')


if __name__ == '__main__':
    main(sys.argv)
