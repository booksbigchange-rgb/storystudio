"""Cancelable commands with a Windows job owning the complete export process tree."""
import ctypes
import os
import signal
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys
from render_control import RenderControl, RenderCancelled


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ('ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class BASIC_LIMIT(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]


class EXTENDED_LIMIT(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', BASIC_LIMIT), ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


class ProcessJob:
    def __init__(self, process):
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = EXTENDED_LIMIT()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        try:
            if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
                raise ctypes.WinError(ctypes.get_last_error())
        except Exception:
            self.close()
            raise

    def peak(self):
        """Peak committed bytes of every process this step started (0 if unavailable)."""
        try:
            limits = EXTENDED_LIMIT()
            self.api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
            if self.api.QueryInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits), None):
                return int(limits.PeakJobMemoryUsed)
        except (OSError, AttributeError):
            pass
        return 0

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


class MixedControl(RenderControl):
    peak_bytes = 0  # largest memory use of any single export step, for endurance reporting

    def run(self, command, log):
        self.check()
        if os.name != 'nt':
            return self.run_posix(command, log)
        gate = Path(__file__).with_name('export_gate.py')
        # A Windows venv executable is itself a launcher that may spawn its real
        # interpreter before job assignment. Start the base interpreter directly
        # for this stdlib-only gate; the requested worker still uses its venv.
        interpreter = getattr(sys, '_base_executable', sys.executable)
        process = subprocess.Popen([interpreter, str(gate), *map(str, command)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
        job = None
        try:
            job = ProcessJob(process)
            self.check()
            first = True
            while True:
                try:
                    stdout, stderr = process.communicate(input='START\n' if first else None, timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    first = False
                    if self.event.is_set():
                        job.close()
                        stdout, stderr = process.communicate(timeout=5)
                        with Path(log).open('a', encoding='utf-8') as handle:
                            handle.write(stdout+stderr+'\nCanceled export process tree.\n')
                        self.check()
            self.peak_bytes = max(self.peak_bytes, job.peak())
            with Path(log).open('a', encoding='utf-8') as handle:
                handle.write(stdout+stderr+'\n')
            self.check()
            if process.returncode:
                raise RuntimeError(f'Export step failed. See {log}\n'+(stderr or stdout)[-800:])
            return stdout
        finally:
            if job:
                job.close()
            if process.poll() is None:
                process.kill()
            process.communicate()

    def run_posix(self, command, log):
        """Development fallback: one process group per step, killed as a whole on cancel."""
        process = subprocess.Popen(list(map(str, command)), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                                   start_new_session=True)
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    if self.event.is_set():
                        os.killpg(process.pid, signal.SIGKILL)
                        stdout, stderr = process.communicate(timeout=5)
                        with Path(log).open('a', encoding='utf-8') as handle:
                            handle.write(stdout+stderr+'\nCanceled export process tree.\n')
                        self.check()
            import resource
            self.peak_bytes = max(self.peak_bytes, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024)
            with Path(log).open('a', encoding='utf-8') as handle:
                handle.write(stdout+stderr+'\n')
            self.check()
            if process.returncode:
                raise RuntimeError(f'Export step failed. See {log}\n'+(stderr or stdout)[-800:])
            return stdout
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
