"""
Dark Souls II SotFS saves: PC <-> PS4 userdata folder.

Each PS4 file is a PC entry's decrypted data without its length prefix,
except entry 0, whose first section is cut to its PS4 size (DS2PSContainer).
The cut part holds the owner SteamID; a PC file built from a PS4 folder
gets it written back, a PS4 folder built from a PC file loses it.
"""

from __future__ import annotations

import os
import struct

from er_save_manager.games import bnd4, ps_userdata
from er_save_manager.games import ds2_dsr_steamid as steamid
from er_save_manager.games.DS2 import save as ds2

_VERSION = b"14e503cb"
_LENGTH_PREFIX = 4
# Size of entry 0's first section in a PS4 save
_PS_SUMMARY_SECTION_SIZE = 0x14


def _entries(save: ds2.DS2Save) -> list[bytes]:
    """Every entry in the PC decrypted layout, with the character edits and
    load-screen caches synced as save_to_file does."""
    for i, character in enumerate(save.characters):
        save.container.set_entry(ds2.PROFILE_ENTRY_START + i, character.raw())
    save.sync_name_caches()
    save.sync_level_caches()
    return [bytes(save.container.get_entry(i)) for i in range(ds2.TOTAL_ENTRIES)]


def to_pc_bytes(save: ds2.DS2Save, steam_id: int) -> bytes:
    if not save.is_ps:
        raise ValueError("The save is already a PC save.")
    entries = _entries(save)
    owner = bytearray(entries[ds2.OCCUPANCY_ENTRY])
    # The SteamID patcher counts the u32 length in front of the entry data.
    off = steamid._OWNER_OFFSET - _LENGTH_PREFIX
    owner[off : off + steamid._OWNER_LEN] = f"{steam_id:016x}".encode("ascii")
    entries[ds2.OCCUPANCY_ENTRY] = bytes(owner)
    blobs = []
    for data in entries:
        iv = os.urandom(ds2._IV_SIZE)
        ciphertext = ds2._encrypt(iv, bytearray(data))
        blobs.append(ds2._md5(iv + ciphertext) + iv + ciphertext)
    return bnd4.build(blobs, _VERSION)


def to_ps4_files(save: ds2.DS2Save) -> dict[str, bytes]:
    """File name -> content of a PS4 folder holding save."""
    if save.is_ps:
        raise ValueError("The save is already a PS4 save.")
    files = {}
    for i, data in enumerate(_entries(save)):
        if i == ds2.OCCUPANCY_ENTRY:
            cut = ds2._SUMMARY_SECTION_DATA + _PS_SUMMARY_SECTION_SIZE
            out = bytearray(data[:cut])
            out += data[ds2._SUMMARY_SECTION_DATA + ds2._PC_SUMMARY_SECTION_SIZE :]
            struct.pack_into(
                "<I", out, ds2._SUMMARY_SECTION_SIZE_OFFSET, _PS_SUMMARY_SECTION_SIZE
            )
            data = bytes(out)
        files[ps_userdata.entry_file_name(i)] = data
    return files
