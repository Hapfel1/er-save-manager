"""
Bundled Inter font (resources/fonts), registered for this process only.

Widgets name the families "Inter" (regular and bold) and "Inter SemiBold".
Windows loads the files with AddFontResourceExW(FR_PRIVATE), Linux adds them
to the fontconfig configuration Tk's Xft renderer reads. Nothing is
installed system-wide. On macOS, or when a file is missing, Tk falls back
to the platform's default font.

GDI draws hinted outlines thinner than FreeType does, so Windows loads
resources/fonts/windows instead: unhinted instances of Inter and Roboto,
renamed to the requested family/style names. Its Roboto, family
"Roboto UI", replaces the theme's Roboto (which CustomTkinter loads hinted)
as the default font of widgets without an explicit one.
"""

from __future__ import annotations

import ctypes
import sys

from er_save_manager.ui.utils import resource_path

_FILES = ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")
_WINDOWS_THEME_FILE = "Roboto-Regular.ttf"
_WINDOWS_THEME_FAMILY = "Roboto UI"
_FR_PRIVATE = 0x10

# Default widget font family set by register(); None keeps the theme's.
theme_family: str | None = None


def register() -> None:
    """Make the bundled fonts available to Tk; call before the first widget."""
    global theme_family
    windows = sys.platform == "win32"
    folder = ("fonts", "windows") if windows else ("fonts",)
    names = (*_FILES, _WINDOWS_THEME_FILE) if windows else _FILES
    paths = [p for p in (resource_path(*folder, f) for f in names) if p.exists()]
    if not paths:
        return
    try:
        if windows:
            add = ctypes.windll.gdi32.AddFontResourceExW
            add.argtypes = (ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p)
            for path in paths:
                if (
                    add(str(path), _FR_PRIVATE, None)
                    and path.name == _WINDOWS_THEME_FILE
                ):
                    theme_family = _WINDOWS_THEME_FAMILY
        elif sys.platform.startswith("linux"):
            # Tk is already linked against this library, so dlopen returns
            # the copy whose configuration Xft uses.
            fc = ctypes.CDLL("libfontconfig.so.1")
            fc.FcConfigAppFontAddFile.argtypes = (ctypes.c_void_p, ctypes.c_char_p)
            for path in paths:
                fc.FcConfigAppFontAddFile(None, str(path).encode())
    except (OSError, AttributeError):
        pass
