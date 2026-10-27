"""Warning dialog with a "don't show again" checkbox backed by a setting.
Every such setting is also listed in the Settings tab."""

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds

# (setting, Settings tab label, Settings tab hint)
WARNINGS = (
    (
        "show_pin_teleport_warning",
        "Show warning before teleporting to a map pin",
        "Elden Ring: a spot picked on the world map can be out of bounds.",
    ),
    (
        "show_custom_teleport_warning",
        "Show warning before teleporting to custom coordinates",
        "Elden Ring: an invalid map ID or position can break the save.",
    ),
    (
        "show_dlc_teleport_warning",
        "Show warning before teleporting into the DLC without owning it",
        "Elden Ring: the game is stuck loading without the DLC.",
    ),
    (
        "show_ashen_teleport_warning",
        "Show ban warning before teleporting to the Ashen Capital early",
        "Elden Ring: vanilla saves with Maliketh alive can get banned online.",
    ),
    (
        "show_boss_gate_teleport_warning",
        "Show warning before teleporting past a living boss",
        "Elden Ring: graces that are not spawned yet and boss arenas.",
    ),
    (
        "show_cut_content_warning",
        "Show warning before spawning cut content",
        "Dark Souls III and Remastered: cut items are likely to be flagged online.",
    ),
    (
        "show_unsafe_item_warning",
        "Show ban warning before adding an unsafe item",
        "Dark Souls II: unsafe items can get the account soft-banned online.",
    ),
    (
        "show_empty_slot_warning",
        "Show warning before writing into an empty slot",
        "Dark Souls III, Remastered and Nightreign: a slot never created in "
        "game stays blank.",
    ),
    (
        "show_relic_validation_warning",
        "Show warning before applying a relic with unknown effects",
        "Nightreign: effects from mod data or an older game version.",
    ),
)


def confirm_warning(
    parent,
    setting: str,
    title: str,
    heading: str,
    paragraphs: list[str],
    confirm_text: str = "Continue",
) -> bool:
    """Ask unless the warning is turned off in setting. True goes ahead."""
    from er_save_manager.ui.settings import get_settings

    settings = get_settings()
    if not settings.get(setting, True):
        return True

    dialog = ds.create(parent, title)
    result = {"go": False}
    dont_show = ctk.BooleanVar(value=False)

    def close(go: bool):
        result["go"] = go
        if go and dont_show.get():
            settings.set(setting, False)
            settings.save()
        dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=20, pady=16)
    ds.button_row(
        main,
        [
            {"text": "Cancel", "command": lambda: close(False), "primary": False},
            {"text": confirm_text, "command": lambda: close(True)},
        ],
    )
    ds.header(main, heading, icon="⚠")
    for i, text in enumerate(paragraphs):
        ctk.CTkLabel(
            main,
            text=text,
            font=ds.FONT,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(10 if i == 0 else 0, 6))
    ctk.CTkCheckBox(
        main,
        text="Don't show this warning again",
        font=ds.FONT,
        variable=dont_show,
    ).pack(anchor="w", pady=(4, 0))
    ds.finish(dialog, parent, min_width=460)
    dialog.wait_window()
    return result["go"]
