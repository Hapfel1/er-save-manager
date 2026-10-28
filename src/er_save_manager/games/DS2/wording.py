"""Count phrases for DS2 messages."""

from __future__ import annotations


def counted(n: int, noun: str, plural: str | None = None) -> str:
    """'1 boss', '2 bosses': n followed by the singular or plural noun. The
    plural defaults to noun + 's'."""
    return f"{n} {noun if n == 1 else plural or noun + 's'}"
