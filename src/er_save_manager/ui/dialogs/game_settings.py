"""Game settings editor (USER_DATA_10 Settings, shared by all characters)."""

import tkinter as tk
from io import BytesIO

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox


def open_game_settings(parent, save_file, save_path, show_toast) -> None:
    """Open the game settings editor (USER_DATA_10 Settings, shared by all characters)."""
    if not save_file:
        CTkMessageBox.showwarning(
            "No Save", "Please load a save file first!", parent=parent
        )
        return

    if not save_file.user_data_10_parsed or not save_file.user_data_10_parsed.settings:
        CTkMessageBox.showerror(
            "Unavailable",
            "Game settings could not be read from this save.",
            parent=parent,
        )
        return

    settings = save_file.user_data_10_parsed.settings

    dialog = ds.create(parent, "Game Settings")

    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    # (group, [(label, field_name, min, max)])
    groups = [
        (
            "Display",
            [
                ("Brightness", "brightness", 0, 10),
                ("HUD", "hud", 0, 2),
                ("Display Blood", "display_blood", 0, 1),
                ("Subtitles", "subtitles", 0, 1),
                ("Cinematic Effects", "cinematic_effects", 0, 1),
                ("Ray Tracing", "is_raytracing_on", 0, 1),
                ("HDR", "hdr", 0, 1),
                ("HDR Adjust Brightness", "hdr_adjust_brightness", 0, 10),
                ("HDR Maximum Brightness", "hdr_maximum_brightness", 0, 10),
                ("HDR Adjust Saturation", "hdr_adjust_saturation", 0, 10),
            ],
        ),
        (
            "Sound",
            [
                ("Master Volume", "master_volume", 0, 10),
                ("Music Volume", "music_volume", 0, 10),
                ("Sound Effects Volume", "sound_effects_volume", 0, 10),
                ("Voice Volume", "voice_volume", 0, 10),
                ("Sound Type", "sound_type", 0, 2),
            ],
        ),
        (
            "Camera and Controls",
            [
                ("Camera Speed", "camera_speed", 0, 10),
                ("Camera X Axis", "camera_x_axis", 0, 1),
                ("Camera Y Axis", "camera_y_axis", 0, 1),
                ("Camera Auto Wall Recovery", "camera_auto_wall_recovery", 0, 1),
                ("Reset Camera Y Axis", "reset_camera_y_axis", 0, 1),
                ("Camera Auto Rotation", "camera_auto_rotation", 0, 1),
                ("Controller Vibration", "controller_vibration", 0, 1),
                ("Toggle Auto Lock-On", "toggle_auto_lockon", 0, 1),
                ("Manual Attack Aim", "manual_attack_aim", 0, 1),
                ("Autotarget", "autotarget", 0, 1),
            ],
        ),
        (
            "Network",
            [
                ("Cross-Region Play", "cross_region_play", 0, 1),
                ("Voice Chat", "voice_chat", 0, 1),
                ("Display Player Names", "display_player_names", 0, 1),
                ("Send Summon Sign", "send_summon_sign", 0, 1),
            ],
        ),
        (
            "Interface",
            [
                ("Mark New Items", "mark_new_items", 0, 1),
                ("Show Recent Tabs", "show_recent_tabs", 0, 1),
                ("Show Tutorials", "show_tutorials", 0, 1),
            ],
        ),
    ]

    vars: dict[str, tk.IntVar] = {}

    def build(body):
        for group, fields in groups:
            ctk.CTkLabel(body, text=group, font=ds.BOLD).pack(anchor="w")
            box = ds.box(body, pady=(4, 12))
            box.grid_columnconfigure(0, weight=1)
            for i, (label, field, lo, hi) in enumerate(fields):
                pady = (8 if i == 0 else 2, 8 if i == len(fields) - 1 else 2)
                ctk.CTkLabel(box, text=label, font=ds.FONT, anchor="w").grid(
                    row=i, column=0, sticky=tk.W, padx=(12, 20), pady=pady
                )
                var = vars.get(field) or tk.IntVar(value=getattr(settings, field, 0))
                vars[field] = var
                ctk.CTkEntry(
                    box, textvariable=var, width=60, height=28, font=ds.FONT
                ).grid(row=i, column=1, pady=pady)
                ctk.CTkLabel(
                    box,
                    text=f"{lo}-{hi}",
                    font=ds.SMALL,
                    text_color=ds.MUTED,
                    width=40,
                    anchor="w",
                ).grid(row=i, column=2, sticky=tk.W, padx=(8, 12), pady=pady)

    def apply_settings():
        if not save_path or not save_path.is_file():
            CTkMessageBox.showerror(
                "Invalid Save Path", "Could not locate save file.", parent=dialog
            )
            return

        try:
            backup_mgr = BackupManager(save_path)
            backup_mgr.create_backup(
                description="Before game settings edit",
                operation="game_settings",
                save=save_file,
            )
        except PermissionError:
            CTkMessageBox.showwarning(
                "Backup Skipped",
                "Could not create backup (permission denied). Proceeding.",
                parent=dialog,
            )

        for field, var in vars.items():
            try:
                setattr(settings, field, var.get())
            except Exception:
                pass

        # Settings follow the checksum (PC only), version and steam_id
        ud10_base = save_file._user_data_10_offset
        checksum_size = 0 if save_file.is_ps else 16
        settings_offset = ud10_base + checksum_size + 4 + 8

        settings_buf = BytesIO()
        settings.write(settings_buf)
        settings_bytes = settings_buf.getvalue()

        # Pad to 0x140 to cover the full Settings region
        padded = settings_bytes + b"\x00" * (0x140 - len(settings_bytes))
        save_file._raw_data[settings_offset : settings_offset + 0x140] = padded[:0x140]

        save_file._recalculate_userdata10_checksum()
        save_file.save(save_path)

        show_toast("Game settings saved", duration=2500)
        dialog.destroy()

    ds.button_row(
        main,
        [
            {"text": "Apply", "command": apply_settings},
            {"text": "Close", "command": dialog.destroy, "primary": False},
        ],
    )
    ds.header(main, "Game Settings", font=ds.TITLE_LARGE)
    ctk.CTkLabel(
        main,
        text="Shared by all characters in this save.",
        font=ds.SMALL,
        text_color=ds.MUTED,
    ).pack(anchor="w")
    ds.content(main, build, max_height=520, width=380, pady=(12, 0))
    ds.finish(dialog, parent)
