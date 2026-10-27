"""Utility functions for UI components."""

import contextlib
import os
import platform as platform_module
import re
import shutil
import subprocess
import sys
import tkinter
import webbrowser
from pathlib import Path

import customtkinter as ctk


def trace_variable(var, mode, callback):
    """
    Cross-version compatible variable trace.

    Args:
        var: Tkinter variable (StringVar, IntVar, etc.)
        mode: "w" for write, "r" for read, "u" for undefine
        callback: Callback function

    Returns:
        Trace id (can be used to remove trace later)
    """
    # Python 3.11+ uses trace_add instead of trace
    if hasattr(var, "trace_add"):
        mode_map = {"w": "write", "r": "read", "u": "undefine"}
        return var.trace_add(mode_map.get(mode, mode), callback)
    else:
        return var.trace(mode, callback)


def raise_existing_window(window) -> bool:
    """Bring an already open popup forward; False if there is none to reuse.

    Popups that edit the same data are opened once each, so a second click
    raises the existing window instead of stacking another copy.
    """
    if window is None or not window.winfo_exists():
        return False
    window.deiconify()
    window.lift()
    window.focus_force()
    return True


def debounced_trace(widget, var, callback, delay_ms: int = 150) -> None:
    """Call callback() once writes to var pause for delay_ms.

    Filtering an icon grid redraws every cell; running it on each keystroke
    stalls typing. The pending call is dropped if widget is destroyed.
    """
    job = None

    def fire():
        nonlocal job
        job = None
        if widget.winfo_exists():
            callback()

    def on_write(*_):
        nonlocal job
        if job is not None:
            widget.after_cancel(job)
        job = widget.after(delay_ms, fire)

    var.trace_add("write", on_write)


def force_render_dialog(dialog):
    """
    Force proper rendering of a CTkToplevel dialog on Linux and all platforms.

    Call this immediately after creating a CTkToplevel dialog to ensure
    it renders properly, especially important on Linux.

    Args:
        dialog: The CTkToplevel dialog to render
    """
    try:
        dialog.update_idletasks()
        dialog.lift()
        dialog.focus_force()
    except Exception:
        pass


# Title bar height used where the window manager does not report it (Linux)
_TITLE_BAR_FALLBACK_PX = 40
# Gap kept between a fitted window and the work area edges
_WORK_AREA_GAP_PX = 8

_linux_work_area: tuple[int, int, int, int] | None = None


def _win_work_area(window, point: tuple[int, int] | None):
    """Work area (x, y, w, h) of the monitor at point, or of the window's monitor."""
    import ctypes
    from ctypes import wintypes

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.restype = wintypes.HMONITOR
    user32.MonitorFromWindow.restype = wintypes.HMONITOR
    MONITOR_DEFAULTTONEAREST = 2
    if point is not None:
        monitor = user32.MonitorFromPoint(
            wintypes.POINT(*point), MONITOR_DEFAULTTONEAREST
        )
    else:
        try:
            hwnd = wintypes.HWND(int(window.wm_frame(), 16))
            monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        except (ValueError, tkinter.TclError):
            # No frame window yet: use the primary monitor
            monitor = user32.MonitorFromPoint(
                wintypes.POINT(0, 0), MONITOR_DEFAULTTONEAREST
            )
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(wintypes.HMONITOR(monitor), ctypes.byref(info)):
        return None
    r = info.rcWork
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def _x11_work_area():
    """_NET_WORKAREA of the first desktop, read once per process."""
    global _linux_work_area
    if _linux_work_area is None:
        _linux_work_area = (0, 0, 0, 0)
        try:
            out = subprocess.run(
                ["xprop", "-root", "_NET_WORKAREA"],
                capture_output=True,
                text=True,
                timeout=2,
            ).stdout
            values = [int(v) for v in re.findall(r"\d+", out.split("=", 1)[1])][:4]
            if len(values) == 4 and values[2] > 0 and values[3] > 0:
                _linux_work_area = tuple(values)
        except Exception:
            pass
    return _linux_work_area if _linux_work_area[2] else None


def get_work_area(window, point: tuple[int, int] | None = None):
    """Usable desktop area (x, y, width, height) in physical pixels.

    Excludes the taskbar or panels. On Windows it is the work area of the
    monitor containing point (screen coordinates), or of the monitor the
    window is on when point is None. Elsewhere it is the X11 _NET_WORKAREA,
    falling back to the whole screen.
    """
    area = None
    try:
        if sys.platform == "win32":
            area = _win_work_area(window, point)
        elif sys.platform.startswith("linux"):
            area = _x11_work_area()
    except Exception:
        area = None
    if area is None:
        area = (0, 0, window.winfo_screenwidth(), window.winfo_screenheight())
    return area


def title_bar_height(window) -> int:
    """Height of the window frame above the client area, in physical pixels."""
    if sys.platform == "win32":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            SM_CYCAPTION, SM_CYSIZEFRAME, SM_CXPADDEDBORDER = 4, 33, 92
            metrics = (SM_CYCAPTION, SM_CYSIZEFRAME, SM_CXPADDEDBORDER)
            try:
                hwnd = int(window.wm_frame(), 16)
                dpi = user32.GetDpiForWindow(hwnd)
                if dpi:
                    return sum(user32.GetSystemMetricsForDpi(m, dpi) for m in metrics)
            except (AttributeError, OSError, ValueError):
                pass
            return sum(user32.GetSystemMetrics(m) for m in metrics)
        except Exception:
            pass
    if sys.platform == "darwin":
        return 28
    return _TITLE_BAR_FALLBACK_PX


def fit_size_to_work_area(window, width: int, height: int, point=None):
    """Logical (width, height) shrunk so the framed window fits the work area."""
    get_scale = getattr(window, "_get_window_scaling", None)
    scale = get_scale() if get_scale else 1.0
    _, _, work_w, work_h = get_work_area(window, point)
    gap = 2 * _WORK_AREA_GAP_PX
    max_w = int((work_w - gap) / scale)
    max_h = int((work_h - title_bar_height(window) - gap) / scale)
    return min(width, max_w), min(height, max_h)


def center_window(
    window,
    width: int | None = None,
    height: int | None = None,
    parent=None,
    *,
    align_top: bool = False,
) -> None:
    """Size a window and center it on the work area or over a parent widget.

    CTk scales the width and height passed to geometry() by the window scaling
    factor but leaves the x/y offset untouched. The offset must therefore be
    computed from the scaled (physical) size, otherwise the window lands right
    and below the intended position whenever the scale is not 1.0.

    The x/y offset places the outer frame (title bar included) while the size
    is the client area, so the title bar height is added before clamping the
    window to the work area of its monitor (screen minus taskbar).

    When width and height are both given the size is applied as well. When
    either is omitted only the position is set, using the requested size of
    the window for the missing dimension.

    Args:
        window: Tk or CTk toplevel to position
        width: Logical width, before UI scaling
        height: Logical height, before UI scaling
        parent: Widget to center over; centers on the work area when None
        align_top: Align to the top of the parent's toplevel instead of
            centering vertically
    """
    window.update_idletasks()

    get_scale = getattr(window, "_get_window_scaling", None)
    scale = get_scale() if get_scale else 1.0

    if parent is not None:
        parent.update_idletasks()
        ref_x, ref_y = parent.winfo_rootx(), parent.winfo_rooty()
        ref_w, ref_h = parent.winfo_width(), parent.winfo_height()
        point = (ref_x + ref_w // 2, ref_y + ref_h // 2)
    else:
        point = None
    work_x, work_y, work_w, work_h = get_work_area(window, point)
    if parent is None:
        ref_x, ref_y, ref_w, ref_h = work_x, work_y, work_w, work_h
    title_h = title_bar_height(window)

    # Keep the window fully inside the work area on small displays
    if width is not None or height is not None:
        fit_w, fit_h = fit_size_to_work_area(window, width or 0, height or 0, point)
    if width is not None:
        width = fit_w
        phys_w = round(width * scale)
    else:
        phys_w = window.winfo_reqwidth()
    if height is not None:
        height = fit_h
        phys_h = round(height * scale)
    else:
        phys_h = window.winfo_reqheight()
    outer_h = phys_h + title_h

    x = ref_x + (ref_w - phys_w) // 2
    y = ref_y + (ref_h - outer_h) // 2
    if align_top and parent is not None:
        # wm_geometry gives the outer frame Y (includes titlebar) on all platforms
        m = re.search(r"\+(-?\d+)\+(-?\d+)$", parent.winfo_toplevel().wm_geometry())
        if m:
            y = int(m.group(2))

    x = max(work_x, min(x, work_x + work_w - phys_w))
    y = max(work_y, min(y, work_y + work_h - outer_h))

    if width is not None and height is not None:
        window.geometry(f"{width}x{height}+{x}+{y}")
    else:
        window.geometry(f"+{x}+{y}")


def _colorref(window, color) -> int:
    """Tk color (name, hex or CTk light/dark tuple) as a Win32 COLORREF."""
    if isinstance(color, (tuple, list)):
        color = color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
    r, g, b = (v // 257 for v in window.winfo_rgb(color))
    return r | (g << 8) | (b << 16)


def style_window_frame(window, *, dialog: bool = True) -> None:
    """Match the Windows title bar to the app instead of the system default.

    Caption color = the window background, caption text = the theme text
    color, border = the purple tint (Windows 11; Windows 10 ignores these
    attributes). Dialogs also lose the minimize and maximize buttons. No-op
    on other platforms, where the window manager draws the frame.
    """
    if sys.platform != "win32":
        return
    if isinstance(window, ctk.CTkToplevel):
        # CTkToplevel.resizable() re-applies the dark title bar 10 ms later by
        # withdrawing the window and restoring its state. With two pending
        # calls the second records the state as withdrawn, so a window shown
        # in between stays hidden while holding the grab. CTkToplevel already
        # set the title bar in __init__; the later calls only redo it.
        window._deactivate_windows_window_header_manipulation = True

    def apply():
        import ctypes

        from er_save_manager.ui import palette

        try:
            hwnd = int(window.wm_frame(), 16)
        except (ValueError, tkinter.TclError):
            return
        DWMWA_BORDER_COLOR, DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR = 34, 35, 36
        try:
            fg = window.cget("fg_color")
        except (ValueError, tkinter.TclError):
            fg = ("#EBEBEB", "#242424")
        colors = {
            DWMWA_CAPTION_COLOR: fg,
            DWMWA_TEXT_COLOR: ctk.ThemeManager.theme["CTkLabel"]["text_color"],
            DWMWA_BORDER_COLOR: palette.PURPLE_TINT,
        }
        dwm = ctypes.windll.dwmapi
        for attr, color in colors.items():
            try:
                value = ctypes.c_int(_colorref(window, color))
                dwm.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
                )
            except (OSError, tkinter.TclError):
                pass
        if dialog:
            user32 = ctypes.windll.user32
            GWL_STYLE = -16
            WS_MAXIMIZEBOX, WS_MINIMIZEBOX = 0x00010000, 0x00020000
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(
                hwnd, GWL_STYLE, style & ~(WS_MAXIMIZEBOX | WS_MINIMIZEBOX)
            )
            # SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x1 | 0x2 | 0x4 | 0x10 | 0x20)

    try:
        window.update_idletasks()
        apply()
    except Exception:
        pass


# Widget classes whose own class bindings scroll them on Button-4/5.
_SELF_SCROLLING_CLASSES = frozenset({"Treeview", "Listbox", "Text"})


def _wheel_target(widget, sequence):
    """Canvas of the innermost CTkScrollableFrame under widget that can scroll.

    None when a widget on the way up handles the wheel itself (own binding
    for sequence, or a Treeview/Listbox/Text). A fully visible frame passes
    the wheel on to the next one out.
    """
    while widget is not None:
        if widget.winfo_class() in _SELF_SCROLLING_CLASSES:
            return None
        frame = None
        if isinstance(widget, ctk.CTkScrollableFrame):
            frame = widget
        elif isinstance(widget, tkinter.Canvas):
            # Pointer over the canvas area around the content frame.
            frame = next(
                (
                    c
                    for c in widget.winfo_children()
                    if isinstance(c, ctk.CTkScrollableFrame)
                    and c._parent_canvas is widget
                ),
                None,
            )
            if frame is None and tkinter.Misc.bind(widget, sequence):
                return None
        elif tkinter.Misc.bind(widget, sequence):
            return None
        if frame is not None:
            canvas = frame._parent_canvas
            if canvas.yview() != (0.0, 1.0):
                return canvas
        widget = widget.master
    return None


def _wheel_linux(event):
    widget = event.widget
    try:
        if isinstance(widget, str):
            widget = event.widget.nametowidget(widget)
        sequence = f"<Button-{event.num}>"
        canvas = _wheel_target(widget, sequence)
        if canvas is not None:
            canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
    except (AttributeError, KeyError, tkinter.TclError):
        # Widget path of a Tk-internal window, or a widget already destroyed.
        return


_ctk_frame_wheel = ctk.CTkScrollableFrame._mouse_wheel_all


def _frame_wheel(self, event):
    """<MouseWheel> handler that scrolls only the innermost scrollable target.

    CTkScrollableFrame binds <MouseWheel> with bind_all, so every frame
    around the pointer scrolls, together with any list, map or grid that
    handles the wheel itself.
    """
    if self._shift_pressed:
        _ctk_frame_wheel(self, event)
        return
    widget = event.widget
    try:
        if isinstance(widget, str):
            widget = self.nametowidget(widget)
        target = _wheel_target(widget, "<MouseWheel>")
    except (AttributeError, KeyError, tkinter.TclError):
        return
    if target is self._parent_canvas:
        _ctk_frame_wheel(self, event)


# Patched on the class so frames created anywhere in the application get it.
# Depends on CTkScrollableFrame internals (customtkinter 5.2.x).
ctk.CTkScrollableFrame._mouse_wheel_all = _frame_wheel


def bind_mousewheel(widget, target_widget=None):
    """
    Enable wheel scrolling of CTkScrollableFrames on Linux.

    Tk 8.6 on X11 reports the wheel as Button-4/5, which CTkScrollableFrame
    does not handle. One application-wide binding scrolls the innermost
    scrollable frame under the pointer, so rows added later and nested frames
    need no per-widget bindings. The arguments are kept for existing callers;
    any widget of the application installs the binding.
    """
    if not sys.platform.startswith("linux"):
        return
    root = (target_widget or widget)._root()
    if getattr(root, "_er_wheel_bound", False):
        return
    root._er_wheel_bound = True
    root.bind_all("<Button-4>", _wheel_linux, add="+")
    root.bind_all("<Button-5>", _wheel_linux, add="+")


# Dropdown rows added per event loop turn after the visible ones
_COMBO_BATCH = 10


def patch_combo_scroll(combo, max_visible_rows: int = 20, row_height: int = 28):
    """
    Replace a CTkComboBox's dropdown with a scrollable popup.
    """

    def _open():
        values = combo.cget("values")
        if not values:
            return

        theme = ctk.ThemeManager.theme["DropdownMenu"]

        popup = ctk.CTkToplevel(combo)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        combo.update()
        # Screen coordinates and winfo sizes are physical pixels, while the
        # popup geometry and widget sizes are logical and get scaled by CTk.
        scale = popup._get_window_scaling()
        text_font = ctk.CTkFont()
        text_width = max(text_font.measure(v) for v in values)
        pad = int(combo._apply_widget_scaling(48))
        width = round(max(combo.winfo_width(), text_width + pad) / scale)

        x = combo.winfo_rootx()
        top = combo.winfo_rooty()
        below = top + combo.winfo_height() + 2
        screen_h = popup.winfo_screenheight()
        row_px = row_height * scale
        rows_below = int((screen_h - below - 40) // row_px)
        rows_above = int((top - 2 - 40) // row_px)
        wanted = min(len(values), max_visible_rows)
        open_up = rows_below < wanted and rows_above > rows_below
        rows = max(min(wanted, rows_above if open_up else rows_below), 1)
        height = rows * row_height + 8
        y = top - 2 - round(height * scale) if open_up else below

        geometry = f"{width}x{height}+{x}+{y}"
        popup.geometry(geometry)

        frame = ctk.CTkScrollableFrame(
            popup,
            width=width - 4,
            height=height - 4,
            fg_color=theme["fg_color"],
            corner_radius=0,
        )
        frame.pack(fill="both", expand=True)
        bind_mousewheel(frame)

        # Clicks go to the popup while it holds the grab, and a click outside
        # it closes it. FocusOut alone is not enough, since an overrideredirect
        # window often never gets focus on Linux. The grab of a modal dialog
        # the combo sits in is handed back on close, so the dialog stays modal.
        previous_grab = combo.grab_current()
        closed = False

        def _close(_e=None):
            nonlocal closed
            if closed:
                return
            closed = True
            try:
                popup.grab_release()
                popup.destroy()
            except Exception:
                pass
            if previous_grab is not None:
                with contextlib.suppress(Exception):
                    previous_grab.grab_set()

        def _on_click(event):
            left, top = popup.winfo_rootx(), popup.winfo_rooty()
            inside = (
                left <= event.x_root < left + popup.winfo_width()
                and top <= event.y_root < top + popup.winfo_height()
            )
            if not inside:
                _close()

        def _select(value):
            _close()
            combo.set(value)
            if combo._command is not None:
                combo._command(value)

        def _add_rows(start: int, count: int) -> None:
            """Buttons for values[start:start + count]; the ones that fit the
            popup are made before it shows, the rest in later event loop
            turns, so a long list opens without a pause."""
            if closed or not popup.winfo_exists():
                return
            for value in values[start : start + count]:
                ctk.CTkButton(
                    frame,
                    text=value,
                    anchor="w",
                    width=width - 16,
                    fg_color="transparent",
                    hover_color=theme["hover_color"],
                    text_color=theme["text_color"],
                    height=row_height - 4,
                    command=lambda v=value: _select(v),
                ).pack(fill="x", pady=1)
            if start + count < len(values):
                # Tk runs due timers before the idle callbacks that repaint,
                # so the timer is armed from an idle callback
                popup.after_idle(
                    lambda: popup.after(1, _add_rows, start + count, _COMBO_BATCH)
                )

        _add_rows(0, rows)

        def _arm_close():
            popup.geometry(geometry)
            popup.bind("<FocusOut>", _close)
            popup.bind("<Button-1>", _on_click, add="+")
            popup.focus_force()
            with contextlib.suppress(Exception):
                popup.grab_set()

        popup.bind("<Escape>", _close)
        popup.update_idletasks()
        popup.deiconify()
        popup.after(100, _arm_close)

    combo._open_dropdown_menu = _open
    return combo


def open_url(url: str) -> bool:
    """Open a URL in the user's default browser with cross-platform fallbacks."""
    platform_name = platform_module.system()
    in_appimage = bool(os.environ.get("APPIMAGE"))

    if not (platform_name == "Linux" and in_appimage):
        try:
            if webbrowser.open(url, new=2):
                return True
        except Exception:
            pass

    if platform_name == "Linux":
        return _open_url_linux(url)
    if platform_name == "Darwin":
        return _run_command(["open", url])
    if platform_name == "Windows":
        try:
            os.startfile(url)
            return True
        except Exception:
            return _run_command(["cmd", "/c", "start", "", url])
    return False


def _open_url_linux(url: str) -> bool:
    env = _get_subprocess_env()
    commands = [
        ["xdg-open", url],
        ["gio", "open", url],
        ["gnome-open", url],
        ["kde-open5", url],
        ["kde-open", url],
    ]
    return any(shutil.which(cmd[0]) and _run_command(cmd, env=env) for cmd in commands)


_LINUX_FILE_MANAGERS = ("nautilus", "dolphin", "thunar", "nemo", "pcmanfm", "caja")


def open_folder(path: str | Path) -> bool:
    """Open a folder in the system file manager.

    A file path opens its folder with the file selected on Windows and
    macOS; Linux file managers have no common select option, so only the
    folder opens there. Returns whether a file manager was launched.
    """
    path = Path(path).resolve()
    select = path.is_file()
    folder = path.parent if select else path
    platform_name = platform_module.system()

    if platform_name == "Windows":
        if select:
            return _run_command(["explorer", f"/select,{path}"])
        try:
            os.startfile(folder)
            return True
        except Exception:
            return _run_command(["explorer", str(folder)])
    if platform_name == "Darwin":
        return _run_command(
            ["open", "-R", str(path)] if select else ["open", str(folder)]
        )
    return _open_folder_linux(str(folder))


def _open_folder_linux(folder: str) -> bool:
    # Inside the AppImage, LD_LIBRARY_PATH points at the bundled libs. A file
    # manager that inherits it fails to load against newer system libs, so
    # every command runs with the cleaned environment.
    env = _get_subprocess_env()
    for opener in (["xdg-open"], ["gio", "open"]):
        if not shutil.which(opener[0]):
            continue
        try:
            result = subprocess.run(
                [*opener, folder],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            # Still running means the opener stayed attached to the file
            # manager it started.
            return True
        except OSError:
            continue
        if result.returncode == 0:
            return True
    for manager in _LINUX_FILE_MANAGERS:
        if shutil.which(manager) and _run_command([manager, folder], env=env):
            return True
    return False


def _run_command(args: list[str], env: dict | None = None) -> bool:
    try:
        subprocess.Popen(
            args,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:
        return False


def _get_subprocess_env() -> dict:
    env = os.environ.copy()
    if env.get("APPIMAGE") or env.get("SNAP") or env.get("FLATPAK_ID"):
        env.pop("LD_LIBRARY_PATH", None)
        env.pop("LD_PRELOAD", None)
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
    return env


def pick_file(
    title: str,
    initialdir: str | None = None,
    filetypes: list[tuple[str, str]] | None = None,
    save: bool = False,
    defaultextension: str | None = None,
    initialfile: str | None = None,
) -> str | None:
    """Open a file picker for opening or saving a file.

    Uses zenity or kdialog on Linux for the system's native dialog, which
    supports typing a path (Ctrl+L) and toggling hidden files (Ctrl+H).
    Falls back to the Tk file dialog on other platforms or when neither
    zenity nor kdialog is installed.

    Returns the selected path, or None if the user cancelled.
    """
    filetypes = filetypes or [("All files", "*.*")]

    if platform_module.system() == "Linux":
        result = _pick_file_native_linux(
            title, initialdir, filetypes, save, defaultextension, initialfile
        )
        if result is not False:
            return result or None

    from tkinter import filedialog

    if save:
        path = filedialog.asksaveasfilename(
            title=title,
            initialdir=initialdir,
            initialfile=initialfile,
            defaultextension=defaultextension,
            filetypes=filetypes,
        )
    else:
        path = filedialog.askopenfilename(
            title=title,
            initialdir=initialdir,
            filetypes=filetypes,
        )
    return path or None


def _pick_file_native_linux(
    title: str,
    initialdir: str | None,
    filetypes: list[tuple[str, str]],
    save: bool,
    defaultextension: str | None,
    initialfile: str | None,
) -> str | bool:
    """Native zenity/kdialog backend for pick_file.

    Returns False when neither tool is installed so the caller falls back
    to the Tk file dialog.
    """
    env = _get_subprocess_env()
    # zenity is a GTK dialog, so KDE gets kdialog first.
    kde = "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
    tools = ("kdialog", "zenity") if kde else ("zenity", "kdialog")
    tool = next((t for t in tools if shutil.which(t)), None)

    if tool == "zenity":
        cmd = ["zenity", "--file-selection", f"--title={title}"]
        if save:
            cmd += ["--save", "--confirm-overwrite"]
        start = initialdir or ""
        if initialfile:
            start = os.path.join(start, initialfile) if start else initialfile
        if start:
            cmd.append(f"--filename={start}")
        for label, pattern in filetypes:
            cmd.append(f"--file-filter={label} | {pattern}")
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env=env
        )
        path = result.stdout.strip() if result.returncode == 0 else ""
        return _apply_default_extension(path, save, defaultextension)

    if tool == "kdialog":
        start = initialdir or os.path.expanduser("~")
        if initialfile:
            start = os.path.join(start, initialfile)
        cmd = ["kdialog", "--title", title]
        cmd.append("--getsavefilename" if save else "--getopenfilename")
        cmd.append(start)
        cmd.append("\n".join(f"{pattern}|{label}" for label, pattern in filetypes))
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env=env
        )
        path = result.stdout.strip() if result.returncode == 0 else ""
        return _apply_default_extension(path, save, defaultextension)

    return False


def _apply_default_extension(
    path: str, save: bool, defaultextension: str | None
) -> str:
    """Append defaultextension to a save-dialog result if it is missing."""
    if path and save and defaultextension and not path.endswith(defaultextension):
        path += defaultextension
    return path


def game_blocks_write(parent, process_name: str, game_name: str) -> bool:
    """Report whether a save write must be aborted because the game is running.

    Shows the standard error dialog and returns True when the write should be
    skipped. Returns False when the advanced "skip_game_running_check" setting
    is on, so the developer bypass covers per-game tabs the same way it covers
    the actions wired up in gui.py.

    Args:
        parent: Widget the error dialog is parented to
        process_name: Executable to look for, e.g. "darksoulsiii.exe"
        game_name: Display name used in the error message
    """
    from er_save_manager.backup.process_monitor import _is_process_running
    from er_save_manager.ui.messagebox import CTkMessageBox
    from er_save_manager.ui.settings import get_settings

    if get_settings().get("skip_game_running_check", False):
        return False

    if not _is_process_running(process_name):
        return False

    CTkMessageBox.showerror(
        "Game Is Running",
        f"Close {game_name} before modifying save files.",
        parent=parent,
    )
    return True


def resource_path(*parts: str) -> Path:
    """Path of a file under the top-level resources/ folder.

    Same lookup as the window icon in gui.py: the PyInstaller bundle, next to
    the cx_Freeze executable, or the repository root when run from source.
    """
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            base = Path(sys._MEIPASS)
        else:
            base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parents[3]
    return base.joinpath("resources", *parts)


def icon_image(name: str, size: int):
    """CTkImage from resources/icon/<name>_light.png and <name>_dark.png.

    Returns None when the files are missing, so callers can fall back to text.
    """
    light = resource_path("icon", f"{name}_light.png")
    dark = resource_path("icon", f"{name}_dark.png")
    if not (light.exists() and dark.exists()):
        return None
    from PIL import Image

    return ctk.CTkImage(Image.open(light), Image.open(dark), size=(size, size))
