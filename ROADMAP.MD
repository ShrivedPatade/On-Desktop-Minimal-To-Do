# Minimal-To-Do — Roadmap & Iteration Log

All features adhere to the core engineering constraints: **Python standard library only, zero background polling loops, and minimal RAM footprint (~20 MB).**

## Iteration 1: Core Architecture & Desktop Widget Shell (Completed)
- [x] **Zero-Dependency Stack:** Built with `tkinter`, `sqlite3` (WAL mode), and `ctypes`.
- [x] **Borderless Rounded Window:** Chroma-keyed rounded canvas shell with High-DPI scaling and `0.85` alpha transparency.
- [x] **Window Persistence:** Saves `win_x`, `win_y`, and `is_pinned` state in SQLite on drag release.
- [x] **Differential UI Rendering:** In-place widget updates to eliminate full-canvas refresh blips.

## Iteration 2: Quality-of-Life & Ergonomics (Completed)
- [x] **Collapsible "Shade" Mode:** Double-clicking the header collapses the window down to the 38px header pill (`TASKS • 3/5`) and restores height when double-clicked again.
- [x] **Isolated System Tray Integration:** Dedicated Win32 message window in the taskbar tray (`^`). Left-click raises the widget; right-click opens the quick action menu.
- [x] **Inline Task Editing:** Double-clicking a task or subtask swaps the label for an inline `Entry` widget (`Return` or `FocusOut` saves, `Escape` cancels).
- [x] **Clear Completed Button:** Footer action (`Clear done (N)`) to bulk-delete all checked tasks and subtasks in a single click.
- [x] **Drag-to-Resize Grip:** Bottom-right corner grip (`⌟`) for custom width/height adjustments persisted in `settings`.

## Iteration 3: Task Organization & Keyboard Workflow (Completed)
- [x] **Priority Tagging:** Supports `!high` (`!h`), `!med` (`!m`), and `!low` (`!l`) tags and clickable 4px left-border accents.
- [x] **Collapsible Subtasks:** Indented subtask drawer per main task with inline creation (`+`) and collapse/expand progress badge (`▾ 1/2`).
- [x] **Drag-and-Drop Reordering:** Manual ordering of tasks via the `⋮⋮` drag handle, persisted to `sort_order` in SQLite.
- [x] **Global Hotkey Toggle:** System-wide `Ctrl + Shift + Y` shortcut via `RegisterHotKey` to unshade, raise, and focus the input bar from anywhere.
- [x] **Keyboard Navigation:** Full `Up`/`Down` selection, `Space` toggle, `Delete` remove, `p` priority cycle, `s` subtask add, `e`/`F2` inline edit, and `/` input focus.

## Iteration 4: Lifecycle & Packaging (Completed)
- [x] **Daily Reset / Recurring Tasks:** Mark daily routine tasks via `!daily` (`!d`), clicking the `↻` icon, or pressing `r`. Daily tasks (and their subtasks) automatically uncheck themselves on the first launch of a new calendar day.
- [x] **Undo Last Delete (`Ctrl + Z`):** Keeps an in-memory snapshot stack of deleted tasks and their subtasks so pressing `Ctrl + Z` restores accidental deletions back into SQLite.
- [x] **Standalone Executable:** Packaged via PyInstaller (`--noconsole --onefile`) with custom `assets/logo.ico` bundling.