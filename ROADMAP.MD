# Minimal-To-Do — Roadmap & Next Iterations

All future features must preserve the core philosophy: **zero external heavy runtimes, zero background polling loops, and minimal RAM footprint.**

## Iteration 2: Quality-of-Life & Ergonomics
- [ ] **Collapsible "Shade" Mode:** Double-clicking the header collapses the window down to just the 38px header bar (`TASKS • 3/5`), freeing up desktop space while keeping the counter visible.
- [ ] **Fixing Issues** The window does not appear in the taskbar, altough it appears in tray, but if clicked on it, the app is closed, so if clicked on the app icon in the tray the app should launch or if it is running, then it should come forward on the screen and if right clicked the app icon in the tray, it should give the option to close, so no taskbar is needed.
- [ ] **Inline Task Editing:** Double-clicking an existing task's text swaps the label for an `Entry` widget to edit typos in place and save on `<Return>` or `<FocusOut>`.
- [ ] **Clear Completed Button:** A subtle button in the header or footer to bulk-delete all checked tasks in a single click.
- [ ] **Drag-to-Resize Grip:** A small bottom-right corner grip allowing custom window height/width adjustments (persisted in `settings`). 

## Iteration 3: Task Organization & Keyboard Workflow
- [ ] **Priority Tagging:** Support `!high`, `!med`, or color-coded left-border accents on task rows to visually separate urgent items.
- [ ] **Subtask Section:** Add subtasks that are collapsible into the main task and other main task features.
- [ ] **Drag-and-Drop Reordering:** Allow manual ordering of active tasks via mouse drag (`sort_order` column in SQLite).
- [ ] **Global Hotkey Toggle:** Register a lightweight Windows hotkey (via `ctypes.windll.user32.RegisterHotKey`) such as `Win + Shift + T` to summon/focus the input bar from anywhere without touching the mouse.
- [ ] **Keyboard Navigation:** Use Up/Down arrow keys to highlight tasks, `Space` to toggle, and `Delete` to remove.

## Iteration 4: Lifecycle & Packaging
- [ ] **Daily Reset / Recurring Tasks:** Option to mark daily routine tasks that automatically uncheck themselves on the first launch of a new calendar day.
- [ ] **Undo Last Delete:** Keep the last deleted task in memory for 5 seconds with a `Ctrl+Z` binding to restore accidental deletions.
- [ ] **Standalone Executable:** Package with PyInstaller (`--noconsole --onefile`) and a custom `.ico` file for zero-terminal startup.