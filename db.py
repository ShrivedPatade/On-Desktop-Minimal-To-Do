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
    """Initializes the tasks and settings tables."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                is_completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


def add_task(content: str) -> Optional[sqlite3.Row]:
    """Inserts a new task and returns the created row."""
    clean_text = content.strip()
    if not clean_text:
        return None
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (content, is_completed) VALUES (?, 0)",
            (clean_text,),
        )
        row = conn.execute(
            "SELECT id, content, is_completed FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return row


def get_tasks() -> List[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT id, content, is_completed 
            FROM tasks 
            ORDER BY is_completed ASC, id DESC
        """)
        return cursor.fetchall()


def toggle_task(task_id: int, completed: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET is_completed = ? WHERE id = ?",
            (1 if completed else 0, task_id),
        )


def delete_task(task_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


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
        
# Testing code for database operations
# if __name__ == "__main__":
#     init_db()
#     tid = add_task("Test lightweight desktop widget")
#     print("Added task ID:", tid)
#     print("All tasks:", [dict(r) for r in get_tasks()])
#     toggle_task(tid, True)
#     print("Toggled tasks:", [dict(r) for r in get_tasks()])
#     delete_task(tid)
#     print("After delete:", [dict(r) for r in get_tasks()])
#     print("DB tests passed successfully!")