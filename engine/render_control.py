"""Cooperative cancellation scoped to one export and its owned child process."""
import subprocess
import threading


class RenderCancelled(Exception):
    pass


class RenderControl:
    def __init__(self):
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.published = False

    def cancel(self):
        with self.lock:
            if not self.published:
                self.event.set()

    def check(self):
        if self.event.is_set():
            raise RenderCancelled('Export canceled; no MP4 was published.')

    def run(self, command):
        self.check()
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    if self.event.is_set():
                        process.terminate()
                        try:
                            process.communicate(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        except OSError:
                            pass  # The owned encoder may have exited between poll and terminate.
                            process.communicate()
                        self.check()
            self.check()
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def publish(self, staged, output):
        import os
        with self.lock:
            self.check()
            os.link(staged, output)
            self.published = True

    def run_frames(self, command, frames, error_log):
        """Stream RGB frames without storing thousands of intermediate PNGs."""
        self.check()
        stopped = threading.Event()
        with open(error_log, 'w+b') as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                       stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            def monitor():
                while not stopped.wait(.1):
                    if self.event.is_set() and process.poll() is None:
                        try:
                            process.terminate()
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        return
            watcher = threading.Thread(target=monitor, daemon=True)
            watcher.start()
            try:
                try:
                    for frame in frames:
                        self.check()
                        process.stdin.write(frame)
                    process.stdin.close()
                    code = process.wait()
                except (BrokenPipeError, OSError):
                    self.check()
                    log.seek(0)
                    raise RuntimeError(log.read().decode('utf-8', errors='replace')[-1500:] or 'Layer encoder stopped')
                self.check()
                if code:
                    log.seek(0)
                    raise RuntimeError(log.read().decode('utf-8', errors='replace')[-1500:] or 'Layer encoding failed')
            finally:
                stopped.set()
                if process.poll() is None:
                    process.kill()
                process.wait()
                if not process.stdin.closed:
                    try:
                        process.stdin.close()
                    except BrokenPipeError:
                        pass
                watcher.join(timeout=4)
