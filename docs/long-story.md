# Longer stories in mixed timelines

## Capacity and behavior

- Up to **200 sections** and **60 minutes** per timeline (previously 20 sections / 10 minutes).
  Titles and shared-audio clips may start anywhere inside the hour.
- The section list scrolls and shows each section's frame-exact length and start time; a summary line
  shows `N of 200 sections · total h:mm:ss`. Missing or unreadable sources are marked and excluded from
  the total until fixed. New buttons: **To top**, **To bottom**, **Duplicate**.
- Durations use the exporter's rule (24 fps whole frames: documentary rounds each scene, a character project
  rounds its total), so the on-screen strip, start times and the finished video agree to the frame.
  Durations are cached by file time/size so redrawing a 200-section strip does not re-read every file.
- Section order is the list order. Export tests decode the middle frame of every section and check
  it matches the expected section (also after a seeded shuffle).

## Resource use (Ryzen 3 / 12 GB target)

- One section is rendered in an isolated process at a time; FFmpeg uses 2 threads. Memory does not grow with
  the number of sections. Measured peak for a single export step: see the validation section below.
- Bulky intermediates (`raw-*.mp4`, `section-*.mov`, `joined.mp4`, title PNGs) are deleted when an export
  finishes, fails or is canceled; `render.log`, source snapshots and `result.json` stay in `exports/mixed-run-*`.
  Set `STORYSTUDIO_KEEP_INTERMEDIATES=1` to keep everything for troubleshooting.
- Before rendering, the free space on the working and output drives is compared with a conservative estimate
  (about 3 MB per second plus 300 MB). A clear error is shown instead of failing late.

## Cancellation

Cancel stops the active step's process tree (Windows job object), publishes nothing, removes partial media,
and a new export can start immediately. Tested part-way through a long story.

## Limits

Very long stories take proportionally long to render (about 2 seconds of render time per second of
documentary video on the test machine). Character sections are far slower because each frame is
captured from a browser. Output is not split into chapters.
