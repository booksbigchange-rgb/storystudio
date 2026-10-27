"""Console executable for documentary export workers and the process gate (never shown to users)."""
import sys
import runtime


def main():
    runtime.prepare_environment()
    if len(sys.argv) > 1 and sys.argv[1] == '--gate':
        import export_gate
        return export_gate.main(sys.argv[2:])
    import mixed_worker
    mixed_worker.main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
