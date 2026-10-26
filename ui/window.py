# ui/window.py
import ctypes
from ctypes import wintypes
import signal
import sys
import tkinter as tk
from typing import Callable, Optional, Tuple
from config import (
    PALETTE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_ALPHA,
    WINDOW_RADIUS,
    FONT_HEADER,
    FONT_ICON,
    draw_rounded_rect,
    ensure_logo_ico,
)

# Enable High-DPI sharp font rendering on Windows
if sys.platform.startswith("win"):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    WM_USER = 0x0400
    WM_TRAYICON = WM_USER + 20
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONUP = 0x0205
    GWLP_WNDPROC = -4
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010

    LRESULT = ctypes.c_ssize_t
    WNDPROC_TYPE = ctypes.WINFUNCTYPE(
        LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

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
        init_pinned: bool = True,
        on_geometry_change: Optional[Callable[[int, int], None]] = None,
        on_pin_change: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__()

        signal.signal(signal.SIGINT, lambda *_: self.close_app())
        self._poll_terminal()

        self.width = WINDOW_WIDTH
        self.height = WINDOW_HEIGHT
        self.is_pinned = init_pinned
        self.on_geometry_change = on_geometry_change
        self.on_pin_change = on_pin_change
        self._nid = None
        self._old_wndproc = None
        self._wndproc_ref = None
        self.logo_path = ensure_logo_ico()

        # Set window icon
        try:
            self.iconbitmap(default=str(self.logo_path))
        except Exception:
            pass

        # Frameless & Transparent-Corner Setup
        self.overrideredirect(True)
        self.configure(bg=PALETTE["chroma_key"], bd=0, highlightthickness=0)
        if sys.platform.startswith("win"):
            self.attributes("-transparentcolor", PALETTE["chroma_key"])
        self.attributes("-alpha", WINDOW_ALPHA)
        self.attributes("-topmost", self.is_pinned)

        # Initial Position
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        if init_pos:
            x, y = init_pos
            x = max(0, min(x, screen_w - 80))
            y = max(0, min(y, screen_h - 80))
        else:
            x = screen_w - self.width - 40
            y = 60

        self.geometry(f"{self.width}x{self.height}+{x}+{y}")

        self._drag_start_x = 0
        self._drag_start_y = 0

        # Rounded Root Canvas Shell
        self.shell_canvas = tk.Canvas(
            self,
            width=self.width,
            height=self.height,
            bg=PALETTE["chroma_key"],
            bd=0,
            highlightthickness=0,
        )
        self.shell_canvas.pack(fill=tk.BOTH, expand=True)

        draw_rounded_rect(
            self.shell_canvas,
            0, 0, self.width, self.height,
            radius=WINDOW_RADIUS,
            corners=(True, True, True, True),
            fill=PALETTE["bg_main"],
            outline="",
        )

        header_h = 40
        draw_rounded_rect(
            self.shell_canvas,
            0, 0, self.width, header_h,
            radius=WINDOW_RADIUS,
            corners=(True, True, False, False),
            fill=PALETTE["bg_surface"],
            outline="",
        )

        self._build_header(header_h)

        self.content_frame = tk.Frame(
            self.shell_canvas, bg=PALETTE["bg_main"], bd=0, highlightthickness=0
        )
        self.shell_canvas.create_window(
            14,
            header_h + 12,
            window=self.content_frame,
            anchor="nw",
            width=self.width - 28,
            height=self.height - header_h - 26,
        )

        self.after(50, self._init_system_tray)

    def _poll_terminal(self) -> None:
        self.after(250, self._poll_terminal)

    def _build_header(self, header_h: int) -> None:
        """Builds draggable header with vector app logo, task counter, and controls."""
        self.header = tk.Frame(
            self.shell_canvas, bg=PALETTE["bg_surface"], bd=0, highlightthickness=0
        )
        self.shell_canvas.create_window(
            12, 4,
            window=self.header,
            anchor="nw",
            width=self.width - 24,
            height=header_h - 6,
        )

        # App Logo Badge in Header (18x18 rounded navy icon with crisp checkmark)
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

        self.title_lbl = tk.Label(
            self.header,
            text="TASKS",
            font=FONT_HEADER,
            bg=PALETTE["bg_surface"],
            fg=PALETTE["accent"],
            padx=2,
        )
        self.title_lbl.pack(side=tk.LEFT)

        for widget in (self.header, self.logo_canvas, self.title_lbl):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._stop_drag)

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

    def _init_system_tray(self) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32

            hwnd = self.winfo_id()

            set_wnd_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            set_wnd_long.argtypes = [wintypes.HWND, ctypes.c_int, WNDPROC_TYPE]
            set_wnd_long.restype = ctypes.c_void_p

            user32.CallWindowProcW.argtypes = [
                ctypes.c_void_p,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            user32.CallWindowProcW.restype = LRESULT

            self._wndproc_ref = WNDPROC_TYPE(self._tray_wndproc)
            self._old_wndproc = set_wnd_long(hwnd, GWLP_WNDPROC, self._wndproc_ref)

            # Load custom assets/Minimal-To-Do-Logo.ico for System Tray
            hicon = user32.LoadImageW(
                None, str(self.logo_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE
            )
            if not hicon:
                hicon = shell32.ExtractIconW(0, sys.executable, 0) or user32.LoadIconW(0, 32512)

            self._nid = NOTIFYICONDATAW()
            self._nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            self._nid.hWnd = hwnd
            self._nid.uID = 1
            self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            self._nid.uCallbackMessage = WM_TRAYICON
            self._nid.hIcon = hicon
            self._nid.szTip = "Minimal To-Do"

            shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid))

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
            self.tray_menu.add_command(label="Show Tasks", command=self.bring_to_front)
            self.tray_menu.add_command(label="Toggle Pin (Always on Top)", command=self.toggle_pin)
            self.tray_menu.add_separator()
            self.tray_menu.add_command(label="Exit", command=self.close_app)
        except Exception:
            pass

    def _tray_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam == WM_LBUTTONUP:
                self.after(1, self.bring_to_front)
                return 0
            elif lparam == WM_RBUTTONUP:
                self.after(1, self._show_tray_menu)
                return 0
        return ctypes.windll.user32.CallWindowProcW(
            self._old_wndproc, hwnd, msg, wparam, lparam
        )

    def _show_tray_menu(self) -> None:
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        self.focus_force()
        self.tray_menu.tk_popup(x, y)

    def bring_to_front(self) -> None:
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        if not self.is_pinned:
            self.after(100, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def close_app(self) -> None:
        if self._nid is not None and sys.platform.startswith("win"):
            try:
                ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
                self._nid = None
            except Exception:
                pass
        self.destroy()

    def update_title_count(self, active_count: int, total_count: int) -> None:
        if total_count == 0:
            self.title_lbl.configure(text="TASKS")
        else:
            self.title_lbl.configure(text=f"TASKS  •  {active_count}/{total_count}")

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _on_drag(self, event: tk.Event) -> None:
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y
        self.geometry(f"+{new_x}+{new_y}")

    def _stop_drag(self, event: tk.Event) -> None:
        if self.on_geometry_change:
            self.on_geometry_change(self.winfo_x(), self.winfo_y())

    def toggle_pin(self) -> None:
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            fg=PALETTE["accent"] if self.is_pinned else PALETTE["text_muted"]
        )
        if self.on_pin_change:
            self.on_pin_change(self.is_pinned)

if __name__ == "__main__":
    app = DesktopTodoWindow()
    app.mainloop()