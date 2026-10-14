# StoryStudio 2D animation branch — first vertical slice

This branch **extends** the Python/Tkinter desktop MVP. The original image-only
scenes, camera keyframes, project version 1 and FFmpeg exporter remain intact.

## New project field (optional)

Existing scenes need no migration. For an animated scene, add transparent PNG
sprite layers under \`layers\`. Position is the sprite center, normalized to
stage width/height; \`width\` is the fraction of stage width used by the sprite.

\`\`\`json
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
\`\`\`

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

\`\`\`sh
python -m unittest discover -s tests -v
python tests/render_integration.py
python tests/render_layers_integration.py
\`\`\`

The layered renderer requires Pillow and FFmpeg. CI installs Pillow before the
layered integration test. Actual Windows GUI and high-resolution export still
require testing on the D: drive workstation.

All legacy projects are read as version 1; layers are optional. Do not merge
into main without desktop acceptance tests.
