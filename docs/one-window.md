# One-window studio

`Open-StoryStudio-Unified.cmd` (and `StoryStudio.exe` in the portable build) now opens **one window**. The shared
timeline, documentary editor and character editor open as **tabs** of that window, all in one program:

- Sidebar: Shared timeline, Documentary, Character, Documentary templates…, Open project…, Close tab.
- Several tabs of the same kind can be open (for example two character projects).
- **Edit source** in the shared timeline opens that section's project as a new tab instead of another program.
- Shortcuts (Ctrl+S, Ctrl+Z, Ctrl+Y, Ctrl+O, Ctrl+E) act only on the tab you are looking at.
- **Close tab** and closing the window ask each tab about its unsaved work first; declining keeps the tab. A tab with a running
  export says so and stays open. Character tabs stop their background workers before they close.
- The character tab keeps the studio's look (it no longer switches the whole program to its own theme).

Nothing about the editors themselves changed: each still runs exactly as before (they were made to fit in a tab by a small
`Host` frame that answers the window calls they make). Exports still run in separate worker processes.

The earlier launcher (one window per editor) is still available: `Open-StoryStudio-Unified.cmd --classic`.

Verification: `tests/studio_shell_gui_integration.py` (Windows, real Tk) — both launchers start; three workspaces as tabs;
theme unchanged; shortcuts per tab; Edit source and Open project as tabs; real mixed and character exports from inside the
window; close-tab and close-window rules. The portable self-test also opens all three as tabs. Run `Verify-One-Window.cmd`.

Limits: tabs cannot be dragged out into separate windows; live character playback still opens a browser window.
