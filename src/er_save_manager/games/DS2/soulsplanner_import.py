"""
Dialog flow importing a soulsplanner.com build into a DS2 character:
link -> stats/items choice -> already owned items -> upgrades and amounts ->
write.
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
    display_name,
    load_build,
    owned_items,
    stat_problems,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.scrollable_frame import ScrollableFrame
from er_save_manager.ui.utils import center_window, force_render_dialog

_HINT_COLOR = ("gray40", "gray70")
_TITLE = "Import Soulsplanner Build"
_POLL_MS = 100
_ICON_SIZE = 36

# Choices of the stats/items step.
_STATS = "stats"
_ITEMS = "items"
_BOTH = "both"


def _modal(parent, title: str, width: int, height: int) -> ctk.CTkToplevel:
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    center_window(dialog, width, height, parent=parent)
    force_render_dialog(dialog)
    dialog.transient(parent.winfo_toplevel())
    dialog.grab_set()
    return dialog


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
    ctk.CTkLabel(row, text=text, wraplength=330, justify="left").pack(
        side="left", padx=(8, 0)
    )
    return row


def _ask_build(parent) -> PlannerBuild | None:
    """Ask for a build link and download it. None when cancelled."""
    dialog = _modal(parent, _TITLE, 520, 190)
    result: dict[str, PlannerBuild | None] = {"build": None}

    ctk.CTkLabel(
        dialog, text="Paste a soulsplanner.com Dark Souls II build link:"
    ).pack(padx=15, pady=(15, 5), anchor="w")
    link_var = tk.StringVar()
    entry = ctk.CTkEntry(
        dialog,
        textvariable=link_var,
        placeholder_text="https://soulsplanner.com/darksouls2/12345",
    )
    entry.pack(fill="x", padx=15)
    status = ctk.CTkLabel(dialog, text="", text_color=_HINT_COLOR, wraplength=480)
    status.pack(padx=15, pady=5, anchor="w")

    buttons = ctk.CTkFrame(dialog, fg_color="transparent")
    buttons.pack(fill="x", padx=15, pady=(0, 15))
    ctk.CTkButton(buttons, text="Cancel", width=100, command=dialog.destroy).pack(
        side="right"
    )
    fetch_button = ctk.CTkButton(buttons, text="Fetch Build", width=120)
    fetch_button.pack(side="right", padx=(0, 8))

    def fetch() -> None:
        link = link_var.get()
        if not link.strip():
            return
        fetch_button.configure(state="disabled")
        status.configure(text="Fetching build...", text_color=_HINT_COLOR)
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
                status.configure(text=outcome["error"], text_color="orange")
                fetch_button.configure(state="normal")
                return
            result["build"] = outcome["build"]
            dialog.destroy()

        dialog.after(_POLL_MS, poll)

    fetch_button.configure(command=fetch)
    dialog.bind("<Return>", lambda _e: fetch())
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    entry.focus_set()
    dialog.wait_window()
    return result["build"]


def _ask_mode(parent, build: PlannerBuild, character) -> str | None:
    """Show the build and ask what to import. None when cancelled."""
    dialog = _modal(parent, _TITLE, 560, 560)
    result: dict[str, str | None] = {"mode": None}

    def choose(mode: str) -> None:
        result["mode"] = mode
        dialog.destroy()

    problems = stat_problems(build)
    buttons = ctk.CTkFrame(dialog, fg_color="transparent")
    buttons.pack(side="bottom", fill="x", padx=15, pady=15)
    ctk.CTkButton(buttons, text="Cancel", width=90, command=dialog.destroy).pack(
        side="right"
    )
    stats_state = "disabled" if problems else "normal"
    items_state = "normal" if build.items else "disabled"
    ctk.CTkButton(
        buttons,
        text="Items Only",
        width=110,
        state=items_state,
        command=lambda: choose(_ITEMS),
    ).pack(side="right", padx=(0, 8))
    ctk.CTkButton(
        buttons,
        text="Stats Only",
        width=110,
        state=stats_state,
        command=lambda: choose(_STATS),
    ).pack(side="right", padx=(0, 8))
    ctk.CTkButton(
        buttons,
        text="Stats and Items",
        width=130,
        state="normal" if not problems and build.items else "disabled",
        command=lambda: choose(_BOTH),
    ).pack(side="right", padx=(0, 8))

    body = ScrollableFrame(dialog, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    def section(title: str) -> None:
        ctk.CTkLabel(body, text=title, font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=5, pady=(8, 2)
        )

    def line(text: str, color=None) -> None:
        ctk.CTkLabel(
            body,
            text=text,
            justify="left",
            wraplength=480,
            text_color=color or _HINT_COLOR,
        ).pack(anchor="w", padx=15)

    section(f"Build {build.build_id} ({build.class_name})")
    stat_lines = [f"Level: {character.get_stat('level')} -> {build.level}"] + [
        f"{name.capitalize()}: {character.get_stat(name)} -> {build.stats[name]}"
        for name in LEVEL_STAT_KEYS
    ]
    line("\n".join(stat_lines))
    line(
        "The character's starting class is not changed. A build made for a "
        "different class can end up with attributes below this class's "
        "starting values."
    )
    if problems:
        line(
            "Stats cannot be imported, out of range: " + ", ".join(problems),
            color="orange",
        )

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
            color="orange",
        )

    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    dialog.wait_window()
    return result["mode"]


def _ask_owned(parent, items: list[PlannerItem], owned: list[PlannerItem]):
    """Ask whether items already owned are added again. Returns the items to
    add, or None when cancelled."""
    if not owned:
        return items
    names = "\n".join(f"- {display_name(item)}" for item in owned)
    answer = CTkMessageBox.askyesnocancel(
        _TITLE,
        f"The character already has:\n{names}\n\n"
        "Add another copy of these anyway?\n"
        "Yes adds them, No skips them.",
        parent=parent,
    )
    if answer is None:
        return None
    if answer:
        return items
    skip = {id(item) for item in owned}
    return [item for item in items if id(item) not in skip]


def _ask_amounts(parent, character, upgradable, stacking):
    """Ask the upgrade level of each weapon and armor piece and the amount of
    each stacking item. Returns ({(item_id, infusion): level},
    {item_id: amount}), or None when cancelled."""
    if not upgradable and not stacking:
        return {}, {}
    dialog = _modal(parent, f"{_TITLE} - Upgrades and Amounts", 560, 480)
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

    buttons = ctk.CTkFrame(dialog, fg_color="transparent")
    buttons.pack(side="bottom", fill="x", padx=15, pady=15)

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
                amount = int(var.get())
            except ValueError:
                amount = 0
            valid = 1 <= amount <= stack_caps[item_id]
            entry.configure(border_color=entry_border if valid else "orange")
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

    ctk.CTkButton(
        buttons, text="All Min", width=80, command=lambda: set_all(False)
    ).pack(side="left")
    ctk.CTkButton(
        buttons, text="All Max", width=80, command=lambda: set_all(True)
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(buttons, text="Cancel", width=90, command=dialog.destroy).pack(
        side="right"
    )
    ctk.CTkButton(buttons, text="Import", width=110, command=confirm).pack(
        side="right", padx=(0, 8)
    )

    ctk.CTkLabel(
        dialog,
        text="Builds do not store upgrade levels or amounts. Pick them per item:",
    ).pack(anchor="w", padx=15, pady=(15, 5))
    if upgradable and not any(caps.values()):
        ctk.CTkLabel(
            dialog,
            text="Upgrade caps could not be read from this save, items are added at +0.",
            text_color="orange",
            wraplength=480,
            justify="left",
        ).pack(anchor="w", padx=15)
    status = ctk.CTkLabel(dialog, text="", text_color="orange")
    status.pack(side="bottom", anchor="w", padx=15)

    body = ScrollableFrame(dialog, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=10)
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
        entry = ctk.CTkEntry(body, textvariable=var, width=80)
        entry.grid(row=row, column=1, sticky="e", padx=5, pady=3)
        amount_entries[item.item_id] = entry
        entry_border = entry.cget("border_color")
        row += 1
    body.grid_columnconfigure(0, weight=1)

    dialog.bind("<Return>", lambda _e: confirm())
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    dialog.wait_window()
    return result["values"]


def _backup(save_path, description: str, operation: str) -> None:
    try:
        from er_save_manager.backup.manager import BackupManager

        BackupManager(Path(save_path)).create_backup(
            description=description, operation=operation
        )
    except Exception:
        pass


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

    build = _ask_build(parent)
    if build is None:
        return
    character = save.characters[slot_index]
    mode = _ask_mode(parent, build, character)
    if mode is None:
        return

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

    _backup(save_path, f"before_soulsplanner_import_slot_{slot_index}", "import_build")

    parts = []
    if mode in (_STATS, _BOTH):
        apply_stats(character, build)
        parts.append(f"stats set, level {build.level}")
    result = apply_items(character, items, upgrades, quantities) if items else None
    if result is not None:
        parts.append(f"{result.added} item(s) added")

    try:
        save.save_to_file(save_path)
    except Exception as e:
        show_toast(f"Failed to write save: {e}", duration=3000)
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
    if problems:
        CTkMessageBox.showwarning(
            _TITLE,
            "Build imported (" + ", ".join(parts) + ").\n\n" + "\n\n".join(problems),
            parent=parent,
        )
    else:
        show_toast("Build imported: " + ", ".join(parts), duration=3500)
