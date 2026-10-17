"""Actual owned-process cancellation and publication boundary tests on Windows."""
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine'))
from mixed_control import MixedControl, RenderCancelled


class CancellationTests(unittest.TestCase):
    def test_command_output_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            control = MixedControl()
            log = Path(folder)/'log.txt'
            self.assertEqual(control.run([sys.executable, '-c', "print('hello')"], log).strip(), 'hello')
            with self.assertRaises(RuntimeError):
                control.run([sys.executable, '-c', 'raise SystemExit(7)'], log)

    def test_cancel_kills_descendants_not_unrelated_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            child = root/'child.py'
            child.write_text("from pathlib import Path\nimport time\nPath(__file__).with_suffix('.ready').touch()\ntime.sleep(3)\nPath(__file__).with_suffix('.escaped').touch()\n")
            parent = root/'parent.py'
            parent.write_text("import subprocess,sys,time\nsubprocess.Popen([sys.executable,sys.argv[1]])\ntime.sleep(30)\n")
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
            control = MixedControl()
            errors = []
            def worker():
                try: control.run([sys.executable,str(parent),str(child)], root/'log.txt')
                except Exception as exc: errors.append(exc)
            thread = threading.Thread(target=worker)
            thread.start()
            try:
                deadline = time.monotonic()+10
                while not child.with_suffix('.ready').exists() and time.monotonic()<deadline:
                    time.sleep(.05)
                self.assertTrue(child.with_suffix('.ready').exists())
                control.cancel(); thread.join(6)
                self.assertFalse(thread.is_alive())
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], RenderCancelled)
                self.assertIsNone(unrelated.poll())
                time.sleep(3.2)
                self.assertFalse(child.with_suffix('.escaped').exists())
            finally:
                control.cancel(); thread.join(6)
                unrelated.kill(); unrelated.wait()

    def test_cancellation_and_publication_are_serialized(self):
        with tempfile.TemporaryDirectory() as folder:
            staged, output = Path(folder)/'staged', Path(folder)/'output'
            staged.write_bytes(b'verified')
            control = MixedControl(); control.cancel()
            with self.assertRaises(RenderCancelled): control.publish(staged, output)
            self.assertFalse(output.exists())
            control = MixedControl(); control.publish(staged, output); control.cancel()
            control.check()
            self.assertEqual(output.read_bytes(), b'verified')


if __name__ == '__main__': unittest.main()
