"""
Nyasu build importer - v3 (full).

Adds on top of v2: Golden Seeds / Sacred Tears for flask upgrades,
talisman pouches, Flask of Wondrous Physick, great rune lookup.
"""

from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog

from er_save_manager.ui.messagebox import CTkMessageBox

_CLASS_MAP = {
    "Vagabond": 0,
    "Warrior": 1,
    "Hero": 2,
    "Bandit": 3,
    "Astrologer": 4,
    "Prophet": 5,
    "Samurai": 6,
    "Prisoner": 7,
    "Confessor": 8,
    "Wretch": 9,
}

# Cumulative Golden Seeds needed to reach N total flask charges from base of 4
_SEED_COST = {
    4: 0,
    5: 1,
    6: 2,
    7: 4,
    8: 6,
    9: 9,
    10: 12,
    11: 16,
    12: 20,
    13: 25,
    14: 30,
}

_GOLDEN_SEED_ID = 0x4000272A  # 10010
_SACRED_TEAR_ID = 0x40002734  # 10020
_TALISMAN_POUCH_ID = 0x40002740  # 10040
_PHYSICK_EMPTY_ID = 0x400000FA  # 250 - Flask of Wondrous Physick (Empty)
_PHYSICK_ID = 0x400000FB  # 251 - Flask of Wondrous Physick


def import_nyasu(
    parent,
    save_file,
    slot_idx: int,
    get_save_path,
    ensure_mutable,
    create_backup,
    on_refresh,
) -> None:
    CTkMessageBox.showinfo(
        "Import from Nyasu",
        (
            "How to get your build JSON:\n\n"
            "1. Go to https://er-inventory.nyasu.business\n"
            "2. Open your build\n"
            "3. Click Load/Save  ->  JSON  ->  Download\n\n"
            "Click OK, then select the downloaded file."
        ),
        parent=parent,
    )

    path = filedialog.askopenfilename(
        title="Select Nyasu Build JSON",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        parent=parent,
    )
    if not path:
        return

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        CTkMessageBox.showerror(
            "Import Error", f"Failed to read JSON:\n{e}", parent=parent
        )
        return

    apply_stats = CTkMessageBox.askyesno(
        "Apply Stats",
        "Also apply stats and starting class from this build?",
        parent=parent,
    )

    from er_save_manager.data.item_database import get_item_database
    from er_save_manager.parser.inventory_ops import add_item as _add_item

    is_cnv = save_file.is_convergence
    db = get_item_database()

    queue: list[tuple[int, int, int, int, str, str]] = []
    failed_parse: list[str] = []

    seen_weapons: set[tuple[int, int, int]] = set()
    seen_ids: set[int] = set()
    seen_names: set[str] = set()

    def _cap(reinf: str) -> int:
        if is_cnv and reinf in ("standard", "somber"):
            return 15
        return 25 if reinf == "standard" else 10 if reinf == "somber" else 0

    def _queue_weapon(s: dict) -> None:
        try:
            full_id = int(s["affinity_hex_id"], 16)
            upgrade = int(s["upgrade_hex_id"], 16)
            aow = s.get("ash_of_war_hex_id", "")
            gem_id = int(aow, 16) if aow and aow not in ("00000000", "FFFFFFFF") else 0
            key = (full_id, upgrade, gem_id)
            if key in seen_weapons:
                return
            seen_weapons.add(key)
            base = (full_id & 0x0FFFFFFF) // 10000 * 10000
            item = db.get_item_by_id(base)
            reinf = getattr(item, "reinforcement", "standard") if item else "standard"
            queue.append(
                (
                    full_id,
                    1,
                    min(upgrade, _cap(reinf)),
                    gem_id,
                    reinf,
                    s.get("name", f"0x{full_id:08X}"),
                )
            )
        except (KeyError, ValueError) as e:
            failed_parse.append(f"{s.get('name', '?')}: {e}")

    def _queue_by_id(s: dict, cat: int) -> None:
        try:
            full_id = int(s["full_hex_id"], 16)
            if full_id in seen_ids or (full_id & 0xF0000000) != cat:
                return
            seen_ids.add(full_id)
            queue.append(
                (full_id, 1, 0, 0, "standard", s.get("name", f"0x{full_id:08X}"))
            )
        except (KeyError, ValueError) as e:
            failed_parse.append(f"{s.get('name', '?')}: {e}")

    def _queue_goods(s: dict) -> None:
        try:
            full_id = int(s["full_hex_id"], 16)
            if full_id in seen_ids or (full_id & 0xF0000000) != 0x40000000:
                return
            raw = full_id & 0x00FFFFFF
            # Never spawn the equipped crimson/cerulean flasks.
            if (1000 <= raw <= 1025) or (1050 <= raw <= 1075):
                return
            # Never spawn physick from tools - the crystal-tears block handles
            # it only when the character doesn't already own one.
            if raw in (0xFA, 0xFB):
                return
            seen_ids.add(full_id)
            item = db.get_item_by_id(full_id)
            qty = getattr(item, "max_num", 1) if item else 1
            queue.append(
                (full_id, qty, 0, 0, "standard", s.get("name", f"0x{full_id:08X}"))
            )
        except (KeyError, ValueError) as e:
            failed_parse.append(f"{s.get('name', '?')}: {e}")

    def _queue_name(name: str, cat: int) -> None:
        if not name or name in seen_names:
            return
        results = db.search_items(name)
        match = next(
            (i for i in results if i.name == name and i.category == cat),
            next((i for i in results if i.category == cat), None),
        )
        if match and match.full_id not in seen_ids:
            seen_names.add(name)
            seen_ids.add(match.full_id)
            queue.append((match.full_id, 1, 0, 0, "standard", name))
        elif not match:
            failed_parse.append(f"{name}: not found in database")

    for s in data.get("inventory", {}).get("slots", []):
        _queue_weapon(s)

    for s in data.get("talismans", {}).get("slots", []):
        _queue_by_id(s, 0x20000000)

    for part in ("head", "body", "arms", "legs"):
        for s in data.get("protectors", {}).get(part, {}).get("slots", []):
            _queue_by_id(s, 0x10000000)

    for s in data.get("spells", {}).get("slots", []):
        _queue_name(s.get("name", "").strip(), 0x40000000)

    crystal_tears = data.get("items", {}).get("crystalTears", [])
    for name in crystal_tears:
        _queue_name((name or "").strip(), 0x40000000)

    for s in data.get("items", {}).get("tools", {}).get("slots", []):
        _queue_goods(s)

    # Great rune
    great_rune = data.get("greatRune", "")
    if isinstance(great_rune, str) and great_rune.strip():
        _queue_name(great_rune.strip(), 0x40000000)

    # --- extra items appended after the main queue -------------------------

    def _goods_handle(full_id: int) -> int:
        return 0xB0000000 | (full_id & 0x00FFFFFF)

    def _inv_qty(full_id: int) -> int:
        handle = _goods_handle(full_id)
        slot = save_file.characters[slot_idx]
        for inv in (slot.inventory_held, slot.inventory_storage_box):
            for it in inv.common_items:
                if it.gaitem_handle == handle:
                    return getattr(it, "quantity", 1)
        return 0

    def _has_item(full_id: int) -> bool:
        return _inv_qty(full_id) > 0

    # Wondrous Physick - needed when crystal tears are being imported
    if (
        crystal_tears
        and not _has_item(_PHYSICK_EMPTY_ID)
        and not _has_item(_PHYSICK_ID)
    ):
        seen_ids.add(_PHYSICK_EMPTY_ID)
        queue.insert(
            0,
            (
                _PHYSICK_EMPTY_ID,
                1,
                0,
                0,
                "standard",
                "Flask of Wondrous Physick (Empty)",
            ),
        )

    # Talisman pouches
    unique_talismans = sum(1 for fid, *_ in queue if (fid & 0xF0000000) == 0x20000000)
    pouches_needed = max(0, min(3, unique_talismans - 1))
    pouches_have = _inv_qty(_TALISMAN_POUCH_ID)
    pouches_to_give = max(0, pouches_needed - pouches_have)
    if pouches_to_give > 0:
        seen_ids.add(_TALISMAN_POUCH_ID)
        queue.append(
            (_TALISMAN_POUCH_ID, pouches_to_give, 0, 0, "standard", "Talisman Pouch")
        )

    # Flask upgrades: golden seeds (count) + sacred tears (level)
    flask_data = data.get("items", {}).get("flasks", {})
    build_total = flask_data.get("total", 0)
    build_level = flask_data.get("level", 0)

    if build_total > 0:
        try:
            char = save_file.characters[slot_idx].player_game_data
            current_total = getattr(char, "max_crimson_flask_count", 0) + getattr(
                char, "max_cerulean_flask_count", 0
            )
            cur = max(4, min(14, current_total))
            tgt = max(4, min(14, build_total))
            if tgt > cur:
                seeds_needed = _SEED_COST[tgt] - _SEED_COST[cur]
                if seeds_needed > 0:
                    seen_ids.add(_GOLDEN_SEED_ID)
                    queue.append(
                        (_GOLDEN_SEED_ID, seeds_needed, 0, 0, "standard", "Golden Seed")
                    )
        except Exception:
            pass

    if build_level > 0:
        # Detect current flask level from inventory (Crimson/Cerulean Tears +N IDs)
        current_level = 0
        try:
            slot = save_file.characters[slot_idx]
            for inv in (slot.inventory_held, slot.inventory_storage_box):
                for it in inv.common_items:
                    h = it.gaitem_handle
                    if (h & 0xF0000000) != 0xB0000000:
                        continue
                    raw = h & 0x00FFFFFF
                    if 1001 <= raw <= 1025 and (raw - 1001) % 2 == 0:
                        current_level = max(current_level, (raw - 1001) // 2)
                    elif 1051 <= raw <= 1075 and (raw - 1051) % 2 == 0:
                        current_level = max(current_level, (raw - 1051) // 2)
        except Exception:
            pass
        tears_needed = max(0, build_level - current_level)
        if tears_needed > 0:
            seen_ids.add(_SACRED_TEAR_ID)
            queue.append(
                (_SACRED_TEAR_ID, tears_needed, 0, 0, "standard", "Sacred Tear")
            )

    if not queue and not apply_stats:
        CTkMessageBox.showinfo("Import", "No items found in JSON.", parent=parent)
        return

    try:
        ensure_mutable()
        create_backup(save_file, slot_idx, "import_nyasu")
    except Exception as e:
        CTkMessageBox.showerror("Error", f"Cannot modify save:\n{e}", parent=parent)
        return

    failed: list[str] = [f"[parse] {m}" for m in failed_parse]
    stats_note = ""

    # --- apply stats FIRST, before any add_item calls ----------------------
    if apply_stats:
        try:
            from io import BytesIO

            from er_save_manager.data import calculate_level_from_stats

            s_json = data.get("stats", {})
            cls_name = data.get("characterClass", "")
            archetype = _CLASS_MAP.get(cls_name, 9)

            slot = save_file.characters[slot_idx]
            char = slot.player_game_data
            char.vigor = s_json.get("vig", char.vigor)
            char.mind = s_json.get("mnd", char.mind)
            char.endurance = s_json.get("vit", char.endurance)
            char.strength = s_json.get("str", char.strength)
            char.dexterity = s_json.get("dex", char.dexterity)
            char.intelligence = s_json.get("int", char.intelligence)
            char.faith = s_json.get("fth", char.faith)
            char.arcane = s_json.get("arc", char.arcane)
            char.archetype = archetype
            char.level = calculate_level_from_stats(
                char.vigor,
                char.mind,
                char.endurance,
                char.strength,
                char.dexterity,
                char.intelligence,
                char.faith,
                char.arcane,
                archetype,
                save_file.is_convergence,
            )

            buf = BytesIO()
            char.write(buf)
            char_data = buf.getvalue()
            if len(char_data) != 432:
                raise RuntimeError(
                    f"PlayerGameData serialized to {len(char_data)} bytes, expected 432"
                )

            abs_off = slot.player_game_data_offset
            save_file._raw_data[abs_off : abs_off + len(char_data)] = char_data
            stats_note = f"Stats applied ({cls_name or 'Unknown'}, RL {char.level})."
        except Exception as e:
            failed.append(f"Stats: {e}")

    # --- add items ---------------------------------------------------------
    def _pick_location() -> str:
        try:
            sl = save_file.characters[slot_idx]
            if all(it.gaitem_handle != 0 for it in sl.inventory_held.common_items):
                return "storage"
        except Exception:
            pass
        return "held"

    added: list[str] = []
    skipped: list[str] = []

    for full_id, qty, upgrade, gem_id, reinf, label in queue:
        loc = _pick_location()
        try:
            _add_item(
                save_file,
                slot_idx,
                full_id,
                qty,
                loc,
                upgrade=upgrade,
                gem_full_id=gem_id,
                reinforcement=reinf,
            )
            added.append(label)
        except ValueError as e:
            msg = str(e)
            if "already" in msg:
                skipped.append(label)
            else:
                failed.append(f"{label}: {msg}")
        except Exception as e:
            failed.append(f"{label}: {e}")

    try:
        save_file.recalculate_checksums()
        sp = get_save_path()
        if sp:
            save_file.to_file(Path(sp))
    except Exception as e:
        CTkMessageBox.showerror("Save Error", f"Failed to save:\n{e}", parent=parent)
        return

    on_refresh()

    from er_save_manager.ui.toast import show_toast

    summary = f"Imported {len(added)}"
    if skipped:
        summary += f", {len(skipped)} already owned"
    if stats_note:
        summary += f". {stats_note}"
    show_toast(parent.winfo_toplevel(), summary, duration=4000, type="success")

    if failed:
        lines = [f"Failed ({len(failed)}):"]
        lines.extend(f"  {f}" for f in failed[:12])
        if len(failed) > 12:
            lines.append(f"  ...and {len(failed) - 12} more")
        CTkMessageBox.showerror("Import Errors", "\n".join(lines), parent=parent)
