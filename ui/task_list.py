# ui/task_list.py
import tkinter as tk
from typing import Callable
from config import (
    PALETTE,
    INPUT_RADIUS,
    FONT_INPUT,
    FONT_TASK,
    FONT_TASK_DONE,
    FONT_ICON,
    draw_rounded_rect,
)


class TaskInput(tk.Canvas):
    """Rounded pill input bar with faint thin border and round, centered '+' button."""

    PLACEHOLDER = "Add a task..."

    def __init__(self, parent, on_add: Callable[[str], None], **kwargs):
        super().__init__(
            parent,
            height=40,
            bg=PALETTE["bg_main"],
            bd=0,
            highlightthickness=0,
            **kwargs,
        )
        self.on_add = on_add
        self._has_placeholder = True
        self._is_focused = False
        self._pill_id = None
        self._circle_id = None

        # Inner borderless text entry
        self.entry = tk.Entry(
            self,
            font=FONT_INPUT,
            bg=PALETTE["bg_input"],
            fg=PALETTE["text_muted"],
            insertbackground=PALETTE["accent"],
            bd=0,
            relief=tk.FLAT,
        )
        self.entry.insert(0, self.PLACEHOLDER)

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Return>", self._handle_submit)

        # Redraw rounded capsule & circular '+' button whenever width is set
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event: tk.Event) -> None:
        w, h = event.width, event.height
        if w < 50:
            return

        self.delete("bg_shapes")
        self.delete("plus_btn")

        # 1. Rounded Input Pill with Faint Thin Border
        border_col = PALETTE["accent"] if self._is_focused else PALETTE["border_faint"]
        self._pill_id = draw_rounded_rect(
            self,
            1, 1, w - 2, h - 2,
            radius=INPUT_RADIUS,
            corners=(True, True, True, True),
            fill=PALETTE["bg_input"],
            outline=border_col,
            width=1,
            tags="bg_shapes",
        )

        # Clicking anywhere on the pill focuses the text box
        self.tag_bind("bg_shapes", "<Button-1>", lambda _: self.entry.focus_set())

        # 2. Position Entry inside the left/middle of the rounded pill
        btn_diameter = 26
        btn_margin_right = 7
        entry_x = 14
        entry_w = w - entry_x - btn_diameter - btn_margin_right - 10

        self.delete("entry_win")
        self.create_window(
            entry_x,
            h // 2,
            window=self.entry,
            anchor="w",
            width=max(50, entry_w),
            tags="entry_win",
        )

        # 3. Round, Almost-Transparent '+' Button on the Right
        cx = w - btn_margin_right - (btn_diameter / 2)
        cy = h / 2
        r = btn_diameter / 2

        self._circle_id = self.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            fill=PALETTE["btn_plus_bg"],
            outline=PALETTE["border_faint"],
            width=1,
            tags="plus_btn",
        )

        # 4. Dead-Center '+' Crosshair Lines
        arm = 4.5
        self.create_line(
            cx - arm, cy, cx + arm, cy,
            fill=PALETTE["accent"],
            width=1.5,
            capstyle=tk.ROUND,
            tags="plus_btn",
        )
        self.create_line(
            cx, cy - arm, cx, cy + arm,
            fill=PALETTE["accent"],
            width=1.5,
            capstyle=tk.ROUND,
            tags="plus_btn",
        )

        # Hover & click events for the '+' button
        self.tag_bind("plus_btn", "<Button-1>", self._handle_submit)
        self.tag_bind("plus_btn", "<Enter>", self._on_btn_enter)
        self.tag_bind("plus_btn", "<Leave>", self._on_btn_leave)

    def _on_btn_enter(self, event=None) -> None:
        self.configure(cursor="hand2")
        if self._circle_id:
            self.itemconfig(
                self._circle_id,
                fill=PALETTE["btn_plus_hover"],
                outline=PALETTE["accent"],
            )

    def _on_btn_leave(self, event=None) -> None:
        self.configure(cursor="")
        if self._circle_id:
            self.itemconfig(
                self._circle_id,
                fill=PALETTE["btn_plus_bg"],
                outline=PALETTE["border_faint"],
            )

    def _on_focus_in(self, event=None) -> None:
        self._is_focused = True
        if self._pill_id:
            self.itemconfig(self._pill_id, outline=PALETTE["accent"])
        if self._has_placeholder:
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=PALETTE["text_primary"])
            self._has_placeholder = False

    def _on_focus_out(self, event=None) -> None:
        self._is_focused = False
        if self._pill_id:
            self.itemconfig(self._pill_id, outline=PALETTE["border_faint"])
        if not self.entry.get().strip():
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.PLACEHOLDER)
            self.entry.configure(fg=PALETTE["text_muted"])
            self._has_placeholder = True

    def _handle_submit(self, event=None) -> None:
        if self._has_placeholder:
            return
        text = self.entry.get().strip()
        if text:
            self.on_add(text)
            self.entry.delete(0, tk.END)


class TaskItem(tk.Frame):
    """Readable task row with dark primary text and subtle divider."""

    def __init__(
        self,
        parent,
        task_id: int,
        content: str,
        is_completed: bool,
        on_toggle: Callable[[int, bool], None],
        on_delete: Callable[[int], None],
    ):
        super().__init__(parent, bg=PALETTE["bg_main"])
        self.task_id = task_id
        self.is_completed = bool(is_completed)
        self.on_toggle = on_toggle
        self.on_delete = on_delete

        self.row = tk.Frame(self, bg=PALETTE["bg_main"], padx=4, pady=7)
        self.row.pack(fill=tk.X, expand=True)

        self.divider = tk.Frame(self, bg=PALETTE["bg_surface"], height=1)
        self.divider.pack(fill=tk.X, side=tk.BOTTOM)

        self.check_btn = tk.Button(
            self.row,
            text="✔" if self.is_completed else "○",
            font=FONT_ICON,
            bg=PALETTE["bg_main"],
            fg=PALETTE["accent"] if self.is_completed else PALETTE["text_muted"],
            activebackground=PALETTE["bg_main"],
            activeforeground=PALETTE["accent"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            width=2,
            command=self._handle_toggle,
        )
        self.check_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.text_lbl = tk.Label(
            self.row,
            text=content,
            font=FONT_TASK_DONE if self.is_completed else FONT_TASK,
            bg=PALETTE["bg_main"],
            fg=PALETTE["text_muted"] if self.is_completed else PALETTE["text_primary"],
            anchor="w",
            wraplength=235,
            justify=tk.LEFT,
            cursor="hand2",
        )
        self.text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.text_lbl.bind("<Button-1>", lambda _: self._handle_toggle())

        self.del_btn = tk.Button(
            self.row,
            text="✕",
            font=("Segoe UI", 9),
            bg=PALETTE["bg_main"],
            fg=PALETTE["bg_surface"],
            activebackground=PALETTE["bg_main"],
            activeforeground=PALETTE["danger"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            padx=6,
            command=self._handle_delete,
        )
        self.del_btn.pack(side=tk.RIGHT)

        for w in (self, self.row, self.text_lbl, self.check_btn, self.del_btn):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None) -> None:
        self.del_btn.configure(fg=PALETTE["text_muted"])

    def _on_leave(self, event=None) -> None:
        self.del_btn.configure(fg=PALETTE["bg_surface"])

    def _update_visuals(self) -> None:
        if self.is_completed:
            self.check_btn.configure(text="✔", fg=PALETTE["accent"])
            self.text_lbl.configure(font=FONT_TASK_DONE, fg=PALETTE["text_muted"])
        else:
            self.check_btn.configure(text="○", fg=PALETTE["text_muted"])
            self.text_lbl.configure(font=FONT_TASK, fg=PALETTE["text_primary"])

    def _handle_toggle(self) -> None:
        self.is_completed = not self.is_completed
        self._update_visuals()
        self.on_toggle(self.task_id, self.is_completed)

    def _handle_delete(self) -> None:
        self.on_delete(self.task_id)


class TaskContainer(tk.Frame):
    """Scrollable container supporting mouse wheel scrolling."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PALETTE["bg_main"], **kwargs)

        self.canvas = tk.Canvas(
            self,
            bg=PALETTE["bg_main"],
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.inner_frame = tk.Frame(self.canvas, bg=PALETTE["bg_main"])

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw"
        )

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner_frame.bind(
            "<Configure>",
            lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.canvas.winfo_exists():
            bbox = self.canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) > self.canvas.winfo_height():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self) -> None:
        for child in self.inner_frame.winfo_children():
            child.destroy()
            
# Test code for task operations
# if __name__ == "__main__":
#     root = tk.Tk()
#     root.geometry("320x450")
#     root.title("Task List Preview")
#     root.configure(bg="#1e1e24")

#     # In-memory test state
#     test_tasks = [
#         {"id": 1, "content": "Sample active task", "is_completed": False},
#         {"id": 2, "content": "Sample completed task", "is_completed": True},
#     ]
#     next_id = 3

#     container = TaskContainer(root)

#     def render_all_tasks():
#         container.clear()
#         for task in test_tasks:
#             item = TaskItem(
#                 container.inner_frame,
#                 task_id=task["id"],
#                 content=task["content"],
#                 is_completed=task["is_completed"],
#                 on_toggle=handle_test_toggle,
#                 on_delete=handle_test_delete,
#             )
#             item.pack(fill=tk.X, pady=3)

#     def handle_test_toggle(tid: int, state: bool):
#         for task in test_tasks:
#             if task["id"] == tid:
#                 task["is_completed"] = state
#                 break

#     def handle_test_delete(tid: int):
#         global test_tasks
#         test_tasks = [t for t in test_tasks if t["id"] != tid]
#         render_all_tasks()

#     def handle_test_add(text: str):
#         global next_id
#         test_tasks.append({"id": next_id, "content": text, "is_completed": False})
#         next_id += 1
#         render_all_tasks()

#     # Input bar
#     inp = TaskInput(root, on_add=handle_test_add)
#     inp.pack(fill=tk.X, padx=12, pady=8)

#     # Scrollable container
#     container.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

#     # Initial render
#     render_all_tasks()

#     root.mainloop()
            