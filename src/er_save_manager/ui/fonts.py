"""
Bundled Inter font (resources/fonts), registered for this process only.

Widgets name the families "Inter" (regular and bold) and "Inter SemiBold".
Windows loads the files with AddFontResourceExW(FR_PRIVATE), Linux adds them
to the fontconfig configuration Tk's Xft renderer reads. Nothing is
installed system-wide. On macOS, or when a file is missing, Tk falls back
to the platform's default font.
"""

from __future__ import annotations

import ctypes
import sys

from er_save_manager.ui.utils import resource_path

_FILES = ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")
_FR_PRIVATE = 0x10


def register() -> None:
    """Make the bundled fonts available to Tk; call before the first widget."""
    paths = [p for p in (resource_path("fonts", f) for f in _FILES) if p.exists()]
    if not paths:
        return
    try:
        if sys.platform == "win32":
            add = ctypes.windll.gdi32.AddFontResourceExW
            add.argtypes = (ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p)
            for path in paths:
                add(str(path), _FR_PRIVATE, None)
        elif sys.platform.startswith("linux"):
            # Tk is already linked against this library, so dlopen returns
            # the copy whose configuration Xft uses.
            fc = ctypes.CDLL("libfontconfig.so.1")
            fc.FcConfigAppFontAddFile.argtypes = (ctypes.c_void_p, ctypes.c_char_p)
            for path in paths:
                fc.FcConfigAppFontAddFile(None, str(path).encode())
    except (OSError, AttributeError):
        pass
