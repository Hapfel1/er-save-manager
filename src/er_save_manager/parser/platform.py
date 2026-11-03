"""
Elden Ring save containers: PC, PlayStation and Switch 2.

All three hold twelve entries: ten character slots (0x280000 each),
USER_DATA_10 (0x60000) and USER_DATA_11 (0x240010).

  PC        BND4 file (bnd4.build), each entry prefixed with its MD5.
            An empty character slot is all zero bytes.
  PS        memory.dat: PS_HEADER, then the entries back to back.
  Switch 2  one file per entry, ER_____0000_userdata0000 to 0011.

Character slots and USER_DATA_11 are the same on every platform. USER_DATA_10
of a console save lacks PCOptionData (0xB2 bytes after the profile summary);
everything after it sits 0xB2 bytes earlier. The SteamID fields are zero on
both consoles.
"""

from __future__ import annotations

import hashlib
import struct

from er_save_manager.games import bnd4, ps_userdata
from er_save_manager.parser.user_data_10 import PCOptionData

PC = "pc"
PS = "ps"
SWITCH2 = "switch2"
CONSOLES = (PS, SWITCH2)

ENTRY_SIZES = ps_userdata.entry_sizes("elden_ring", ps_userdata.SWITCH2)
PS_MAGIC = bytes.fromhex("cb019c2c")
PS_HEADER = ps_userdata.memory_dat_header(PS_MAGIC, len(ENTRY_SIZES))

# PCOptionData given to a console save moved to PC: a 1280 x 720 window and
# the default keyboard keys (u16 virtual-key code, u16 modifier).
DEFAULT_PC_OPTION_DATA = bytes.fromhex(
    "0005d00200001e05000000000000000000005700000053000000440000004100"
    "0000570004005300040044000400410004005200000056000000540000004500"
    "0000460000003100000032000000330000003400000060000000610000006200"
    "0000630000006400000065000000660000006700000021000400670004002300"
    "0000260000002800000025000000270000000d000000080000000d0008000d00"
    "02002e0000002d0000000000000000000000"
)
assert len(DEFAULT_PC_OPTION_DATA) == PCOptionData.SIZE

SLOT_COUNT = 10
USER_DATA_10 = SLOT_COUNT
_MD5_SIZE = 16
_PC_VERSION = b"00000001"


def _user_data_10_start(save) -> int:
    return save._user_data_10_offset + (0 if save.is_ps else _MD5_SIZE)


def entries(save) -> list[bytes]:
    """The twelve entries of a parsed save as stored, without PC checksums.
    Offsets are those recorded while parsing."""
    starts = [save.slot_data_offset(i) for i in range(SLOT_COUNT)]
    starts.append(_user_data_10_start(save))
    starts.append(save._user_data_11_offset)
    raw = save._raw_data
    out = []
    for start, size in zip(starts, ENTRY_SIZES, strict=True):
        piece = bytes(raw[start : start + size])
        if len(piece) != size:
            raise ValueError(
                "The save is cut off; it cannot be written in another format."
            )
        out.append(piece)
    return out


def _steamid_fields(save) -> dict[int, int]:
    """Entry index -> offset within that entry of each SteamID field: every
    occupied slot and USER_DATA_10."""
    found = {}
    for i, slot in enumerate(save.character_slots):
        offset = getattr(slot, "steamid_offset", 0)
        if not slot.is_empty() and offset:
            found[i] = offset - save.slot_data_offset(i)
    ud10 = save.user_data_10_parsed
    if ud10 is not None and ud10.steam_id_offset:
        found[USER_DATA_10] = ud10.steam_id_offset - _user_data_10_start(save)
    return found


def _move_user_data_10(save, data: bytes, to_pc: bool) -> bytes:
    """USER_DATA_10 with PCOptionData added (console -> PC) or removed (PC
    -> console). The entry keeps its size; the bytes that move past its end
    or fill it are the unused tail."""
    ud10 = save.user_data_10_parsed
    if ud10 is None or not ud10.pc_option_data_offset:
        raise ValueError("USER_DATA_10 could not be read.")
    at = ud10.pc_option_data_offset - _user_data_10_start(save)
    size = PCOptionData.SIZE
    if to_pc:
        return data[:at] + DEFAULT_PC_OPTION_DATA + data[at : len(data) - size]
    return data[:at] + data[at + size :] + bytes(size)


def convert(save, platform: str, steam_id: int = 0) -> list[bytes]:
    """The twelve entries of save laid out for platform. A PC target gets
    steam_id in every SteamID field, a console target zero."""
    if platform not in (PC, *CONSOLES):
        raise ValueError(f"Unknown platform {platform}")
    parts = entries(save)
    value = struct.pack("<Q", steam_id if platform == PC else 0)
    # SteamID offsets are those of the source layout, so they are written
    # before USER_DATA_10 moves.
    for i, offset in _steamid_fields(save).items():
        part = bytearray(parts[i])
        part[offset : offset + 8] = value
        parts[i] = bytes(part)
    if (platform == PC) != (save.platform == PC):
        parts[USER_DATA_10] = _move_user_data_10(
            save, parts[USER_DATA_10], to_pc=platform == PC
        )
    return parts


def pc_bytes(parts: list[bytes]) -> bytes:
    return bnd4.build([hashlib.md5(p).digest() + p for p in parts], _PC_VERSION)


def ps_bytes(parts: list[bytes]) -> bytes:
    return PS_HEADER + b"".join(parts)


def switch2_files(parts: list[bytes]) -> dict[str, bytes]:
    """File name -> content of a Switch 2 save folder."""
    return {
        ps_userdata.entry_file_name(i, ps_userdata.SWITCH2): p
        for i, p in enumerate(parts)
    }
