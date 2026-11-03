"""
Dark Souls III PC save -> PS4 userdata folder.

A PS4 file holds the PC entry's decrypted bytes without the u32 length in
front (DS3PSParser). The PC file's regulation entry (USER_DATA011) has no
PS4 file, so a PS4 folder cannot be turned into a new PC file. The SteamID
fields are zero on PS4.
"""

from __future__ import annotations

import struct

from er_save_manager.games import ps_userdata
from er_save_manager.games.DS3 import character_ops
from er_save_manager.games.DS3.save import DS3Save

_LENGTH_PREFIX = 4
_GLOBAL = DS3Save.CHARACTER_SLOTS
_GLOBAL_STEAMID = 0x8


def to_ps4_files(save: DS3Save) -> dict[str, bytes]:
    """File name -> content of a PS4 folder holding save."""
    if save.is_ps:
        raise ValueError("The save is already a PS4 save.")
    parser = save._parser
    files = {}
    for i in range(parser.TOTAL_SLOTS):
        char = save.characters[i] if i < _GLOBAL else None
        data = bytearray(char.get_raw() if char is not None else parser.get_slot(i))
        if i < _GLOBAL:
            character_ops._patch_slot_steamid(data, 0)
        else:
            struct.pack_into("<Q", data, _GLOBAL_STEAMID, 0)
        files[ps_userdata.entry_file_name(i)] = bytes(data[_LENGTH_PREFIX:])
    return files
