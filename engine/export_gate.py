"""Wait until the parent assigns our Windows job before starting any children."""
import subprocess
import sys

def main(argv):
    if sys.stdin.readline().strip() != 'START':
        return 1
    return subprocess.call(argv, stdin=subprocess.DEVNULL)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
