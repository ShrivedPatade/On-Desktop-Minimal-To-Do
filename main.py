# main.py
import tkinter as tk
from typing import Dict, Optional
from config import PALETTE, FONT_TASK
from db import (
    init_db,
    add_task,
    get_tasks,
    toggle_task,
    delete_task,
    get_setting,
    set_setting,
)
from ui.window import DesktopTodoWindow
from ui.task_list import TaskInput, TaskItem, TaskContainer


class TodoApp:
    def __init__(self):
        init_db()

        saved_x = get_setting("win_x")
        saved_y = get_setting("win_y")
        saved_pin = get_setting("is_pinned", "1")

        init_pos = (
            (int(saved_x), int(saved_y))
            if saved_x is not None and saved_y is not None
            else None
        )
        init_pinned = saved_pin == "1"

        self.window = DesktopTodoWindow(
            init_pos=init_pos,
            init_pinned=init_pinned,
            on_geometry_change=self.save_position,
            on_pin_change=self.save_pin_state,
        )

        self.input_bar = TaskInput(self.window.content_frame, on_add=self.handle_add)
        self.input_bar.pack(fill=tk.X, pady=(0, 10))

        self.container = TaskContainer(self.window.content_frame)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Live widget registry to avoid full-screen teardown blips
        self.task_widgets: Dict[int, TaskItem] = {}
        self.empty_lbl: Optional[tk.Label] = None

        self._initial_load()

    def save_position(self, x: int, y: int) -> None:
        set_setting("win_x", str(x))
        set_setting("win_y", str(y))

    def save_pin_state(self, is_pinned: bool) -> None:
        set_setting("is_pinned", "1" if is_pinned else "0")

    def _initial_load(self) -> None:
        """Populates widgets once on startup."""
        tasks = get_tasks()
        for task in tasks:
            tid = task["id"]
            item = TaskItem(
                self.container.inner_frame,
                task_id=tid,
                content=task["content"],
                is_completed=bool(task["is_completed"]),
                on_toggle=self.handle_toggle,
                on_delete=self.handle_delete,
            )
            item.pack(fill=tk.X)
            self.task_widgets[tid] = item

        self._sync_empty_and_counter()

    def handle_add(self, text: str) -> None:
        """Creates only the single new widget without touching existing rows."""
        new_row = add_task(text)
        if not new_row:
            return

        tid = new_row["id"]
        item = TaskItem(
            self.container.inner_frame,
            task_id=tid,
            content=new_row["content"],
            is_completed=False,
            on_toggle=self.handle_toggle,
            on_delete=self.handle_delete,
        )
        self.task_widgets[tid] = item
        self._repack_in_order()
        self._sync_empty_and_counter()

    def handle_toggle(self, task_id: int, is_completed: bool) -> None:
        """Updates DB and re-orders existing widgets in-place with zero destruction."""
        toggle_task(task_id, is_completed)
        self._repack_in_order()
        self._sync_empty_and_counter()

    def handle_delete(self, task_id: int) -> None:
        """Destroys only the deleted task widget."""
        delete_task(task_id)
        widget = self.task_widgets.pop(task_id, None)
        if widget is not None:
            widget.destroy()
        self._sync_empty_and_counter()

    def _repack_in_order(self) -> None:
        """Reorders existing widgets (active first, newest on top) without recreating them."""
        sorted_items = sorted(
            self.task_widgets.values(),
            key=lambda w: (w.is_completed, -w.task_id),
        )
        for widget in sorted_items:
            widget.pack_forget()
        for widget in sorted_items:
            widget.pack(fill=tk.X)

    def _sync_empty_and_counter(self) -> None:
        total_count = len(self.task_widgets)
        active_count = sum(
            1 for w in self.task_widgets.values() if not w.is_completed
        )
        self.window.update_title_count(active_count, total_count)

        if total_count == 0:
            if self.empty_lbl is None:
                self.empty_lbl = tk.Label(
                    self.container.inner_frame,
                    text="All clear.\nAdd a task above to get started.",
                    font=FONT_TASK,
                    bg=PALETTE["bg_main"],
                    fg=PALETTE["text_muted"],
                    pady=50,
                    justify=tk.CENTER,
                )
                self.empty_lbl.pack(fill=tk.X)
        else:
            if self.empty_lbl is not None:
                self.empty_lbl.destroy()
                self.empty_lbl = None

    def run(self) -> None:
        self.window.mainloop()


if __name__ == "__main__":
    app = TodoApp()
    app.run()