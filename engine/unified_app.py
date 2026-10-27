"""Entry point of the unified portable build: hub, documentary and shared-timeline editors."""
import sys
import runtime


def main():
    if runtime.FROZEN:
        runtime.prepare_environment()
    if '--self-test' in sys.argv:
        import frozen_selftest
        return frozen_selftest.run(sys.argv)
    if '--gui-test' in sys.argv:
        from pathlib import Path
        if not runtime.FROZEN:
            sys.path.insert(0, str(runtime.app_root(__file__)/'integrations/lemo-lite'))
        import gui_regression
        gui_regression.run(Path(sys.argv[sys.argv.index('--output')+1]))
        return 0
    import studio_hub
    studio_hub.main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
