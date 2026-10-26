"""Warning before a teleport to a spot picked on the world map."""

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds

SETTING = "show_pin_teleport_warning"


def confirm_pin_teleport(parent) -> bool:
    """Ask before a pin teleport unless the user turned the warning off.
    True teleports."""
    from er_save_manager.ui.settings import get_settings

    settings = get_settings()
    if not settings.get(SETTING, True):
        return True

    dialog = ds.create(parent, "Teleport to Map Pin")
    result = {"go": False}
    dont_show = ctk.BooleanVar(value=False)

    def close(go: bool):
        result["go"] = go
        if go and dont_show.get():
            settings.set(SETTING, False)
            settings.save()
        dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=20, pady=16)
    ds.button_row(
        main,
        [
            {"text": "Cancel", "command": lambda: close(False), "primary": False},
            {"text": "Teleport", "command": lambda: close(True)},
        ],
    )
    ds.header(main, "Custom location", icon="⚠")
    ctk.CTkLabel(
        main,
        text=(
            "Map pins come from the game's navigation mesh, not from a known "
            "safe spot. Some spots can still put the character under the "
            "ground, inside a wall or out of bounds."
        ),
        font=ds.FONT,
        wraplength=420,
        justify="left",
    ).pack(anchor="w", pady=(10, 6))
    ctk.CTkLabel(
        main,
        text=(
            "A backup is made before the teleport. If the character ends up "
            "stuck, restore it in the Backup Manager."
        ),
        font=ds.FONT,
        wraplength=420,
        justify="left",
    ).pack(anchor="w", pady=(0, 10))
    ctk.CTkCheckBox(
        main,
        text="Don't show this warning again",
        font=ds.FONT,
        variable=dont_show,
    ).pack(anchor="w")
    ds.finish(dialog, parent, min_width=460)
    dialog.wait_window()
    return result["go"]
