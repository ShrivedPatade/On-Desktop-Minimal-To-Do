# db.py
import sqlite3
from typing import List, Optional
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Creates a connection with row access and WAL mode for low overhead."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    """Initializes tables and migrates schema for Iteration 3 columns."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                is_completed INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                parent_id INTEGER DEFAULT NULL,
                is_expanded INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Auto-migrate existing databases from Iteration 1 & 2
        existing_cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(tasks)").fetchall()
        }
        migrations = [
            ("priority", "INTEGER NOT NULL DEFAULT 0"),
            ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
            ("parent_id", "INTEGER DEFAULT NULL"),
            ("is_expanded", "INTEGER NOT NULL DEFAULT 1"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}")


def add_task(
    content: str, priority: int = 0, parent_id: Optional[int] = None
) -> Optional[sqlite3.Row]:
    """Inserts a new main task or subtask and assigns it the top sort_order."""
    clean_text = content.strip()
    if not clean_text:
        return None
    with get_connection() as conn:
        if parent_id is None:
            # Place new main tasks at the top of the manual order
            min_row = conn.execute(
                "SELECT COALESCE(MIN(sort_order), 0) AS min_order FROM tasks WHERE parent_id IS NULL"
            ).fetchone()
            next_order = (min_row["min_order"] if min_row else 0) - 1
        else:
            max_row = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM tasks WHERE parent_id = ?",
                (parent_id,),
            ).fetchone()
            next_order = (max_row["max_order"] if max_row else 0) + 1

        cursor = conn.execute(
            """
            INSERT INTO tasks (content, is_completed, priority, sort_order, parent_id, is_expanded)
            VALUES (?, 0, ?, ?, ?, 1)
            """,
            (clean_text, priority, next_order, parent_id),
        )
        row = conn.execute(
            """
            SELECT id, content, is_completed, priority, sort_order, parent_id, is_expanded
            FROM tasks WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return row


def get_main_tasks() -> List[sqlite3.Row]:
    """Fetches top-level tasks ordered by completion, sort_order, and priority."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, content, is_completed, priority, sort_order, parent_id, is_expanded
            FROM tasks
            WHERE parent_id IS NULL
            ORDER BY is_completed ASC, sort_order ASC, priority DESC, id DESC
        """).fetchall()


def get_subtasks(parent_id: int) -> List[sqlite3.Row]:
    """Fetches subtasks for a given main task."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, content, is_completed, priority, sort_order, parent_id
            FROM tasks
            WHERE parent_id = ?
            ORDER BY is_completed ASC, sort_order ASC, id ASC
            """,
            (parent_id,),
        ).fetchall()


def toggle_task(task_id: int, completed: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET is_completed = ? WHERE id = ?",
            (1 if completed else 0, task_id),
        )


def update_task_content(
    task_id: int, new_content: str, new_priority: Optional[int] = None
) -> bool:
    """Updates task text and optionally its priority."""
    clean_text = new_content.strip()
    if not clean_text:
        return False
    with get_connection() as conn:
        if new_priority is not None:
            conn.execute(
                "UPDATE tasks SET content = ?, priority = ? WHERE id = ?",
                (clean_text, new_priority, task_id),
            )
        else:
            conn.execute(
                "UPDATE tasks SET content = ? WHERE id = ?",
                (clean_text, task_id),
            )
    return True


def update_task_priority(task_id: int, priority: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET priority = ? WHERE id = ?",
            (priority, task_id),
        )


def update_task_expanded(task_id: int, is_expanded: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET is_expanded = ? WHERE id = ?",
            (1 if is_expanded else 0, task_id),
        )


def update_tasks_order(ordered_task_ids: List[int]) -> None:
    """Persists manual drag-and-drop ordering in a single transaction."""
    with get_connection() as conn:
        conn.executemany(
            "UPDATE tasks SET sort_order = ? WHERE id = ?",
            [(idx, tid) for idx, tid in enumerate(ordered_task_ids)],
        )


def delete_task(task_id: int) -> None:
    """Deletes a task and any child subtasks attached to it."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM tasks WHERE id = ? OR parent_id = ?",
            (task_id, task_id),
        )


def clear_completed_tasks() -> None:
    """Bulk-deletes all completed main tasks (and their subtasks) plus completed subtasks."""
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM tasks
            WHERE is_completed = 1
               OR parent_id IN (SELECT id FROM tasks WHERE is_completed = 1)
        """)


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )