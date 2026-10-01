"""
Monochrome fallbacks for emoji in widget text on Linux.

Tk on X11 draws text through Xft, which has no emoji support: characters
outside the Basic Multilingual Plane show as boxes (Tk 8.6 stores them as
surrogate pairs), and when fontconfig falls back to a color emoji font,
libXft before 2.3.5 aborts the process with BadLength. The AppImage targets
Ubuntu 22.04, which ships libXft 2.3.4.

install() rewrites the "text" option of every Tk widget as it is created or
configured, replacing emoji with symbols common Linux fonts cover and
dropping the rest. Windows and macOS render emoji natively and are left
alone.
"""

from __future__ import annotations

import re
import sys
import tkinter

_VS16 = "\N{VARIATION SELECTOR-16}"

# Emoji -> symbol in the Misc Symbols, Dingbats, Arrows or Geometric Shapes
# blocks. Emoji-style variation selectors are stripped separately.
_REPLACEMENTS = {
    "\N{HEAVY BLACK HEART}": "\N{BLACK HEART SUIT}",
    "\N{WHITE HEAVY CHECK MARK}": "\N{HEAVY CHECK MARK}",
    "\N{CROSS MARK}": "\N{HEAVY BALLOT X}",
    "\N{HIGH VOLTAGE SIGN}": "\N{DOWNWARDS ZIGZAG ARROW}",
    "\N{DOWNWARDS BLACK ARROW}": "\N{DOWNWARDS ARROW}",
    "\N{THUMBS UP SIGN}": "\N{BLACK UP-POINTING TRIANGLE}",
    "\N{TRIANGULAR FLAG ON POST}": "\N{BLACK FLAG}",
    "\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}": (
        "\N{CLOCKWISE OPEN CIRCLE ARROW}"
    ),
}

_PATTERN = re.compile("|".join(map(re.escape, _REPLACEMENTS)))
# Emoji without a fallback (astral-plane characters and the hot beverage),
# with one following space so "X Label" becomes "Label".
_UNSUPPORTED = re.compile("[\U00010000-\U0010ffff\N{HOT BEVERAGE}] ?")


def to_monochrome(text: str) -> str:
    """text with emoji replaced by monochrome symbols or removed."""
    text = _PATTERN.sub(lambda m: _REPLACEMENTS[m[0]], text.replace(_VS16, ""))
    return _UNSUPPORTED.sub("", text)


def install() -> None:
    """Patch Tk option handling on Linux; a no-op elsewhere or when repeated."""
    if not sys.platform.startswith("linux"):
        return
    original = tkinter.Misc._options
    if getattr(original, "_emoji_fallback", False):
        return

    def _options(self, cnf, kw=None):
        if isinstance(cnf, dict) and isinstance(cnf.get("text"), str):
            cnf = {**cnf, "text": to_monochrome(cnf["text"])}
        if isinstance(kw, dict) and isinstance(kw.get("text"), str):
            kw = {**kw, "text": to_monochrome(kw["text"])}
        return original(self, cnf, kw)

    _options._emoji_fallback = True
    tkinter.Misc._options = _options
