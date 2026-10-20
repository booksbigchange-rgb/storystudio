"""Console executable for character export workers and MP4 verification (never shown to users)."""
import os
import sys

import project  # noqa: F401  (bundled so the shared worker finds the character project model)
import renderer  # noqa: F401


def main():
    home = os.environ.get('STORYSTUDIO_HOME')
    if home:
        os.environ.setdefault('STORYSTUDIO_TEMP', os.path.join(home, 'temp'))
    import mixed_worker
    mixed_worker.main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
