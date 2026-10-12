"""CSNetMan validation and repair.

The slot's NetMan region starts at net_man_offset and is 0x20004 bytes: u32 2,
then 0x20000 bytes holding a chain of chunks (u16 type, u16 version, u32 size, size bytes) in the
order 2, 5, 6, 8, 9, 7, closed by a type 0xFFFF chunk of size 0 and zero
padding. Every chunk holds a sub-entry list (u32 kind, u32 size, size bytes,
padded to 4) closed by a kind 0xFFFF entry of size 0; chunk 8 starts with a
12-byte header before its list. Chunks 2, 5, 9 and 7 hold an empty list.

Repair keeps every chunk that is still intact and takes only the damaged
ones from the clean CSNetMan.bin template. A damaged chunk 6 (messages) is
rebuilt from its own bytes instead: every message entry that is still whole
is kept and only the damaged bytes are skipped.

CSNetMan.bin also covers the 4 bytes before the region (the end of
temp_spawn_point_entity_id and game_man_0xcb3); load_template() drops them.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from er_save_manager.fixes.base import BaseFix, FixResult

if TYPE_CHECKING:
    from er_save_manager.parser import Save

NETMAN_SIZE = 0x20004
_PREFIX = struct.pack("<I", 2)
_TERMINATOR = struct.pack("<HHI", 0xFFFF, 0, 0)

# (type, version) in the order the game writes them
_CHUNK_ORDER = ((2, 0), (5, 0), (6, 2), (8, 0), (9, 0), (7, 1))
_LIST_START = {8: 12}
_CHUNK_NAMES = {
    2: "chunk 2",
    5: "chunk 5",
    6: "messages",
    8: "chunk 8",
    9: "chunk 9",
    7: "chunk 7",
}


# Chunk 6 sub-entry kinds: 0 own message, 1 cached message, 2 session id.
# Allowed sizes per kind and where the author's FACE block sits in a message.
_MESSAGE_SIZES = {0: (600,), 1: (606, 602), 2: (8, 12)}
_MESSAGE_FACE = {(0, 600): 0xB8, (1, 606): 0x74, (1, 602): 0x70}
_SUB_TERMINATOR = struct.pack("<II", 0xFFFF, 0)


def _sub_list_ok(payload: bytes, pos: int) -> bool:
    """Walk a sub-entry list; True if it ends with the terminator at the payload end."""
    while pos + 8 <= len(payload):
        kind, size = struct.unpack_from("<II", payload, pos)
        if kind == 0xFFFF:
            return size == 0 and pos + 8 == len(payload)
        if size > len(payload) - pos - 8:
            return False
        pos += 8 + size
        pos += -pos % 4
    return False


def _messages_ok(payload: bytes) -> bool:
    """Every chunk 6 entry has a known kind, a known size and its FACE block."""
    pos = 0
    while payload[pos : pos + 8] != _SUB_TERMINATOR:
        length = _message_entry_at(payload, pos)
        if not length:
            return False
        pos += length
    return True


def _chunk_ok(ctype: int, payload: bytes) -> bool:
    if len(payload) % 4 or not _sub_list_ok(payload, _LIST_START.get(ctype, 0)):
        return False
    return ctype != 6 or _messages_ok(payload)


def _chunk_at(data: bytes, pos: int, ctype: int, version: int) -> bytes | None:
    """Return the whole chunk at pos if it has the given type and a valid body."""
    if pos + 8 > len(data):
        return None
    t, v, size = struct.unpack_from("<HHI", data, pos)
    if t != ctype or v != version or size > len(data) - pos - 8:
        return None
    payload = data[pos + 8 : pos + 8 + size]
    return data[pos : pos + 8 + size] if _chunk_ok(ctype, payload) else None


def _message_entry_at(data: bytes, pos: int) -> int:
    """Total length (header + padded body) of a whole chunk 6 entry at pos, or 0."""
    if pos + 8 > len(data):
        return 0
    kind, size = struct.unpack_from("<II", data, pos)
    if size not in _MESSAGE_SIZES.get(kind, ()) or pos + 8 + size > len(data):
        return 0
    face = _MESSAGE_FACE.get((kind, size))
    if face is not None and data[pos + 8 + face : pos + 12 + face] != b"FACE":
        return 0
    return 8 + size + (-size % 4)


def salvage_messages(region: bytes) -> tuple[bytes, int, int]:
    """Rebuild chunk 6 from the bytes where it was, keeping every whole entry.

    Entries are recognised by kind, size and (for messages) the author's FACE
    block; anything else is skipped in 4-byte steps until the next whole
    entry. Returns the chunk, the number of entries kept and the number of
    bytes skipped.
    """
    pos = 8 if _chunk_at_header(region, 6, 2) else 0
    entries, skipped = [], 0
    while pos + 8 <= len(region):
        if region[pos : pos + 8] == _SUB_TERMINATOR:
            break
        length = _message_entry_at(region, pos)
        if length:
            size = struct.unpack_from("<I", region, pos + 4)[0]
            entries.append(region[pos : pos + 8 + size] + bytes(-size % 4))
            pos += length
        else:
            pos += 4
            skipped += 4
    payload = b"".join(entries) + _SUB_TERMINATOR
    return struct.pack("<HHI", 6, 2, len(payload)) + payload, len(entries), skipped


def _chunk_at_header(data: bytes, ctype: int, version: int) -> bool:
    return len(data) >= 8 and struct.unpack_from("<HH", data, 0) == (ctype, version)


def netman_problems(blob: bytes) -> list[str]:
    """Describe what is wrong with a NetMan region; empty if it is valid.

    An all-zero region is treated as valid (nothing written yet).
    """
    if len(blob) != NETMAN_SIZE:
        return [f"NetMan size 0x{len(blob):x}, expected 0x{NETMAN_SIZE:x}"]
    if not any(blob):
        return []
    problems = []
    if blob[: len(_PREFIX)] != _PREFIX:
        problems.append("NetMan header is invalid")
    data = blob[len(_PREFIX) :]
    pos = 0
    for ctype, version in _CHUNK_ORDER:
        chunk = _chunk_at(data, pos, ctype, version)
        if chunk is None:
            problems.append(f"NetMan {_CHUNK_NAMES[ctype]} is damaged or missing")
            return problems
        pos += len(chunk)
    if data[pos : pos + 8] != _TERMINATOR:
        problems.append("NetMan chunk list is not terminated")
    elif any(data[pos + 8 :]):
        problems.append("NetMan has data after the chunk list")
    return problems


def load_template() -> bytes | None:
    """Load the clean CSNetMan.bin as a NetMan region, or None if missing or invalid."""
    path = Path(__file__).parent / "CSNetMan.bin"
    if not path.is_file():
        return None
    raw = path.read_bytes()
    if len(raw) != NETMAN_SIZE:
        return None
    data = raw[4:] + bytes(4)
    return None if netman_problems(data) else data


def _template_chunks(template: bytes) -> dict[int, bytes]:
    data = template[len(_PREFIX) :]
    chunks, pos = {}, 0
    for ctype, version in _CHUNK_ORDER:
        chunk = _chunk_at(data, pos, ctype, version)
        chunks[ctype] = chunk
        pos += len(chunk)
    return chunks


def repair_netman(blob: bytes, template: bytes) -> tuple[bytes, list[str]]:
    """Rebuild a NetMan region of any length into a valid 0x20004-byte region.

    Each chunk is taken from blob when an intact copy is found at or after the
    end of the previous one (a torn write can shift it), otherwise from the
    template. A missing chunk 6 is salvaged from the bytes between the
    previous and the next intact chunk instead. Returns the new region and a
    description of every chunk that was not kept as it was.
    """
    data = blob[len(_PREFIX) :] if blob[: len(_PREFIX)] == _PREFIX else blob
    clean = _template_chunks(template)
    parts, replaced, pos = [], [], 0
    salvage_from = None
    for ctype, version in _CHUNK_ORDER:
        header = struct.pack("<HH", ctype, version)
        found = None
        start = pos
        while found is None:
            start = data.find(header, start)
            if start < 0:
                break
            found = _chunk_at(data, start, ctype, version)
            if found is None:
                start += 1
        if salvage_from is not None:
            # chunk 6 ends where the next intact chunk starts
            end = start if found is not None else len(data)
            chunk, kept, skipped = salvage_messages(data[salvage_from:end])
            parts[2] = chunk
            replaced.append(
                f"{_CHUNK_NAMES[6]} (kept {kept} whole entries, "
                f"skipped {skipped} damaged bytes)"
            )
            salvage_from = None
        if found is None:
            if ctype == 6:
                salvage_from = pos
                parts.append(b"")
                continue
            parts.append(clean[ctype])
            replaced.append(f"{_CHUNK_NAMES[ctype]} (from template)")
        else:
            parts.append(found)
            pos = start + len(found)

    body = b"".join(parts) + _TERMINATOR
    if len(_PREFIX) + len(body) > NETMAN_SIZE:
        parts[2] = clean[6]
        replaced.append(f"{_CHUNK_NAMES[6]} (from template)")
        body = b"".join(parts) + _TERMINATOR
    return _PREFIX + body + bytes(NETMAN_SIZE - len(_PREFIX) - len(body)), replaced


class NetManFix(BaseFix):
    """Repairs a damaged CSNetMan region in place, keeping intact chunks."""

    name = "CSNetMan"
    description = "Repairs damaged network data (CSNetMan)"

    @staticmethod
    def _region(save: Save, slot) -> tuple[int, bytes]:
        start = slot.net_man_offset
        return start, bytes(save._raw_data[start : start + NETMAN_SIZE])

    def detect(self, save: Save, slot_index: int) -> bool:
        slot = self.get_slot(save, slot_index)
        if slot is None or slot.is_empty() or slot.net_man_offset <= 0:
            return False
        return bool(netman_problems(self._region(save, slot)[1]))

    def apply(self, save: Save, slot_index: int) -> FixResult:
        slot = self.get_slot(save, slot_index)
        if slot is None or slot.is_empty() or slot.net_man_offset <= 0:
            return FixResult(applied=False, description="Slot is empty")
        start, blob = self._region(save, slot)
        problems = netman_problems(blob)
        if not problems:
            return FixResult(applied=False, description="CSNetMan is valid")
        template = load_template()
        if template is None:
            return FixResult(
                applied=False, description="CSNetMan.bin template not found"
            )

        repaired, replaced = repair_netman(blob, template)
        save._raw_data[start : start + NETMAN_SIZE] = repaired

        from er_save_manager.parser.world import NetMan

        slot.net_man = NetMan.read(BytesIO(repaired))
        return FixResult(
            applied=True,
            description="CSNetMan repaired",
            details=problems + [f"Rebuilt {name}" for name in replaced],
        )
