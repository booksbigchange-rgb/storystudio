# Mixed export cancellation — 17 October 2026

In **Shared timeline**, click **Cancel export** while a render is running.
The editor restores its controls after stopping the export. You can change the
timeline or immediately start another export. Closing still waits for the export
to finish or cancel, so an active export cannot be abandoned by closing its window.

Every command runs inside a dedicated Windows Job Object. A small launch gate
waits until job assignment succeeds before starting renderer/browser/FFmpeg
children. Cancellation closes that job, stopping only its owned process tree.
It never kills all Python, browser or FFmpeg processes by name. Job assignment
failure aborts the command before its child renderer starts.

Cancellation and final publication use the same lock: cancel before publication
leaves no final MP4; cancel after successful publication keeps the verified file.
Existing outputs remain protected by atomic no-overwrite publication. Diagnostic
intermediates stay in the run's `exports/mixed-run-*` folder, including incomplete
section files after cancellation. Automatic disk cleanup remains separate work.

## Automated checks

- Three additional unit tests exercise command results/failures, a real child and
  grandchild process tree, an unrelated process that must survive, and cancellation
  at the publication boundary. The full local unified unit suite has 64 tests.
- `Verify-Mixed-Cancel.cmd` waits for actual encoder staging bytes, invokes the
  real Tk Cancel button, verifies no published output/source changes, then exports
  a short verified MP4 from the same editor to prove recovery.
- `Verify-Timed-Titles.cmd` reruns both engines/orientations, title boundaries,
  full decoding, persistence and no-overwrite checks with the new controller.
- Windows Actions includes the real cancellation/retry suite and publishes its
  evidence with the existing unified validation artifact.
- The one-second retry exposed millisecond timestamp rounding in the old MKV
  intermediates. MOV intermediates now use a 24,000-tick video timescale while
  retaining PCM audio; the strict 24 fps verification remains unchanged.

This is the unified Windows source app. The previous portable cartoon executable
is unchanged. Manual usability and another physical computer remain separate
from local automated tests and the hosted Windows runner.
