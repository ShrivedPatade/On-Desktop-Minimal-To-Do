# main.py
import tkinter as tk
from typing import Dict, Optional
from config import PALETTE, FONT_TASK, WINDOW_WIDTH, WINDOW_HEIGHT
from db import (
    init_db,
    add_task,
    get_tasks,
    toggle_task,
    update_task_content,
    delete_task,
    clear_completed_tasks,
    get_setting,
    set_setting,
)
from ui.window import DesktopTodoWindow
from ui.task_list import TaskInput, TaskItem, TaskContainer


class TodoApp:
    def __init__(self):
        init_db()

        # Load persisted position, size, pin, and shade settings
        saved_x = get_setting("win_x")
        saved_y = get_setting("win_y")
        saved_w = get_setting("win_w", str(WINDOW_WIDTH))
        saved_h = get_setting("win_h", str(WINDOW_HEIGHT))
        saved_pin = get_setting("is_pinned", "1")
        saved_shade = get_setting("is_shaded", "0")

        init_pos = (
            (int(saved_x), int(saved_y))
            if saved_x is not None and saved_y is not None
            else None
        )
        init_size = (int(saved_w), int(saved_h))
        init_pinned = saved_pin == "1"
        init_shaded = saved_shade == "1"

        self.window = DesktopTodoWindow(
            init_pos=init_pos,
            init_size=init_size,
            init_pinned=init_pinned,
            init_shaded=init_shaded,
            on_geometry_change=self.save_geometry,
            on_pin_change=self.save_pin_state,
            on_shade_change=self.save_shade_state,
            on_clear_completed=self.handle_clear_completed,
        )

        self.input_bar = TaskInput(self.window.content_frame, on_add=self.handle_add)
        self.input_bar.pack(fill=tk.X, pady=(0, 10))

        self.container = TaskContainer(self.window.content_frame)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.task_widgets: Dict[int, TaskItem] = {}
        self.empty_lbl: Optional[tk.Label] = None

        self._initial_load()

    def save_geometry(self, x: int, y: int, w: int, h: int) -> None:
        set_setting("win_x", str(x))
        set_setting("win_y", str(y))
        set_setting("win_w", str(w))
        set_setting("win_h", str(h))

    def save_pin_state(self, is_pinned: bool) -> None:
        set_setting("is_pinned", "1" if is_pinned else "0")

    def save_shade_state(self, is_shaded: bool) -> None:
        set_setting("is_shaded", "1" if is_shaded else "0")

    def _initial_load(self) -> None:
        tasks = get_tasks()
        for task in tasks:
            tid = task["id"]
            item = TaskItem(
                self.container.inner_frame,
                task_id=tid,
                content=task["content"],
                is_completed=bool(task["is_completed"]),
                on_toggle=self.handle_toggle,
                on_edit=self.handle_edit,
                on_delete=self.handle_delete,
                wraplength=self.container.current_wraplength,
            )
            item.pack(fill=tk.X)
            self.task_widgets[tid] = item

        self._sync_empty_and_counter()

    def handle_add(self, text: str) -> None:
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
            on_edit=self.handle_edit,
            on_delete=self.handle_delete,
            wraplength=self.container.current_wraplength,
        )
        self.task_widgets[tid] = item
        self._repack_in_order()
        self._sync_empty_and_counter()

    def handle_toggle(self, task_id: int, is_completed: bool) -> None:
        toggle_task(task_id, is_completed)
        self._repack_in_order()
        self._sync_empty_and_counter()

    def handle_edit(self, task_id: int, new_text: str) -> None:
        update_task_content(task_id, new_text)

    def handle_delete(self, task_id: int) -> None:
        delete_task(task_id)
        widget = self.task_widgets.pop(task_id, None)
        if widget is not None:
            widget.destroy()
        self._sync_empty_and_counter()

    def handle_clear_completed(self) -> None:
        """Removes all completed tasks from DB and destroys only completed widgets."""
        clear_completed_tasks()
        completed_ids = [
            tid for tid, w in self.task_widgets.items() if w.is_completed
        ]
        for tid in completed_ids:
            widget = self.task_widgets.pop(tid, None)
            if widget is not None:
                widget.destroy()
        self._sync_empty_and_counter()

    def _repack_in_order(self) -> None:
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
        self.window.update_status_counts(active_count, total_count)

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