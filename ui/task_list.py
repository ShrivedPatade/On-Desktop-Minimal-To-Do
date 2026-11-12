# ui/task_list.py
import tkinter as tk
from typing import Callable, Dict, List, Optional
from config import (
    PALETTE,
    PRIORITY_COLORS,
    INPUT_RADIUS,
    FONT_INPUT,
    FONT_TASK,
    FONT_TASK_DONE,
    FONT_SUBTASK,
    FONT_SUBTASK_DONE,
    FONT_BADGE,
    FONT_ICON,
    draw_rounded_rect,
)


class TaskInput(tk.Canvas):
    """Rounded pill input bar supporting !high / !med priority tags."""

    PLACEHOLDER = "Add task... (!high, !med)"

    def __init__(
        self,
        parent,
        on_add: Callable[[str], None],
        on_down_key: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            height=40,
            bg=PALETTE["bg_main"],
            bd=0,
            highlightthickness=0,
            **kwargs,
        )
        self.on_add = on_add
        self.on_down_key = on_down_key
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
        self.entry.bind("<Down>", self._handle_down_arrow)
        self.entry.bind("<Escape>", lambda _: self.focus_set())

        self.bind("<Configure>", self._redraw)

    def focus_input(self) -> None:
        """Focuses the text entry box and clears placeholder ready for typing."""
        self.entry.focus_set()
        self._on_focus_in()

    def _handle_down_arrow(self, event=None) -> str:
        if self.on_down_key:
            self.focus_set()
            self.on_down_key()
            return "break"
        return ""

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

        # 3. Round, Almost-Transparent '+' Button (integer-snapped center)
        r = btn_diameter // 2
        cx = int(w - btn_margin_right - r)
        cy = int(h // 2)

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

        # 4. Pixel-Symmetric '+' Crosshair (2px thick, 4px arms, zero GDI line clipping)
        arm = 5  # Spans [cx - 5, cx + 5) = 10px total (4px left, 2px center, 4px right)
        self.create_rectangle(
            cx - arm, cy - 1, cx + arm, cy + 1,
            fill=PALETTE["accent"],
            outline="",
            tags="plus_btn",
        )
        self.create_rectangle(
            cx - 1, cy - arm, cx + 1, cy + arm,
            fill=PALETTE["accent"],
            outline="",
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

class SubtaskItem(tk.Frame):
    """Indented child subtask row with toggle, double-click edit, and delete."""

    def __init__(
        self,
        parent,
        subtask_id: int,
        content: str,
        is_completed: bool,
        on_toggle: Callable[[int, bool], None],
        on_edit: Callable[[int, str], None],
        on_delete: Callable[[int], None],
        wraplength: int = 190,
    ):
        super().__init__(parent, bg=PALETTE["bg_main"])
        self.subtask_id = subtask_id
        self.content = content
        self.is_completed = bool(is_completed)
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_delete = on_delete
        self._click_timer: Optional[str] = None
        self.edit_entry: Optional[tk.Entry] = None

        self.row = tk.Frame(self, bg=PALETTE["bg_main"], pady=2)
        self.row.pack(fill=tk.X, expand=True)

        self.check_btn = tk.Button(
            self.row,
            text="✔" if self.is_completed else "◦",
            font=("Segoe UI", 9, "bold"),
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
        self.check_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.del_btn = tk.Button(
            self.row,
            text="✕",
            font=("Segoe UI", 8),
            bg=PALETTE["bg_main"],
            fg=PALETTE["bg_surface"],
            activebackground=PALETTE["bg_main"],
            activeforeground=PALETTE["danger"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            padx=4,
            command=lambda: self.on_delete(self.subtask_id),
        )
        self.del_btn.pack(side=tk.RIGHT)

        self.text_lbl = tk.Label(
            self.row,
            text=self.content,
            font=FONT_SUBTASK_DONE if self.is_completed else FONT_SUBTASK,
            bg=PALETTE["bg_main"],
            fg=PALETTE["text_muted"] if self.is_completed else PALETTE["text_primary"],
            anchor="w",
            wraplength=wraplength,
            justify=tk.LEFT,
            cursor="hand2",
        )
        self.text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.text_lbl.bind("<Button-1>", self._on_single_click)
        self.text_lbl.bind("<Double-Button-1>", self._on_double_click)

        for w in (self, self.row, self.text_lbl, self.check_btn, self.del_btn):
            w.bind("<Enter>", lambda _: self.del_btn.configure(fg=PALETTE["text_muted"]))
            w.bind("<Leave>", lambda _: self.del_btn.configure(fg=PALETTE["bg_surface"]))

    def set_bg(self, color: str) -> None:
        self.configure(bg=color)
        self.row.configure(bg=color)
        self.check_btn.configure(bg=color, activebackground=color)
        self.text_lbl.configure(bg=color)
        self.del_btn.configure(bg=color, activebackground=color)

    def set_wraplength(self, wraplength: int) -> None:
        self.text_lbl.configure(wraplength=max(90, wraplength - 35))

    def _on_single_click(self, event=None) -> None:
        if self._click_timer is not None:
            self.after_cancel(self._click_timer)
        self._click_timer = self.after(180, self._deferred_toggle)

    def _deferred_toggle(self) -> None:
        self._click_timer = None
        if self.edit_entry is None:
            self._handle_toggle()

    def _on_double_click(self, event=None) -> None:
        if self._click_timer is not None:
            self.after_cancel(self._click_timer)
            self._click_timer = None
        self.start_edit()

    def start_edit(self) -> None:
        if self.edit_entry is not None:
            return
        self.text_lbl.pack_forget()
        self.edit_entry = tk.Entry(
            self.row,
            font=FONT_SUBTASK,
            bg=PALETTE["bg_input"],
            fg=PALETTE["text_primary"],
            insertbackground=PALETTE["accent"],
            highlightbackground=PALETTE["accent"],
            highlightthickness=1,
            bd=1,
            relief=tk.FLAT,
        )
        self.edit_entry.insert(0, self.content)
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.edit_entry.focus_set()

        self.edit_entry.bind("<Return>", self._commit_edit)
        self.edit_entry.bind("<FocusOut>", self._commit_edit)
        self.edit_entry.bind("<Escape>", lambda _: self._close_editor())

    def _commit_edit(self, event=None) -> None:
        if self.edit_entry is None:
            return
        new_text = self.edit_entry.get().strip()
        self._close_editor()
        if new_text and new_text != self.content:
            self.content = new_text
            self.text_lbl.configure(text=self.content)
            self.on_edit(self.subtask_id, self.content)

    def _close_editor(self) -> None:
        if self.edit_entry is not None:
            entry = self.edit_entry
            self.edit_entry = None
            entry.destroy()
        self.text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _handle_toggle(self) -> None:
        self.is_completed = not self.is_completed
        self.check_btn.configure(
            text="✔" if self.is_completed else "◦",
            fg=PALETTE["accent"] if self.is_completed else PALETTE["text_muted"],
        )
        self.text_lbl.configure(
            font=FONT_SUBTASK_DONE if self.is_completed else FONT_SUBTASK,
            fg=PALETTE["text_muted"] if self.is_completed else PALETTE["text_primary"],
        )
        self.on_toggle(self.subtask_id, self.is_completed)


class TaskItem(tk.Frame):
    """
    Main task row featuring:
    - Left priority border accent (click to cycle priority)
    - Drag-and-drop reorder handle (⋮⋮)
    - Collapsible subtask section with inline add & progress badge
    - Keyboard selection highlighting
    """

    def __init__(
        self,
        parent,
        task_id: int,
        content: str,
        is_completed: bool,
        priority: int,
        sort_order: int,
        is_expanded: bool,
        on_toggle: Callable[[int, bool], None],
        on_edit: Callable[[int, str], None],
        on_priority_change: Callable[[int, int], None],
        on_expand_change: Callable[[int, bool], None],
        on_delete: Callable[[int], None],
        on_select: Callable[[int], None],
        on_add_subtask: Callable[[int, str], Optional[dict]],
        on_toggle_subtask: Callable[[int, int, bool], None],
        on_edit_subtask: Callable[[int, str], None],
        on_delete_subtask: Callable[[int, int], None],
        on_drag_start: Callable[["TaskItem", tk.Event], None],
        on_drag_motion: Callable[["TaskItem", tk.Event], None],
        on_drag_end: Callable[["TaskItem", tk.Event], None],
        wraplength: int = 200,
    ):
        super().__init__(parent, bg=PALETTE["bg_main"])
        self.task_id = task_id
        self.content = content
        self.is_completed = bool(is_completed)
        self.priority = int(priority)
        self.sort_order = int(sort_order)
        self.is_expanded = bool(is_expanded)
        self.is_selected = False

        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_priority_change = on_priority_change
        self.on_expand_change = on_expand_change
        self.on_delete = on_delete
        self.on_select = on_select
        self.on_add_subtask = on_add_subtask
        self.on_toggle_subtask = on_toggle_subtask
        self.on_edit_subtask = on_edit_subtask
        self.on_delete_subtask = on_delete_subtask

        self._click_timer: Optional[str] = None
        self.edit_entry: Optional[tk.Entry] = None
        self.subtask_entry: Optional[tk.Entry] = None
        self.subtask_widgets: Dict[int, SubtaskItem] = {}
        self._wraplength = wraplength

        # Outer container holding left priority accent bar + content column
        self.main_area = tk.Frame(self, bg=PALETTE["bg_main"])
        self.main_area.pack(fill=tk.X, expand=True)

        # 1. Color-coded Left Priority Bar (4px wide, click to cycle priority)
        self.priority_bar = tk.Frame(
            self.main_area,
            bg=PRIORITY_COLORS.get(self.priority, PALETTE["priority_none"]),
            width=4,
            cursor="hand2",
        )
        self.priority_bar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 3), pady=2)
        self.priority_bar.bind("<Button-1>", lambda _: self.cycle_priority())

        # Right side column (Main row + Subtask section)
        self.col = tk.Frame(self.main_area, bg=PALETTE["bg_main"])
        self.col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Primary Row
        self.row = tk.Frame(self.col, bg=PALETTE["bg_main"], padx=2, pady=6)
        self.row.pack(fill=tk.X, expand=True)

        # 2. Drag-and-Drop Handle (⋮⋮)
        self.drag_lbl = tk.Label(
            self.row,
            text="⋮⋮",
            font=("Segoe UI", 8, "bold"),
            bg=PALETTE["bg_main"],
            fg=PALETTE["border_faint"],
            cursor="fleur",
            padx=2,
        )
        self.drag_lbl.pack(side=tk.LEFT)
        self.drag_lbl.bind("<ButtonPress-1>", lambda e: on_drag_start(self, e))
        self.drag_lbl.bind("<B1-Motion>", lambda e: on_drag_motion(self, e))
        self.drag_lbl.bind("<ButtonRelease-1>", lambda e: on_drag_end(self, e))

        # 3. Checkmark Toggle Button
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
        self.check_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 4. Right-Side Controls (Delete '✕', Add Subtask '+', Collapse Badge '▾ 1/2')
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
            padx=4,
            command=self._handle_delete,
        )
        self.del_btn.pack(side=tk.RIGHT)

        self.add_sub_btn = tk.Button(
            self.row,
            text="+",
            font=("Segoe UI", 9, "bold"),
            bg=PALETTE["bg_main"],
            fg=PALETTE["bg_surface"],
            activebackground=PALETTE["bg_main"],
            activeforeground=PALETTE["accent"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            padx=4,
            command=self.open_subtask_input,
        )
        self.add_sub_btn.pack(side=tk.RIGHT)

        self.expand_btn = tk.Label(
            self.row,
            text="",
            font=FONT_BADGE,
            bg=PALETTE["bg_main"],
            fg=PALETTE["text_muted"],
            cursor="hand2",
            padx=4,
        )
        self.expand_btn.bind("<Button-1>", lambda _: self.toggle_expand())

        # 5. Task Text Label
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

        # 6. Collapsible Subtask Container
        self.subtask_container = tk.Frame(self.col, bg=PALETTE["bg_main"])
        # Indented left guide line for subtasks
        self.subtask_guide = tk.Frame(
            self.subtask_container, bg=PALETTE["border_faint"], width=1
        )
        self.subtask_guide.pack(side=tk.LEFT, fill=tk.Y, padx=(18, 8), pady=(0, 4))

        self.subtask_list_frame = tk.Frame(self.subtask_container, bg=PALETTE["bg_main"])
        self.subtask_list_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(0, 4))

        # Bottom separator line
        self.divider = tk.Frame(self, bg=PALETTE["bg_surface"], height=1)
        self.divider.pack(fill=tk.X, side=tk.BOTTOM)

        for w in (
            self,
            self.main_area,
            self.col,
            self.row,
            self.text_lbl,
            self.check_btn,
            self.add_sub_btn,
            self.del_btn,
        ):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    # --- Priority Management ---

    def cycle_priority(self) -> None:
        """Cycles priority: 0 (Normal) -> 1 (Med) -> 2 (High) -> 0."""
        self.set_priority((self.priority + 1) % 3)
        self.on_priority_change(self.task_id, self.priority)

    def set_priority(self, priority: int) -> None:
        self.priority = priority
        self.priority_bar.configure(
            bg=PRIORITY_COLORS.get(self.priority, PALETTE["priority_none"])
        )

    # --- Keyboard Selection & Drag Highlighting ---

    def set_selected(self, selected: bool, is_dragging: bool = False) -> None:
        self.is_selected = selected
        if is_dragging:
            bg = PALETTE["bg_drag"]
        elif selected:
            bg = PALETTE["bg_selected"]
        else:
            bg = PALETTE["bg_main"]

        for w in (
            self,
            self.main_area,
            self.col,
            self.row,
            self.drag_lbl,
            self.text_lbl,
            self.expand_btn,
            self.subtask_container,
            self.subtask_list_frame,
        ):
            w.configure(bg=bg)

        for btn in (self.check_btn, self.add_sub_btn, self.del_btn):
            btn.configure(bg=bg, activebackground=bg)

        for sub in self.subtask_widgets.values():
            sub.set_bg(bg)

    # --- Subtask Management ---

    def load_subtasks(self, subtasks: list) -> None:
        for sub in subtasks:
            self._mount_subtask_widget(
                sub["id"], sub["content"], bool(sub["is_completed"])
            )
        self._sync_subtask_visibility()

    def _mount_subtask_widget(
        self, sub_id: int, content: str, is_completed: bool
    ) -> SubtaskItem:
        item = SubtaskItem(
            self.subtask_list_frame,
            subtask_id=sub_id,
            content=content,
            is_completed=is_completed,
            on_toggle=self._handle_subtask_toggle,
            on_edit=self.on_edit_subtask,
            on_delete=self._handle_subtask_delete,
            wraplength=self._wraplength,
        )
        if self.is_selected:
            item.set_bg(PALETTE["bg_selected"])
        item.pack(fill=tk.X)
        self.subtask_widgets[sub_id] = item
        return item

    def open_subtask_input(self) -> None:
        """Opens an inline Entry below the main task to add a subtask."""
        self.on_select(self.task_id)
        if not self.is_expanded:
            self.is_expanded = True
            self.on_expand_change(self.task_id, True)

        self._sync_subtask_visibility(force_show=True)

        if self.subtask_entry is not None:
            self.subtask_entry.focus_set()
            return

        self.subtask_entry = tk.Entry(
            self.subtask_list_frame,
            font=FONT_SUBTASK,
            bg=PALETTE["bg_input"],
            fg=PALETTE["text_primary"],
            insertbackground=PALETTE["accent"],
            highlightbackground=PALETTE["accent"],
            highlightthickness=1,
            bd=2,
            relief=tk.FLAT,
        )
        self.subtask_entry.pack(fill=tk.X, padx=(2, 8), pady=(3, 2))
        self.subtask_entry.focus_set()

        self.subtask_entry.bind("<Return>", self._commit_new_subtask)
        self.subtask_entry.bind("<FocusOut>", self._commit_new_subtask)
        self.subtask_entry.bind("<Escape>", self._cancel_new_subtask)

    def _commit_new_subtask(self, event=None) -> None:
        if self.subtask_entry is None:
            return
        text = self.subtask_entry.get().strip()
        entry = self.subtask_entry
        self.subtask_entry = None
        entry.destroy()

        if text:
            new_sub = self.on_add_subtask(self.task_id, text)
            if new_sub:
                self._mount_subtask_widget(
                    new_sub["id"], new_sub["content"], bool(new_sub["is_completed"])
                )
        self._sync_subtask_visibility()

    def _cancel_new_subtask(self, event=None) -> None:
        if self.subtask_entry is not None:
            entry = self.subtask_entry
            self.subtask_entry = None
            entry.destroy()
        self._sync_subtask_visibility()

    def _handle_subtask_toggle(self, sub_id: int, is_completed: bool) -> None:
        self.on_toggle_subtask(self.task_id, sub_id, is_completed)
        self._sync_subtask_visibility()

    def _handle_subtask_delete(self, sub_id: int) -> None:
        self.on_delete_subtask(self.task_id, sub_id)
        widget = self.subtask_widgets.pop(sub_id, None)
        if widget:
            widget.destroy()
        self._sync_subtask_visibility()

    def toggle_expand(self) -> None:
        if not self.subtask_widgets:
            return
        self.is_expanded = not self.is_expanded
        self.on_expand_change(self.task_id, self.is_expanded)
        self._sync_subtask_visibility()

    def _sync_subtask_visibility(self, force_show: bool = False) -> None:
        total = len(self.subtask_widgets)
        done = sum(1 for w in self.subtask_widgets.values() if w.is_completed)

        if total > 0:
            arrow = "▾" if self.is_expanded else "▸"
            self.expand_btn.configure(text=f"{arrow} {done}/{total}")
            self.expand_btn.pack(side=tk.RIGHT, before=self.add_sub_btn)
        else:
            self.expand_btn.configure(text="")
            self.expand_btn.pack_forget()

        if (total > 0 and self.is_expanded) or force_show:
            self.subtask_container.pack(fill=tk.X, expand=True)
        else:
            self.subtask_container.pack_forget()

    # --- Responsive Wrapping & Hover ---

    def set_wraplength(self, wraplength: int) -> None:
        self._wraplength = max(100, wraplength)
        self.text_lbl.configure(wraplength=self._wraplength)
        for sub in self.subtask_widgets.values():
            sub.set_wraplength(self._wraplength)

    def _on_enter(self, event=None) -> None:
        self.del_btn.configure(fg=PALETTE["text_muted"])
        self.add_sub_btn.configure(fg=PALETTE["text_muted"])
        self.drag_lbl.configure(fg=PALETTE["text_muted"])

    def _on_leave(self, event=None) -> None:
        self.del_btn.configure(fg=PALETTE["bg_surface"])
        self.add_sub_btn.configure(fg=PALETTE["bg_surface"])
        self.drag_lbl.configure(fg=PALETTE["border_faint"])

    # --- Single Click (Select + Toggle) vs Double Click (Inline Edit) ---

    def _on_label_single_click(self, event=None) -> None:
        self.on_select(self.task_id)
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
        raw_text = self.edit_entry.get().strip()
        self._close_editor()

        if raw_text:
            self.on_edit(self.task_id, raw_text)

    def _cancel_edit(self, event=None) -> None:
        self._close_editor()

    def _close_editor(self) -> None:
        if self.edit_entry is not None:
            entry = self.edit_entry
            self.edit_entry = None
            entry.destroy()
        self.text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _update_visuals(self) -> None:
        if self.is_completed:
            self.check_btn.configure(text="✔", fg=PALETTE["accent"])
            self.text_lbl.configure(font=FONT_TASK_DONE, fg=PALETTE["text_muted"])
        else:
            self.check_btn.configure(text="○", fg=PALETTE["text_muted"])
            self.text_lbl.configure(font=FONT_TASK, fg=PALETTE["text_primary"])

    def _handle_toggle(self) -> None:
        self.on_select(self.task_id)
        self.is_completed = not self.is_completed
        self._update_visuals()
        self.on_toggle(self.task_id, self.is_completed)

    def _handle_delete(self) -> None:
        self.on_delete(self.task_id)


class TaskContainer(tk.Frame):
    """Scrollable container supporting mouse wheel scrolling and responsive wraplength."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PALETTE["bg_main"], **kwargs)
        self.current_wraplength = 195

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
        new_wrap = max(110, event.width - 115)
        if abs(new_wrap - self.current_wraplength) > 4:
            self.current_wraplength = new_wrap
            for child in self.inner_frame.winfo_children():
                if isinstance(child, TaskItem):
                    child.set_wraplength(new_wrap)

    def ensure_visible(self, widget: tk.Widget) -> None:
        """Scrolls the canvas minimally if a keyboard-selected task is out of view."""
        self.update_idletasks()
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        total_h = bbox[3] - bbox[1]
        canvas_h = self.canvas.winfo_height()
        if total_h <= canvas_h:
            return

        wy = widget.winfo_y()
        wh = widget.winfo_height()
        top_frac, bot_frac = self.canvas.yview()

        view_top = top_frac * total_h
        view_bot = bot_frac * total_h

        if wy < view_top:
            self.canvas.yview_moveto(wy / total_h)
        elif wy + wh > view_bot:
            self.canvas.yview_moveto((wy + wh - canvas_h) / total_h)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.canvas.winfo_exists():
            bbox = self.canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) > self.canvas.winfo_height():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self) -> None:
        for child in self.inner_frame.winfo_children():
            child.destroy()