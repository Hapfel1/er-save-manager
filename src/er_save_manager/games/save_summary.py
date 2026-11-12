"""Short description of the characters in a save file, for the save picker."""

from __future__ import annotations

from pathlib import Path

# Names shown before the rest is counted
_SHOWN = 4
# Sekiro character slots: BND4 entries USER_DATA000 to 009, each an MD5 then
# the slot data, all zero while the slot is empty
_SEKIRO_SLOTS = 10
_MD5_SIZE = 16


def _join(names: list[str]) -> str:
    if not names:
        return "No characters"
    if len(names) <= _SHOWN:
        return ", ".join(names)
    return ", ".join(names[:_SHOWN]) + f" +{len(names) - _SHOWN} more"


def _sekiro_summary(path: Path) -> str:
    from er_save_manager.games import bnd4

    entries = bnd4.read_entries(path.read_bytes())
    used = sum(
        1 for entry in entries[:_SEKIRO_SLOTS] if any(entry[_MD5_SIZE:].tobytes())
    )
    # Sekiro characters have no names; the load screen shows each slot by place
    if used == 0:
        return "No characters"
    return f"{used} character{'s' if used != 1 else ''}"


def character_summary(path: str | Path, game_key: str) -> str | None:
    """Character names in the save (Sekiro: the character count), None when
    the game has no characters to list or the file cannot be read."""
    path = Path(path)
    try:
        if game_key == "sekiro":
            return _sekiro_summary(path)
        from er_save_manager.games.extension_copy import _GAMES

        game = _GAMES.get(game_key)
        if game is None:
            return None
        save = game.load(path)
        names = []
        for i in range(10):
            try:
                if game.occupied(save, i):
                    names.append(game.name(save, i))
            except (IndexError, AttributeError):
                break
        return _join(names)
    except Exception:
        return None
