"""
Warnings for graces the game spawns only after a boss is defeated.

flag_state(flag_id) returns the character's event flag state, or None when
it cannot be read; an unreadable gate counts as open.
"""

from __future__ import annotations

from collections.abc import Callable

from er_save_manager.data.grace_data import (
    BossGate,
    arena_gate,
    get_graces,
    grace_gate,
    location_gate,
)
from er_save_manager.data.locations import MapLocation
from er_save_manager.parser.event_flags import FixFlags
from er_save_manager.ui.dialogs.opt_out_warning import confirm_warning
from er_save_manager.ui.dialogs.teleport_warnings import BOSS_GATE_SETTING
from er_save_manager.ui.messagebox import CTkMessageBox

FlagState = Callable[[int], bool | None]

_LIST_LIMIT = 10
ASHEN_CAPITAL_REGION = "Leyndell, Ashen Capital"


def closed_gate(
    loc: MapLocation, convergence: bool, flag_state: FlagState
) -> BossGate | None:
    """Gate of a location whose flag is not set on the character."""
    if loc.tile_type in ("pin", "bloodstain"):
        gate = arena_gate(loc.arena_flag, convergence)
    else:
        gate = location_gate(loc.tile_type, loc.map_id_str, loc.flag_id, convergence)
    if gate is None or flag_state(gate.flag_id) is not False:
        return None
    return gate


def gate_status(gate: BossGate, flag_state: FlagState) -> str:
    """Short status text: "Godrick the Grafted (alive)"."""
    state = flag_state(gate.flag_id)
    what = gate.boss or f"Event flag {gate.flag_id}"
    if state is None:
        return what
    if gate.boss:
        return f"{what} ({'defeated' if state else 'alive'})"
    return f"{what} ({'set' if state else 'not set'})"


def confirm_teleport(
    loc: MapLocation, convergence: bool, flag_state: FlagState, parent
) -> bool:
    """Warn before a teleport onto a grace that the game has not spawned yet,
    or into the arena of a living boss."""
    gate = closed_gate(loc, convergence, flag_state)
    if gate is None:
        return True
    arrival = (
        " The character arrives in the boss arena with the boss alive."
        if gate.boss
        else ""
    )
    if loc.tile_type == "grace":
        where = f"The grace {loc.name} only appears after {gate.condition}."
    elif loc.tile_type in ("pin", "bloodstain"):
        where = (
            f"This spot is inside the fog wall of {gate.boss}."
            if gate.boss
            else "This spot is inside a boss fog wall. The boss (event flag "
            f"{gate.flag_id}) is not defeated on this character."
        )
    else:
        where = f"{loc.name} is at a grace that only appears after {gate.condition}."
    boss = gate.boss or loc.tile_type in ("pin", "bloodstain")
    return confirm_warning(
        parent,
        BOSS_GATE_SETTING,
        "Boss Not Defeated" if boss else "Grace Not Spawned",
        "Boss alive" if boss else "Grace not spawned",
        [f"{where}{arrival}"],
        confirm_text="Teleport",
    )


def filter_unlock(
    grace_flags: list[int],
    names: dict[int, str],
    convergence: bool,
    flag_state: FlagState,
    parent,
    vanilla: bool = False,
) -> list[int] | None:
    """Ask whether to include graces the game has not spawned yet and, on a
    vanilla save with Maliketh alive, the Leyndell, Ashen Capital graces.

    Returns the grace flags to unlock, or None when cancelled. Graces that
    are already unlocked are not asked about.
    """
    grace_flags = _filter_closed(grace_flags, names, convergence, flag_state, parent)
    if grace_flags is None or not vanilla:
        return grace_flags
    return _filter_ashen(grace_flags, names, flag_state, parent)


def _filter_ashen(
    grace_flags: list[int], names: dict[int, str], flag_state: FlagState, parent
) -> list[int] | None:
    if flag_state(FixFlags.DEFEATED_MALIKETH) is not False:
        return grace_flags
    ashen = {g.flag_id for g in get_graces() if g.region == ASHEN_CAPITAL_REGION}
    asked = [f for f in grace_flags if f in ashen and flag_state(f) is False]
    if not asked:
        return grace_flags
    n = len(asked)
    answer = CTkMessageBox.askyesnocancel(
        "Ashen Capital Graces Included",
        f"{n} of these graces are in Leyndell, Ashen Capital:\n\n"
        + "\n".join(f"- {names.get(f, str(f))}" for f in asked[:_LIST_LIMIT])
        + "\n\nMaliketh is alive on this character, so the rest of the world "
        "is not ashen yet. Entering the Ashen Capital in this state on a "
        "vanilla save can get the account banned online.\n\n"
        f"Unlock {'it' if n == 1 else 'them'} too? No skips "
        f"{'it' if n == 1 else 'them'} and unlocks the rest.",
        parent=parent,
    )
    if answer is None:
        return None
    if answer:
        return grace_flags
    skip = set(asked)
    return [f for f in grace_flags if f not in skip]


def _filter_closed(
    grace_flags: list[int],
    names: dict[int, str],
    convergence: bool,
    flag_state: FlagState,
    parent,
) -> list[int] | None:
    closed = []
    for flag in grace_flags:
        if flag_state(flag) is not False:
            continue
        gate = grace_gate(flag, convergence)
        if gate is not None and flag_state(gate.flag_id) is False:
            closed.append((flag, gate))
    if not closed:
        return grace_flags

    lines = [
        f"- {names.get(flag, str(flag))}: {gate.boss or f'event flag {gate.flag_id}'}"
        for flag, gate in closed[:_LIST_LIMIT]
    ]
    if len(closed) > _LIST_LIMIT:
        lines.append(f"- and {len(closed) - _LIST_LIMIT} more")
    n = len(closed)
    answer = CTkMessageBox.askyesnocancel(
        "Boss Graces Included",
        f"{n} of these graces only appear after their boss is defeated, "
        f"and the boss is alive on this character:\n\n"
        + "\n".join(lines)
        + f"\n\nUnlock {'it' if n == 1 else 'them'} too? No skips "
        f"{'it' if n == 1 else 'them'} and unlocks the rest.",
        parent=parent,
    )
    if answer is None:
        return None
    if answer:
        return grace_flags
    skip = {flag for flag, _ in closed}
    return [flag for flag in grace_flags if flag not in skip]
