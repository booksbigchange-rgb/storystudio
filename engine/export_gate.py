"""Wait until the parent assigns our Windows job before starting any children."""
import subprocess
import sys

if __name__ == '__main__':
    if sys.stdin.readline().strip() != 'START':
        raise SystemExit(1)
    raise SystemExit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL))
