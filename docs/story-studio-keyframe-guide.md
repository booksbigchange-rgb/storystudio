# StoryStudio Pose Keyframes — Milestone 2

## What this adds
StoryStudio now supports manually placed **character position + size** keyframes in each scene. The 2D renderer uses the same deterministic interpolation in browser previews and MP4 exports.

## Use in the Windows editor
1. In **Your Scenes**, select the scene you want to animate.
2. In the timeline, click at the moment you want to add a pose.
3. Open **Character**, enter Position (0.2–0.7) and Size (0.6–1.25).
4. Click **◆ Set pose**. A diamond appears near the bottom of the timeline.
5. Repeat at a later time with a different position and size.
6. Use **Refresh frame** or **Play live preview** to inspect the animation, then export.
7. To delete a keyframe, move the playhead onto or near its diamond and click **Remove ◆**.

A scene can have up to **12 pose keyframes**, with timestamps measured from the beginning of that scene. Frames interpolate smoothly using Lemo-style easing. Current motion presets (walk, wave, jump, talk, idle) remain available. Scenes without pose keyframes retain their previous behavior.

## Data format
Keyframes are optional in existing **version 2** StoryStudio project JSON:

```json
{
  "keyframes": [
    {"t": 0, "x": 0.2, "size": 0.7},
    {"t": 4, "x": 0.45, "size": 1.0},
    {"t": 8, "x": 0.7, "size": 1.2}
  ]
}
```

Each keyframe must contain exactly `t`, `x`, and `size`. Times must be strictly increasing and within the scene's duration. Shortening a scene below its last keyframe is rejected safely rather than silently discarding poses.

## Scope and caveats
- This controls character **horizontal position and size**, not skeletal joint poses, camera paths, or hand-drawn imported artworks.
- The current numeric controls are precise but not yet draggable directly on the visual stage.
- Saved JSON remains backward-compatible with older version 2 scenes, but opening a newer project in an old build may not preserve its animation when edited.
- For the initial 'story' motion preset, the character still starts off-screen; early keyframes may be less visible before the entrance completes.
- The new Windows build should be tested with GitHub Actions and a real laptop before being merged into main.

## Regression gates
- Legacy projects without keyframes load unchanged.
- Optional tracks validate time, bounds, ordering, size and non-mutation.
- Saved projects keep keyframes.
- Browser frames at different times produce distinct positions/sizes; seeking back is deterministic.
- Existing landscape/portrait MP4, audio and cancellation regression gates stay in place.
- A real Tk GUI regression clicks keyframe controls and saves/reloads a project.
