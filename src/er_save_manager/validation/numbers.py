"""Number field parsing shared by the editors.

int() also accepts underscores ("1_000"), a leading sign and digits of other
scripts (Arabic-Indic, full-width), so a typo or pasted text can turn into a
value the user did not mean.
"""

from __future__ import annotations


def parse_whole(text: str) -> int:
    """Value of text made of ASCII digits 0-9, surrounding whitespace allowed.

    Raises ValueError for anything else, including signs and underscores.
    """
    digits = text.strip()
    if not digits or not digits.isascii() or not digits.isdigit():
        raise ValueError(f"not a whole number: {text!r}")
    return int(digits)
