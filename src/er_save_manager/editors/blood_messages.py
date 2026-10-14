"""Messages stored in NetMan chunk 6: the player's own and cached ones from other players.

Chunk 6 is a sub-entry list (u32 kind, u32 size, size bytes padded to 4).
Kind 0 = own message (600 bytes), kind 1 = cached message of another player
(606 or 602 bytes), kind 2 = session ids. The message body is

    u16 template, u8 gesture index, u8 unknown,
    u16 word, u16 conjunction, u16 template 2, u16 word 2

with conjunction, template 2 and word 2 all 0 on a one-phrase message.
Template, word and conjunction are BloodMsg FMG ids; the gesture id is
2 * index + 1, 0xFF = none.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from er_save_manager.data.gestures import get_gesture_name
from er_save_manager.data.locations import get_name_for_map_id
from er_save_manager.fixes.netman import NETMAN_SIZE, netman_problems

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

_BLANK = "<?bmsg?>"
_FIRST_PHRASE = "<?belongMsg?>"
_SUB_TERMINATOR_KIND = 0xFFFF
_CHUNK_HEADER = struct.Struct("<HHI")
_SUB_HEADER = struct.Struct("<II")
_BODY = struct.Struct("<HBBHHHH")

# Field offsets inside an entry body, keyed by (kind, size)
_LAYOUT = {
    (0, 600): {"map": 0x0C, "pos": 0x24, "body": 0x34, "name": 0x1D8},
    (1, 606): {"map": 0x1C4, "pos": 0x1CC, "body": 0x1DC, "name": 0x194},
    (1, 602): {"map": 0x1C0, "pos": 0x1C8, "body": 0x1D8, "name": 0x190},
}
_PROTECTED = 0x46  # own messages only
_NAME_SIZE = 32


@cache
def _tables() -> dict[str, dict[int, str]]:
    raw = json.loads(
        (Path(__file__).parent.parent / "data" / "blood_messages.json").read_text(
            encoding="utf-8"
        )
    )
    return {key: {int(k): v for k, v in table.items()} for key, table in raw.items()}


def _phrase(template: int, word: int) -> str:
    tables = _tables()
    text = tables["templates"].get(template, f"[{template}] {_BLANK}")
    return text.replace(_BLANK, tables["words"].get(word, f"[{word}]"))


def message_lines(
    template: int, word: int, conjunction: int = 0, template2: int = 0, word2: int = 0
) -> list[str]:
    """Message text as the game shows it, one line per phrase."""
    first = _phrase(template, word)
    if not conjunction:
        return [first]
    joiner = _tables()["conjunctions"].get(conjunction, f"[{conjunction}] ")
    second = _phrase(template2, word2)
    if _FIRST_PHRASE in joiner:
        return [joiner.replace(_FIRST_PHRASE, first), second]
    return [first, joiner + second]


@dataclass
class BloodMessage:
    kind: int
    offset: int  # entry header offset inside chunk 6 payload
    size: int
    map_id: bytes
    position: tuple[float, float, float]
    template: int
    gesture_index: int
    word: int
    conjunction: int
    template2: int
    word2: int
    author: str
    protected: bool

    @property
    def is_own(self) -> bool:
        return self.kind == 0

    @property
    def lines(self) -> list[str]:
        return message_lines(
            self.template, self.word, self.conjunction, self.template2, self.word2
        )

    @property
    def text(self) -> str:
        return " ".join(line.strip() for line in self.lines)

    @property
    def gesture_name(self) -> str:
        if self.gesture_index == 0xFF:
            return ""
        return get_gesture_name(2 * self.gesture_index + 1)

    @property
    def map_str(self) -> str:
        d = self.map_id
        return f"m{d[3]:02d}_{d[2]:02d}_{d[1]:02d}_{d[0]:02d}"

    @property
    def map_name(self) -> str:
        return get_name_for_map_id(self.map_str)


def _chunks(region: bytes) -> list[tuple[int, int, int, int]]:
    """(type, version, payload start, payload size) of each chunk in a valid region."""
    out, pos = [], 4
    while True:
        ctype, version, size = _CHUNK_HEADER.unpack_from(region, pos)
        if ctype == 0xFFFF:
            return out
        out.append((ctype, version, pos + 8, size))
        pos += 8 + size


def _parse_entry(kind: int, offset: int, body: bytes) -> BloodMessage | None:
    layout = _LAYOUT.get((kind, len(body)))
    if layout is None:
        return None
    template, gesture, _, word, conj, template2, word2 = _BODY.unpack_from(
        body, layout["body"]
    )
    name = body[layout["name"] : layout["name"] + _NAME_SIZE].decode(
        "utf-16-le", errors="replace"
    )
    return BloodMessage(
        kind=kind,
        offset=offset,
        size=len(body),
        map_id=bytes(body[layout["map"] : layout["map"] + 4]),
        position=struct.unpack_from("<3f", body, layout["pos"]),
        template=template,
        gesture_index=gesture,
        word=word,
        conjunction=conj,
        template2=template2,
        word2=word2,
        author=name.split("\x00", 1)[0],
        protected=kind == 0 and body[_PROTECTED] != 0,
    )


class BloodMessageEditor:
    """List, protect and delete the messages of one slot."""

    def __init__(self, save: Save, slot_index: int):
        self._save = save
        self._slot_index = slot_index

    @property
    def _slot(self):
        return self._save.character_slots[self._slot_index]

    def _region(self) -> bytes:
        start = self._slot.net_man_offset
        return bytes(self._save._raw_data[start : start + NETMAN_SIZE])

    def problems(self) -> list[str]:
        """NetMan problems that block reading and editing; empty if usable."""
        slot = self._slot
        if slot.is_empty() or getattr(slot, "net_man_offset", 0) <= 0:
            return ["Slot is empty"]
        region = self._region()
        if not any(region):
            return []
        return netman_problems(region)

    def _chunk6(self, region: bytes) -> tuple[int, int] | None:
        for ctype, _, start, size in _chunks(region):
            if ctype == 6:
                return start, size
        return None

    def messages(self) -> list[BloodMessage]:
        """Own and cached messages in save order; empty if NetMan is unusable."""
        if self.problems():
            return []
        region = self._region()
        if not any(region):
            return []
        found = self._chunk6(region)
        if found is None:
            return []
        start, size = found
        payload = region[start : start + size]
        out, pos = [], 0
        while pos + 8 <= len(payload):
            kind, length = _SUB_HEADER.unpack_from(payload, pos)
            if kind == _SUB_TERMINATOR_KIND:
                break
            msg = _parse_entry(kind, pos, payload[pos + 8 : pos + 8 + length])
            if msg is not None:
                out.append(msg)
            pos += 8 + length
            pos += -pos % 4
        return out

    def set_protected(self, msg: BloodMessage, protected: bool) -> tuple[bool, str]:
        if not msg.is_own:
            return False, "Only your own messages can be protected"
        flag = 8 + _PROTECTED

        def change(entry: bytes) -> bytes:
            return entry[:flag] + bytes([int(protected)]) + entry[flag + 1 :]

        return self._rewrite(msg, change)

    def delete(self, msg: BloodMessage) -> tuple[bool, str]:
        if not msg.is_own:
            return False, "Only your own messages can be deleted"
        return self._rewrite(msg, lambda entry: b"")

    def _rewrite(self, msg: BloodMessage, change) -> tuple[bool, str]:
        """Replace the entry of msg with change(entry) and write the region back."""
        problems = self.problems()
        if problems:
            return False, "; ".join(problems)
        region = self._region()
        found = self._chunk6(region)
        if found is None:
            return False, "No message data in this slot"
        start, size = found
        payload = region[start : start + size]
        length = 8 + msg.size + (-msg.size % 4)
        entry = payload[msg.offset : msg.offset + length]
        current = _parse_entry(msg.kind, msg.offset, entry[8 : 8 + msg.size])
        if current is None or current != msg:
            return False, "Message data changed since it was read; reload the slot"

        payload = payload[: msg.offset] + change(entry) + payload[msg.offset + length :]
        chain = region[4 : start - 8] + _CHUNK_HEADER.pack(6, 2, len(payload)) + payload
        chain += region[
            start + size : start + size + self._tail_length(region, start + size)
        ]
        new_region = region[:4] + chain
        new_region += bytes(NETMAN_SIZE - len(new_region))
        problems = netman_problems(new_region)
        if problems:
            return False, "; ".join(problems)

        offset = self._slot.net_man_offset
        self._save._raw_data[offset : offset + NETMAN_SIZE] = new_region
        from er_save_manager.parser.world import NetMan

        self._slot.net_man = NetMan.read(BytesIO(new_region))
        return True, "Message updated"

    @staticmethod
    def _tail_length(region: bytes, pos: int) -> int:
        """Length of the chunks after chunk 6 including the terminator."""
        start = pos
        while True:
            ctype, _, size = _CHUNK_HEADER.unpack_from(region, pos)
            pos += 8 + size
            if ctype == 0xFFFF:
                return pos - start
