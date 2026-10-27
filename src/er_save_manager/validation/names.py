"""Character and preset name checks shared by every game.

The games store names as fixed-size UTF-16LE fields, so a limit counts UTF-16
code units: a character outside the Basic Multilingual Plane (most emoji)
takes two.
"""

from __future__ import annotations

import unicodedata


def utf16_len(text: str) -> int:
    """Length of text in UTF-16 code units."""
    return len(text.encode("utf-16-le", "surrogatepass")) // 2


def name_problem(text: str, max_units: int, field: str = "Name") -> str | None:
    """Message naming the field when text cannot be stored as a name, else
    None.

    Rejects empty and whitespace-only text, control characters (category
    Cc, such as tabs and line breaks), lone surrogates and text longer than
    max_units UTF-16 code units.
    """
    if not text or not text.strip():
        return f"{field} is empty."
    for ch in text:
        category = unicodedata.category(ch)
        if category == "Cc":
            return f"{field} contains a control character (U+{ord(ch):04X})."
        if category == "Cs":
            return f"{field} contains an invalid character (U+{ord(ch):04X})."
    length = utf16_len(text)
    if length > max_units:
        return (
            f"{field} is too long: {length} of {max_units} characters. Emoji "
            "and other characters outside the Basic Multilingual Plane count "
            "as two."
        )
    return None
