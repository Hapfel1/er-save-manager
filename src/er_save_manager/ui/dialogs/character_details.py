"""
Character Details Dialog
Shows detailed character information with corruption detection
"""

from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox

_WRAP = 600


@dataclass
class CharacterScan:
    """Character Details check results for one slot."""

    # "key:text" entries that Fix All Issues repairs
    issues: list[str]
    deep_scan_result: object | None
    # A torn write was found and the deep scan fix applies
    deep_scan_available: bool
    has_dlc_flag: bool
    has_invalid_dlc: bool
    has_tarnished_pack_flag: bool

    @property
    def issue_texts(self) -> list[str]:
        texts = [issue.split(":", 1)[-1] for issue in self.issues]
        if self.deep_scan_available:
            texts.insert(0, "Torn write detected")
        return texts


def scan_character(save_file, slot_idx) -> CharacterScan:
    """Run the Character Details checks on one slot."""
    slot = save_file.characters[slot_idx]
    has_corruption = False
    issues_detected = []
    try:
        correct_steam_id = None
        if save_file.user_data_10_parsed and hasattr(
            save_file.user_data_10_parsed, "steam_id"
        ):
            correct_steam_id = save_file.user_data_10_parsed.steam_id

        has_corruption, corruption_issues = slot.has_corruption(correct_steam_id)
        if has_corruption:
            # PS saves have no SteamID - filter that issue out
            if getattr(save_file, "is_ps", False):
                corruption_issues = [
                    i
                    for i in corruption_issues
                    if not i.startswith("steamid_corruption")
                ]
            issues_detected = corruption_issues
    except Exception:
        pass

    has_dlc_flag = False
    has_invalid_dlc = False
    has_tarnished_pack_flag = False
    try:
        has_dlc_flag = slot.has_dlc_flag()
        has_invalid_dlc = slot.has_invalid_dlc()
        has_tarnished_pack_flag = slot.has_tarnished_pack_flag()
    except Exception:
        pass

    # Checksum check - PS saves have no per-slot checksums
    if not getattr(save_file, "is_ps", False):
        try:
            from er_save_manager.fixes.checksum import check_slot_checksum

            valid, _, _ = check_slot_checksum(save_file, slot_idx)
            if not valid:
                issues_detected.append("checksum:Invalid slot checksum")
        except Exception:
            pass

    # Deep scan check
    deep_scan_available = False
    deep_scan_result = None
    try:
        from er_save_manager.fixes.deep_scan import DeepScanFix

        deep_fix = DeepScanFix()
        deep_scan_result = deep_fix.scan_only(save_file, slot_idx)
        deep_scan_available = (
            deep_scan_result.steamid_found and deep_scan_result.delta != 0
        )
    except Exception:
        pass

    # Inventory counter check
    has_inv_counter_issue = False
    try:
        from er_save_manager.fixes.inventory_counters import InventoryCountersFix

        has_inv_counter_issue = InventoryCountersFix().detect(save_file, slot_idx)
        if has_inv_counter_issue:
            issues_detected.append(
                "inventory_counters:Corrupted inventory item counters (can prevent key item pickups or cause crashes)"
            )
    except Exception:
        pass

    # NetMan chunk chain check (a torn write is handled by the deep scan)
    if not deep_scan_available:
        try:
            from er_save_manager.fixes.netman import NetManFix

            if NetManFix().detect(save_file, slot_idx):
                issues_detected.append(
                    "netman:Damaged network data (CSNetMan), can cause the"
                    " 'save corrupted' message or crashes on load"
                )
        except Exception:
            pass

    # Structural checks with a well-defined, safe correction
    try:
        from er_save_manager.fixes.structural_scan import (
            DanglingInventoryHandleFix,
            StorageInventoryCountersFix,
        )

        if DanglingInventoryHandleFix().detect(save_file, slot_idx):
            issues_detected.append(
                "dangling_inventory_handle:Inventory rows reference items that no longer exist"
            )
        if StorageInventoryCountersFix().detect(save_file, slot_idx):
            issues_detected.append(
                "storage_inventory_counters:Corrupted storage box item counters"
            )
    except Exception:
        pass

    return CharacterScan(
        issues_detected,
        deep_scan_result,
        deep_scan_available,
        has_dlc_flag,
        has_invalid_dlc,
        has_tarnished_pack_flag,
    )


class CharacterDetailsDialog:
    """Dialog showing character details with fix/teleport options (customtkinter version)"""

    @staticmethod
    def show(
        parent,
        save_file,
        slot_idx,
        save_path=None,
        reload_callback=None,
        open_backup_settings=None,
    ):
        if not save_file:
            CTkMessageBox.showwarning("No Save", "No save file loaded.", parent=parent)
            return

        from er_save_manager.fixes.wiped_slot import is_wiped_slot

        if is_wiped_slot(save_file, slot_idx):
            from er_save_manager.ui.dialogs.wiped_slot_dialog import (
                show_wiped_slot_dialog,
            )

            show_wiped_slot_dialog(
                parent, save_file, slot_idx, save_path, open_backup_settings
            )
            return

        slot = save_file.characters[slot_idx]

        name = f"Character {slot_idx + 1}"
        level = "?"
        playtime = "Unknown"

        try:
            if save_file.user_data_10_parsed:
                profiles = save_file.user_data_10_parsed.profile_summary.profiles
                if profiles and slot_idx < len(profiles):
                    profile = profiles[slot_idx]
                    name = profile.character_name or name
                    level = str(profile.level) if profile.level else level
                    playtime = CharacterDetailsDialog._format_playtime(
                        profile.seconds_played
                    )
        except Exception as e:
            print(f"Warning: Could not load profile data: {e}")

        location = "Unknown"
        is_dlc_location = False
        try:
            if hasattr(slot, "map_id") and slot.map_id:
                location = slot.map_id.to_string_decimal()
                is_dlc_location = slot.map_id.is_dlc()
        except Exception:
            pass

        scan = scan_character(save_file, slot_idx)
        issues_detected = scan.issues
        deep_scan_result = scan.deep_scan_result
        deep_scan_available = scan.deep_scan_available
        has_dlc_flag = scan.has_dlc_flag
        has_invalid_dlc = scan.has_invalid_dlc
        has_tarnished_pack_flag = scan.has_tarnished_pack_flag
        has_dlc_section = (
            has_dlc_flag
            or has_tarnished_pack_flag
            or (has_invalid_dlc and not deep_scan_available)
        )

        # Structural checks with no safe automatic correction, informational only
        structural_notes = []
        try:
            from er_save_manager.fixes.structural_scan import (
                DuplicateGaitemHandleFix,
                RebuildRoundtripFix,
                WorldStructSizeFix,
            )

            for fix in (
                RebuildRoundtripFix(),
                DuplicateGaitemHandleFix(),
                WorldStructSizeFix(),
            ):
                if fix.detect(save_file, slot_idx):
                    result = fix.apply(save_file, slot_idx)
                    structural_notes.append(f"{fix.name}: {result.description}")
                    structural_notes.extend(f"    {d}" for d in result.details)
        except Exception:
            pass

        dialog = ds.create(parent, f"Character Details - {name}")

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Buttons first so they keep their place at the bottom
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", pady=(14, 0))

        # Packed bottom up: this line ends up below the CSNetMan hint
        ctk.CTkLabel(
            main_frame,
            text="Infinite loading screen? Try Teleport Character.",
            font=ds.SMALL,
            text_color=ds.HINT,
            wraplength=_WRAP,
            justify="left",
        ).pack(side="bottom", anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            main_frame,
            text="Still corrupted or crashing on load after fixing, or nothing "
            "detected? Try Replace CSNetMan.",
            font=ds.SMALL,
            text_color=ds.HINT,
            wraplength=_WRAP,
            justify="left",
        ).pack(side="bottom", anchor="w", pady=(10, 0))

        has_fix = deep_scan_available or bool(issues_detected)
        if deep_scan_available:
            ds.header(main_frame, f"{name}: torn write detected", icon="⚠")
        elif issues_detected:
            count = len(issues_detected)
            ds.header(
                main_frame,
                f"{name}: {count} issue{'s' if count != 1 else ''} found",
                icon="⚠",
            )
        else:
            ds.header(
                main_frame, f"{name}: no issues found", icon="✓", icon_color=ds.FOUND
            )

        def grid_rows(box, rows):
            box.grid_columnconfigure(1, weight=1)
            for i, (label, value, color) in enumerate(rows):
                pady = (8 if i == 0 else 2, 8 if i == len(rows) - 1 else 2)
                ctk.CTkLabel(box, text=label, font=ds.FONT, text_color=ds.MUTED).grid(
                    row=i, column=0, sticky="w", padx=(12, 20), pady=pady
                )
                ctk.CTkLabel(
                    box,
                    text=value,
                    font=ds.FONT,
                    text_color=color,
                    wraplength=_WRAP - 140,
                    justify="left",
                ).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=pady)

        def bullets(box, items, color=None):
            for i, text in enumerate(items):
                ctk.CTkLabel(
                    box,
                    text=f"•  {text}",
                    font=ds.FONT,
                    text_color=color,
                    wraplength=_WRAP - 24,
                    justify="left",
                    anchor="w",
                ).pack(
                    fill="x",
                    padx=12,
                    pady=(8 if i == 0 else 2, 8 if i == len(items) - 1 else 2),
                )

        def section(body, title):
            ctk.CTkLabel(body, text=title, font=ds.BOLD).pack(anchor="w", pady=(10, 0))
            return ds.box(body, pady=(4, 0))

        clear_dlc_flag_var = ctk.BooleanVar(value=False) if has_dlc_flag else None
        clear_tarnished_pack_flag_var = (
            ctk.BooleanVar(value=False) if has_tarnished_pack_flag else None
        )
        clear_invalid_dlc_var = (
            ctk.BooleanVar(value=False)
            if has_invalid_dlc and not deep_scan_available
            else None
        )

        def build(body):
            location_text = location
            if is_dlc_location:
                location_text += "  (Shadow of the Erdtree area)"
            grid_rows(
                section(body, "Character"),
                [
                    ("Level", level, None),
                    ("Playtime", playtime, None),
                    (
                        "Location",
                        location_text,
                        ds.WARNING if is_dlc_location else None,
                    ),
                ],
            )

            if deep_scan_available and deep_scan_result:
                delta = deep_scan_result.delta
                grid_rows(
                    section(body, "Torn write"),
                    [
                        (
                            "Shift",
                            f"{'+' if delta > 0 else ''}{delta} bytes (0x{abs(delta):x})",
                            ds.WARNING,
                        ),
                        (
                            "Location",
                            getattr(deep_scan_result, "tear_location", "netman"),
                            None,
                        ),
                        ("Confidence", deep_scan_result.confidence, None),
                    ],
                )
            elif issues_detected:
                bullets(
                    section(body, "Issues"),
                    [issue.split(":", 1)[-1] for issue in issues_detected],
                    ds.WARNING,
                )
                if any("dlc_location" in issue for issue in issues_detected):
                    ctk.CTkLabel(
                        body,
                        text="Teleport Character moves the character out of the "
                        "DLC area to Roundtable Hold (safest location).",
                        font=ds.SMALL,
                        text_color=ds.MUTED,
                        wraplength=_WRAP,
                        justify="left",
                    ).pack(anchor="w", pady=(4, 0))

            if has_dlc_section:
                dlc_box = section(body, "DLC flags")
                options = [
                    (
                        clear_dlc_flag_var,
                        "Clear Shadow of the Erdtree flag",
                        "Use if the save does not load without the DLC installed.",
                    ),
                    (
                        clear_tarnished_pack_flag_var,
                        "Clear Tarnished pack flag",
                        "Use if the save does not load without the Tarnished pack "
                        "installed.",
                    ),
                    (
                        clear_invalid_dlc_var,
                        "Clear invalid DLC data",
                        "Invalid data in unused DLC slots can prevent the save "
                        "from loading.",
                    ),
                ]
                options = [o for o in options if o[0] is not None]
                for i, (var, text, hint) in enumerate(options):
                    ctk.CTkCheckBox(
                        dlc_box, text=text, font=ds.FONT, variable=var
                    ).pack(anchor="w", padx=12, pady=(10 if i == 0 else 6, 0))
                    ctk.CTkLabel(
                        dlc_box,
                        text=hint,
                        font=ds.SMALL,
                        text_color=ds.MUTED,
                        wraplength=_WRAP - 60,
                        justify="left",
                    ).pack(
                        anchor="w",
                        padx=(42, 12),
                        pady=(0, 10 if i == len(options) - 1 else 0),
                    )

            if structural_notes:
                # Technical detail most users never need, so it starts closed
                notes = [note.strip() for note in structural_notes]
                # Detail lines are indented under their check
                count = sum(not n.startswith(" ") for n in structural_notes)
                ds.collapsible(
                    body,
                    f"Structural notes ({count}, no automatic fix)",
                    lambda box: bullets(box, notes),
                )

            if has_fix:
                ctk.CTkLabel(
                    body,
                    text="Fix All Issues repairs everything above; a backup is "
                    "made first.",
                    font=ds.SMALL,
                    text_color=ds.MUTED,
                ).pack(anchor="w", pady=(10, 0))

        ds.content(main_frame, build, max_height=440, width=_WRAP, pady=(4, 0))

        def teleport():
            CharacterDetailsDialog._show_teleport_dialog(
                parent,
                dialog,
                save_file,
                slot_idx,
                save_path,
                reload_callback,
                clear_dlc_flag_var,
                clear_tarnished_pack_flag_var,
                clear_invalid_dlc_var,
            )

        def _replace_netman():
            CharacterDetailsDialog._replace_netman(
                dialog,
                save_file,
                slot_idx,
                save_path,
                reload_callback,
            )

        # Repair tools on the left, dialog actions on the right
        ds.button(
            button_frame, "Teleport Character", teleport, primary=False, width=140
        ).pack(side="left")
        ds.button(
            button_frame, "Replace CSNetMan", _replace_netman, primary=False, width=140
        ).pack(side="left", padx=(8, 0))
        ds.button(
            button_frame,
            "Close",
            dialog.destroy,
            primary=not has_fix and not has_dlc_section,
        ).pack(side="right")

        if has_fix:

            def fix_all():
                if deep_scan_available:
                    CharacterDetailsDialog._run_deep_scan_fix(
                        dialog,
                        save_file,
                        slot_idx,
                        save_path,
                        reload_callback,
                    )
                else:
                    CharacterDetailsDialog._fix_character(
                        dialog,
                        save_file,
                        slot_idx,
                        len(issues_detected),
                        save_path,
                        reload_callback,
                        clear_dlc_flag_var,
                        clear_tarnished_pack_flag_var,
                        clear_invalid_dlc_var,
                    )

            ds.button(button_frame, "Fix All Issues", fix_all, width=120).pack(
                side="right", padx=(0, 8)
            )

        elif has_dlc_section:
            apply_btn = ds.button(
                button_frame,
                "Apply",
                lambda: CharacterDetailsDialog._apply_dlc_flags(
                    dialog,
                    save_file,
                    slot_idx,
                    save_path,
                    reload_callback,
                    clear_dlc_flag_var,
                    clear_tarnished_pack_flag_var,
                    clear_invalid_dlc_var,
                ),
                state="disabled",
            )
            apply_btn.pack(side="right", padx=(0, 8))

            def _on_dlc_checkbox_change(*_):
                any_ticked = any(
                    var is not None and var.get()
                    for var in (
                        clear_dlc_flag_var,
                        clear_tarnished_pack_flag_var,
                        clear_invalid_dlc_var,
                    )
                )
                apply_btn.configure(state="normal" if any_ticked else "disabled")

            for var in (
                clear_dlc_flag_var,
                clear_tarnished_pack_flag_var,
                clear_invalid_dlc_var,
            ):
                if var is not None:
                    var.trace_add("write", _on_dlc_checkbox_change)

        ds.finish(dialog, parent, min_width=_WRAP + 40)

    @staticmethod
    def _format_playtime(seconds):
        if not seconds:
            return "0h 0m 0s"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"

    @staticmethod
    def _apply_dlc_flags(
        dialog,
        save_file,
        slot_idx,
        save_path,
        reload_callback,
        clear_dlc_flag_var=None,
        clear_tarnished_pack_flag_var=None,
        clear_invalid_dlc_var=None,
    ):
        should_clear_dlc = clear_dlc_flag_var and clear_dlc_flag_var.get()
        should_clear_tarnished = (
            clear_tarnished_pack_flag_var and clear_tarnished_pack_flag_var.get()
        )
        should_clear_invalid = clear_invalid_dlc_var and clear_invalid_dlc_var.get()

        if (
            not should_clear_dlc
            and not should_clear_tarnished
            and not should_clear_invalid
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_dlc_flag_fix_slot_{slot_idx + 1}",
                    operation="dlc_flag_fix",
                    save=save_file,
                )

            slot = save_file.characters[slot_idx]

            if should_clear_dlc:
                slot.clear_dlc_flag()
                if hasattr(slot, "dlc_offset") and slot.dlc_offset > 0:
                    from io import BytesIO

                    dlc_bytes = BytesIO()
                    slot.dlc.write(dlc_bytes)
                    dlc_data = dlc_bytes.getvalue()
                    save_file._raw_data[
                        slot.dlc_offset : slot.dlc_offset + len(dlc_data)
                    ] = dlc_data

            if should_clear_tarnished:
                slot.clear_tarnished_pack_flag()
                if hasattr(slot, "dlc_offset") and slot.dlc_offset > 0:
                    from io import BytesIO

                    dlc_bytes = BytesIO()
                    slot.dlc.write(dlc_bytes)
                    dlc_data = dlc_bytes.getvalue()
                    save_file._raw_data[
                        slot.dlc_offset : slot.dlc_offset + len(dlc_data)
                    ] = dlc_data

            if should_clear_invalid:
                slot.clear_invalid_dlc()
                if hasattr(slot, "dlc_offset") and slot.dlc_offset > 0:
                    from io import BytesIO

                    dlc_bytes = BytesIO()
                    slot.dlc.write(dlc_bytes)
                    dlc_data = dlc_bytes.getvalue()
                    save_file._raw_data[
                        slot.dlc_offset : slot.dlc_offset + len(dlc_data)
                    ] = dlc_data

            save_file.recalculate_checksums()

            if save_path:
                save_file.to_file(Path(save_path))

            if reload_callback:
                reload_callback()

            _parent = dialog.master
            dialog.destroy()
            CTkMessageBox.showinfo(
                "DLC Flags",
                "DLC flag cleared. The save file has been updated.",
                parent=_parent,
            )

        except Exception as e:
            CTkMessageBox.showerror(
                "DLC Fix Failed", f"Failed to apply DLC fix:\n{e}", parent=dialog
            )

    @staticmethod
    def _run_deep_scan_fix(dialog, save_file, slot_idx, save_path, reload_callback):
        """Run deep scan and show result before applying."""
        try:
            from er_save_manager.fixes.deep_scan import (
                FLAG_RELOCATION_NOTE,
                NETMAN_RESET_NOTE,
                DeepScanFix,
            )

            deep_fix = DeepScanFix()
            result = deep_fix.scan_only(save_file, slot_idx)

            if not result.steamid_found:
                CTkMessageBox.showwarning(
                    "Deep Scan",
                    "SteamID64 not found in slot data.\nCannot determine shift.",
                    parent=dialog,
                )
                return

            if result.delta == 0:
                CTkMessageBox.showinfo(
                    "Deep Scan", "No byte shift detected.", parent=dialog
                )
                return

            delta = result.delta
            detail_lines = "\n".join(f"  {d}" for d in result.details)
            msg = (
                f"Torn write detected:\n\n"
                f"  Shift: {'+' if delta > 0 else ''}{delta} bytes (0x{abs(delta):x})\n"
                f"  Confidence: {result.confidence}\n\n"
                f"Details:\n{detail_lines}\n\n"
                f"Apply fix? A backup will be created."
            )

            if result.confidence == "low":
                msg = f"WARNING: Low confidence scan result.\n\n{msg}"

            if not CTkMessageBox.askyesno("Deep Scan Fix", msg, parent=dialog):
                return

            from er_save_manager.backup.manager import BackupManager

            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_deep_scan_fix_slot_{slot_idx + 1}",
                    operation="deep_scan_fix",
                    save=save_file,
                )

            fix_result = deep_fix.apply(save_file, slot_idx)

            if fix_result.applied:
                save_file.recalculate_checksums()
                if save_path:
                    save_file.to_file(Path(save_path))
                if reload_callback:
                    reload_callback()
                detail_text = "\n".join(f"  - {d}" for d in fix_result.details)
                note_text = ""
                if getattr(fix_result, "netman_reset", False):
                    note_text += f"NOTE: {NETMAN_RESET_NOTE}\n\n"
                if getattr(fix_result, "flags_relocated", False):
                    note_text += f"NOTE: {FLAG_RELOCATION_NOTE}\n\n"
                CTkMessageBox.showinfo(
                    "Deep Scan Fix",
                    f"{fix_result.description}\n\n{detail_text}\n\n{note_text}"
                    "Backup saved.\n\n"
                    "If the game still reports the save as corrupted or crashes on load,"
                    " open Character Details again and click 'Replace CSNetMan'.",
                    parent=dialog,
                )
                dialog.destroy()
            else:
                CTkMessageBox.showwarning(
                    "Deep Scan Fix",
                    f"Fix not applied:\n{fix_result.description}",
                    parent=dialog,
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Deep Scan Failed", f"Deep scan failed:\n{str(e)}", parent=dialog
            )
            import traceback

            traceback.print_exc()

    @staticmethod
    def _show_teleport_dialog(
        parent,
        details_dialog,
        save_file,
        slot_idx,
        save_path,
        reload_callback,
        clear_dlc_flag_var=None,
        clear_tarnished_pack_flag_var=None,
        clear_invalid_dlc_var=None,
    ):
        details_dialog.destroy()

        teleport_dialog = ds.create(parent, "Teleport Character")

        main_frame = ctk.CTkFrame(teleport_dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=16)

        ds.header(main_frame, f"Teleport Slot {slot_idx + 1} to Roundtable Hold")
        ctk.CTkLabel(
            main_frame,
            text="Roundtable Hold is the safest location to get a stuck "
            "character out, including out of the DLC area. A backup is made "
            "first.",
            font=ds.FONT,
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))
        ticked = [
            text
            for var, text in (
                (clear_dlc_flag_var, "Shadow of the Erdtree flag"),
                (clear_tarnished_pack_flag_var, "Tarnished pack flag"),
                (clear_invalid_dlc_var, "invalid DLC data"),
            )
            if var is not None and var.get()
        ]
        if ticked:
            ctk.CTkLabel(
                main_frame,
                text="Also clears: " + ", ".join(ticked),
                font=ds.SMALL,
                text_color=ds.MUTED,
            ).pack(anchor="w", pady=(6, 0))

        def do_teleport():
            try:
                from er_save_manager.backup.manager import BackupManager
                from er_save_manager.fixes.teleport import TeleportFix

                destination = "roundtable"

                if save_path:
                    manager = BackupManager(Path(save_path))
                    manager.create_backup(
                        description=f"before_teleport_to_{destination}",
                        operation=f"teleport_to_{destination}",
                        save=save_file,
                    )

                teleport = TeleportFix(destination)
                result = teleport.apply(save_file, slot_idx)

                fixes_applied = []
                if result.applied:
                    fixes_applied.append(result.description)
                    if result.details:
                        fixes_applied.extend(result.details)

                should_clear_dlc = clear_dlc_flag_var and clear_dlc_flag_var.get()
                if should_clear_dlc:
                    from er_save_manager.fixes.dlc import DLCFlagFix

                    dlc_result = DLCFlagFix().apply(save_file, slot_idx)
                    if dlc_result.applied:
                        fixes_applied.append(dlc_result.description)

                should_clear_tarnished = (
                    clear_tarnished_pack_flag_var
                    and clear_tarnished_pack_flag_var.get()
                )
                if should_clear_tarnished:
                    from er_save_manager.fixes.dlc import TarnishedPackFlagFix

                    tarnished_result = TarnishedPackFlagFix().apply(save_file, slot_idx)
                    if tarnished_result.applied:
                        fixes_applied.append(tarnished_result.description)

                should_clear_invalid = (
                    clear_invalid_dlc_var and clear_invalid_dlc_var.get()
                )
                if should_clear_invalid:
                    from er_save_manager.fixes.dlc import InvalidDLCFix

                    invalid_result = InvalidDLCFix().apply(save_file, slot_idx)
                    if invalid_result.applied:
                        fixes_applied.append(invalid_result.description)

                if fixes_applied:
                    save_file.recalculate_checksums()
                    if save_path:
                        save_file.to_file(Path(save_path))
                    if reload_callback:
                        reload_callback()
                    fixes_text = "\n".join(f"  - {fix}" for fix in fixes_applied)
                    CTkMessageBox.showinfo(
                        "Fixes Applied",
                        f"Applied fixes:\n\n{fixes_text}\n\nBackup saved to backup manager.",
                        parent=teleport_dialog,
                    )
                    teleport_dialog.destroy()
                else:
                    CTkMessageBox.showwarning(
                        "Not Applied", "No fixes were applied.", parent=teleport_dialog
                    )

            except Exception as e:
                CTkMessageBox.showerror(
                    "Teleport Failed",
                    f"Teleport failed:\n{str(e)}",
                    parent=teleport_dialog,
                )
                import traceback

                traceback.print_exc()

        ds.button_row(
            main_frame,
            [
                {"text": "Teleport", "command": do_teleport},
                {
                    "text": "Cancel",
                    "command": teleport_dialog.destroy,
                    "primary": False,
                },
            ],
        )
        ds.finish(teleport_dialog, parent, min_width=440)

    @staticmethod
    def _replace_netman(
        dialog,
        save_file,
        slot_idx,
        save_path,
        reload_callback,
    ):
        _parent = dialog.master

        from er_save_manager.fixes.deep_scan import NETMAN_REPLACED_NOTE
        from er_save_manager.fixes.netman import NETMAN_SIZE, load_template

        clean = load_template()
        if clean is None:
            CTkMessageBox.showerror(
                "Not Available",
                "CSNetMan.bin not found or invalid.\nPlace a valid CSNetMan.bin next to the fixes module.",
                parent=_parent,
            )
            return

        slot = save_file.characters[slot_idx]
        if not hasattr(slot, "net_man_offset") or slot.net_man_offset <= 0:
            CTkMessageBox.showerror(
                "NetMan Not Found",
                "Cannot determine NetMan offset for this slot.",
                parent=_parent,
            )
            return

        if not CTkMessageBox.askyesno(
            "Replace CSNetMan",
            f"Use this if you are still getting a Save is corrupted message or are still crashing after fixing corruption via the tool or if it does not detect any corruption."
            f" Replace the entire CSNetMan block in Slot {slot_idx + 1} with the clean template?\n\nA backup will be created.",
            parent=_parent,
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_netman_replace_slot_{slot_idx + 1}",
                    operation="netman_replace",
                    save=save_file,
                )

            offset = slot.net_man_offset
            save_file._raw_data[offset : offset + NETMAN_SIZE] = clean
            save_file.recalculate_checksums()

            if save_path:
                save_file.to_file(Path(save_path))
            if reload_callback:
                reload_callback()

            CTkMessageBox.showinfo(
                "CSNetMan Replaced",
                f"CSNetMan replaced in Slot {slot_idx + 1}.\n\nNOTE: {NETMAN_REPLACED_NOTE}"
                "\n\nBackup saved to backup manager.",
                parent=_parent,
            )
            dialog.destroy()

        except Exception as e:
            CTkMessageBox.showerror(
                "Replace Failed", f"Replace failed:\n{e}", parent=_parent
            )
            import traceback

            traceback.print_exc()

    @staticmethod
    def _fix_character(
        dialog,
        save_file,
        slot_idx,
        issue_count,
        save_path,
        reload_callback,
        clear_dlc_flag_var=None,
        clear_tarnished_pack_flag_var=None,
        clear_invalid_dlc_var=None,
    ):
        dialog.destroy()

        _parent = dialog.master
        should_clear_dlc = clear_dlc_flag_var and clear_dlc_flag_var.get()
        should_clear_tarnished = (
            clear_tarnished_pack_flag_var and clear_tarnished_pack_flag_var.get()
        )
        should_clear_invalid = clear_invalid_dlc_var and clear_invalid_dlc_var.get()

        confirm_parts = [f"Fix all {issue_count} issue(s) in Slot {slot_idx + 1}?"]
        if should_clear_dlc or should_clear_tarnished or should_clear_invalid:
            confirm_parts.append("\nAdditional fixes:")
            if should_clear_dlc:
                confirm_parts.append("  - Clear Shadow of the Erdtree flag")
            if should_clear_tarnished:
                confirm_parts.append("  - Clear Tarnished pack flag")
            if should_clear_invalid:
                confirm_parts.append("  - Clear invalid DLC data")
        confirm_parts.append("\nA backup will be created.")

        if not CTkMessageBox.askyesno(
            "Fix Character", "\n".join(confirm_parts), parent=_parent
        ):
            return

        try:
            from er_save_manager.backup.manager import BackupManager

            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_fix_slot_{slot_idx + 1}",
                    operation="fix_corruption",
                    save=save_file,
                )

            was_fixed, fixes = save_file.fix_character_corruption(slot_idx)

            from er_save_manager.fixes.inventory_counters import InventoryCountersFix

            inv_result = InventoryCountersFix().apply(save_file, slot_idx)
            if inv_result.applied:
                fixes.append(inv_result.description)
                was_fixed = True

            from er_save_manager.fixes.structural_scan import (
                DanglingInventoryHandleFix,
                StorageInventoryCountersFix,
            )

            for structural_fix in (
                DanglingInventoryHandleFix(),
                StorageInventoryCountersFix(),
            ):
                result = structural_fix.apply(save_file, slot_idx)
                if result.applied:
                    fixes.append(result.description)
                    was_fixed = True

            from er_save_manager.fixes.netman import NetManFix

            netman_result = NetManFix().apply(save_file, slot_idx)
            if netman_result.applied:
                fixes.append(netman_result.description)
                was_fixed = True

            slot = save_file.characters[slot_idx]
            has_dlc_location = (
                hasattr(slot, "map_id") and slot.map_id and slot.map_id.is_dlc()
            )

            if has_dlc_location:
                from er_save_manager.fixes.teleport import TeleportFix

                teleport_result = TeleportFix("roundtable").apply(save_file, slot_idx)
                if teleport_result.applied:
                    fixes.append(teleport_result.description)
                    was_fixed = True

            if should_clear_dlc:
                from er_save_manager.fixes.dlc import DLCFlagFix

                result = DLCFlagFix().apply(save_file, slot_idx)
                if result.applied:
                    fixes.append(result.description)
                    was_fixed = True

            if should_clear_tarnished:
                from er_save_manager.fixes.dlc import TarnishedPackFlagFix

                result = TarnishedPackFlagFix().apply(save_file, slot_idx)
                if result.applied:
                    fixes.append(result.description)
                    was_fixed = True

            if should_clear_invalid:
                from er_save_manager.fixes.dlc import InvalidDLCFix

                result = InvalidDLCFix().apply(save_file, slot_idx)
                if result.applied:
                    fixes.append(result.description)
                    was_fixed = True

            if save_path and fixes:
                first_fix = fixes[0].lower()
                if "torrent" in first_fix:
                    operation = "fix_corruption_torrent"
                elif "weather" in first_fix:
                    operation = "fix_corruption_weather"
                elif "time" in first_fix:
                    operation = "fix_corruption_time"
                elif "steamid" in first_fix:
                    operation = "fix_corruption_steamid"
                elif "event" in first_fix or "flag" in first_fix:
                    operation = "fix_corruption_event_flags"
                elif "dlc" in first_fix:
                    operation = "fix_corruption_dlc"
                else:
                    operation = "fix_corruption"
                manager.history.backups[0].operation = operation
                manager._save_history()

            if was_fixed:
                save_file.recalculate_checksums()
                if save_path:
                    save_file.to_file(Path(save_path))
                if reload_callback:
                    reload_callback()
                fix_summary = "\n".join(f"  - {fix}" for fix in fixes)
                CTkMessageBox.showinfo(
                    "Issues Fixed",
                    f"Fixed {len(fixes)} issue(s):\n\n{fix_summary}\n\nBackup saved to backup manager.\n\n"
                    "If the game still reports the save as corrupted or crashes on load,"
                    " open Character Details again and click 'Replace CSNetMan'.",
                    parent=_parent,
                )
            else:
                CTkMessageBox.showinfo(
                    "Nothing to Fix",
                    "No fixes were needed or could be applied.",
                    parent=_parent,
                )

        except Exception as e:
            CTkMessageBox.showerror(
                "Fix Failed", f"Fix failed:\n{str(e)}", parent=_parent
            )
            import traceback

            traceback.print_exc()
