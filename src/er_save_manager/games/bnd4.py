"""
Build a BND4 save container from its entries.

Layout written (the one the games' own PC saves use):

  0x00  "BND4", u32 0, u32 0x10000, u32 entry count
  0x10  u64 header size (0x40), 8-byte version string
  0x20  u64 entry record size (0x20), u64 data start
  0x30  u8 1 (UTF-16 names), u8 0x20 (format), 14 zero bytes
  0x40  entry records: u32 flags, i32 -1, u64 size, u32 data offset,
        u32 name offset, u64 0. Flags are 0x50, Nightreign writes 0x40.
        UTF-16LE names, each NUL-terminated, padded to 0x10
        entry data back to back
"""

from __future__ import annotations

import struct

HEADER_SIZE = 0x40
RECORD_SIZE = 0x20
_ALIGN = 0x10


def entry_name(index: int) -> str:
    return f"USER_DATA{index:03d}"


def build(entries: list[bytes], version: bytes, record_flags: int = 0x50) -> bytes:
    """BND4 file holding entries in order, named USER_DATA000, 001, ...
    version is the 8-byte version string of the game's saves."""
    if len(version) != 8:
        raise ValueError("BND4 version string must be 8 bytes")
    count = len(entries)
    names = [(entry_name(i) + "\0").encode("utf-16-le") for i in range(count)]
    names_start = HEADER_SIZE + count * RECORD_SIZE
    names_end = names_start + sum(len(n) for n in names)
    data_start = -(-names_end // _ALIGN) * _ALIGN

    out = bytearray(data_start)
    struct.pack_into("<4sIII", out, 0, b"BND4", 0, 0x10000, count)
    struct.pack_into("<Q8s", out, 0x10, HEADER_SIZE, version)
    struct.pack_into("<QQ", out, 0x20, RECORD_SIZE, data_start)
    struct.pack_into("<BB", out, 0x30, 1, 0x20)

    name_offset = names_start
    data_offset = data_start
    for i, (entry, name) in enumerate(zip(entries, names, strict=True)):
        struct.pack_into(
            "<IiQIIQ",
            out,
            HEADER_SIZE + i * RECORD_SIZE,
            record_flags,
            -1,
            len(entry),
            data_offset,
            name_offset,
            0,
        )
        out[name_offset : name_offset + len(name)] = name
        name_offset += len(name)
        data_offset += len(entry)
    for entry in entries:
        out += entry
    return bytes(out)
