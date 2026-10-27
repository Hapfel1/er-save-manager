"""
Dialog flow importing a soulsplanner.com build into a DS2 character:
link -> stats/items choice and whether to equip the loadout -> already owned
items -> upgrades and amounts -> write.
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS2.icon_manager import (
    fit_size,
    get_icon,
    with_infusion_badge,
)
from er_save_manager.games.DS2.save import (
    LEVEL_STAT_KEYS,
    STARTING_CLASSES,
    UPGRADABLE_CATEGORIES,
    DS2Save,
)
from er_save_manager.games.DS2.soulsplanner import (
    QUANTITY_CATEGORIES,
    PlannerBuild,
    PlannerError,
    PlannerItem,
    apply_items,
    apply_stats,
    build_class_id,
    display_name,
    equip_build,
    has_loadout,
    load_build,
    owned_items,
    stat_problems,
    without_owned,
)
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import save_writable, write_failed
from er_save_manager.ui.scrollable_frame import ScrollableFrame
from er_save_manager.validation.numbers import parse_whole

_TITLE = "Import Soulsplanner Build"
_POLL_MS = 100
_ICON_SIZE = 36

# Choices of the stats/items step.
_STATS = "stats"
_ITEMS = "items"
_BOTH = "both"


def _modal(parent, title: str):
    """Hidden dialog with a padded main frame; the caller
    fills it and calls ds.finish()."""
    dialog = ds.create(parent.winfo_toplevel(), title)
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=20, pady=16)
    return dialog, main


def _heading(main, heading: str, subtitle: str = "") -> None:
    ds.header(main, heading, font=ds.TITLE_LARGE)
    if subtitle:
        ctk.CTkLabel(
            main,
            text=subtitle,
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
            justify="left",
            wraplength=500,
        ).pack(fill="x", pady=(2, 0))


def _item_icon(item: PlannerItem) -> ctk.CTkImage | None:
    """Icon of an item, with the infusion badge on infused weapons. The
    caller keeps a reference, or Tk drops the image."""
    img = get_icon(item.item_id, item.category)
    if img is None:
        return None
    if item.category == "weapons" and item.infusion:
        img = with_infusion_badge(img, item.infusion)
    return ctk.CTkImage(light_image=img, dark_image=img, size=fit_size(img, _ICON_SIZE))


def _icon_row(master, item: PlannerItem, text: str, images: list) -> ctk.CTkFrame:
    """Frame holding an item's icon (blank space when it has none) and a
    label."""
    row = ctk.CTkFrame(master, fg_color="transparent")
    image = _item_icon(item)
    if image is not None:
        images.append(image)
    ctk.CTkLabel(row, text="", image=image, width=_ICON_SIZE, height=_ICON_SIZE).pack(
        side="left"
    )
    ctk.CTkLabel(row, text=text, font=ds.FONT, wraplength=330, justify="left").pack(
        side="left", padx=(8, 0)
    )
    return row


def _ask_build(parent) -> PlannerBuild | None:
    """Ask for a build link and download it. None when cancelled."""
    dialog, main = _modal(parent, _TITLE)
    result: dict[str, PlannerBuild | None] = {"build": None}

    _, (fetch_button, _) = ds.button_row(
        main,
        [
            {"text": "Fetch Build", "command": None, "width": 120},
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
        ],
    )
    _heading(main, _TITLE, "Paste a soulsplanner.com Dark Souls II build link.")
    link_var = tk.StringVar()
    entry = ctk.CTkEntry(
        main,
        textvariable=link_var,
        placeholder_text="https://soulsplanner.com/darksouls2/12345",
        width=440,
        height=32,
        font=ds.FONT,
    )
    entry.pack(fill="x", pady=(12, 0))
    status = ctk.CTkLabel(
        main, text="", font=ds.SMALL, text_color=ds.MUTED, wraplength=440, anchor="w"
    )
    status.pack(fill="x", pady=(6, 0))

    def fetch() -> None:
        link = link_var.get()
        if not link.strip():
            return
        fetch_button.configure(state="disabled")
        status.configure(text="Fetching build...", text_color=ds.MUTED)
        outcome: dict[str, object] = {}

        def work() -> None:
            try:
                outcome["build"] = load_build(link)
            except PlannerError as e:
                outcome["error"] = str(e)

        worker = threading.Thread(target=work, daemon=True)
        worker.start()

        def poll() -> None:
            if not dialog.winfo_exists():
                return
            if worker.is_alive():
                dialog.after(_POLL_MS, poll)
                return
            if "error" in outcome:
                status.configure(text=outcome["error"], text_color=ds.ERROR)
                fetch_button.configure(state="normal")
                return
            result["build"] = outcome["build"]
            dialog.destroy()

        dialog.after(_POLL_MS, poll)

    fetch_button.configure(command=fetch)
    dialog.bind("<Return>", lambda _e: fetch())
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, parent.winfo_toplevel())
    entry.focus_set()
    dialog.wait_window()
    return result["build"]


def _ask_mode(
    parent, build: PlannerBuild, character
) -> tuple[str, bool, int | None] | None:
    """Show the build and ask what to import, whether to equip the build's
    loadout afterwards and, when the build is for another class, whether to
    switch the character to it. Returns (mode, equip, class id to switch to
    or None), or None when cancelled."""
    dialog, main = _modal(parent, _TITLE)
    dialog.resizable(True, True)
    result: dict[str, str | None] = {"mode": None}
    equip_var = tk.BooleanVar(value=has_loadout(build))

    def choose(mode: str) -> None:
        result["mode"] = mode
        dialog.destroy()

    current_problems = stat_problems(build, character)
    new_class = build_class_id(build)
    if new_class == character.starting_class or character.class_base(new_class) is None:
        new_class = None
    new_problems = (
        stat_problems(build, character, new_class) if new_class is not None else []
    )
    # Switching is preselected when only the build's own class fits its stats.
    class_var = tk.BooleanVar(
        value=new_class is not None and bool(current_problems) and not new_problems
    )

    def problems() -> list[str]:
        return new_problems if class_var.get() else current_problems

    items_state = "normal" if build.items else "disabled"
    _, (both_button, stats_button, _, _) = ds.button_row(
        main,
        [
            {"text": "Stats and Items", "command": lambda: choose(_BOTH), "width": 130},
            {"text": "Stats Only", "command": lambda: choose(_STATS), "width": 110},
            {
                "text": "Items Only",
                "command": lambda: choose(_ITEMS),
                "width": 110,
                "state": items_state,
            },
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
        ],
    )
    equip_box = ctk.CTkCheckBox(
        main,
        text="Equip the build's loadout after adding the items",
        font=ds.FONT,
        variable=equip_var,
        state="normal" if has_loadout(build) else "disabled",
    )
    equip_box.pack(side="bottom", anchor="w", pady=(10, 0))
    if new_class is not None:
        ctk.CTkCheckBox(
            main,
            text=(
                f"Change the starting class to {STARTING_CLASSES[new_class]} "
                "when importing stats"
            ),
            font=ds.FONT,
            variable=class_var,
            command=lambda: update_problems(),
        ).pack(side="bottom", anchor="w", pady=(10, 0))

    _heading(main, f"Build {build.build_id} ({build.class_name})")
    body = ScrollableFrame(main, fg_color="transparent")
    body.pack(fill="both", expand=True, pady=(8, 0))

    def section(title: str) -> None:
        ctk.CTkLabel(body, text=title, font=ds.BOLD).pack(
            anchor="w", padx=5, pady=(8, 2)
        )

    def line(text: str, color=None) -> None:
        ctk.CTkLabel(
            body,
            text=text,
            font=ds.FONT,
            justify="left",
            wraplength=480,
            text_color=color or ds.MUTED,
        ).pack(anchor="w", padx=15)

    class_name = character.starting_class_name or "unknown class"
    section("Attributes")
    stat_lines = [f"Level: {character.get_stat('level')} -> {build.level}"] + [
        f"{name.capitalize()}: {character.get_stat(name)} -> {build.stats[name]}"
        for name in LEVEL_STAT_KEYS
    ]
    line("\n".join(stat_lines))
    line(
        f"The character's starting class is {class_name}. Attributes below the "
        "starting class's values cannot be imported. Soul memory is raised to "
        "cover the new level if needed."
    )
    problem_label = ctk.CTkLabel(
        body,
        text="",
        font=ds.FONT,
        justify="left",
        wraplength=480,
        text_color=ds.WARNING,
    )

    def update_problems() -> None:
        found = problems()
        stats_state = "disabled" if found else "normal"
        stats_button.configure(state=stats_state)
        both_button.configure(state=stats_state if build.items else "disabled")
        problem_label.configure(
            text="Stats cannot be imported, out of range: " + ", ".join(found)
            if found
            else ""
        )

    problem_label.pack(anchor="w", padx=15)
    update_problems()

    section(f"Items ({len(build.items)})")
    images: list[ctk.CTkImage] = []
    for item in build.items:
        _icon_row(body, item, display_name(item), images).pack(
            anchor="w", padx=15, pady=1
        )
    if not build.items:
        line("The build has no equipment.")
    if build.unknown:
        line(
            "Not importable: " + ", ".join(build.unknown),
            color=ds.WARNING,
        )

    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, parent.winfo_toplevel(), width=580, height=620)
    dialog.wait_window()
    if result["mode"] is None:
        return None
    return (
        result["mode"],
        equip_var.get() and result["mode"] != _STATS,
        new_class if class_var.get() and result["mode"] != _ITEMS else None,
    )


def _ask_owned(parent, items: list[PlannerItem], owned: list[tuple[PlannerItem, int]]):
    """Ask whether items already owned are added again. Returns the items to
    add, or None when cancelled."""
    if not owned:
        return items
    names = "\n".join(
        f"- {display_name(item)}"
        + (f" ({count} carried)" if count < item.count else "")
        for item, count in owned
    )
    answer = CTkMessageBox.askyesnocancel(
        _TITLE,
        f"The character already has:\n{names}\n\n"
        "Add the build's copies of these anyway?\n"
        "Yes adds them all, No adds only the copies still missing.",
        parent=parent,
    )
    if answer is None:
        return None
    if answer:
        return items
    return without_owned(items, owned)


def _ask_amounts(parent, character, upgradable, stacking):
    """Ask the upgrade level of each weapon and armor piece and the amount of
    each stacking item. Returns ({(item_id, infusion): level},
    {item_id: amount}), or None when cancelled."""
    if not upgradable and not stacking:
        return {}, {}
    dialog, main = _modal(parent, _TITLE)
    dialog.resizable(True, True)
    result: dict[str, tuple | None] = {"values": None}
    caps = {
        (item.item_id, item.infusion): character.max_upgrade(
            item.item_id, item.category
        )
        for item in upgradable
    }
    stack_caps = {item.item_id: character.max_stack(item.item_id) for item in stacking}
    level_vars: dict[tuple[int, int], tk.StringVar] = {}
    amount_vars: dict[int, tk.StringVar] = {}
    amount_entries: dict[int, ctk.CTkEntry] = {}

    buttons = ctk.CTkFrame(main, fg_color="transparent")
    buttons.pack(side="bottom", fill="x", pady=(12, 0))

    def set_all(to_max: bool) -> None:
        for key, var in level_vars.items():
            var.set(f"+{caps[key] if to_max else 0}")
        for item_id, var in amount_vars.items():
            var.set(str(stack_caps[item_id] if to_max else 1))

    def read_amounts() -> dict[int, int] | None:
        """Amounts entered, or None after marking the invalid ones."""
        amounts: dict[int, int] = {}
        for item_id, var in amount_vars.items():
            entry = amount_entries[item_id]
            try:
                amount = parse_whole(var.get())
            except ValueError:
                amount = 0
            valid = 1 <= amount <= stack_caps[item_id]
            entry.configure(border_color=entry_border if valid else ds.ERROR)
            if valid:
                amounts[item_id] = amount
        return amounts if len(amounts) == len(amount_vars) else None

    def confirm() -> None:
        amounts = read_amounts()
        if amounts is None:
            status.configure(text="Amounts must be between 1 and the item's max.")
            return
        upgrades = {key: int(var.get().lstrip("+")) for key, var in level_vars.items()}
        result["values"] = (upgrades, amounts)
        dialog.destroy()

    ds.button(buttons, "All Min", lambda: set_all(False), primary=False, width=80).pack(
        side="left"
    )
    ds.button(buttons, "All Max", lambda: set_all(True), primary=False, width=80).pack(
        side="left", padx=(8, 0)
    )
    ds.button(buttons, "Cancel", dialog.destroy, primary=False).pack(side="right")
    ds.button(buttons, "Import", confirm, width=110).pack(side="right", padx=(0, 8))
    status = ctk.CTkLabel(main, text="", font=ds.SMALL, text_color=ds.ERROR, anchor="w")
    status.pack(side="bottom", fill="x", pady=(6, 0))

    _heading(
        main,
        "Upgrades and Amounts",
        "Builds do not store upgrade levels or amounts. Pick them per item.",
    )
    if upgradable and not any(caps.values()):
        ctk.CTkLabel(
            main,
            text="Upgrade caps could not be read from this save, items are added at +0.",
            font=ds.FONT,
            text_color=ds.WARNING,
            wraplength=500,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(6, 0))

    body = ScrollableFrame(main, fg_color="transparent")
    body.pack(fill="both", expand=True, pady=(8, 0))
    images: list[ctk.CTkImage] = []
    row = 0
    for item in upgradable:
        key = (item.item_id, item.infusion)
        name = display_name(item)
        if item.infusion not in character.allowed_infusions(item.item_id):
            name += " (infusion not allowed, added plain)"
        _icon_row(body, item, name, images).grid(
            row=row, column=0, sticky="w", padx=5, pady=2
        )
        var = tk.StringVar(value=f"+{caps[key]}")
        level_vars[key] = var
        ctk.CTkComboBox(
            body,
            variable=var,
            values=[f"+{level}" for level in range(caps[key] + 1)],
            state="readonly",
            font=ds.FONT,
            width=80,
        ).grid(row=row, column=1, sticky="e", padx=5, pady=3)
        row += 1
    entry_border = None
    for item in stacking:
        _icon_row(
            body, item, f"{display_name(item)} (max {stack_caps[item.item_id]})", images
        ).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        var = tk.StringVar(value=str(stack_caps[item.item_id]))
        amount_vars[item.item_id] = var
        entry = ctk.CTkEntry(body, textvariable=var, font=ds.FONT, width=80)
        entry.grid(row=row, column=1, sticky="e", padx=5, pady=3)
        amount_entries[item.item_id] = entry
        entry_border = entry.cget("border_color")
        row += 1
    body.grid_columnconfigure(0, weight=1)

    dialog.bind("<Return>", lambda _e: confirm())
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, parent.winfo_toplevel(), width=580, height=520)
    dialog.wait_window()
    return result["values"]


def _backup(save_path, description: str, operation: str) -> None:
    """Raises when the backup fails, so the write does not go ahead."""
    from er_save_manager.backup.manager import BackupManager

    try:
        BackupManager(Path(save_path)).create_backup(
            description=description, operation=operation
        )
    except Exception as exc:
        raise RuntimeError(f"Backup failed: {exc}") from exc


def import_soulsplanner(
    parent,
    save: DS2Save,
    slot_index: int,
    get_save_path: Callable[[], str | None],
    show_toast: Callable[..., None],
    on_done: Callable[[], None],
) -> None:
    """Run the import flow on one character slot and write the save."""
    save_path = get_save_path()
    if not save_path:
        show_toast("No save path to write to", duration=2000)
        return
    reason = save.slot_lock_reason(slot_index)
    if reason:
        CTkMessageBox.showerror("Slot Locked", reason, parent=parent)
        return

    build = _ask_build(parent)
    if build is None:
        return
    character = save.characters[slot_index]
    choice = _ask_mode(parent, build, character)
    if choice is None:
        return
    mode, equip, new_class = choice

    items: list[PlannerItem] = []
    upgrades: dict[tuple[int, int], int] = {}
    quantities: dict[int, int] = {}
    if mode in (_ITEMS, _BOTH):
        items = _ask_owned(parent, build.items, owned_items(character, build.items))
        if items is None:
            return
        amounts = _ask_amounts(
            parent,
            character,
            [item for item in items if item.category in UPGRADABLE_CATEGORIES],
            [item for item in items if item.category in QUANTITY_CATEGORIES],
        )
        if amounts is None:
            return
        upgrades, quantities = amounts
        if not items and mode == _ITEMS:
            show_toast("Nothing to import", duration=2500)
            return

    if not save_writable():
        return
    try:
        _backup(
            save_path, f"before_soulsplanner_import_slot_{slot_index}", "import_build"
        )
    except RuntimeError as exc:
        CTkMessageBox.showerror(
            "Backup Failed", f"Nothing was written:\n{exc}", parent=parent
        )
        return

    parts = []
    if mode in (_STATS, _BOTH):
        if new_class is not None:
            # Before apply_stats, whose soul memory sync counts level-ups from
            # the class's starting level.
            character.starting_class = new_class
            save.sync_class_cache(slot_index)
            parts.append(f"class set to {STARTING_CLASSES[new_class]}")
        soul_memory_added = apply_stats(character, build)
        parts.append(f"stats set, level {build.level}")
        if soul_memory_added:
            parts.append(f"soul memory raised by {soul_memory_added:,}")
    result = apply_items(character, items, upgrades, quantities) if items else None
    if result is not None:
        parts.append(f"{result.added} item(s) added")
    equipped = None
    if equip and character.has_equipment_block():
        equipped = equip_build(character, build, upgrades)
        save.sync_equipment_cache(slot_index)
        parts.append("loadout equipped")

    try:
        save.save_to_file(save_path)
    except Exception as exc:
        write_failed(exc, parent)
        return
    on_done()

    problems = []
    if result is not None:
        if result.no_space:
            problems.append("No inventory space for: " + ", ".join(result.no_space))
        if result.infusion_fallback:
            problems.append(
                "Added plain, infusion not allowed: "
                + ", ".join(result.infusion_fallback)
            )
    if equipped is not None and equipped.missing:
        problems.append(
            "Not carried, slot left empty: "
            + ", ".join(dict.fromkeys(equipped.missing))
        )
    if equipped is not None and equipped.no_slots:
        problems.append(
            "Not enough attunement slots, not attuned: " + ", ".join(equipped.no_slots)
        )
    if problems:
        CTkMessageBox.showwarning(
            _TITLE,
            "Build imported (" + ", ".join(parts) + ").\n\n" + "\n\n".join(problems),
            parent=parent,
        )
    else:
        show_toast("Build imported: " + ", ".join(parts), duration=3500)
