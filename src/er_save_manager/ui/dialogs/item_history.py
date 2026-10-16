"""Read-only view of a character's Legendary trophy progress and item history.

Trophy progress comes from TrophyEquipData, the item history from
GaitemGameData (every item type the character has picked up, kept after the
item is sold or discarded).
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from er_save_manager.data.item_database import (
    ItemCategory,
    get_item_database,
    get_item_name,
)
from er_save_manager.data.legendary_items import trophy_progress
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.utils import (
    center_window,
    force_render_dialog,
    patch_combo_scroll,
    style_window_frame,
)

_ALL = "All"
_MISSING = "Missing"
_ACQUIRED = "Acquired"
_COUNTED = "Counted"
_OTHER = "Other"
_PREFIXES = ("DLC ", "Convergence ")


def _category_group(category_name: str) -> str:
    for prefix in _PREFIXES:
        if category_name.startswith(prefix):
            return category_name[len(prefix) :]
    return category_name


def _history_rows(acquired: set[int], is_convergence: bool):
    """(item id, name, category, is_dlc, acquired) for every database item of
    the save's flavor, plus acquired records the database does not list."""
    db = get_item_database()
    rows = []
    listed: set[int] = set()
    for item in db.items:
        cat = item.category_name
        if cat.startswith("Convergence") and not is_convergence:
            continue
        if item.full_id in listed:
            continue
        listed.add(item.full_id)
        name = db.resolve(item, is_convergence).name
        rows.append(
            (
                item.full_id,
                name,
                _category_group(cat),
                cat.startswith("DLC"),
                item.full_id in acquired,
            )
        )

    for item_id in sorted(acquired - listed):
        base_id, category = db.decode_item_id(item_id)
        # Spirit ash upgrade levels are separate goods ids of a listed item.
        if category == ItemCategory.GOODS and any(
            (ItemCategory.GOODS | (base_id - d)) in listed for d in range(1, 11)
        ):
            continue
        name = get_item_name(item_id, 0, is_convergence)
        if name:  # empty for the bare-body armor placeholders
            rows.append((item_id, name, _OTHER, False, True))
    return rows


def show_item_history(parent, save, slot_idx: int):
    slot = save.character_slots[slot_idx]
    is_convergence = bool(save.is_convergence)
    acquired = set(slot.gaitem_game_data.acquired_item_ids())
    rows = _history_rows(acquired, is_convergence)

    dialog = ctk.CTkToplevel(parent)
    dialog.title("Item History")
    dialog.transient(parent)
    center_window(dialog, 960, 700, parent=parent)
    dialog.resizable(True, True)
    style_window_frame(dialog, dialog=False)
    force_render_dialog(dialog)
    dialog.grab_set()

    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14, 12))
    ds.header(main, "Item History", font=ds.TITLE_LARGE)
    ctk.CTkLabel(
        main,
        text="Items stay in the history after they are sold, discarded or used up.",
        font=ds.FONT,
        text_color=ds.MUTED,
        anchor="w",
    ).pack(fill=tk.X, pady=(2, 6))

    tabs = ctk.CTkTabview(main)
    tabs.pack(fill=tk.BOTH, expand=True)
    _build_legendary_tab(tabs.add("Legendary Items"), slot, is_convergence)
    _build_history_tab(tabs.add("All Items"), rows, len(acquired))

    ds.button_row(main, [{"text": "Close", "command": dialog.destroy}], pady=(10, 0))


def _make_tree(parent, columns: dict[str, tuple[str, int, bool]]):
    box, tree = ds.themed_tree(parent, columns=tuple(columns), show="headings")
    box.pack(fill=tk.BOTH, expand=True)
    for col, (title, width, stretch) in columns.items():
        tree.heading(col, text=title)
        tree.column(col, width=width, anchor="w", stretch=stretch)
    tree.tag_configure("yes", foreground=palette.pick(palette.GREEN_TEXT))
    tree.tag_configure("no", foreground=palette.pick(palette.RED_TEXT))
    return tree


def _build_legendary_tab(tab, slot, is_convergence: bool):
    progress = trophy_progress(slot.trophy_equip_data)
    summary = "    ".join(
        f"{name.removeprefix('Legendary ')}: {sum(c for _, c in items)} / {len(items)}"
        for name, items in progress
    )
    ctk.CTkLabel(tab, text=summary, font=ds.FONT, anchor="w").pack(
        fill=tk.X, padx=4, pady=(4, 6)
    )
    tree = _make_tree(
        tab,
        {
            "state": ("State", 100, False),
            "item": ("Item", 380, True),
            "trophy": ("Trophy", 320, True),
        },
    )
    for name, items in progress:
        for item_id, counted in items:
            tree.insert(
                "",
                "end",
                values=(
                    _COUNTED if counted else _MISSING,
                    get_item_name(item_id, 0, is_convergence),
                    name,
                ),
                tags=("yes" if counted else "no",),
            )


def _build_history_tab(tab, rows, acquired_count: int):
    filters = ctk.CTkFrame(tab, fg_color="transparent")
    filters.pack(fill=tk.X, padx=4, pady=(4, 6))

    scope_var = tk.StringVar(value=_ALL)
    category_var = tk.StringVar(value=_ALL)
    state_var = tk.StringVar(value=_ALL)
    search_var = tk.StringVar()

    categories = sorted({r[2] for r in rows} - {_OTHER})
    if any(r[2] == _OTHER for r in rows):
        categories.append(_OTHER)

    for label, var, values, width in (
        ("Scope:", scope_var, [_ALL, "Base Game", "DLC"], 120),
        ("Category:", category_var, [_ALL, *categories], 220),
        ("Show:", state_var, [_ALL, _ACQUIRED, _MISSING], 120),
    ):
        ctk.CTkLabel(filters, text=label, font=ds.FONT).pack(side=tk.LEFT, padx=(0, 6))
        combo = ctk.CTkComboBox(
            filters,
            variable=var,
            values=values,
            state="readonly",
            width=width,
            command=lambda _v: refresh(),
        )
        combo.pack(side=tk.LEFT, padx=(0, 14))
        patch_combo_scroll(combo)

    entry = ctk.CTkEntry(
        tab, textvariable=search_var, placeholder_text="Search items..."
    )
    entry.pack(fill=tk.X, padx=4, pady=(0, 6))
    search_var.trace_add("write", lambda *_: refresh())

    summary = ctk.CTkLabel(tab, text="", font=ds.SMALL, anchor="w")
    summary.pack(fill=tk.X, padx=4, pady=(0, 4))

    tree = _make_tree(
        tab,
        {
            "state": ("State", 100, False),
            "item": ("Item", 420, True),
            "category": ("Category", 240, True),
        },
    )

    def refresh():
        tree.delete(*tree.get_children())
        scope = scope_var.get()
        category = category_var.get()
        state = state_var.get()
        query = search_var.get().strip().lower()
        shown = have = total = 0
        for _item_id, name, cat, is_dlc, got in rows:
            if scope == "DLC" and not is_dlc or scope == "Base Game" and is_dlc:
                continue
            if category != _ALL and cat != category:
                continue
            if query and query not in name.lower():
                continue
            total += 1
            have += got
            if state == _ACQUIRED and not got or state == _MISSING and got:
                continue
            tree.insert(
                "",
                "end",
                values=(_ACQUIRED if got else _MISSING, name, cat),
                tags=("yes" if got else "no",),
            )
            shown += 1
        summary.configure(
            text=f"{have} of {total} acquired in this filter, {shown} shown. "
            f"{acquired_count} item types in the character's history."
        )

    refresh()
