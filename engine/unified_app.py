"""Entry point of the unified portable build: hub, documentary and shared-timeline editors."""
import sys
import runtime


def main():
    if runtime.FROZEN:
        runtime.prepare_environment()
    if '--self-test' in sys.argv:
        import frozen_selftest
        return frozen_selftest.run(sys.argv)
    import studio_hub
    studio_hub.main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
