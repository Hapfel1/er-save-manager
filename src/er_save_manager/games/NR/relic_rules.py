"""
Relic roll rules from the game's params (relic_rules.json).

EquipParamAntique names one AttachEffectTableParam table per effect slot;
a table lists the effects that slot can roll. Rules for a relic the game
can roll:

  Normal relics: one effect per slot table, each effect assignable to a
  different slot whose table holds it, no curses. A fixed relic (boss and
  event relics) has single-effect tables, so its effects never change.
  Deep relics: one effect per slot from the deep pools. An effect from the
  "needs curse" pool carries a curse from the curse pool in the same row;
  any other effect carries none. No curse appears twice.
  All relics: no effect twice, and no two effects that share a
  compatibilityId (AttachEffectParam). Hero-specific effects all share one,
  so a relic holds at most one of them.

The game stores effects sorted by (overrideEffectId, effectId); canonical()
gives that order, with each deep curse kept in its effect's row.

Pool contents change between game versions.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "data" / "relic_rules.json"
_EMPTY = 0xFFFFFFFF
_rules: dict | None = None

# Issue codes a relic from an older game version can trigger.
VERSION_SENSITIVE = frozenset({"pool", "pairing", "fixed"})


@dataclass(frozen=True)
class Issue:
    code: str
    message: str


def _load() -> dict:
    global _rules
    if _rules is None:
        _rules = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    return _rules


def _pool(table_id: int) -> frozenset[int] | None:
    """Rollable effects of a table, or None when the table does not exist."""
    data = _load()
    index = data["tables"].get(str(table_id))
    if index is None:
        return None
    return frozenset(data["pools"][index])


def _slot_tables(real_item_id: int) -> list[int] | None:
    return _load()["relics"].get(str(real_item_id))


def _is_deep(real_item_id: int) -> bool:
    from er_save_manager.games.NR.item_db import get_relic

    row = get_relic(real_item_id)
    return bool(row and row["deep"])


def relic_kind(real_item_id: int) -> str:
    """Relic category: unknown, unobtainable, deep, fixed or random.

    Unobtainable relics name a slot table that does not exist (placeholder
    rows such as the 20000 and 30000 scene relics).
    """
    tables = _slot_tables(real_item_id)
    if tables is None:
        return "unknown"
    pools = [_pool(t) for t in tables]
    if any(p is None for p in pools):
        return "unobtainable"
    if _is_deep(real_item_id):
        return "deep"
    if all(len(p) == 1 for p in pools):
        return "fixed"
    return "random"


def slot_count(real_item_id: int) -> int:
    return len(_slot_tables(real_item_id) or [])


def fixed_effects(real_item_id: int) -> list[int]:
    """Effects of a fixed relic in canonical order, else an empty list."""
    if relic_kind(real_item_id) != "fixed":
        return []
    effects = [next(iter(_pool(t))) for t in _slot_tables(real_item_id)]
    return [e for e in canonical(effects, [])[0] if e != _EMPTY]


def _deep_pools() -> tuple[frozenset[int], frozenset[int], frozenset[int]]:
    """(needs-curse effects, other deep effects, curses)."""
    deep = _load()["deep_pools"]
    other = frozenset().union(*(_pool(t) or frozenset() for t in deep["other"]))
    return _pool(deep["needs_curse"]), other, _pool(deep["curses"])


def rollable_effects(real_item_id: int) -> frozenset[int] | None:
    """Every effect the relic type can roll, or None when unknown."""
    kind = relic_kind(real_item_id)
    if kind == "deep":
        needs_curse, other, _ = _deep_pools()
        return needs_curse | other
    if kind in ("fixed", "random"):
        return frozenset().union(*(_pool(t) for t in _slot_tables(real_item_id)))
    return None


def curse_pool() -> frozenset[int]:
    return _deep_pools()[2]


def _effect_info(effect_id: int) -> list[int] | None:
    """[compatibilityId, overrideEffectId], or None for an unknown effect."""
    return _load()["effects"].get(str(effect_id))


def canonical(effects: list[int], curses: list[int]) -> tuple[list[int], list[int]]:
    """Effects in the game's stored order, curses moved with their rows,
    empty rows last. Both lists come back with 3 entries."""
    effects = (list(effects) + [_EMPTY] * 3)[:3]
    curses = (list(curses) + [_EMPTY] * 3)[:3]
    rows = list(zip(effects, curses, strict=True))

    def key(row: tuple[int, int]) -> tuple:
        effect = row[0]
        if effect == _EMPTY:
            return (2, 0, 0)
        info = _effect_info(effect)
        if info is None:
            return (1, 0, 0)
        return (0, info[1], effect)

    rows.sort(key=key)
    return [r[0] for r in rows], [r[1] for r in rows]


def conflicts(effect_id: int, others: list[int]) -> bool:
    """Whether effect_id cannot share a relic with any of others: the same
    effect, or the same compatibilityId."""
    info = _effect_info(effect_id)
    group = info[0] if info else -1
    for other in others:
        if other == _EMPTY:
            continue
        if other == effect_id:
            return True
        other_info = _effect_info(other)
        if group != -1 and other_info and other_info[0] == group:
            return True
    return False


def picker_relics() -> list[tuple[int, str, bool]]:
    """(relic id, label, deep) per relic type a player can get, sorted by
    label.

    Random and deep relics of one name share their rules, so each name is
    listed once (lowest id). Relics on the pre-1.03 tables only, relics
    without effect slots (Murk, Sovereign Sigil, Scenic Flatstone), the
    "Antique" rows 1-6 (placeholders whose tables hold effects no other
    relic uses) and unobtainable placeholders are left out. A fixed relic whose name other
    entries share gets its effects in the label.
    """
    from er_save_manager.games.NR.item_db import all_relics, effect_name

    legacy = set(_load()["legacy_tables"])
    groups: dict[tuple, int] = {}
    for rid_str, row in all_relics().items():
        rid = int(rid_str)
        kind = relic_kind(rid)
        tables = _slot_tables(rid) or []
        if kind in ("unknown", "unobtainable") or not tables:
            continue
        if row["name"] == "Antique":
            continue
        if kind == "random" and set(tables) <= legacy:
            continue
        key = (row["name"], kind, tuple(fixed_effects(rid)) if kind == "fixed" else ())
        groups[key] = min(groups.get(key, rid), rid)

    per_name: dict[str, int] = {}
    for name, _kind, _fixed in groups:
        per_name[name] = per_name.get(name, 0) + 1
    out = []
    for (name, kind, fixed), rid in groups.items():
        label = name
        if kind == "fixed" and per_name[name] > 1:
            label = f"{name} ({', '.join(effect_name(e) for e in fixed)})"
        out.append((rid, label, kind == "deep"))
    return sorted(out, key=lambda x: x[1])


def needs_curse(effect_id: int) -> bool:
    """Whether a deep relic effect always comes with a curse."""
    return effect_id in _deep_pools()[0]


def can_add(real_item_id: int, effect_id: int, others: list[int]) -> bool:
    """Whether effect_id fits next to the effects in the other rows: no
    conflict, and the relic's slot tables can still hold all of them."""
    if conflicts(effect_id, others):
        return False
    kind = relic_kind(real_item_id)
    filled = [e for e in others if e != _EMPTY]
    if kind == "deep":
        return effect_id in rollable_effects(real_item_id)
    if kind == "fixed":
        return effect_id in fixed_effects(real_item_id)
    if kind == "random":
        pools = [_pool(t) for t in _slot_tables(real_item_id)]
        if effect_id not in frozenset().union(*pools):
            return False
        if len(filled) >= len(pools) or not _assignable(filled, pools):
            # Other rows already break the slot rules; check() reports it.
            return True
        return _assignable([*filled, effect_id], pools)
    return True


def _assignable(effects: list[int], pools: list[frozenset[int]]) -> bool:
    return any(
        all(e in p for e, p in zip(effects, perm, strict=True))
        for perm in itertools.permutations(pools, len(effects))
    )


def check(real_item_id: int, effects: list[int], curses: list[int]) -> list[Issue]:
    """Every rule the relic breaks. An empty list means the game can roll it."""
    from er_save_manager.games.NR.item_db import effect_name, relic_name

    kind = relic_kind(real_item_id)
    if kind == "unknown":
        return [Issue("unknown", f"Unknown relic ID {real_item_id}.")]
    if kind == "unobtainable":
        return [
            Issue(
                "unobtainable",
                f"{relic_name(real_item_id)} ({real_item_id}) cannot be "
                "obtained in the game.",
            )
        ]

    effects, curses = canonical(effects, curses)
    filled = [e for e in effects if e != _EMPTY]
    cursed = [c for c in curses if c != _EMPTY]
    unknown = [e for e in filled + cursed if _effect_info(e) is None]
    issues = [Issue("unknown", f"Effect {e} is not in the game data.") for e in unknown]
    known = [e for e in filled if e not in unknown]

    if len(filled) != len(set(filled)):
        issues.append(Issue("duplicate", "The same effect appears more than once."))
    if len(cursed) != len(set(cursed)):
        issues.append(Issue("duplicate", "The same curse appears more than once."))
    groups: dict[int, int] = {}
    for e in known:
        group = _effect_info(e)[0]
        if group == -1:
            continue
        if group in groups and groups[group] != e:
            issues.append(
                Issue(
                    "compat",
                    f"{effect_name(groups[group])} and {effect_name(e)} cannot be "
                    "on the same relic.",
                )
            )
        groups[group] = e

    slots = slot_count(real_item_id)
    if len(filled) != slots:
        issues.append(
            Issue(
                "count",
                f"{relic_name(real_item_id)} holds {slots} effect(s), "
                f"not {len(filled)}.",
            )
        )

    if kind == "deep":
        needs_curse, other, curse_ids = _deep_pools()
        issues.extend(
            Issue("pool", f"{effect_name(e)} cannot roll on a deep relic.")
            for e in known
            if e not in needs_curse and e not in other
        )
        for i, (e, c) in enumerate(zip(effects, curses, strict=True), 1):
            if c != _EMPTY and c not in unknown and c not in curse_ids:
                issues.append(Issue("curse", f"{effect_name(c)} is not a curse."))
            if e == _EMPTY or e in unknown:
                if c != _EMPTY and e == _EMPTY:
                    issues.append(Issue("pairing", f"Curse {i} has no effect."))
                continue
            if e in needs_curse and c == _EMPTY:
                issues.append(
                    Issue("pairing", f"{effect_name(e)} needs a curse in row {i}.")
                )
            elif e not in needs_curse and c != _EMPTY:
                issues.append(
                    Issue("pairing", f"{effect_name(e)} cannot carry a curse.")
                )
        return issues

    if cursed:
        issues.append(Issue("curse", "Only deep relics carry curses."))
    if kind == "fixed":
        if sorted(filled) != sorted(fixed_effects(real_item_id)):
            issues.append(
                Issue(
                    "fixed",
                    f"{relic_name(real_item_id)} always has the same effects; "
                    "they cannot be changed.",
                )
            )
        return issues

    pools = [_pool(t) for t in _slot_tables(real_item_id)]
    union = frozenset().union(*pools)
    outside = [e for e in known if e not in union]
    issues.extend(
        Issue("pool", f"{effect_name(e)} cannot roll on this relic.") for e in outside
    )
    if (
        not outside
        and not unknown
        and len(filled) <= slots
        and not _assignable(filled, pools)
    ):
        issues.append(
            Issue("pool", "These effects cannot roll together on this relic.")
        )
    return issues


def edit_issues(
    old: tuple[int, list[int], list[int]], new: tuple[int, list[int], list[int]]
) -> tuple[list[Issue], list[Issue]]:
    """(blocking, warnings) for changing relic `old` into `new`.

    Unknown effects (mod data) only warn. A version-sensitive issue the
    relic already had before the edit also only warns, since the relic may
    come from an older game version.
    """
    before = {i.code for i in check(*old)} if old[0] == new[0] else set()
    blocking, warnings = [], []
    for issue in check(*new):
        if issue.code == "unknown" or (
            issue.code in VERSION_SENSITIVE and issue.code in before
        ):
            warnings.append(issue)
        else:
            blocking.append(issue)
    return blocking, warnings
