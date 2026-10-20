"""Frozen-build routing, manifest/checksum generation and launcher safety rules (no packaging tools needed)."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
import mixed_control
import mixed_render
import runtime
import studio_hub


class FrozenRouting(unittest.TestCase):
    def frozen(self, home):
        return patch.multiple(runtime, FROZEN=True), patch.dict('os.environ', {'STORYSTUDIO_HOME': str(home)})

    def test_source_layout_is_unchanged(self):
        self.assertEqual(runtime.app_root(ROOT/'engine'/'studio_hub.py'), ROOT)
        command = studio_hub.command('mixed', 'x.json')
        self.assertEqual(command[0], sys.executable)
        self.assertIn('--editor', command)
        self.assertEqual(mixed_render.worker('cartoon')[0], sys.executable)

    def test_helpers_live_where_the_layout_says(self):
        with tempfile.TemporaryDirectory() as home:
            a, b = self.frozen(home)
            with a, b:
                self.assertEqual(runtime.app_root(), Path(home).resolve())
                self.assertEqual(runtime.helper('hub'), Path(home).resolve()/'StoryStudio.exe')
                self.assertEqual(runtime.helper('gate'), Path(home).resolve()/'StoryStudioWorker.exe')
                self.assertEqual(runtime.helper('cartoon'), Path(home).resolve()/'character'/'StoryStudioCharacterWorker.exe')

    def test_editors_and_workers_route_to_the_right_exe(self):
        with tempfile.TemporaryDirectory() as home:
            a, b = self.frozen(home)
            with a, b:
                home = Path(home).resolve()
                self.assertEqual(studio_hub.command('documentary', 'p.json')[:3], [str(home/'StoryStudio.exe'), '--editor', 'documentary'])
                self.assertEqual(studio_hub.command('mixed'), [str(home/'StoryStudio.exe'), '--editor', 'mixed'])
                character = studio_hub.command('cartoon', 'p.json')
                self.assertEqual(character[0], str(home/'character'/'StoryStudioCharacter.exe'))
                self.assertEqual(character[1], '--open')
                self.assertEqual(mixed_render.worker('documentary'), [str(home/'StoryStudioWorker.exe')])
                self.assertEqual(mixed_render.worker('cartoon'), [str(home/'character'/'StoryStudioCharacterWorker.exe')])

    def test_character_exe_finds_the_shared_top_folder(self):
        with tempfile.TemporaryDirectory() as home:
            home = Path(home).resolve()
            with patch.multiple(runtime, FROZEN=True), patch.dict('os.environ', {}, clear=False), \
                    patch.object(sys, 'executable', str(home/'character'/'StoryStudioCharacter.exe')):
                import os
                os.environ.pop('STORYSTUDIO_HOME', None)
                self.assertEqual(runtime.app_root(), home)

    def test_prepare_environment_scopes_everything_to_the_folder(self):
        with tempfile.TemporaryDirectory() as home:
            home = Path(home).resolve()
            (home/'bin').mkdir()
            (home/'bin'/'ffmpeg.exe').write_bytes(b'x')
            with patch.multiple(runtime, FROZEN=True), patch.dict('os.environ', {'STORYSTUDIO_HOME': str(home)}):
                import os
                runtime.prepare_environment()
                self.assertEqual(os.environ['STORYSTUDIO_FFMPEG'], str(home/'bin'/'ffmpeg.exe'))
                self.assertEqual(os.environ['TEMP'], str(home/'temp'))
                self.assertTrue((home/'projects').is_dir() and (home/'exports').is_dir())

    def test_tool_prefers_bundled_bin(self):
        with tempfile.TemporaryDirectory() as home:
            home = Path(home)
            (home/'bin').mkdir()
            (home/'bin'/'ffprobe.exe').write_bytes(b'x')
            with patch.object(mixed_render, 'ROOT', home):
                self.assertEqual(mixed_render.tool('ffprobe'), str(home/'bin'/'ffprobe.exe'))

    def test_gate_main_waits_for_start(self):
        import export_gate
        with patch.object(sys, 'stdin', open(__file__)):
            self.assertEqual(export_gate.main([sys.executable, '-c', 'raise SystemExit(7)']), 1)
        import io
        with patch.object(sys, 'stdin', io.StringIO('START\n')):
            self.assertEqual(export_gate.main([sys.executable, '-c', 'raise SystemExit(7)']), 7)


class Manifest(unittest.TestCase):
    def test_manifest_and_sums(self):
        script = ROOT/'packaging'/'make_manifest.py'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'build'
            (root/'sub').mkdir(parents=True)
            (root/'a.txt').write_text('alpha')
            (root/'sub'/'b.exe').write_bytes(b'beta')
            provenance = Path(folder)/'ffmpeg-provenance.json'
            provenance.write_text(json.dumps({'url': 'https://example', 'sha256': 'ab'}))
            subprocess.run([sys.executable, str(script), str(root), '2.0.0-abc1234', 'f'*40, str(provenance)], check=True, capture_output=True)
            manifest = json.loads((root/'MANIFEST.json').read_text())
            self.assertEqual(manifest['version'], '2.0.0-abc1234')
            self.assertEqual([e['path'] for e in manifest['files']], ['a.txt', 'sub/b.exe'])
            self.assertEqual(manifest['files'][0]['sha256'], hashlib.sha256(b'alpha').hexdigest())
            self.assertEqual(manifest['executables'], ['sub/b.exe'])
            self.assertEqual(manifest['provenance']['ffmpeg-provenance']['url'], 'https://example')
            (root/'BUILD-REPORT.md').write_text('report')
            subprocess.run([sys.executable, str(script), '--sums-only', str(root)], check=True, capture_output=True)
            lines = (root/'SHA256SUMS.txt').read_text().splitlines()
            listed = {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in lines}
            self.assertEqual(set(listed), {'MANIFEST.json', 'a.txt', 'sub/b.exe', 'BUILD-REPORT.md'})
            for name, value in listed.items():
                self.assertEqual(value, hashlib.sha256((root/name).read_bytes()).hexdigest())


class LauncherRules(unittest.TestCase):
    """Static checks of the installer's safety rules (PowerShell is exercised for real on Windows CI)."""
    def setUp(self):
        self.install = (ROOT/'launchers'/'install-unified-portable.ps1').read_text(encoding='utf-8')
        self.open = (ROOT/'launchers'/'open-unified-portable.ps1').read_text(encoding='utf-8')

    def test_installer_never_overwrites(self):
        self.assertIn("if (Test-Path -LiteralPath $destination) { throw", self.install)
        self.assertLess(self.install.index('Test-Path -LiteralPath $destination'), self.install.index('ExtractToDirectory'))
        self.assertIn('Move-Item', self.install)
        self.assertNotIn('Remove-Item -LiteralPath $destination', self.install)
        self.assertIn("'unified-portable-' + $manifest.version", self.install)
        self.assertNotIn('portable-766646f', self.install.replace('portable-766646f build', ''))

    def test_installer_verifies_before_publishing(self):
        self.assertLess(self.install.index('Zip checksum mismatch'), self.install.index('ExtractToDirectory'))
        self.assertLess(self.install.index('SHA256SUMS.txt'), self.install.index('Move-Item'))

    def test_root_launchers_exist_and_use_scoped_scripts(self):
        for name, script in (('Install-StoryStudio-Unified-Portable.cmd', 'install-unified-portable.ps1'),
                             ('Open-StoryStudio-Unified-Portable.cmd', 'open-unified-portable.ps1')):
            text = (ROOT/name).read_text()
            self.assertIn(script, text)
            self.assertIn('-ExecutionPolicy Bypass', text)
        self.assertIn('unified-portable-*', self.open)
        self.assertNotIn('Remove-Item', self.open)


if __name__ == '__main__':
    unittest.main()
