# main.py
import tkinter as tk
from typing import Dict, List, Optional
from config import (
    PALETTE,
    FONT_TASK,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    parse_priority_tag,
)
from db import (
    init_db,
    add_task,
    get_main_tasks,
    get_subtasks,
    toggle_task,
    update_task_content,
    update_task_priority,
    update_task_expanded,
    update_tasks_order,
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
            on_hotkey_summon=self.focus_input_bar,
        )

        self.input_bar = TaskInput(
            self.window.content_frame,
            on_add=self.handle_add,
            on_down_key=self.select_first_task,
        )
        self.input_bar.pack(fill=tk.X, pady=(0, 10))

        self.container = TaskContainer(self.window.content_frame)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.task_widgets: Dict[int, TaskItem] = {}
        self.ordered_ids: List[int] = []
        self.selected_task_id: Optional[int] = None
        self._dragging_item: Optional[TaskItem] = None
        self.empty_lbl: Optional[tk.Label] = None

        self._bind_keyboard_navigation()
        self._initial_load()

    # --- Settings Persistence ---

    def save_geometry(self, x: int, y: int, w: int, h: int) -> None:
        set_setting("win_x", str(x))
        set_setting("win_y", str(y))
        set_setting("win_w", str(w))
        set_setting("win_h", str(h))

    def save_pin_state(self, is_pinned: bool) -> None:
        set_setting("is_pinned", "1" if is_pinned else "0")

    def save_shade_state(self, is_shaded: bool) -> None:
        set_setting("is_shaded", "1" if is_shaded else "0")

    def focus_input_bar(self) -> None:
        self.select_task(None)
        self.input_bar.focus_input()

    # --- Initial Load & Widget Factory ---

    def _initial_load(self) -> None:
        tasks = get_main_tasks()
        for task in tasks:
            tid = task["id"]
            item = self._create_task_widget(task)
            item.pack(fill=tk.X)
            item.load_subtasks(get_subtasks(tid))
            self.task_widgets[tid] = item
            self.ordered_ids.append(tid)

        self._sync_empty_and_counter()

    def _create_task_widget(self, row) -> TaskItem:
        return TaskItem(
            self.container.inner_frame,
            task_id=row["id"],
            content=row["content"],
            is_completed=bool(row["is_completed"]),
            priority=int(row["priority"]),
            sort_order=int(row["sort_order"]),
            is_expanded=bool(row["is_expanded"]),
            on_toggle=self.handle_toggle,
            on_edit=self.handle_edit,
            on_priority_change=self.handle_priority_change,
            on_expand_change=self.handle_expand_change,
            on_delete=self.handle_delete,
            on_select=self.select_task,
            on_add_subtask=self.handle_add_subtask,
            on_toggle_subtask=self.handle_toggle_subtask,
            on_edit_subtask=self.handle_edit_subtask,
            on_delete_subtask=self.handle_delete_subtask,
            on_drag_start=self.handle_drag_start,
            on_drag_motion=self.handle_drag_motion,
            on_drag_end=self.handle_drag_end,
            wraplength=self.container.current_wraplength,
        )

    # --- Main Task CRUD & Priority Parsing ---

    def handle_add(self, raw_text: str) -> None:
        clean_text, priority = parse_priority_tag(raw_text, default_priority=0)
        if not clean_text:
            return
        new_row = add_task(clean_text, priority=priority, parent_id=None)
        if not new_row:
            return

        tid = new_row["id"]
        item = self._create_task_widget(new_row)
        self.task_widgets[tid] = item
        self.ordered_ids.insert(0, tid)
        self._repack_in_order()
        self._sync_empty_and_counter()

    def handle_toggle(self, task_id: int, is_completed: bool) -> None:
        toggle_task(task_id, is_completed)
        self._repack_in_order()
        self._sync_empty_and_counter()

    def handle_edit(self, task_id: int, raw_text: str) -> None:
        widget = self.task_widgets.get(task_id)
        if not widget:
            return
        clean_text, new_priority = parse_priority_tag(
            raw_text, default_priority=widget.priority
        )
        if not clean_text:
            return
        widget.content = clean_text
        widget.text_lbl.configure(text=clean_text)
        widget.set_priority(new_priority)
        update_task_content(task_id, clean_text, new_priority=new_priority)

    def handle_priority_change(self, task_id: int, priority: int) -> None:
        update_task_priority(task_id, priority)

    def handle_expand_change(self, task_id: int, is_expanded: bool) -> None:
        update_task_expanded(task_id, is_expanded)

    def handle_delete(self, task_id: int) -> None:
        # Determine next task to select if deleting via keyboard
        next_sel = None
        if self.selected_task_id == task_id and task_id in self.ordered_ids:
            idx = self.ordered_ids.index(task_id)
            if len(self.ordered_ids) > 1:
                next_sel = (
                    self.ordered_ids[idx + 1]
                    if idx + 1 < len(self.ordered_ids)
                    else self.ordered_ids[idx - 1]
                )

        delete_task(task_id)
        if task_id in self.ordered_ids:
            self.ordered_ids.remove(task_id)
        widget = self.task_widgets.pop(task_id, None)
        if widget is not None:
            widget.destroy()

        self.select_task(next_sel)
        self._sync_empty_and_counter()

    def handle_clear_completed(self) -> None:
        clear_completed_tasks()
        completed_ids = [
            tid for tid, w in self.task_widgets.items() if w.is_completed
        ]
        for tid in completed_ids:
            if tid in self.ordered_ids:
                self.ordered_ids.remove(tid)
            widget = self.task_widgets.pop(tid, None)
            if widget is not None:
                widget.destroy()
            if self.selected_task_id == tid:
                self.selected_task_id = None

        # Also remove any completed subtasks inside remaining active tasks
        for w in self.task_widgets.values():
            done_subs = [
                sid for sid, sw in w.subtask_widgets.items() if sw.is_completed
            ]
            for sid in done_subs:
                sw = w.subtask_widgets.pop(sid, None)
                if sw:
                    sw.destroy()
            w._sync_subtask_visibility()

        self._sync_empty_and_counter()

    # --- Subtask Callbacks ---

    def handle_add_subtask(self, parent_id: int, text: str) -> Optional[dict]:
        row = add_task(text, priority=0, parent_id=parent_id)
        return dict(row) if row else None

    def handle_toggle_subtask(
        self, parent_id: int, subtask_id: int, is_completed: bool
    ) -> None:
        toggle_task(subtask_id, is_completed)

    def handle_edit_subtask(self, subtask_id: int, new_text: str) -> None:
        update_task_content(subtask_id, new_text)

    def handle_delete_subtask(self, parent_id: int, subtask_id: int) -> None:
        delete_task(subtask_id)

    # --- Drag-and-Drop Reordering ---

    def handle_drag_start(self, item: TaskItem, event: tk.Event) -> None:
        self._dragging_item = item
        self.select_task(item.task_id)
        item.set_selected(True, is_dragging=True)

    def handle_drag_motion(self, item: TaskItem, event: tk.Event) -> None:
        if self._dragging_item is not item:
            return

        # Reorder only within the same completion group (active with active)
        group_ids = [
            tid
            for tid in self.ordered_ids
            if self.task_widgets[tid].is_completed == item.is_completed
        ]
        if len(group_ids) <= 1:
            return

        pointer_y = event.y_root
        current_idx = group_ids.index(item.task_id)
        target_idx = current_idx

        for idx, tid in enumerate(group_ids):
            w = self.task_widgets[tid]
            wy = w.winfo_rooty()
            wh = w.winfo_height()
            mid_y = wy + (wh / 2)
            if idx < current_idx and pointer_y < mid_y:
                target_idx = idx
                break
            elif idx > current_idx and pointer_y > mid_y:
                target_idx = idx

        if target_idx != current_idx:
            # Swap position inside self.ordered_ids and re-pack smoothly
            old_global = self.ordered_ids.index(item.task_id)
            target_tid = group_ids[target_idx]
            new_global = self.ordered_ids.index(target_tid)

            self.ordered_ids.pop(old_global)
            self.ordered_ids.insert(new_global, item.task_id)
            self._repack_visual_only()

    def handle_drag_end(self, item: TaskItem, event: tk.Event) -> None:
        if self._dragging_item is not item:
            return
        self._dragging_item = None
        item.set_selected(self.selected_task_id == item.task_id, is_dragging=False)

        # Persist updated manual order to SQLite
        for idx, tid in enumerate(self.ordered_ids):
            self.task_widgets[tid].sort_order = idx
        update_tasks_order(self.ordered_ids)

    def _repack_in_order(self) -> None:
        """Keeps active tasks above completed tasks while preserving manual sort_order."""
        active_ids = [
            tid for tid in self.ordered_ids if not self.task_widgets[tid].is_completed
        ]
        done_ids = [
            tid for tid in self.ordered_ids if self.task_widgets[tid].is_completed
        ]
        self.ordered_ids = active_ids + done_ids
        self._repack_visual_only()
        update_tasks_order(self.ordered_ids)

    def _repack_visual_only(self) -> None:
        for tid in self.ordered_ids:
            self.task_widgets[tid].pack_forget()
        for tid in self.ordered_ids:
            self.task_widgets[tid].pack(fill=tk.X)

    # --- Keyboard Navigation & Shortcuts ---

    def _is_typing_in_entry(self) -> bool:
        focused = self.window.focus_get()
        return isinstance(focused, tk.Entry)

    def select_task(self, task_id: Optional[int]) -> None:
        if self.selected_task_id is not None and self.selected_task_id in self.task_widgets:
            self.task_widgets[self.selected_task_id].set_selected(False)

        self.selected_task_id = task_id

        if task_id is not None and task_id in self.task_widgets:
            w = self.task_widgets[task_id]
            w.set_selected(True)
            self.container.ensure_visible(w)

    def select_first_task(self) -> None:
        if self.ordered_ids:
            self.select_task(self.ordered_ids[0])

    def _bind_keyboard_navigation(self) -> None:
        self.window.bind("<Up>", self._on_key_up)
        self.window.bind("<Down>", self._on_key_down)
        self.window.bind("<space>", self._on_key_space)
        self.window.bind("<Delete>", self._on_key_delete)
        self.window.bind("<F2>", self._on_key_edit)
        self.window.bind("e", self._on_key_edit)
        self.window.bind("p", self._on_key_priority)
        self.window.bind("s", self._on_key_subtask)
        self.window.bind("/", self._on_key_focus_input)
        self.window.bind("<Escape>", self._on_key_escape)

    def _on_key_up(self, event: tk.Event) -> None:
        if self._is_typing_in_entry() or not self.ordered_ids:
            return
        if self.selected_task_id not in self.ordered_ids:
            self.select_task(self.ordered_ids[-1])
        else:
            idx = self.ordered_ids.index(self.selected_task_id)
            if idx > 0:
                self.select_task(self.ordered_ids[idx - 1])
            else:
                self.focus_input_bar()

    def _on_key_down(self, event: tk.Event) -> None:
        if self._is_typing_in_entry() or not self.ordered_ids:
            return
        if self.selected_task_id not in self.ordered_ids:
            self.select_task(self.ordered_ids[0])
        else:
            idx = self.ordered_ids.index(self.selected_task_id)
            if idx + 1 < len(self.ordered_ids):
                self.select_task(self.ordered_ids[idx + 1])

    def _on_key_space(self, event: tk.Event) -> None:
        if self._is_typing_in_entry() or self.selected_task_id is None:
            return
        w = self.task_widgets.get(self.selected_task_id)
        if w:
            w._handle_toggle()

    def _on_key_delete(self, event: tk.Event) -> None:
        if self._is_typing_in_entry() or self.selected_task_id is None:
            return
        self.handle_delete(self.selected_task_id)

    def _on_key_edit(self, event: tk.Event) -> None:
        if self._is_typing_in_entry() or self.selected_task_id is None:
            return
        w = self.task_widgets.get(self.selected_task_id)
        if w:
            w.start_edit()

    def _on_key_priority(self, event: tk.Event) -> None:
        if self._is_typing_in_entry() or self.selected_task_id is None:
            return
        w = self.task_widgets.get(self.selected_task_id)
        if w:
            w.cycle_priority()

    def _on_key_subtask(self, event: tk.Event) -> None:
        if self._is_typing_in_entry() or self.selected_task_id is None:
            return
        w = self.task_widgets.get(self.selected_task_id)
        if w:
            w.open_subtask_input()

    def _on_key_focus_input(self, event: tk.Event) -> None:
        if self._is_typing_in_entry():
            return
        self.focus_input_bar()

    def _on_key_escape(self, event: tk.Event) -> None:
        if self._is_typing_in_entry():
            self.window.focus_set()
        else:
            self.select_task(None)

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
                    text="All clear.\nPress Win+Shift+T or click above to add a task.",
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