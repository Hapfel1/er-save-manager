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
    Bind mousewheel scrolling to a CTkScrollableFrame (cross-platform).
    """
    if target_widget is None:
        target_widget = widget

    is_linux = platform_module.system() == "Linux"

    def _on_mousewheel(event):
        # For CTkScrollableFrame, use _parent_canvas
        if hasattr(target_widget, "_parent_canvas"):
            try:
                canvas = target_widget._parent_canvas
                if canvas and hasattr(canvas, "yview_scroll"):
                    if hasattr(event, "delta"):
                        delta = int(-1 * (event.delta / 120))
                    elif hasattr(event, "num"):
                        delta = -1 if event.num == 4 else 1
                    else:
                        delta = 0
                    if delta != 0:
                        canvas.yview_scroll(delta, "units")
                        return "break"  # Stop event propagation
            except Exception as e:
                print(f"[DEBUG] Scroll error: {e}")
        elif hasattr(target_widget, "yview_scroll"):
            try:
                if hasattr(event, "delta"):
                    delta = int(-1 * (event.delta / 120))
                elif hasattr(event, "num"):
                    delta = -1 if event.num == 4 else 1
                else:
                    delta = 0
                if delta != 0:
                    target_widget.yview_scroll(delta, "units")
                    return "break"
            except Exception as e:
                print(f"[DEBUG] Scroll error: {e}")

    # Bind to the toplevel window instead of recursing through children
    try:
        toplevel = widget.winfo_toplevel()
        if is_linux:
            toplevel.bind_all("<Button-4>", _on_mousewheel, add="+")
            toplevel.bind_all("<Button-5>", _on_mousewheel, add="+")
        else:
            toplevel.bind_all("<MouseWheel>", _on_mousewheel, add="+")
    except Exception as e:
        print(f"[DEBUG] Bind error: {e}")


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
