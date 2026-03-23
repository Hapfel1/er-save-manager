"""
Character Details Dialog (customtkinter version)
Shows detailed character information with corruption detection
"""

from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox


class CharacterDetailsDialog:
    """Dialog showing character details with fix/teleport options (customtkinter version)"""

    @staticmethod
    def show(parent, save_file, slot_idx, save_path=None, reload_callback=None):
        if not save_file:
            CTkMessageBox.showwarning("No Save", "No save file loaded!")
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
                issues_detected = corruption_issues
        except Exception:
            pass

        has_dlc_flag = False
        has_invalid_dlc = False
        try:
            has_dlc_flag = slot.has_dlc_flag()
            has_invalid_dlc = slot.has_invalid_dlc()
        except Exception:
            pass

        # Checksum check
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

        info = []
        info.append("=" * 50)
        info.append(f"  CHARACTER: {name}")
        info.append("=" * 50)
        info.append(f"  Level: {level}")
        info.append(f"  Playtime: {playtime}")
        info.append(f"  Location: {location}")
        if is_dlc_location:
            info.append("  WARNING: Currently in DLC area!")
        info.append("")

        if has_dlc_flag or (has_invalid_dlc and not deep_scan_available):
            info.append("DLC FLAGS:")
            if has_dlc_flag:
                info.append("  Has DLC Access: Yes")
            if has_invalid_dlc and not deep_scan_available:
                info.append("  WARNING: Invalid data in unused DLC slots")
            info.append("")

        if deep_scan_available and deep_scan_result:
            info.append("=" * 50)
            info.append("TORN WRITE DETECTED:")
            info.append("=" * 50)
            delta = deep_scan_result.delta
            info.append(
                f"  Shift: {'+' if delta > 0 else ''}{delta} bytes (0x{abs(delta):x})"
            )
            tear_loc = getattr(deep_scan_result, "tear_location", "netman")
            info.append(f"  Location: {tear_loc}")
            info.append(f"  Confidence: {deep_scan_result.confidence}")
            info.append("")
            info.append("RECOMMENDATION:")
            info.append("  Click 'Fix All Issues' to repair the torn write.")
        elif issues_detected:
            info.append("=" * 50)
            info.append("ISSUES DETECTED:")
            info.append("=" * 50)
            for issue in issues_detected:
                if ":" in issue:
                    issue_type, issue_detail = issue.split(":", 1)
                    info.append(f"  - {issue_detail}")
                else:
                    info.append(f"  - {issue}")
            info.append("")
            if any("dlc_location" in issue for issue in issues_detected):
                info.append("RECOMMENDATION:")
                info.append("  Click 'Teleport Character' to escape the DLC area")
                info.append("  to Roundtable Hold (safest location).")
                info.append("")
            info.append("Click 'Fix All Issues' to correct everything")
        else:
            info.append("=" * 50)
            info.append("NO ISSUES DETECTED")
            info.append("=" * 50)
            info.append("")
            info.append("Character appears healthy!")

        dialog = ctk.CTkToplevel(parent)
        dialog.title(f"Character Details - {name}")

        width = 640
        height = 520
        if deep_scan_available:
            height = 560
        elif has_dlc_flag or (has_invalid_dlc and not deep_scan_available):
            height = 560
        dialog.update_idletasks()
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.resizable(True, True)

        dialog.update_idletasks()
        dialog.lift()
        dialog.focus_force()

        main_frame = ctk.CTkFrame(dialog, corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header = ctk.CTkLabel(
            main_frame,
            text=f"Character Details - {name}",
            font=("Segoe UI", 16, "bold"),
        )
        header.pack(anchor="w", padx=10, pady=(8, 6))

        info_box = ctk.CTkTextbox(
            main_frame,
            font=("Consolas", 13),
            wrap="word",
            fg_color=("#f5f5f5", "#111827"),
            text_color=("#1f1f28", "#e5e7eb"),
        )
        info_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        info_box.insert("1.0", "\n".join(info))
        info_box.configure(state="disabled")

        clear_dlc_flag_var = None
        clear_invalid_dlc_var = None

        if has_dlc_flag or (has_invalid_dlc and not deep_scan_available):
            dlc_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            dlc_frame.pack(fill="x", padx=10, pady=(5, 10))

            if has_dlc_flag:
                clear_dlc_flag_var = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(
                    dlc_frame,
                    text="Clear Shadow of the Erdtree flag (allows loading without DLC)",
                    variable=clear_dlc_flag_var,
                ).pack(anchor="w", pady=(0, 2))
                ctk.CTkLabel(
                    dlc_frame,
                    text="   Use if you cannot load the save file without the DLC installed.",
                    font=("Segoe UI", 10),
                    text_color=("gray50", "gray50"),
                ).pack(anchor="w", pady=(0, 8))

            if has_invalid_dlc and not deep_scan_available:
                clear_invalid_dlc_var = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(
                    dlc_frame,
                    text="Clear invalid DLC data (fixes corrupted DLC flags)",
                    variable=clear_invalid_dlc_var,
                ).pack(anchor="w", pady=(0, 2))
                ctk.CTkLabel(
                    dlc_frame,
                    text="   Invalid data in unused DLC slots can prevent save from loading.",
                    font=("Segoe UI", 10),
                    text_color=("gray50", "gray50"),
                ).pack(anchor="w")

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=6, pady=(0, 4))

        if deep_scan_available or issues_detected:

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
                        clear_invalid_dlc_var,
                    )

            ctk.CTkButton(
                button_frame,
                text="Fix All Issues",
                command=fix_all,
                width=150,
            ).pack(side="left", padx=5)

        elif has_dlc_flag or (has_invalid_dlc and not deep_scan_available):
            apply_btn = ctk.CTkButton(
                button_frame,
                text="Apply",
                command=lambda: CharacterDetailsDialog._apply_dlc_flags(
                    dialog,
                    save_file,
                    slot_idx,
                    save_path,
                    reload_callback,
                    clear_dlc_flag_var,
                    clear_invalid_dlc_var,
                ),
                width=150,
                state="disabled",
            )
            apply_btn.pack(side="left", padx=5)

            def _on_dlc_checkbox_change(*_):
                any_ticked = (clear_dlc_flag_var and clear_dlc_flag_var.get()) or (
                    clear_invalid_dlc_var and clear_invalid_dlc_var.get()
                )
                apply_btn.configure(state="normal" if any_ticked else "disabled")

            if clear_dlc_flag_var:
                clear_dlc_flag_var.trace_add("write", _on_dlc_checkbox_change)
            if clear_invalid_dlc_var:
                clear_invalid_dlc_var.trace_add("write", _on_dlc_checkbox_change)

        def teleport():
            CharacterDetailsDialog._show_teleport_dialog(
                parent,
                dialog,
                save_file,
                slot_idx,
                save_path,
                reload_callback,
                clear_dlc_flag_var,
                clear_invalid_dlc_var,
            )

        ctk.CTkButton(
            button_frame,
            text="Teleport Character",
            command=teleport,
            width=150,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Close",
            command=dialog.destroy,
            width=100,
        ).pack(side="right", padx=5)

        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

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
        clear_invalid_dlc_var=None,
    ):
        should_clear_dlc = clear_dlc_flag_var and clear_dlc_flag_var.get()
        should_clear_invalid = clear_invalid_dlc_var and clear_invalid_dlc_var.get()

        if not should_clear_dlc and not should_clear_invalid:
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

            dialog.destroy()
            CTkMessageBox.showinfo(
                "DLC Flags",
                "DLC flag cleared. The save file has been updated.",
            )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Failed to apply DLC fix:\n{e}")

    @staticmethod
    def _run_deep_scan_fix(dialog, save_file, slot_idx, save_path, reload_callback):
        """Run deep scan and show result before applying."""
        try:
            from er_save_manager.fixes.deep_scan import DeepScanFix

            deep_fix = DeepScanFix()
            result = deep_fix.scan_only(save_file, slot_idx)

            if not result.steamid_found:
                CTkMessageBox.showwarning(
                    "Deep Scan",
                    "SteamID64 not found in slot data.\nCannot determine shift.",
                )
                return

            if result.delta == 0:
                CTkMessageBox.showinfo("Deep Scan", "No byte shift detected.")
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

            if not CTkMessageBox.askyesno("Deep Scan Fix", msg):
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
                CTkMessageBox.showinfo(
                    "Deep Scan Fix",
                    f"{fix_result.description}\n\n{detail_text}\n\nBackup saved.",
                )
                dialog.destroy()
            else:
                CTkMessageBox.showwarning(
                    "Deep Scan Fix",
                    f"Fix not applied:\n{fix_result.description}",
                )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Deep scan failed:\n{str(e)}")
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
        clear_invalid_dlc_var=None,
    ):
        details_dialog.destroy()

        teleport_dialog = ctk.CTkToplevel(parent)
        teleport_dialog.title("Teleport Character")
        width, height = 400, 250
        teleport_dialog.update_idletasks()
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        teleport_dialog.geometry(f"{width}x{height}+{x}+{y}")
        teleport_dialog.grab_set()
        teleport_dialog.lift()
        teleport_dialog.focus_force()

        main_frame = ctk.CTkFrame(teleport_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            main_frame,
            text=f"Teleport Slot {slot_idx + 1}",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 20))

        location_frame = ctk.CTkFrame(main_frame)
        location_frame.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            location_frame,
            text="Roundtable Hold",
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=10)

        ctk.CTkLabel(
            location_frame,
            text="Character will be teleported to Roundtable Hold.\nThis is the safest location for unstuck/DLC escape.",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(pady=5)

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
                        "Success",
                        f"Applied fixes:\n\n{fixes_text}\n\nBackup saved to backup manager.",
                    )
                    teleport_dialog.destroy()
                else:
                    CTkMessageBox.showwarning("Not Applied", "No fixes were applied.")

            except Exception as e:
                CTkMessageBox.showerror("Error", f"Teleport failed:\n{str(e)}")
                import traceback

                traceback.print_exc()

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            button_frame, text="Teleport", command=do_teleport, width=100
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame, text="Cancel", command=teleport_dialog.destroy, width=100
        ).pack(side="right", padx=5)

    @staticmethod
    def _fix_character(
        dialog,
        save_file,
        slot_idx,
        issue_count,
        save_path,
        reload_callback,
        clear_dlc_flag_var=None,
        clear_invalid_dlc_var=None,
    ):
        dialog.destroy()

        should_clear_dlc = clear_dlc_flag_var and clear_dlc_flag_var.get()
        should_clear_invalid = clear_invalid_dlc_var and clear_invalid_dlc_var.get()

        confirm_parts = [f"Fix all {issue_count} issue(s) in Slot {slot_idx + 1}?"]
        if should_clear_dlc or should_clear_invalid:
            confirm_parts.append("\nAdditional fixes:")
            if should_clear_dlc:
                confirm_parts.append("  - Clear Shadow of the Erdtree flag")
            if should_clear_invalid:
                confirm_parts.append("  - Clear invalid DLC data")
        confirm_parts.append("\nA backup will be created.")

        if not CTkMessageBox.askyesno("Confirm", "\n".join(confirm_parts)):
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
                    "Success",
                    f"Fixed {len(fixes)} issue(s):\n\n{fix_summary}\n\nBackup saved to backup manager.",
                )
            else:
                CTkMessageBox.showinfo(
                    "Info", "No fixes were needed or could be applied."
                )

        except Exception as e:
            CTkMessageBox.showerror("Error", f"Fix failed:\n{str(e)}")
            import traceback

            traceback.print_exc()
