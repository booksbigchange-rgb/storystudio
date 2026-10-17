# Layer motion keys — 17 October 2026

In the documentary editor, open **Layers**, select artwork, then **Motion keys…**.
Enter a time percentage strictly between 0 and 100. **Sample pose here** fills the
fields from the current animation. Change X/Y, size, angle or opacity, then use
**Add key** or select a listed key and **Update key**. **Remove key** deletes only
the selected interior pose. **Preview** shows stored keys at the entered time;
add/update field edits before previewing them.

Click **Apply keys**, then **Apply to scene** in the parent layer window. The entire
layer edit is one undo/redo step. Cancel at either level preserves the appropriate
parent state. The start/end poses remain in the existing layer window.

Each layer supports up to 16 ordered interior keys. Times are fractions of scene
duration, so changing a scene's duration scales its motion timing. Position, size,
angle and opacity interpolate between adjacent poses using the layer's easing.
Seeking is deterministic. There is no new playback clock or separate export path:
preview and rendering both use the same compositor. Motion presets adjust the
start/end poses and preserve interior keys.

Keys persist in each version-5 layer's optional `keyframes` list as `t` and `pose`.
Existing endpoint-only projects retain their previous motion. Use the current
unified source app for these projects; older builds may discard the new field.
Imported rigging, per-key easing, anchor editing, masks and camera-linked depth
remain later work. This milestone does not implement those separate controls.

## Automated validation

- 69 unified unit tests passed locally, including direction reversal, seek
  consistency, exact key poses, invalid/duplicate/unordered times and preset
  preservation. The workflow also runs the 12 character tests.
- `Verify-Layer-Keys.cmd` exercises real Tk Add/Update/Remove, preview, cancel,
  Apply, parent undo/redo and JSON save/reopen.
- Actual two-second widescreen and portrait MP4s pass strict dimensions, 24 fps,
  48-frame count, audio-span and full-decoding checks.
- Five decoded frames per orientation match the compositor within the test's
  mean RGB-error threshold of 5/255. Observed local errors were 1.36–1.44/255.
- The motion-key window screenshot was inspected; key controls and Apply remain
  visible. Automated checks remain distinct from manual usability acceptance.

The existing portable cartoon executable is unchanged. Open the unified source
application with `Open-StoryStudio-Unified.cmd` for this feature.
