# ui/task_list.py
import tkinter as tk
from typing import Callable, Optional
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

        self.bind("<Configure>", self._redraw)

    def _redraw(self, event: tk.Event) -> None:
        w, h = event.width, event.height
        if w < 50:
            return

        self.delete("bg_shapes")
        self.delete("plus_btn")

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

        self.tag_bind("bg_shapes", "<Button-1>", lambda _: self.entry.focus_set())

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
    """Task row supporting click-to-toggle and double-click inline editing."""

    def __init__(
        self,
        parent,
        task_id: int,
        content: str,
        is_completed: bool,
        on_toggle: Callable[[int, bool], None],
        on_edit: Callable[[int, str], None],
        on_delete: Callable[[int], None],
        wraplength: int = 235,
    ):
        super().__init__(parent, bg=PALETTE["bg_main"])
        self.task_id = task_id
        self.content = content
        self.is_completed = bool(is_completed)
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_delete = on_delete
        self._click_timer: Optional[str] = None
        self.edit_entry: Optional[tk.Entry] = None

        self.row = tk.Frame(self, bg=PALETTE["bg_main"], padx=4, pady=7)
        self.row.pack(fill=tk.X, expand=True)

        self.divider = tk.Frame(self, bg=PALETTE["bg_surface"], height=1)
        self.divider.pack(fill=tk.X, side=tk.BOTTOM)

        # Status Toggle Button (Immediate toggle)
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

        # Delete Button (packed on right before text_lbl so it stays anchored)
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

        # Task Text Label (Single-click toggles, Double-click edits inline)
        self.text_lbl = tk.Label(
            self.row,
            text=self.content,
            font=FONT_TASK_DONE if self.is_completed else FONT_TASK,
            bg=PALETTE["bg_main"],
            fg=PALETTE["text_muted"] if self.is_completed else PALETTE["text_primary"],
            anchor="w",
            wraplength=wraplength,
            justify=tk.LEFT,
            cursor="hand2",
        )
        self.text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.text_lbl.bind("<Button-1>", self._on_label_single_click)
        self.text_lbl.bind("<Double-Button-1>", self._on_label_double_click)

        for w in (self, self.row, self.text_lbl, self.check_btn, self.del_btn):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def set_wraplength(self, wraplength: int) -> None:
        self.text_lbl.configure(wraplength=max(100, wraplength))

    def _on_enter(self, event=None) -> None:
        self.del_btn.configure(fg=PALETTE["text_muted"])

    def _on_leave(self, event=None) -> None:
        self.del_btn.configure(fg=PALETTE["bg_surface"])

    # --- Single Click (Toggle) vs Double Click (Inline Edit) ---

    def _on_label_single_click(self, event=None) -> None:
        if self._click_timer is not None:
            self.after_cancel(self._click_timer)
        self._click_timer = self.after(180, self._deferred_toggle)

    def _deferred_toggle(self) -> None:
        self._click_timer = None
        if self.edit_entry is None:
            self._handle_toggle()

    def _on_label_double_click(self, event=None) -> None:
        if self._click_timer is not None:
            self.after_cancel(self._click_timer)
            self._click_timer = None
        self.start_edit()

    def start_edit(self) -> None:
        """Swaps the task label for an Entry widget to edit text in place."""
        if self.edit_entry is not None:
            return

        self.text_lbl.pack_forget()

        self.edit_entry = tk.Entry(
            self.row,
            font=FONT_TASK,
            bg=PALETTE["bg_input"],
            fg=PALETTE["text_primary"],
            insertbackground=PALETTE["accent"],
            highlightbackground=PALETTE["accent"],
            highlightcolor=PALETTE["accent"],
            highlightthickness=1,
            bd=2,
            relief=tk.FLAT,
        )
        self.edit_entry.insert(0, self.content)
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.edit_entry.focus_set()

        self.edit_entry.bind("<Return>", self._commit_edit)
        self.edit_entry.bind("<FocusOut>", self._commit_edit)
        self.edit_entry.bind("<Escape>", self._cancel_edit)

    def _commit_edit(self, event=None) -> None:
        if self.edit_entry is None:
            return
        new_text = self.edit_entry.get().strip()
        self._close_editor()

        if new_text and new_text != self.content:
            self.content = new_text
            self.text_lbl.configure(text=self.content)
            self.on_edit(self.task_id, self.content)

    def _cancel_edit(self, event=None) -> None:
        self._close_editor()

    def _close_editor(self) -> None:
        if self.edit_entry is not None:
            entry = self.edit_entry
            self.edit_entry = None
            entry.destroy()
        self.text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --- Visual & State Updates ---

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
    """Scrollable container supporting mouse wheel scrolling and responsive wraplength."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PALETTE["bg_main"], **kwargs)
        self.current_wraplength = 235

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
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        new_wrap = max(120, event.width - 75)
        if abs(new_wrap - self.current_wraplength) > 4:
            self.current_wraplength = new_wrap
            for child in self.inner_frame.winfo_children():
                if isinstance(child, TaskItem):
                    child.set_wraplength(new_wrap)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.canvas.winfo_exists():
            bbox = self.canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) > self.canvas.winfo_height():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self) -> None:
        for child in self.inner_frame.winfo_children():
            child.destroy()