# Minimal-To-Do — Architecture & File Guide (Iterations 1–3)

A low-resource, zero-dependency desktop to-do list widget built strictly with Python's standard library (`tkinter`, `sqlite3`, `ctypes`). Engineered for ~0.0% idle CPU consumption and a ~20 MB RAM footprint.

---

## Color Palette & Visual Tokens

| Token | Hex | Role |
| :--- | :--- | :--- |
| `chroma_key` | `#010102` | Transparent corner mask color for borderless rounded geometry |
| `bg_main` | `#E5E5E5` | Main window & task list background (`0.85` alpha transparency) |
| `bg_surface` | `#D4D6DC` | Header bar, Shade Mode pill, and 1px row dividers |
| `bg_selected` | `#D8DCE6` | Keyboard-selected task highlight tint |
| `bg_drag` | `#CFD5E2` | Active row highlight while drag-reordering |
| `bg_input` | `#F2F2F4` | Rounded task input pill & inline edit fields |
| `border_faint` | `#C8CAD0` | 1px subtle border for input pill, `+` button ring, and subtask guide |
| `accent` | `#14213D` | Deep Navy — active pins, checkmarks, header logo, and focus border |
| `text_primary` | `#000000` | Pure Black — primary active task and subtask text |
| `text_muted` | `#6E7382` | Completed task overstrike text, counters, and placeholders |
| `priority_high` | `#C94A4A` | Crimson — High priority (`!high` / `!h`) 4px left accent bar & delete hover |
| `priority_med` | `#D97706` | Amber — Medium priority (`!med` / `!m`) 4px left accent bar |
| `priority_none` | `#C8CAD0` | Subtle Gray — Normal priority (`!low` / `!l`) 4px left accent bar |

---

## File-by-File Breakdown

### 1. `config.py`
* **Role:** Central configuration, geometry utilities, and asset bootstrap.
* **Key Responsibilities:**
  * **Build-Safe Path Resolution:** Distinguishes `APP_DIR` (executable directory for persistent `data/tasks.db`) from `BUNDLE_DIR` (PyInstaller `_MEIPASS` temp directory for bundled `assets/logo.ico`).
  * **UI & Layout Metrics:** Defines default and minimum window dimensions (`350x520`, min `280x250`), `HEADER_HEIGHT` (`38px`), `FOOTER_HEIGHT` (`28px`), and `WINDOW_ALPHA` (`0.85`).
  * **`parse_priority_tag()`:** Regex parser that strips `!high` (`!h`), `!med` (`!m`), or `!low` (`!l`) from input strings and returns `(clean_text, priority_int)`.
  * **`draw_rounded_rect()`:** Polygon generator that renders smooth, anti-aliased rounded rectangles and capsules on a Tkinter `Canvas`.
  * **`ensure_logo_ico()`:** Pure-stdlib binary PNG/ICO generator that creates `assets/logo.ico` if no custom icon is present.

### 2. `db.py`
* **Role:** SQLite persistence layer (`data/tasks.db`).
* **Key Responsibilities:**
  * **Low-Overhead Connection:** Enables `PRAGMA journal_mode=WAL` and `synchronous=NORMAL` for non-blocking microsecond reads/writes.
  * **Automatic Schema Migration:** `init_db()` inspects `PRAGMA table_info(tasks)` on launch and non-destructively adds Iteration 3 columns (`priority`, `sort_order`, `parent_id`, `is_expanded`) to existing databases.
  * **Hierarchical Task & Subtask CRUD:**
    * `add_task()`: Inserts main tasks at the top of `sort_order` (`parent_id IS NULL`) or appends subtasks under a parent task (`parent_id = ?`).
    * `get_main_tasks()` & `get_subtasks()`: Queries active items first, ordered by manual `sort_order` and `priority`.
    * `update_tasks_order()`: Batch-updates manual drag-and-drop order in a single transaction via `executemany()`.
    * `delete_task()` & `clear_completed_tasks()`: Cascades deletions to child subtasks and bulk-removes completed items.
  * **Window State Persistence:** Stores `win_x`, `win_y`, `win_w`, `win_h`, `is_pinned`, and `is_shaded` in the `settings` key-value table.

### 3. `ui/window.py`
* **Role:** Frameless desktop widget shell, window ergonomics, and Win32 OS integration (`DesktopTodoWindow`).
* **Key Responsibilities:**
  * **Borderless Rounded Shell:** Uses `overrideredirect(True)` paired with `-transparentcolor` chroma-keying and Windows High-DPI scaling (`SetProcessDpiAwareness(1)`).
  * **Collapsible "Shade" Mode:** Double-clicking the header collapses the widget to a `38px` floating pill (`TASKS • X/Y`) and restores full height when double-clicked again.
  * **Footer Bar (`Clear done` & Resize Grip):** Houses the dynamic `Clear done (N)` bulk-delete action on the bottom-left and a diagonal drag-to-resize grip (`⌟`) on the bottom-right.
  * **Crash-Proof Isolated System Tray:** Creates a dedicated hidden Win32 message window (`WNDCLASSEXW` / `CreateWindowExW`) for `Shell_NotifyIconW` so tray callbacks never collide with Tkinter's internal window handle. Left-click raises the widget to the front; right-click opens the tray menu.
  * **Global Hotkey (`Ctrl + Shift + Y`):** Registers a system-wide hotkey via `user32.RegisterHotKey` that unshades the window, brings it to the foreground, and focuses the input bar from any application.

### 4. `ui/task_list.py`
* **Role:** Interactive task components (`TaskInput`, `TaskItem`, `SubtaskItem`, `TaskContainer`).
* **Key Responsibilities:**
  * **`TaskInput`:** Rounded capsule input bar with focus border highlighting, `<Down>` arrow handoff to the task list, and a circular `+` button drawn with integer-snapped `create_rectangle` bars to prevent GDI line-cap clipping.
  * **`TaskItem`:**
    * **Priority Bar:** 4px left-border accent (`#C94A4A` High, `#D97706` Med, `#C8CAD0` Normal) that cycles priority when clicked.
    * **Drag Handle (`⋮⋮`):** Initiates live mouse drag-and-drop reordering.
    * **Debounced Click vs. Inline Edit:** Single-clicking toggles completion; double-clicking swaps the label for an inline `tk.Entry` editor (`<Return>` / `<FocusOut>` commits, `<Escape>` cancels).
    * **Collapsible Subtask Drawer:** Includes an inline `+` button to add subtasks and a progress badge (`▾ 1/2` or `▸ 1/2`) to collapse or expand child subtasks.
  * **`SubtaskItem`:** Indented subtask row with a vertical guide line, completion toggle, double-click inline editing, and delete button.
  * **`TaskContainer`:** Scrollable canvas that dynamically recalculates text `wraplength` during window resizing and scrolls minimally (`ensure_visible`) during keyboard navigation.

### 5. `main.py`
* **Role:** Application controller (`TodoApp`) and state coordinator.
* **Key Responsibilities:**
  * **Differential UI Rendering (Zero-Blip):** Maintains live widget references in `self.task_widgets` and `self.ordered_ids` so adding, toggling, reordering, or deleting tasks updates only the affected widgets without redrawing the entire list.
  * **Live Drag-and-Drop Reordering:** Tracks cursor Y-coordinates against task midpoints to swap rows in real time and commits `sort_order` to SQLite on mouse release.
  * **Keyboard Navigation Engine:** Binds global window keys while suppressing shortcuts whenever an inline `tk.Entry` is actively focused.

---

## Keyboard Shortcuts Reference

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + Shift + Y` | **Global Hotkey:** Summon widget, unshade if collapsed, and focus input bar |
| `Down` / `Up` | Move selection highlight down or up through tasks (`Up` at top returns to input) |
| `Space` | Toggle completion state of the selected task |
| `e` or `F2` | Inline edit the selected task's text (also supports `!high`, `!med`, `!low` tags) |
| `p` | Cycle priority (`Normal` $\rightarrow$ `Medium` $\rightarrow$ `High`) on the selected task |
| `s` | Open inline subtask input under the selected task |
| `Delete` | Delete the selected task (and its subtasks) and select the adjacent task |
| `/` | Jump focus directly to the `"Add task..."` input bar |
| `Escape` | Cancel inline edit, exit input focus, or clear task selection |

---

## Building the Standalone Executable

Run PyInstaller from the project root to package the widget into a single no-console `.exe`:

```powershell
pyinstaller --noconsole --onefile --name "MinimalToDo" --icon "assets/logo.ico" --add-data "assets/logo.ico;assets" main.py