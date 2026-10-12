"""Destination slot picker for character transfers, shared by all games."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.utils import patch_combo_scroll


def pick_target_slot(
    parent, target_path, names: list[str], to_index: Callable[[str], int]
) -> int | None:
    """Ask for a slot in the target save; None when cancelled.

    names are the slot display names; to_index maps the chosen name back to a
    slot index (0 when it cannot be parsed).
    """
    dialog = ds.create(parent, "Select Target Slot")

    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    result = {"value": None}
    slot_var = tk.StringVar(value=names[0] if names else "")

    def confirm():
        try:
            result["value"] = to_index(slot_var.get())
        except Exception:
            result["value"] = 0
        dialog.destroy()

    ds.button_row(
        main,
        [
            {"text": "Transfer", "command": confirm},
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
        ],
    )

    ds.header(main, "Select the destination slot")
    ctk.CTkLabel(
        main,
        text=str(target_path),
        font=ds.SMALL,
        text_color=ds.MUTED,
        wraplength=440,
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(4, 12))
    combo = ctk.CTkComboBox(
        main,
        variable=slot_var,
        values=names,
        state="readonly",
        width=360,
        height=32,
        font=ds.FONT,
        dropdown_font=ds.FONT,
    )
    combo.pack(anchor="w")
    patch_combo_scroll(combo)

    dialog.bind("<Return>", lambda _e: confirm())
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, parent, min_width=460)
    dialog.wait_window()
    return result["value"]
