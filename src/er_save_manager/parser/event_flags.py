"""
Elden Ring Save Parser - Event Flags

Implements event flag reading and writing using the binary search tree
from the game's CSFD4VirtualMemoryFlag structure.

Includes corruption detection and fixes for:
- Ranni's Tower quest soft-lock
- Warp sickness (Radahn, Morgott, Radagon, Sealing Tree)
"""

from pathlib import Path


class EventFlags:
    """
    Event flag reader/writer for Elden Ring save files.

    Uses pre-computed BST mapping from eventflag_bst.txt to convert
    event IDs to byte offsets in the event_flags array.
    """

    FLAG_DIVISOR = 1000
    BLOCK_SIZE = 125
    EVENT_FLAGS_SIZE = 0x1BF99F

    _bst_map: dict[int, int] | None = None

    @classmethod
    def _load_bst_map(cls) -> dict[int, int]:
        """
        Load the BST mapping from eventflag_bst.txt.

        Format: each line is "block,offset" where:
        - block = event_id // 1000
        - offset = byte offset in the event_flags array / 125

        Returns:
            Dictionary mapping block numbers to offsets
        """
        if cls._bst_map is not None:
            return cls._bst_map

        cls._bst_map = {}

        possible_paths = [
            Path("eventflag_bst.txt"),
            Path("resources/eventflag_bst.txt"),
            Path(__file__).parent / "eventflag_bst.txt",
            Path(__file__).parent / "resources" / "eventflag_bst.txt",
            Path(__file__).parent.parent / "resources" / "eventflag_bst.txt",
            Path(__file__).parent.parent.parent
            / "resources"
            / "eventflag_bst.txt",  # /src/resources/
        ]

        loaded = False
        for path in possible_paths:
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        parts = line.split(",")
                        if len(parts) != 2:
                            continue

                        block = int(parts[0])
                        offset = int(parts[1])
                        cls._bst_map[block] = offset
                loaded = True
                break
            except FileNotFoundError:
                continue

        if not loaded:
            raise FileNotFoundError(
                f"eventflag_bst.txt not found. Tried: {[str(p) for p in possible_paths]}"
            )

        return cls._bst_map

    @classmethod
    def get_flag(cls, event_flags: bytes, event_id: int) -> bool:
        """
        Get the state of an event flag.

        Args:
            event_flags: The event_flags byte array from a character slot
            event_id: The event flag ID to check

        Returns:
            True if the flag is set, False otherwise
        """
        if len(event_flags) != cls.EVENT_FLAGS_SIZE:
            raise ValueError(
                f"event_flags must be {cls.EVENT_FLAGS_SIZE} bytes, "
                f"got {len(event_flags)}"
            )

        bst_map = cls._load_bst_map()

        block = event_id // cls.FLAG_DIVISOR
        index = event_id - block * cls.FLAG_DIVISOR

        if block not in bst_map:
            raise ValueError(f"Event ID {event_id} (block {block}) not found in BST")

        offset = bst_map[block] * cls.BLOCK_SIZE
        byte_index = index // 8
        bit_index = index - byte_index * 8
        bit_index = 7 - bit_index

        byte_pos = offset + byte_index
        if byte_pos >= len(event_flags):
            raise ValueError(
                f"Calculated byte position {byte_pos} exceeds event_flags size"
            )

        event_byte = event_flags[byte_pos]
        return ((event_byte >> bit_index) & 1) == 1

    @classmethod
    def set_flag(cls, event_flags: bytearray, event_id: int, state: bool) -> None:
        """
        Set the state of an event flag.

        Args:
            event_flags: The event_flags byte array from a character slot (mutable)
            event_id: The event flag ID to set
            state: True to set the flag, False to clear it
        """
        if not isinstance(event_flags, bytearray):
            raise TypeError("event_flags must be a bytearray for modification")

        if len(event_flags) != cls.EVENT_FLAGS_SIZE:
            raise ValueError(
                f"event_flags must be {cls.EVENT_FLAGS_SIZE} bytes, "
                f"got {len(event_flags)}"
            )

        bst_map = cls._load_bst_map()

        block = event_id // cls.FLAG_DIVISOR
        index = event_id - block * cls.FLAG_DIVISOR

        if block not in bst_map:
            raise ValueError(f"Event ID {event_id} (block {block}) not found in BST")

        offset = bst_map[block] * cls.BLOCK_SIZE
        byte_index = index // 8
        bit_index = index - byte_index * 8
        bit_index = 7 - bit_index

        byte_pos = offset + byte_index
        if byte_pos >= len(event_flags):
            raise ValueError(
                f"Calculated byte position {byte_pos} exceeds event_flags size"
            )

        event_byte = event_flags[byte_pos]

        if state:
            event_byte |= 1 << bit_index
        else:
            event_byte &= ~(1 << bit_index)

        event_flags[byte_pos] = event_byte


class FixFlags:
    """Event flag IDs used for corruption fixes."""

    # Ranni quest flags
    # Flag 1034500738 blocks progression when ON
    RANNI_BLOCKING_FLAG = 1034500738

    # All flags that need to be enabled for Ranni's quest to progress
    # These cover: entering service, exhausting dialogues (Iji, Blaidd, Seluvis, Ranni)
    RANNI_FLAGS_TO_ENABLE = [
        1034509410,
        1034509412,
        1034500732,
        1034500736,
        1034505015,
        1034509361,
        1034500715,
        1034500710,
        1034500700,
        1034490701,
        1034490700,
        1034509413,
        1034509418,
        1034509355,
        1034509357,
        1034509358,
        1034509205,
        1045379208,
        1034509305,
        1034509306,
        1034509417,
        1034500734,
        1034509416,
        1034500739,
        1034500733,
        1034502610,
        1034505002,
        1034505003,
        1034505004,
        1034500716,
        1034503600,
    ]

    # Warp sickness flags - Radahn
    METEORITE_GREEN = 310
    DEFEATED_RADAHN = 9130
    RADAHN_MAP_MARKER = 9417
    GRACE_RADAHN = 76422
    GRACE_WAR_DEAD_CATACOMBS = 73016

    # Warp sickness flags - Morgott
    MORGOTT_DEFEATED = 11000800
    MORGOTT_THORNS_TOUCHED = 11000500
    MORGOTT_FOG_WALL = 11000501

    # Warp sickness flags - Radagon
    DEFEATED_RADAGON = 9123
    ENDING_CUTSCENE = 121
    GRACE_FRACTURED_MARIKA = 71900

    # Warp sickness flags - Sealing Tree (DLC)
    SPIRIT_TREE_BURNING = 330
    DEFEATED_DANCING_LION = 9140
    SEALING_TREE_RESTED_AFTER = 20010500
    GRACE_ENIR_ILIM_OUTER_WALL = 72012


class CorruptionDetector:
    """Detect quest soft-locks and warp sickness issues."""

    @staticmethod
    def check_ranni_softlock(event_flags: bytes) -> bool:
        """
        Detect Ranni's Tower quest soft-lock.

        Checks if blocking flag 1034500738 is ON.
        """
        try:
            return EventFlags.get_flag(event_flags, FixFlags.RANNI_BLOCKING_FLAG)
        except ValueError:
            return False

    @staticmethod
    def check_radahn_alive_warp(event_flags: bytes) -> bool:
        """
        Detect Radahn warp sickness (alive variant).

        Condition: EventFlag(310) && !EventFlag(9130)
        """
        try:
            meteorite = EventFlags.get_flag(event_flags, FixFlags.METEORITE_GREEN)
            defeated = EventFlags.get_flag(event_flags, FixFlags.DEFEATED_RADAHN)
            return meteorite and not defeated
        except ValueError:
            return False

    @staticmethod
    def check_radahn_dead_warp(event_flags: bytes) -> bool:
        """
        Detect Radahn warp sickness (dead variant).

        Condition: EventFlag(310) && EventFlag(9130) && !(EventFlag(76422) || EventFlag(73016))
        """
        try:
            meteorite = EventFlags.get_flag(event_flags, FixFlags.METEORITE_GREEN)
            defeated = EventFlags.get_flag(event_flags, FixFlags.DEFEATED_RADAHN)
            grace1 = EventFlags.get_flag(event_flags, FixFlags.GRACE_RADAHN)
            grace2 = EventFlags.get_flag(event_flags, FixFlags.GRACE_WAR_DEAD_CATACOMBS)
            return meteorite and defeated and not (grace1 or grace2)
        except ValueError:
            return False

    @staticmethod
    def check_morgott_warp(event_flags: bytes) -> bool:
        """
        Detect Morgott warp sickness.

        Condition: EventFlag(11000800) && !(EventFlag(11000500) && EventFlag(11000501))
        """
        try:
            defeated = EventFlags.get_flag(event_flags, FixFlags.MORGOTT_DEFEATED)
            thorns = EventFlags.get_flag(event_flags, FixFlags.MORGOTT_THORNS_TOUCHED)
            fog = EventFlags.get_flag(event_flags, FixFlags.MORGOTT_FOG_WALL)
            return defeated and not (thorns and fog)
        except ValueError:
            return False

    @staticmethod
    def check_radagon_warp(event_flags: bytes) -> bool:
        """
        Detect Radagon/Elden Beast warp sickness.

        Condition: EventFlag(9123) && !(EventFlag(121) || EventFlag(71900))
        """
        try:
            defeated = EventFlags.get_flag(event_flags, FixFlags.DEFEATED_RADAGON)
            ending = EventFlags.get_flag(event_flags, FixFlags.ENDING_CUTSCENE)
            grace = EventFlags.get_flag(event_flags, FixFlags.GRACE_FRACTURED_MARIKA)
            return defeated and not (ending or grace)
        except ValueError:
            return False

    @staticmethod
    def check_sealing_tree_warp(event_flags: bytes) -> bool:
        """
        Detect Sealing Tree warp sickness (DLC).

        Condition: EventFlag(330) && !EventFlag(9140) && !EventFlag(72012)
        """
        try:
            burning = EventFlags.get_flag(event_flags, FixFlags.SPIRIT_TREE_BURNING)
            defeated = EventFlags.get_flag(event_flags, FixFlags.DEFEATED_DANCING_LION)
            grace = EventFlags.get_flag(
                event_flags, FixFlags.GRACE_ENIR_ILIM_OUTER_WALL
            )
            return burning and not defeated and not grace
        except ValueError:
            return False

    @classmethod
    def detect_all(cls, event_flags: bytes) -> list[str]:
        """
        Detect all known corruption issues.

        Returns:
            List of issue names
        """
        issues = []

        if cls.check_ranni_softlock(event_flags):
            issues.append("ranni_softlock")
        if cls.check_radahn_alive_warp(event_flags):
            issues.append("radahn_alive_warp")
        if cls.check_radahn_dead_warp(event_flags):
            issues.append("radahn_dead_warp")
        if cls.check_morgott_warp(event_flags):
            issues.append("morgott_warp")
        if cls.check_radagon_warp(event_flags):
            issues.append("radagon_warp")
        if cls.check_sealing_tree_warp(event_flags):
            issues.append("sealing_tree_warp")

        return issues


class CorruptionFixer:
    """Apply fixes for detected corruption issues."""

    @staticmethod
    def fix_ranni_softlock(event_flags: bytearray) -> bool:
        """
        Fix Ranni's Tower quest soft-lock.

        Matches Cheat Engine script behavior:
        1. Set blocking flag 1034500738 OFF
        2. Enable all 31 progression flags
        """
        try:
            # Set blocking flag OFF
            EventFlags.set_flag(event_flags, FixFlags.RANNI_BLOCKING_FLAG, False)

            # Enable all progression flags
            for flag_id in FixFlags.RANNI_FLAGS_TO_ENABLE:
                EventFlags.set_flag(event_flags, flag_id, True)

            return True
        except Exception:
            return False

    @staticmethod
    def fix_radahn_alive_warp(event_flags: bytearray) -> bool:
        """
        Fix Radahn warp sickness (alive variant).

        Closes crater and removes map marker.
        """
        try:
            EventFlags.set_flag(event_flags, FixFlags.METEORITE_GREEN, False)
            EventFlags.set_flag(event_flags, FixFlags.RADAHN_MAP_MARKER, False)
            return True
        except Exception:
            return False

    @staticmethod
    def fix_radahn_dead_warp(event_flags: bytearray) -> bool:
        """
        Fix Radahn warp sickness (dead variant).

        Grants the grace site.
        """
        try:
            EventFlags.set_flag(event_flags, FixFlags.GRACE_RADAHN, True)
            return True
        except Exception:
            return False

    @staticmethod
    def fix_morgott_warp(event_flags: bytearray) -> bool:
        """
        Fix Morgott warp sickness.

        Touches thorns and drops fog wall.
        """
        try:
            EventFlags.set_flag(event_flags, FixFlags.MORGOTT_THORNS_TOUCHED, True)
            EventFlags.set_flag(event_flags, FixFlags.MORGOTT_FOG_WALL, True)
            return True
        except Exception:
            return False

    @staticmethod
    def fix_radagon_warp(event_flags: bytearray) -> bool:
        """
        Fix Radagon/Elden Beast warp sickness.

        Grants the grace site.
        """
        try:
            EventFlags.set_flag(event_flags, FixFlags.GRACE_FRACTURED_MARIKA, True)
            return True
        except Exception:
            return False

    @staticmethod
    def fix_sealing_tree_warp(event_flags: bytearray) -> bool:
        """
        Fix Sealing Tree warp sickness (DLC).

        Grants grace and blocks warp sickness.
        """
        try:
            EventFlags.set_flag(event_flags, FixFlags.GRACE_ENIR_ILIM_OUTER_WALL, True)
            EventFlags.set_flag(event_flags, FixFlags.SEALING_TREE_RESTED_AFTER, True)
            return True
        except Exception:
            return False

    @classmethod
    def fix_all(
        cls, event_flags: bytearray, issues: list[str]
    ) -> tuple[int, list[str]]:
        """
        Apply fixes for all detected issues.

        Args:
            event_flags: Mutable event flags array
            issues: List of issue names from detect_all()

        Returns:
            (fixes_applied, list_of_fix_descriptions)
        """
        fix_map = {
            "ranni_softlock": (cls.fix_ranni_softlock, "Ranni's Tower soft-lock"),
            "radahn_alive_warp": (cls.fix_radahn_alive_warp, "Radahn warp (alive)"),
            "radahn_dead_warp": (cls.fix_radahn_dead_warp, "Radahn warp (dead)"),
            "morgott_warp": (cls.fix_morgott_warp, "Morgott warp"),
            "radagon_warp": (cls.fix_radagon_warp, "Radagon warp"),
            "sealing_tree_warp": (cls.fix_sealing_tree_warp, "Sealing Tree warp"),
        }

        fixes_applied = 0
        fix_descriptions = []

        for issue in issues:
            if issue in fix_map:
                fixer, description = fix_map[issue]
                if fixer(event_flags):
                    fixes_applied += 1
                    fix_descriptions.append(description)

        return fixes_applied, fix_descriptions
