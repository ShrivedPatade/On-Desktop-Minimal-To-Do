# Minimal-To-Do — Architecture & File Guide (Iteration 1)

A lightweight, zero-dependency desktop to-do list widget built with Python's standard library (`tkinter` + `sqlite3`). Designed for near-zero idle CPU usage and minimal RAM (~20 MB).

## Color Palette
| Token | Hex | Role |
| :--- | :--- | :--- |
| `bg_main` | `#4B3B47` | Main window & list background |
| `bg_surface` | `#6A6262` | Header bar, input box, subtle borders/dividers |
| `text_muted` | `#9C9990` | Completed tasks, placeholder text, inactive icons |
| `accent` | `#CFD2B2` | Active pin state, checkmarks, `+` button, focus ring |
| `text_primary` | `#E0D8DE` | High-contrast active task text and titles |

---

## File-by-File Breakdown

### 1. `config.py`
* **Role:** Single source of truth for UI constants.
* **Work Done:** Stores the 5-color palette (`PALETTE`), default window dimensions (`340x500`), window transparency (`0.96`), and `Segoe UI` font definitions.

### 2. `db.py`
* **Role:** SQLite persistence engine (`data/tasks.db`).
* **Work Done:**
  * Configures SQLite with `WAL` (Write-Ahead Logging) mode for fast, non-blocking disk writes.
  * Manages the `tasks` table (`id`, `content`, `is_completed`, `created_at`) with CRUD helpers.
  * Manages the `settings` key-value table (`win_x`, `win_y`, `is_pinned`) so window placement persists across restarts.

### 3. `ui/window.py`
* **Role:** Frameless desktop widget shell (`DesktopTodoWindow`).
* **Work Done:**
  * Strips native OS window borders via `overrideredirect(True)` and enables Windows High-DPI scaling (`SetProcessDpiAwareness`).
  * Uses `ctypes` (`WS_EX_APPWINDOW`) so the frameless window still appears in the Windows Taskbar and `Alt + Tab`.
  * Implements delta-based window dragging on the header and fires `on_geometry_change` only on `<ButtonRelease-1>` to avoid disk I/O during movement.
  * Clamps startup coordinates so the window never spawns off-screen.
  * Includes a `SIGINT` polling hook so `Ctrl+C` in the terminal exits cleanly.

### 4. `ui/task_list.py`
* **Role:** Task components (`TaskInput`, `TaskItem`, `TaskContainer`).
* **Work Done:**
  * `TaskInput`: Entry bar with focus border highlighting, placeholder behavior, and `<Return>` submission.
  * `TaskItem`: Individual task row with full-row click-to-toggle, overstrike styling on completion, and hover-revealed delete button.
  * `TaskContainer`: Scrollable `tk.Canvas` wrapper bound to `<MouseWheel>` that only scrolls when tasks overflow the viewport.

### 5. `main.py`
* **Role:** Application controller (`TodoApp`) and entry point.
* **Work Done:**
  * Initializes the database, reads saved coordinates and pin status, mounts `TaskInput` and `TaskContainer` inside `DesktopTodoWindow`, and updates the `TASKS • X/Y` counter badge in the header.