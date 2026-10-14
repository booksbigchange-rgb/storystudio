# StoryStudio 2D animation branch — first vertical slice

This branch **extends** the Python/Tkinter desktop MVP. The original image-only
scenes, camera keyframes, project version 1 and FFmpeg exporter remain intact.

## New project field (optional)

Existing scenes need no migration. For an animated scene, add transparent PNG
sprite layers under `layers`. Position is the sprite center, normalized to
stage width/height; `width` is the fraction of stage width used by the sprite.

```json
{
  "version": 1,
  "scenes": [{
    "image": "D:/StoryStudio/projects/story/background.png",
    "duration": 2,
    "layers": [{
      "id": "hero",
      "name": "Hero",
      "image": "D:/StoryStudio/projects/story/hero.png",
      "x": 0.2, "y": 0.65, "width": 0.3,
      "keyframes": [
        {"time": 0, "x": 0.2},
        {"time": 2, "x": 0.8, "ease": "smooth"}
      ]
    }]
  }]
}
```

- Animated fields: x, y, scale, rotation (degrees), opacity.
- Easing: linear, smooth or hold.
- A scene without layers uses the original FFmpeg still-image export.
- A scene with layers uses Pillow to compose each frame and streams RGB frames
  directly to FFmpeg without caching large image sequences.
- Preview and new layer export use the same compositing function.
- Camera movement acts on the whole composited scene.
- No character body-part rigs, talking animation, audio integration or full
  keyframe-track editing yet. These are follow-on milestones.

## Verification

```sh
python -m unittest discover -s tests -v
python tests/render_integration.py
python tests/render_layers_integration.py
```

The layered renderer requires Pillow and FFmpeg. CI installs Pillow before the
layered integration test. Actual Windows GUI and high-resolution export still
require testing on the D: drive workstation.

All legacy projects are read as version 1; layers are optional. Do not merge
into main without desktop acceptance tests.

## Desktop controls (first iteration)

1. Open StoryStudio on the **2D branch** using the existing D: launcher.
2. Import a background image and select the scene.
3. Click **Add PNG** under character layers to import transparent character artwork.
4. Select the layer and drag anywhere inside the preview to place its center.
5. Click **Animate right** for a smooth rightward movement. Compare **Start frame** and **End frame**.
6. Save the project, then export MP4 using the existing button.
7. **Clear motion** removes that layer's motion. Changing scene duration retimes its existing keyframes proportionally.

This is a first working control set, not a finished animation UI. Desktop mouse handling and full-resolution playback have not been tested on the user's Windows system. The current preview offers start/end frames rather than continuous playback. Existing silent video exports remain silent; narration mixing and advanced rigging come later.

## Milestone 2 — Timeline, playback and canvas controls

Update the Windows checkout using `git pull --ff-only` while on
`feature/2d-animation`, then open `Open-StoryStudio.cmd`.

- **Canvas:** choose Portrait 9:16 or Landscape 16:9 and **Fit** to
  show the entire original image, or **Fill** to crop it to the stage.
  Press **Apply canvas**. Canvas settings are saved into project JSON
  as an optional top-level `canvas` field; old version-1 files default
  to Portrait 9:16 Fill and remain supported.
- **Play/Pause:** plays the currently selected scene. CPU preview
  approximately 10 FPS, not a realtime 24-FPS guarantee.
  MP4 export continues at 24 FPS.
- **Scrub:** drag the slider or click the scene timeline. Use **-1 frame**
  and **+1 frame** for frame-step navigation.
- **Keyframe editor:** select a character layer, scrub to a point in
  the scene, enter x/y/scale/rotation/opacity, choose easing, and click
  **Set keyframe**. Repeat at a later time to animate.
- **Diamond markers:** click a layer timeline diamond to select an
  existing keyframe; drag left/right to retime it, or click
  **Delete keyframe**. The marker cannot overtake another marker.
- **Drag on preview:** adjusts the selected layer's pose at the
  playhead, preserving other keyframes.
- **Export:** `Export MP4` uses project canvas settings and supports
  both image-only and layered scenes in the same story.

**Current boundaries:** no body-part puppet rig, lip-sync, audio timeline,
undo/redo or advanced path editing yet. Before merging, verify Windows
playback and one Portrait Fit and Landscape Fit MP4 manually.
