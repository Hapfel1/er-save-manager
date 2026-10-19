"""Face param overrides and the Eye Alterations toggle of a character slot.

The FaceData blob ends with the Face Edit "Eye Alterations" toggle (u8 at
+0x125) and two FaceParam override ids (i32 at +0x127 and +0x12B, -1 none),
set in game by EMEVD 2004[75] Set Character Face Param Override.

The game loads the override ids from the save. common.emevd 1800 (slot 0)
and 1801 (slot 1) only react when a flag changes while playing:
- 1800 sets 9420 and picks 81000 if 9431 is on, else 81001 if 9432 is on,
  else 81002 if 9433 is on; 9434 blocks 81001 and 81002. 9431 turning off
  falls back to the next one, or clears the override and 9420.
- 1801 sets 9421 and 80000 once 9430 turns on.
Miquella's Needle (common 920) clears 9431 only. common 3080 sets 9433
after four Dragon Communion purchases unless 9433 is already on, so 9433 is
never cleared here: the eyes would come back on the next load.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING

from er_save_manager.parser.event_flags import EventFlags

if TYPE_CHECKING:
    from er_save_manager.parser.save import Save

# Offsets inside the slot FaceData blob
_EYE_ALTERATIONS = 0x125
_OVERRIDE_0 = 0x127
_OVERRIDE_1 = 0x12B

NONE = -1
FRENZIED_FLAME_EYES = 81000
BLOODY_FINGER_EYES = 81001
DRAGON_COMMUNION_EYES = 81002
FRENZIED_FLAME_MARK = 80000

# Slot 0 ids in event 1800 priority order, with the flag that selects each
EYE_OVERRIDES = {
    FRENZIED_FLAME_EYES: 9431,
    BLOODY_FINGER_EYES: 9432,
    DRAGON_COMMUNION_EYES: 9433,
}
_SLOT0_ACTIVE = 9420
_SLOT1_ACTIVE = 9421
_BLOCKS_LATER_EYES = 9434


@dataclass
class FaceOverrides:
    eyes: int = NONE
    mark: bool = False
    eye_alterations: bool = True
    # 9434 is on: event 1800 replaces 81001 / 81002 with no override on the
    # next flag change
    eyes_blocked: bool = False


def read(save: Save, slot_idx: int) -> FaceOverrides:
    slot = save.character_slots[slot_idx]
    raw = slot.face_data.raw_data
    eyes = struct.unpack_from("<i", raw, _OVERRIDE_0)[0]
    mark = struct.unpack_from("<i", raw, _OVERRIDE_1)[0]
    return FaceOverrides(
        eyes=eyes,
        mark=mark == FRENZIED_FLAME_MARK,
        eye_alterations=raw[_EYE_ALTERATIONS] != 0,
        eyes_blocked=EventFlags.get_flag(slot.event_flags, _BLOCKS_LATER_EYES),
    )


def write(save: Save, slot_idx: int, state: FaceOverrides) -> None:
    """Write the fields of state that differ from the slot, with their flags.

    Unchanged fields keep their bytes, also ids other tools left that the
    game never sets. Raises ValueError for a new eye id the game has no
    event for.
    """
    current = read(save, slot_idx)
    eyes_changed = state.eyes != current.eyes
    if eyes_changed and state.eyes != NONE and state.eyes not in EYE_OVERRIDES:
        raise ValueError(f"unknown eye override {state.eyes}")
    slot = save.character_slots[slot_idx]
    if isinstance(save._raw_data, bytes):
        save._raw_data = bytearray(save._raw_data)

    face = bytearray(slot.face_data.raw_data)
    if state.eye_alterations != current.eye_alterations:
        face[_EYE_ALTERATIONS] = 1 if state.eye_alterations else 0
    if eyes_changed:
        struct.pack_into("<i", face, _OVERRIDE_0, state.eyes)
    if state.mark != current.mark:
        struct.pack_into(
            "<i", face, _OVERRIDE_1, FRENZIED_FLAME_MARK if state.mark else NONE
        )
    off = slot.data_start + slot.face_data_offset
    save._raw_data[off : off + len(face)] = face
    slot.face_data.raw_data = bytes(face)

    flags = bytearray(slot.event_flags)
    if eyes_changed:
        EventFlags.set_flag(flags, _SLOT0_ACTIVE, state.eyes in EYE_OVERRIDES)
        if state.eyes in EYE_OVERRIDES:
            EventFlags.set_flag(flags, EYE_OVERRIDES[state.eyes], True)
        if state.eyes != FRENZIED_FLAME_EYES:
            # The Needle's write; a set 9431 outranks every other id
            EventFlags.set_flag(flags, EYE_OVERRIDES[FRENZIED_FLAME_EYES], False)
    if state.mark != current.mark:
        EventFlags.set_flag(flags, _SLOT1_ACTIVE, state.mark)
    off = slot.event_flags_offset
    save._raw_data[off : off + len(flags)] = flags
    slot.event_flags = bytes(flags)
