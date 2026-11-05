"""Verbose log: every record of the er_save_manager loggers, written to
er_save_manager.log in the settings data folder next to errors.log while the
"Verbose logging to file" setting is on."""

from __future__ import annotations

import logging
import platform
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_NAME = "er_save_manager.log"
# er_save_manager.log is moved to er_save_manager.log.1 past this size
_MAX_BYTES = 1_000_000

_handler: RotatingFileHandler | None = None


def log_path() -> Path:
    from er_save_manager.ui.settings import Settings

    return Settings.get_data_dir() / LOG_NAME


def set_enabled(enabled: bool) -> None:
    """Attach or remove the file handler on the package logger."""
    global _handler
    package = logging.getLogger("er_save_manager")
    if enabled and _handler is None:
        path = log_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                path, maxBytes=_MAX_BYTES, backupCount=1, encoding="utf-8", delay=True
            )
        except OSError:
            return
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        package.addHandler(handler)
        package.setLevel(logging.DEBUG)
        _handler = handler
        from er_save_manager import __version__

        package.info(
            "Verbose logging on: version %s, %s", __version__, platform.platform()
        )
    elif not enabled and _handler is not None:
        package.removeHandler(_handler)
        _handler.close()
        _handler = None
        package.setLevel(logging.NOTSET)
