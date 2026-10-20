# Character animation keys and reusable presets

Scope: the character editor (`Open-StoryStudio-Unified.cmd` → Cartoon character, or the same code in the
character workspace). The three built-in cutout characters (fox, rabbit, bear) are drawn procedurally.
**This is not painterly rigging.** There is no custom artwork import, layered puppet or bone editor; that
would need layered artwork and a real rig, which do not exist in this project.

## New: Animate tab (per-scene 2D keyframes)

Up to 8 keys per scene. Each key has a **time** (% of that scene) and any of:

| Setting | Range | Behavior |
|---|---|---|
| Position (x) | 0.2–0.7 | eased between keys |
| Size | 0.6–1.25 | eased |
| Lift | −150…150 | vertical offset in canvas units, positive is up; eased |
| Tilt | −0.6…0.6 rad | rotation about the feet; eased |
| Expression | happy/curious/sad/surprised | switches at the key |
| Motion | story/idle/wave/walk/jump/talk | switches at the key |

Rules: keys must be in increasing time order, a key must change something, blanks keep the scene value, and a
setting holds its first/last key value before/after its keys. Easing is a smoothstep (no overshoot). Selecting a key
scrubs the preview to that moment. Scenes with no keys render exactly as before; projects stay `version 2` and old
projects open unchanged (the `keys` list is optional). Editing a scene's caption/length/backdrop keeps its keys and
duplicating a scene copies them.

## New: Presets tab (reusable characters)

A preset stores character, expression, motion, position, size, speed and animation keys under a name
(≤ 40 characters, ≤ 50 presets) in `projects/character-presets.json` (your projects folder is never cleaned).
**Apply preset** changes only those fields; caption, length and backdrop are kept. Saving over an existing name asks
first; declining leaves the library byte-identical. Library writes are atomic.

## Verification

- `integrations/lemo-lite/tests/test_keys.py`: validation (17 bad forms), interpolation, no mutation, presets
  (limits, atomic failure, no silent replace, corrupt library).
- `tests/cartoon_keys_integration.py`: real browser. JavaScript and Python agree at 49 times in both orientations;
  neutral keys give a byte-identical frame; lift/tilt/size change pixels and lift moves exactly 80 units; a real
  2-second 720p MP4 is verified (H.264/AAC, frame count, duration, full decode) and the fox's decoded position
  travels left→right; a keyed character section also exports inside a mixed timeline.
- `tests/cartoon_keys_gui_integration.py`: real Tk, both laptop sizes, add/update/remove/select, invalid input,
  save/open, duplicate, presets save/decline/apply/delete.
- Run on Windows with `Verify-Character-Keys.cmd`.

Not verified automatically: how the motion *feels*. Watch an exported clip on your computer.
