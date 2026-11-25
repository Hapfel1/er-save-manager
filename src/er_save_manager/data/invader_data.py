"""
Elden Ring NPC invaders and NPC red summon signs.

invaders.json rows, from map EMEVD and MSB:
[name, kind, defeat_flag, clear_flags, reward_flags, location, map,
x, y, z, vanilla_only, needs_on, needs_off, convergence_xyz]

kind "invasion": the NPC invades the player (common_func 90005790). The
invasion stops for good once the defeat flag (X4) is set; X8 and X12 are
the summon and dismissal flags of the invasion sign, cleared too on reset.
The position is the invader's MSB part.

kind "red_sign": the player invades the NPC's world through a red summon
sign (common_func 90005795 with sign type 30010, or a map event placing a
30010 sign). The sign is gone once the defeat flag (76xx) is set. The
position is the sign asset.

reward_flags are the pickup flags of the defeat reward lot (common_func
90005774 X8, or the lot of 90005792 X16). Clearing them lets the reward
drop again on the next defeat.

vanilla_only rows are invasions The Convergence's event scripts remove.
convergence_xyz is the position in The Convergence's MSB where it differs.

needs_on / needs_off are the quest conditions of the invasion or sign
event besides the defeat flag: the gate flag the event waits for (90005790
X36, 90005795 X8) and the flag that ends it (90005790 X0). The game
re-evaluates the gates from quest progress, so a reset only brings the NPC
back while they hold. Moore's revenge invasions are gated by common_func
90005759, which ends once 2045429280 or 4901 is set; defeating any of his
invasions sets both (90005767) and marks Moore dead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

KIND_INVASION = "invasion"
KIND_RED_SIGN = "red_sign"

_KIND_LABELS = {KIND_INVASION: "invasion", KIND_RED_SIGN: "red sign"}


@dataclass(frozen=True)
class Invader:
    name: str
    kind: str
    defeat_flag: int
    clear_flags: tuple[int, ...]
    reward_flags: tuple[int, ...]
    location: str
    map_id: str
    position: tuple[float, float, float]
    vanilla_only: bool
    needs_on: tuple[int, ...]
    needs_off: tuple[int, ...]
    convergence_position: tuple[float, float, float] | None

    @property
    def key(self) -> str:
        """Unique row id: one NPC can invade in several places."""
        return f"invader:{self.defeat_flag}"

    @property
    def label(self) -> str:
        return f"{self.name} ({_KIND_LABELS[self.kind]})"


@cache
def _all() -> tuple[Invader, ...]:
    rows = json.loads(
        (Path(__file__).parent / "invaders.json").read_text(encoding="utf-8")
    )
    return tuple(
        Invader(
            name,
            kind,
            defeat,
            tuple(clear),
            tuple(reward),
            location,
            map_id,
            (x, y, z),
            bool(vanilla_only),
            tuple(needs_on),
            tuple(needs_off),
            tuple(cnv_xyz) if cnv_xyz else None,
        )
        for (
            name,
            kind,
            defeat,
            clear,
            reward,
            location,
            map_id,
            x,
            y,
            z,
            vanilla_only,
            needs_on,
            needs_off,
            cnv_xyz,
        ) in rows
    )


def get_invaders(is_convergence: bool = False) -> list[Invader]:
    """Invaders of the save's flavor, sorted by name then location."""
    invaders = []
    for invader in _all():
        if is_convergence and invader.vanilla_only:
            continue
        if is_convergence and invader.convergence_position:
            invader = replace(invader, position=invader.convergence_position)
        invaders.append(invader)
    return sorted(invaders, key=lambda i: (i.name, i.location))


def invader_by_key(key: str) -> Invader | None:
    return next((i for i in _all() if i.key == key), None)


def invader_defeated(event_flags_accessor, invader: Invader) -> bool:
    return bool(event_flags_accessor.get_flag(invader.defeat_flag))


def invader_blocked(event_flags_accessor, invader: Invader) -> bool:
    """Whether the quest state keeps the invasion or sign from returning."""
    get = event_flags_accessor.get_flag
    return not all(get(f) for f in invader.needs_on) or any(
        get(f) for f in invader.needs_off
    )


def reset_invader(event_flags_accessor, invader: Invader, reward: bool = False):
    """Clear the defeat state so the invasion or red sign returns; with
    reward, also clear the reward's pickup flags."""
    for flag_id in invader.clear_flags:
        event_flags_accessor.set_flag(flag_id, False)
    if reward:
        for flag_id in invader.reward_flags:
            event_flags_accessor.set_flag(flag_id, False)
