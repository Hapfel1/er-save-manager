"""Utility functions for UI components."""

import os
import platform as platform_module
import shutil
import subprocess
import webbrowser

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

        # Bind children recursively so widgets added later also scroll
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


def patch_combo_scroll(combo, max_visible_rows: int = 20, row_height: int = 28):
    """
    Replace a CTkComboBox's dropdown with a scrollable popup.

    CTkComboBox (customtkinter 5.2.2, the version this project is pinned to)
    opens its dropdown as a native tkinter.Menu. Native menus have no canvas
    or scrollbar, so long value lists cannot be scrolled by mousewheel or
    otherwise on any platform. This overrides _open_dropdown_menu to instead
    show a borderless CTkToplevel containing a CTkScrollableFrame of buttons,
    sized to fit the longest value and the available screen space.
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

        # Full update so a freshly-mapped tab's
        # geometry from the window manager is settled before reading it.
        combo.update()
        text_font = ctk.CTkFont()
        text_width = max(text_font.measure(v) for v in values)
        pad = combo._apply_widget_scaling(48)
        width = max(combo.winfo_width(), text_width + pad)

        x = combo.winfo_rootx()
        y = combo.winfo_rooty() + combo.winfo_height() + 2
        screen_h = popup.winfo_screenheight()
        available_rows = max((screen_h - y - 40) // row_height, 4)
        rows = min(len(values), max_visible_rows, available_rows)
        height = rows * row_height + 8

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

        def _select(value):
            popup.destroy()
            combo.set(value)
            if combo._command is not None:
                combo._command(value)

        for value in values:
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

        def _close(_e=None):
            try:
                popup.destroy()
            except Exception:
                pass

        def _arm_close():
            # Reassert geometry after mapping: some window managers ignore
            # the position set on a withdrawn/override-redirect window and
            # place it at a default location instead (seen as the popup
            # opening on the wrong monitor in a multi-monitor setup).
            popup.geometry(geometry)
            popup.bind("<FocusOut>", _close)
            popup.focus_force()

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

    if shutil.which("zenity"):
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

    if shutil.which("kdialog"):
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
        "Game is running",
        f"Please close {game_name} before modifying save files.",
        parent=parent,
    )
    return True
