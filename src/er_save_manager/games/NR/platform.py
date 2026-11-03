"""
Nightreign save containers: PC (BND4, AES-encrypted entries) and PlayStation
memory.dat.

memory.dat holds each PC entry's decrypted bytes without the 4-byte prefix
and the 28-byte checksum tail, unencrypted, after a memory_dat_header. As in
Elden Ring, the PlayStation global entry (entry 10) lacks PCOptionData, which
on PC sits right before the KeyConfigSaveLoad block. The SteamID fields are
zero on PlayStation.
"""

from __future__ import annotations

import os
import struct
from copy import deepcopy

from er_save_manager.games import bnd4, ps_userdata
from er_save_manager.games.NR import parser as nr
from er_save_manager.parser.platform import DEFAULT_PC_OPTION_DATA

PS_MAGIC = bytes.fromhex("4b01341b")
_PC_VERSION = b"00000001"
_RECORD_FLAGS = 0x40
_GLOBAL = 10
# KeyConfigSaveLoad header: u16 0x1F, u16 1, u32 0x2000
_KEY_CONFIG_HEADER = struct.pack("<HHI", 0x1F, 1, 0x2000)


def _key_config_offset(data: bytes) -> int:
    offset = data.find(_KEY_CONFIG_HEADER)
    if offset < 0:
        raise ValueError("The global save data has no key config block.")
    return offset


def _move_pc_option_data(data: bytearray, to_pc: bool) -> None:
    """Add (PlayStation -> PC) or remove (PC -> PlayStation) PCOptionData in
    the decrypted global entry. The body keeps its size; the bytes that move
    past its end or fill it are the unused tail."""
    size = len(DEFAULT_PC_OPTION_DATA)
    body_end = len(data) - nr._CHECKSUM_TAIL
    key_config = _key_config_offset(data)
    if to_pc:
        moved = data[key_config : body_end - size]
        data[key_config:body_end] = DEFAULT_PC_OPTION_DATA + moved
    else:
        moved = data[key_config:body_end]
        data[key_config - size : body_end] = moved + bytes(size)


def convert(save: nr.NightreignSave, to_ps: bool, steam_id: int = 0) -> bytes:
    """File bytes of save as a PlayStation memory.dat (to_ps) or a PC file
    with steam_id in every SteamID field."""
    # The copy keeps edits made in memory (deleted slots) and leaves save as
    # it is.
    copy = deepcopy(save)
    value = 0 if to_ps else steam_id
    for slot in copy.slots:
        if not slot.is_empty() and slot.steam_id_offset >= 0:
            slot.steam_id = value
    glob = copy.entries[_GLOBAL].decrypted
    struct.pack_into("<Q", glob, nr._E10_STEAM_ID, value)
    if to_ps != copy.is_ps:
        _move_pc_option_data(glob, to_pc=not to_ps)

    if to_ps:
        bodies = [
            bytes(e.decrypted[nr._ENTRY_PREFIX : -nr._CHECKSUM_TAIL])
            for e in copy.entries
        ]
        return ps_userdata.memory_dat_header(PS_MAGIC, len(bodies)) + b"".join(bodies)
    blobs = []
    for entry in copy.entries:
        nr._patch_checksum(entry.decrypted)
        iv = entry.iv or os.urandom(nr._IV_SIZE)
        blobs.append(nr._encrypt_entry(iv, entry.decrypted))
    return bnd4.build(blobs, _PC_VERSION, _RECORD_FLAGS)
