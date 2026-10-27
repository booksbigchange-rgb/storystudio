"""Repeatable local MVP acceptance. No installs, downloads or asset replacement."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sandbox-fixtures', action='store_true',
                        help='Use inherited ACLs for synthetic fixtures under restricted Windows tokens')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    expected = root/'engine'/'.venv'
    if Path(sys.prefix).resolve() != expected.resolve() or Path(os.environ.get('TEMP', '')).resolve() != root/'temp':
        parser.error('Run Verify-StoryStudio.cmd so the D: runtime and environment are selected')
    report_dir = root/'exports'/'verification-runs'/('run-'+uuid.uuid4().hex)
    report_dir.mkdir(parents=True)
    report = dict(started_utc=datetime.now(timezone.utc).isoformat(), status='running',
                  sandbox_fixtures=args.sandbox_fixtures, results=[],
                  limitations=['Speaker calls mocked in transport checks', 'Not clean-machine or low-spec certification'])
    def save():
        temporary = report_dir/'report.tmp'
        temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
        os.replace(temporary, report_dir/'report.json')
    options = ['--sandbox-fixtures'] if args.sandbox_fixtures else []
    checks = [('setup', [str(root/'engine'/'check_setup.py')])]
    for name in ('unit', 'gui_integration', 'preview_audio_integration', 'waveform_integration',
                 'two_track_integration', 'cancel_export_integration', 'repeat_audio_integration', 'layers_integration', 'formats_integration'):
        checks.append((name, [str(root/'tests'/'run_check.py'), *options, name]))
    checks.append(('master_video', [str(root/'tests'/'master_video.py'), '--gui']))
    save()
    try:
        for name, command in checks:
            print('Checking '+name+'...', flush=True)
            start = time.monotonic()
            with (report_dir/(name+'.log')).open('w', encoding='utf-8') as log:
                result = subprocess.run([sys.executable, *command], stdout=log, stderr=subprocess.STDOUT,
                                        cwd=root, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            entry = dict(name=name, passed=result.returncode == 0,
                         seconds=round(time.monotonic()-start, 2), log=name+'.log')
            report['results'].append(entry)
            save()
            print(('PASS' if entry['passed'] else 'FAIL')+f": {name} ({entry['seconds']}s)", flush=True)
            if name == 'setup' and not entry['passed']:
                break
        report['status'] = 'passed' if len(report['results']) == len(checks) and all(r['passed'] for r in report['results']) else 'failed'
    except Exception as exc:
        report['status'], report['error'] = 'failed', str(exc)
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        print('Report: '+str(report_dir/'report.json'), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
