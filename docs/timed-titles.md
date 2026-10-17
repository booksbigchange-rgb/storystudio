# Shared timed titles — 16 October 2026

Run `Open-StoryStudio-Unified.cmd`, choose **Shared timeline**, then **Timed text**.
Choose Title, Date, Source or Caption; enter text and start/end seconds; click
**Add** (or select an existing item and **Update**), then **Apply to timeline**.
Save the timeline to retain the changes. Cancel discards the dialog's edits.

Times use the whole shared timeline, not the selected section. A title can span
a documentary/character boundary. Reordering sections does not move these times.
The end time is exclusive and times snap to the nearest 24 fps frame during export.
Titles/dates use the top position; sources/captions use the bottom. Same-position
items cannot overlap. Up to 32 items, each with 240 characters, are supported.
Export rejects text extending past the current story duration before rendering.

The neutral-background preview shows the actual card layout for the selected
output format. It is not live footage playback. Text is rasterized with the local
Windows Segoe UI font into small transparent cards; literal punctuation is never
interpreted as FFmpeg commands. Font coverage depends on that installed font;
automatic transcription, translation, custom fonts and subtitle-file import are
not included. Text may wrap across words at the available width.

Existing timelines without `titles` continue to load and export. Titles are an
optional field in the shared timeline version-1 document. Older application builds
do not render this new field; use this source build when editing these timelines.
Neither linked project format is converted or overwritten. Shared exports remain
720p/24fps H.264/AAC, fully verified before atomic no-overwrite publication.

## Verification

- 61 unified/editor unit tests and 12 character unit tests passed locally.
- `Verify-Timed-Titles.cmd` runs real Tk controls and actual documentary/character
  exports using self-contained synthetic fixtures, with no user media needed.
- Acceptance checks add/update/remove/cancel/preview/save, relative persistence,
  source hashes, existing-output protection and rejection of out-of-range titles.
- Both output orientations are fully decoded. Pixel checks examine the exact
  start/end frames and the engine boundary; plain exports without titles also run.
- Boundary tests caught and repaired a one-frame title offset and a filter reset
  caused by differing section color metadata. Sections now normalize to BT.709.
- `.github/workflows/story-studio-unified.yml` runs unit and real GUI/MP4 checks
  on Windows and uploads videos, reports, screenshots and dependency provenance.
- Windows run [38947861109](https://github.com/booksbigchange-rgb/storystudio/actions/runs/38947861109)
  passed on commit `644dfaf`: all 73 unit tests and real GUI/MP4 acceptance.
  The first run exposed two older test fixtures comparing Windows short paths
  with expanded paths; fixture normalization repaired them without changing
  project storage behavior.
- Local acceptance: `exports/titles-acceptance-1158900de8a0421790d1de4e14ccc250/`.
  Local evidence ZIP: `exports/story-studio-timed-titles-validation.zip`.
  Downloaded Windows evidence: `exports/titles-windows-644dfaf/`.
- Draft review: [PR #7](https://github.com/booksbigchange-rgb/storystudio/pull/7),
  stacked on the portable feature branch. No merge into main.

The existing packaged cartoon EXE is unchanged; this feature belongs to the
source unified app. A combined portable executable, live mixed playback,
crossfades and shared mixing remain separate work. Mixed-export cancellation is
implemented separately; see `mixed-export-cancellation.md` for its validation.
Automated checks do not establish manual listening or usability acceptance.
