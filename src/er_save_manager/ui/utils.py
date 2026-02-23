"""Utility functions for UI components."""

import os
import platform as platform_module
import shutil
import subprocess
import webbrowser


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


def bind_mousewheel(widget, target_widget=None):
    """
    Bind mousewheel scrolling to a CTkScrollableFrame (AppImage-compatible).
    """
    if target_widget is None:
        target_widget = widget

    # For CTkScrollableFrame, bind directly to internal canvas
    if hasattr(target_widget, "_parent_canvas"):
        canvas = target_widget._parent_canvas

        def scroll_up(event):
            canvas.yview_scroll(-1, "units")
            return "break"

        def scroll_down(event):
            canvas.yview_scroll(1, "units")
            return "break"

        # Bind to canvas itself
        canvas.bind("<Button-4>", scroll_up)
        canvas.bind("<Button-5>", scroll_down)

        # Bind to the scrollable frame
        target_widget.bind("<Button-4>", scroll_up)
        target_widget.bind("<Button-5>", scroll_down)

        # CRITICAL: Recursively bind to ALL children (for dynamic content)
        def bind_to_children(w):
            try:
                w.bind("<Button-4>", scroll_up)
                w.bind("<Button-5>", scroll_down)
                for child in w.winfo_children():
                    bind_to_children(child)
            except Exception:
                pass

        bind_to_children(target_widget)

        # Re-bind when content changes
        def on_map(event):
            bind_to_children(target_widget)

        target_widget.bind("<Map>", on_map, add="+")


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
    for cmd in commands:
        if shutil.which(cmd[0]) and _run_command(cmd, env=env):
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
        env.pop("LD_PRELOAD", None)  # Add this line
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
    return env
