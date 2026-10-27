"""Handlers for exceptions nothing else caught: Tk callbacks, the main
thread and worker threads.

Each traceback is appended to errors.log in the settings data folder and the
user gets an error dialog naming that file. Without them a failed callback
only printed to stderr, which the packaged builds do not show.
"""

from __future__ import annotations

import datetime
import sys
import threading
import traceback
from pathlib import Path

LOG_NAME = "errors.log"
# errors.log is moved to errors.log.1 once it grows past this size
_MAX_BYTES = 1_000_000

_root = None
_dialog_open = False


def log_path() -> Path:
    from er_save_manager.ui.settings import Settings

    return Settings.get_data_dir() / LOG_NAME


def log_exception(exc_type, exc, tb, where: str) -> Path | None:
    """Append the traceback to errors.log; the log path, None when it could
    not be written."""
    path = log_path()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > _MAX_BYTES:
            path.replace(path.with_name(LOG_NAME + ".1"))
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {where}\n{text}\n")
    except OSError:
        return None
    return path


def _show(exc_type, exc, path: Path | None) -> None:
    """Error dialog on the Tk thread; one at a time, later errors while it
    is open are only logged."""
    global _dialog_open
    if _root is None or _dialog_open:
        return
    try:
        if not _root.winfo_exists():
            return
    except Exception:
        return
    from er_save_manager.ui.messagebox import CTkMessageBox

    where = f"Details were written to:\n{path}" if path else "No log could be written."
    _dialog_open = True
    try:
        CTkMessageBox.showerror(
            "Unexpected Error",
            f"An operation failed with an unexpected error:\n"
            f"{exc_type.__name__}: {exc}\n\n{where}\n\n"
            "Reload the save before writing it if the error came from an edit.",
            parent=_root,
        )
    except Exception:
        pass
    finally:
        _dialog_open = False


def _report(exc_type, exc, tb, where: str) -> None:
    # Windows GUI builds run without a console; sys.stderr is None there
    if sys.stderr is not None:
        traceback.print_exception(exc_type, exc, tb)
    path = log_exception(exc_type, exc, tb, where)
    if _root is None:
        return
    if threading.current_thread() is threading.main_thread():
        _show(exc_type, exc, path)
    else:
        try:
            _root.after(0, _show, exc_type, exc, path)
        except Exception:
            pass


def _tk_callback(exc_type, exc, tb) -> None:
    _report(exc_type, exc, tb, "Tk callback")


def _excepthook(exc_type, exc, tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    _report(exc_type, exc, tb, "main thread")


def _thread_excepthook(args) -> None:
    if args.exc_type is SystemExit:
        return
    name = args.thread.name if args.thread is not None else "unknown"
    _report(args.exc_type, args.exc_value, args.exc_traceback, f"thread {name}")


def install(root) -> None:
    """Route uncaught exceptions of root's callbacks, the main thread and
    worker threads to errors.log and an error dialog over root."""
    global _root
    _root = root
    root.report_callback_exception = _tk_callback
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
