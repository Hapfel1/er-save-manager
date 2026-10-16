"""Chest Auto-refill settings per item."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from er_save_manager.data.item_database import get_item_name
from er_save_manager.editors.auto_refill import RefillEntry
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.utils import (
    center_window,
    force_render_dialog,
    style_window_frame,
)

_ON = "On"
_OFF = "Off"


def show_auto_refill(
    parent,
    entries: list[RefillEntry],
    is_convergence: bool,
    on_apply: Callable[[list[RefillEntry]], bool],
):
    """on_apply writes the entries and returns True when it saved them."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Auto-refill")
    dialog.transient(parent)
    center_window(dialog, 720, 640, parent=parent)
    dialog.resizable(True, True)
    style_window_frame(dialog, dialog=False)
    force_render_dialog(dialog)
    dialog.grab_set()

    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14, 12))
    ds.header(main, "Auto-refill", font=ds.TITLE_LARGE)
    ctk.CTkLabel(
        main,
        text="The chest's Auto-refill option per item: when it is on, the game "
        "refills the item from storage. Double-click a row to switch it.",
        font=ds.FONT,
        text_color=ds.MUTED,
        anchor="w",
        justify=tk.LEFT,
        wraplength=660,
    ).pack(fill=tk.X, pady=(2, 8))

    names = {e.index: get_item_name(e.item_id, 0, is_convergence) for e in entries}
    state = {e.index: e.on for e in entries}
    search_var = tk.StringVar()
    ctk.CTkEntry(
        main, textvariable=search_var, placeholder_text="Search items..."
    ).pack(fill=tk.X, pady=(0, 6))

    summary = ctk.CTkLabel(main, text="", font=ds.SMALL, anchor="w")

    # Buttons first, from the bottom, so the list takes the remaining height.
    def apply():
        changed = [
            RefillEntry(e.index, e.item_id, state[e.index], e.default)
            for e in entries
            if state[e.index] != e.on
        ]
        if not changed:
            dialog.destroy()
            return
        if on_apply(changed):
            dialog.destroy()

    ds.button_row(
        main,
        [
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
            {"text": "Apply", "command": apply},
        ],
        pady=(10, 0),
    )

    actions = ctk.CTkFrame(main, fg_color="transparent")
    actions.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

    summary.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))

    box, tree = ds.themed_tree(
        main, columns=("on", "item", "default"), show="headings", selectmode="extended"
    )
    box.pack(fill=tk.BOTH, expand=True)
    for col, title, width, stretch in (
        ("on", "Auto-refill", 100, False),
        ("item", "Item", 420, True),
        ("default", "Game default", 120, False),
    ):
        tree.heading(col, text=title)
        tree.column(col, width=width, anchor="w", stretch=stretch)
    tree.tag_configure("on", foreground=palette.pick(palette.GREEN_TEXT))
    tree.tag_configure("off", foreground=palette.pick(palette.RED_TEXT))

    def default_text(e: RefillEntry) -> str:
        if e.default is None:
            return "Unknown"
        return _ON if e.default else _OFF

    def refresh():
        selected = set(tree.selection())
        tree.delete(*tree.get_children())
        query = search_var.get().strip().lower()
        for e in entries:
            name = names[e.index]
            if query and query not in name.lower():
                continue
            on = state[e.index]
            iid = str(e.index)
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(_ON if on else _OFF, name, default_text(e)),
                tags=("on" if on else "off",),
            )
            if iid in selected:
                tree.selection_add(iid)
        changed = sum(1 for e in entries if state[e.index] != e.on)
        on_count = sum(state.values())
        summary.configure(
            text=f"{len(entries)} items, {on_count} on."
            + (f" {changed} changed, not applied yet." if changed else "")
        )

    def set_selected(value: bool | None):
        """True / False sets, None switches each selected row."""
        for iid in tree.selection():
            index = int(iid)
            state[index] = (not state[index]) if value is None else value
        refresh()

    def reset_defaults():
        for e in entries:
            if e.default is not None:
                state[e.index] = e.default
        refresh()

    ds.button(actions, "Switch", lambda: set_selected(None), width=90).pack(
        side=tk.LEFT
    )
    ds.button(
        actions, "Turn On", lambda: set_selected(True), primary=False, width=90
    ).pack(side=tk.LEFT, padx=6)
    ds.button(
        actions, "Turn Off", lambda: set_selected(False), primary=False, width=90
    ).pack(side=tk.LEFT)
    ds.button(
        actions, "Reset to Defaults", reset_defaults, primary=False, width=150
    ).pack(side=tk.RIGHT)

    tree.bind(
        "<Double-1>", lambda e: set_selected(None) if tree.identify_row(e.y) else None
    )
    search_var.trace_add("write", lambda *_: refresh())
    refresh()
