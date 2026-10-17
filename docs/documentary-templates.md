# Documentary templates — 17 October 2026

Open `Open-StoryStudio-Unified.cmd` → **Documentary templates**.

1. Choose Evidence desk, Chronology or Map focus, plus widescreen or portrait.
2. Enter a title, source/credit and your notes. Chronology accepts 1–4 lines in
   `date | event description` format and retains your order; it does not sort dates.
3. For evidence/map templates, choose your own image. Map focus uses an X/Y point
   from 0 to 1 across/down the displayed image; it does not geocode locations.
4. Choose 1–30 seconds, then **Create new project**. Review its rendered preview.
5. **Open generated project** opens the existing documentary editor. Layer position,
   size, opacity and motion remain editable there. Add the saved project to a shared
   timeline for mixed-engine export, timed titles or narration in its source editor.

Each creation writes a unique `projects/documentary-<id>/` directory with ordinary
version-5 `story.json`, separate PNG layers, a local orientation-correct copy of the
selected image, and `template.json` inputs. Originals and existing project folders
are not overwritten. **Load template inputs** loads that JSON; editing its fields
and creating again produces a separate version.

Template text is rasterized into individual layer images, using the installed
Segoe UI font. To change its wording, reload the inputs and create a new version;
the documentary layer editor is not a rich-text editor. Notes/events/markers use a
restrained opacity reveal. These are one-scene visual starters, not complete stories.
Source credit is entered by the user and is not independently fact-checked.

Evidence and map images fit without stretching or cropping, with padding where
needed. Inputs are limited to 50 MB and 25 megapixels. No map service, AI generation,
new model, paid account or network request is needed. No soundtrack is added.
The example exports use synthetic diagrams and silent audio; they do not claim
to be factual maps or narrated documentaries. Advanced route animation, map data,
automatic fact research and multilingual font coverage remain outside this milestone.

## Automated validation

- 67 unified unit tests passed locally, including six layout/format combinations,
  new-version generation from saved inputs, validation and source preservation.
- `Verify-Documentary-Templates.cmd` uses actual Tk create/load controls and opens
  generated-project dispatch (the launch callback is recorded in this test).
- It renders all three layer projects in both formats through the real shared
  export pipeline, verifies MP4 dimensions/frame count/audio/full decode, and
  checks three distinct nonblank decoded sections per video.
- A screenshot caught footer controls outside the visible window. The fixed footer
  reserves their space, and GUI tests assert Create/Open remain visible.
- Preview and decoded map frames are visually inspected. This remains separate
  from manual usability testing or testing another physical computer.

The feature belongs to the unified source application. The previous packaged
cartoon EXE is unchanged; combined Windows packaging remains a later milestone.

## Completed validation

Application commit `dc4f212` passed [Windows run 39029378951](https://github.com/booksbigchange-rgb/storystudio/actions/runs/39029378951):
all 79 unit tests, real template GUI/export tests, existing timed-text exports and
cancellation/retry checks. The final template acceptance also passed locally.

- Local evidence: `exports/templates-acceptance-224119b4858441c3b0205e7376e5603b/`.
- Local downloadable package: `exports/documentary-templates-validation-dc4f212.zip`.
- [Windows evidence artifact](https://github.com/booksbigchange-rgb/storystudio/actions/runs/39029378951/artifacts/12099309208)
  expires 31 October 2026 at 14:38 EAT.
- Feature branch: `feature/unified-story-studio`; draft PR #7; main untouched.
