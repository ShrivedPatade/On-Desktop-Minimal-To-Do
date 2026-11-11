# ui/window.py
import ctypes
from ctypes import wintypes
import signal
import sys
import tkinter as tk
from typing import Callable, List, Optional, Tuple
from config import (
    PALETTE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    MIN_WIDTH,
    MIN_HEIGHT,
    HEADER_HEIGHT,
    FOOTER_HEIGHT,
    WINDOW_ALPHA,
    WINDOW_RADIUS,
    FONT_HEADER,
    FONT_FOOTER,
    FONT_ICON,
    draw_rounded_rect,
    ensure_logo_ico,
)

# Enable High-DPI sharp font rendering & define 64-bit Win32 signatures
if sys.platform.startswith("win"):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32

    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    WM_USER = 0x0400
    WM_TRAYICON = WM_USER + 20
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    WM_NULL = 0x0000
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010

    HWND_TOP = 0
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

    LRESULT = ctypes.c_ssize_t
    WNDPROC_TYPE = ctypes.WINFUNCTYPE(
        LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

    user32.DefWindowProcW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.DefWindowProcW.restype = LRESULT

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC_TYPE),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
            ("hIconSm", wintypes.HICON),
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 64),
        ]


class DesktopTodoWindow(tk.Tk):
    def __init__(
        self,
        init_pos: Optional[Tuple[int, int]] = None,
        init_size: Optional[Tuple[int, int]] = None,
        init_pinned: bool = True,
        init_shaded: bool = False,
        on_geometry_change: Optional[Callable[[int, int, int, int], None]] = None,
        on_pin_change: Optional[Callable[[bool], None]] = None,
        on_shade_change: Optional[Callable[[bool], None]] = None,
        on_clear_completed: Optional[Callable[[], None]] = None,
    ):
        super().__init__()

        # --- State & Callbacks ---
        self.width = max(MIN_WIDTH, init_size[0]) if init_size else WINDOW_WIDTH
        self.height = max(MIN_HEIGHT, init_size[1]) if init_size else WINDOW_HEIGHT
        self.is_pinned = init_pinned
        self.is_shaded = init_shaded

        self.on_geometry_change = on_geometry_change
        self.on_pin_change = on_pin_change
        self.on_shade_change = on_shade_change
        self.on_clear_completed = on_clear_completed

        self._nid = None
        self._tray_hwnd = None
        self._wndproc_ref = None
        self._pending_tray_events: List[str] = []
        self.logo_path = ensure_logo_ico()

        # Terminal Ctrl+C & Tray Event Queue Polling
        signal.signal(signal.SIGINT, lambda *_: self.close_app())
        self._poll_system()

        try:
            self.iconbitmap(default=str(self.logo_path))
        except Exception:
            pass

        # --- Frameless & Transparent-Corner Setup ---
        self.overrideredirect(True)
        self.configure(bg=PALETTE["chroma_key"], bd=0, highlightthickness=0)
        if sys.platform.startswith("win"):
            self.attributes("-transparentcolor", PALETTE["chroma_key"])
        self.attributes("-alpha", WINDOW_ALPHA)
        self.attributes("-topmost", self.is_pinned)

        # --- Initial Position ---
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        if init_pos:
            x, y = init_pos
            x = max(0, min(x, screen_w - 80))
            y = max(0, min(y, screen_h - 80))
        else:
            x = screen_w - self.width - 40
            y = 60

        cur_h = HEADER_HEIGHT if self.is_shaded else self.height
        self.geometry(f"{self.width}x{cur_h}+{x}+{y}")

        # Drag & Resize tracking
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = self.width
        self._resize_start_h = self.height

        # --- Rounded Root Canvas Shell ---
        self.shell_canvas = tk.Canvas(
            self,
            width=self.width,
            height=cur_h,
            bg=PALETTE["chroma_key"],
            bd=0,
            highlightthickness=0,
        )
        self.shell_canvas.pack(fill=tk.BOTH, expand=True)

        # Build Header, Content Frame, and Footer
        self._build_header()

        self.content_frame = tk.Frame(
            self.shell_canvas, bg=PALETTE["bg_main"], bd=0, highlightthickness=0
        )

        self._build_footer()

        # Draw rounded shell and place windows
        self._redraw_shell()

        # Initialize isolated System Tray Icon
        self.after(50, self._init_system_tray)

    def _poll_system(self) -> None:
        """Processes tray clicks on the main thread and keeps Ctrl+C responsive."""
        while self._pending_tray_events:
            evt = self._pending_tray_events.pop(0)
            if evt == "left":
                self.bring_to_front()
            elif evt == "right":
                self._show_tray_menu()
        self.after(80, self._poll_system)

    # --- Shell Redraw (Handles Shade Mode & Dynamic Resizing) ---

    def _redraw_shell(self) -> None:
        """Redraws the rounded background and repositions internal containers."""
        self.shell_canvas.delete("shell_bg")
        cur_h = HEADER_HEIGHT if self.is_shaded else self.height

        if self.is_shaded:
            # Shade Mode: Only the header pill is drawn, with all 4 corners rounded
            draw_rounded_rect(
                self.shell_canvas,
                0, 0, self.width, HEADER_HEIGHT,
                radius=WINDOW_RADIUS // 1.3,
                corners=(True, True, True, True),
                fill=PALETTE["bg_surface"],
                outline="",
                tags="shell_bg",
            )
            self.shell_canvas.delete("body_win")
            self.shell_canvas.delete("footer_win")
        else:
            # Normal Mode: Full rounded body + top-rounded header
            draw_rounded_rect(
                self.shell_canvas,
                0, 0, self.width, cur_h,
                radius=WINDOW_RADIUS,
                corners=(True, True, True, True),
                fill=PALETTE["bg_main"],
                outline="",
                tags="shell_bg",
            )
            draw_rounded_rect(
                self.shell_canvas,
                0, 0, self.width, HEADER_HEIGHT,
                radius=WINDOW_RADIUS,
                corners=(True, True, False, False),
                fill=PALETTE["bg_surface"],
                outline="",
                tags="shell_bg",
            )

            # Position Content Frame
            content_h = max(50, cur_h - HEADER_HEIGHT - FOOTER_HEIGHT - 12)
            self.shell_canvas.delete("body_win")
            self.shell_canvas.create_window(
                14,
                HEADER_HEIGHT + 10,
                window=self.content_frame,
                anchor="nw",
                width=self.width - 28,
                height=content_h,
                tags="body_win",
            )

            # Position Footer Bar (Clear Completed + Resize Grip)
            self.shell_canvas.delete("footer_win")
            self.shell_canvas.create_window(
                12,
                cur_h - FOOTER_HEIGHT - 2,
                window=self.footer,
                anchor="nw",
                width=self.width - 18,
                height=FOOTER_HEIGHT,
                tags="footer_win",
            )

        # Position Header Controls
        self.shell_canvas.delete("header_win")
        self.shell_canvas.create_window(
            12, 4,
            window=self.header,
            anchor="nw",
            width=self.width - 24,
            height=HEADER_HEIGHT - 8,
            tags="header_win",
        )

    # --- Header & Collapsible Shade Mode ---

    def _build_header(self) -> None:
        self.header = tk.Frame(
            self.shell_canvas, bg=PALETTE["bg_surface"], bd=0, highlightthickness=0
        )

        # App Logo Badge
        self.logo_canvas = tk.Canvas(
            self.header,
            width=18,
            height=18,
            bg=PALETTE["bg_surface"],
            bd=0,
            highlightthickness=0,
        )
        self.logo_canvas.pack(side=tk.LEFT, padx=(2, 4))
        draw_rounded_rect(
            self.logo_canvas, 1, 1, 17, 17, radius=5,
            fill=PALETTE["accent"], outline=""
        )
        self.logo_canvas.create_line(
            5, 9, 8, 12, 13, 6,
            fill=PALETTE["bg_main"], width=1.8, capstyle=tk.ROUND, joinstyle=tk.ROUND
        )

        # Title Label
        self.title_lbl = tk.Label(
            self.header,
            text="TASKS",
            font=FONT_HEADER,
            bg=PALETTE["bg_surface"],
            fg=PALETTE["accent"],
            padx=2,
        )
        self.title_lbl.pack(side=tk.LEFT)

        # Bind Drag and Double-Click Shade Toggle to header elements
        for widget in (self.header, self.logo_canvas, self.title_lbl):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._stop_drag)
            widget.bind("<Double-Button-1>", lambda _: self.toggle_shade())

        # Close Button
        self.close_btn = tk.Button(
            self.header,
            text="✕",
            font=FONT_ICON,
            bg=PALETTE["bg_surface"],
            fg=PALETTE["text_muted"],
            activebackground=PALETTE["danger"],
            activeforeground="#FFFFFF",
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            command=self.close_app,
        )
        self.close_btn.pack(side=tk.RIGHT, fill=tk.Y)

        # Pin / Always-on-top Button
        self.pin_btn = tk.Button(
            self.header,
            text="📌",
            font=FONT_ICON,
            bg=PALETTE["bg_surface"],
            fg=PALETTE["accent"] if self.is_pinned else PALETTE["text_muted"],
            activebackground=PALETTE["bg_surface"],
            activeforeground=PALETTE["accent"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            padx=6,
            command=self.toggle_pin,
        )
        self.pin_btn.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Footer (Clear Completed Button & Drag-to-Resize Grip) ---

    def _build_footer(self) -> None:
        self.footer = tk.Frame(
            self.shell_canvas, bg=PALETTE["bg_main"], bd=0, highlightthickness=0
        )

        # Subtle "Clear Completed" button on bottom-left
        self.clear_btn = tk.Label(
            self.footer,
            text="",
            font=FONT_FOOTER,
            bg=PALETTE["bg_main"],
            fg=PALETTE["text_muted"],
            cursor="hand2",
            padx=2,
        )
        self.clear_btn.pack(side=tk.LEFT, anchor="s", pady=3)
        self.clear_btn.bind("<Button-1>", self._handle_clear_click)
        self.clear_btn.bind(
            "<Enter>",
            lambda _: self.clear_btn.configure(fg=PALETTE["danger"])
            if self.clear_btn.cget("text")
            else None,
        )
        self.clear_btn.bind(
            "<Leave>",
            lambda _: self.clear_btn.configure(fg=PALETTE["text_muted"]),
        )

        # Bottom-Right Corner Resize Grip
        self.grip_canvas = tk.Canvas(
            self.footer,
            width=16,
            height=16,
            bg=PALETTE["bg_main"],
            bd=0,
            highlightthickness=0,
            cursor="size_nw_se",
        )
        self.grip_canvas.pack(side=tk.RIGHT, anchor="se", pady=2)

        # Draw diagonal grip lines
        for offset in (4, 8, 12):
            self.grip_canvas.create_line(
                15 - offset, 15, 15, 15 - offset,
                fill=PALETTE["text_muted"],
                width=1.5,
                capstyle=tk.ROUND,
            )

        self.grip_canvas.bind("<ButtonPress-1>", self._start_resize)
        self.grip_canvas.bind("<B1-Motion>", self._on_resize)
        self.grip_canvas.bind("<ButtonRelease-1>", self._stop_resize)

    def _handle_clear_click(self, event=None) -> None:
        if self.clear_btn.cget("text") and self.on_clear_completed:
            self.on_clear_completed()

    def update_status_counts(self, active_count: int, total_count: int) -> None:
        """Updates both the header counter and the footer 'Clear done' button."""
        if total_count == 0:
            self.title_lbl.configure(text="TASKS")
        else:
            self.title_lbl.configure(text=f"TASKS  •  {active_count}/{total_count}")

        completed_count = total_count - active_count
        if completed_count > 0:
            self.clear_btn.configure(
                text=f"Clear done ({completed_count})", cursor="hand2"
            )
        else:
            self.clear_btn.configure(text="", cursor="")

    # --- Collapsible Shade Mode Toggle ---

    def toggle_shade(self) -> None:
        """Collapses window to header bar or restores full height."""
        self.is_shaded = not self.is_shaded
        target_h = HEADER_HEIGHT if self.is_shaded else self.height
        self.geometry(f"{self.width}x{target_h}+{self.winfo_x()}+{self.winfo_y()}")
        self._redraw_shell()
        if self.on_shade_change:
            self.on_shade_change(self.is_shaded)

    # --- Drag-to-Resize Mechanics ---

    def _start_resize(self, event: tk.Event) -> None:
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_w = self.width
        self._resize_start_h = self.height

    def _on_resize(self, event: tk.Event) -> None:
        if self.is_shaded:
            return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y

        new_w = max(MIN_WIDTH, self._resize_start_w + dx)
        new_h = max(MIN_HEIGHT, self._resize_start_h + dy)

        if new_w != self.width or new_h != self.height:
            self.width = new_w
            self.height = new_h
            self.geometry(f"{self.width}x{self.height}+{self.winfo_x()}+{self.winfo_y()}")
            self._redraw_shell()

    def _stop_resize(self, event: tk.Event) -> None:
        if self.on_geometry_change:
            self.on_geometry_change(
                self.winfo_x(), self.winfo_y(), self.width, self.height
            )

    # --- Window Dragging ---

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _on_drag(self, event: tk.Event) -> None:
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y
        self.geometry(f"+{new_x}+{new_y}")

    def _stop_drag(self, event: tk.Event) -> None:
        if self.on_geometry_change:
            self.on_geometry_change(
                self.winfo_x(), self.winfo_y(), self.width, self.height
            )

    # --- Pin / Topmost Management ---

    def _get_top_hwnd(self) -> int:
        if sys.platform.startswith("win"):
            parent = user32.GetParent(self.winfo_id())
            return parent if parent else self.winfo_id()
        return self.winfo_id()

    def toggle_pin(self) -> None:
        """Toggles Always-on-Top state and syncs header button & DB."""
        self.is_pinned = not self.is_pinned

        # Update native topmost state via Tk's 64-bit wrapper
        self.attributes("-topmost", self.is_pinned)
        self.update_idletasks()

        self.pin_btn.configure(
            fg=PALETTE["accent"] if self.is_pinned else PALETTE["text_muted"]
        )
        if self.on_pin_change:
            self.on_pin_change(self.is_pinned)

    # --- Crash-Proof Isolated Win32 System Tray ---

    def _init_system_tray(self) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            hinst = kernel32.GetModuleHandleW(None)
            class_name = "MinimalToDoTrayMsgWindow"

            self._wndproc_ref = WNDPROC_TYPE(self._tray_wndproc)

            wc = WNDCLASSEXW()
            wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
            wc.lpfnWndProc = self._wndproc_ref
            wc.hInstance = hinst
            wc.lpszClassName = class_name
            user32.RegisterClassExW(ctypes.byref(wc))

            # Dedicated hidden Win32 window for tray events (never touches Tk's HWND)
            self._tray_hwnd = user32.CreateWindowExW(
                0, class_name, "MinimalToDoTray", 0,
                0, 0, 0, 0, 0, None, hinst, None
            )

            hicon = user32.LoadImageW(
                None, str(self.logo_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE
            )
            if not hicon:
                hicon = shell32.ExtractIconW(0, sys.executable, 0) or user32.LoadIconW(0, 32512)

            self._nid = NOTIFYICONDATAW()
            self._nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            self._nid.hWnd = self._tray_hwnd
            self._nid.uID = 1
            self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            self._nid.uCallbackMessage = WM_TRAYICON
            self._nid.hIcon = hicon
            self._nid.szTip = "Minimal To-Do"

            shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid))

            # Right-click context menu
            self.tray_menu = tk.Menu(
                self,
                tearoff=0,
                bg=PALETTE["bg_input"],
                fg=PALETTE["text_primary"],
                activebackground=PALETTE["accent"],
                activeforeground="#FFFFFF",
                font=("Segoe UI", 9),
                bd=1,
                relief=tk.SOLID,
            )
            self.tray_menu.add_command(
                label="Bring to Front", command=self.bring_to_front
            )
            self.tray_menu.add_command(
                label="Collapse / Expand (Shade)", command=self.toggle_shade
            )
            self.tray_menu.add_command(
                label="Toggle Pin (Always on Top)", command=self.toggle_pin
            )
            if self.on_clear_completed:
                self.tray_menu.add_command(
                    label="Clear Completed Tasks", command=self.on_clear_completed
                )
            self.tray_menu.add_separator()
            self.tray_menu.add_command(label="Close", command=self.close_app)
        except Exception:
            pass

    def _tray_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            event_code = lparam & 0xFFFF
            if event_code in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self._pending_tray_events.append("left")
                return 0
            elif event_code == WM_RBUTTONUP:
                self._pending_tray_events.append("right")
                return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_tray_menu(self) -> None:
        self.bring_to_front()
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        self.tray_menu.tk_popup(x, y)
        self.tray_menu.grab_release()

    def bring_to_front(self) -> None:
        """Raises the widget in front of active apps without locking pin state."""
        self.deiconify()
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        if not self.is_pinned:
            # Drop topmost flag after raising so clicking another app sends it to background
            self.after(60, lambda: self.attributes("-topmost", False))

    def close_app(self) -> None:
        if sys.platform.startswith("win"):
            if self._nid is not None:
                try:
                    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
                    self._nid = None
                except Exception:
                    pass
            if self._tray_hwnd:
                try:
                    user32.DestroyWindow(self._tray_hwnd)
                    self._tray_hwnd = None
                except Exception:
                    pass
        self.destroy()