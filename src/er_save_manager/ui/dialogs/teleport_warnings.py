"""Warnings before an Elden Ring teleport, each with a "don't show again"
checkbox backed by a setting (also listed in the Settings tab)."""

from er_save_manager.ui.dialogs.opt_out_warning import confirm_warning

PIN_SETTING = "show_pin_teleport_warning"
DLC_SETTING = "show_dlc_teleport_warning"
CUSTOM_SETTING = "show_custom_teleport_warning"
ASHEN_SETTING = "show_ashen_teleport_warning"
BOSS_GATE_SETTING = "show_boss_gate_teleport_warning"


def confirm_pin_teleport(parent) -> bool:
    return confirm_warning(
        parent,
        PIN_SETTING,
        "Teleport to Map Pin",
        "Custom location",
        [
            "Map pins come from the game's navigation mesh, not from a known "
            "safe spot. Some spots can still put the character under the "
            "ground, inside a wall or out of bounds.",
            "A backup is made before the teleport. If the character ends up "
            "stuck, restore it in the Backup Manager.",
        ],
        confirm_text="Teleport",
    )


def confirm_dlc_teleport(parent, place: str) -> bool:
    return confirm_warning(
        parent,
        DLC_SETTING,
        "Teleport to DLC Area",
        "Shadow of the Erdtree area",
        [
            f"{place} is in the Shadow of the Erdtree DLC. Without the DLC "
            "the game is stuck on an endless loading screen.",
        ],
        confirm_text="Teleport",
    )


def confirm_custom_teleport(parent, coords: str) -> bool:
    return confirm_warning(
        parent,
        CUSTOM_SETTING,
        "Teleport to Custom Location",
        "Custom location",
        [
            "An invalid map ID or coordinates can put the character out of "
            "bounds or keep the save from loading.",
            f"Coordinates: {coords}",
            "A backup is made before the teleport. If the save breaks, "
            "restore it in the Backup Manager.",
        ],
        confirm_text="Teleport",
    )


def confirm_ashen_teleport(parent) -> bool:
    return confirm_warning(
        parent,
        ASHEN_SETTING,
        "Teleport to Ashen Capital",
        "Online ban risk",
        [
            "Maliketh is not defeated on this character, so the rest of the "
            "world is not ashen yet. Entering Leyndell, Ashen Capital in this "
            "state on a vanilla save can get the account banned online.",
            "Play offline or use Seamless Co-op, or teleport after defeating Maliketh.",
        ],
        confirm_text="Teleport",
    )
