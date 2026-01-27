"""Advanced Tools Tab (customtkinter version)."""

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.ui.messagebox import CTkMessageBox


class AdvancedToolsTab:
    """Tab for advanced save file operations (customtkinter version)."""

    def __init__(
        self, parent, get_save_file_callback, get_save_path_callback, reload_callback
    ):
        """
        Initialize advanced tools tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.save_info_text = None

    def setup_ui(self):
        """Setup the advanced tools tab UI."""
        # Main scrollable container
        scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        from er_save_manager.ui.utils import bind_mousewheel

        bind_mousewheel(scroll_frame)

        ctk.CTkLabel(
            scroll_frame,
            text="Advanced Tools",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Save info
        info_frame = ctk.CTkFrame(scroll_frame, corner_radius=12)
        info_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="Save Information",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        appearance = ctk.get_appearance_mode()
        info_bg = "#1f1f28" if appearance == "Dark" else "#f5f5f5"
        info_fg = "#e5e5f5" if appearance == "Dark" else "#1f1f28"

        self.save_info_text = tk.Text(
            info_frame,
            height=8,
            font=("Consolas", 11),
            state="disabled",
            wrap="word",
            bg=info_bg,
            fg=info_fg,
            insertbackground=info_fg,
        )
        self.save_info_text.pack(fill="x", padx=12, pady=(0, 12))

        # Tools
        tools_frame = ctk.CTkFrame(scroll_frame, corner_radius=12)
        tools_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            tools_frame,
            text="Tools",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        ctk.CTkButton(
            tools_frame,
            text="Validate Save File",
            command=self.validate_save,
            width=200,
        ).pack(pady=5, padx=12)

        ctk.CTkButton(
            tools_frame,
            text="Recalculate All Checksums",
            command=self.recalculate_checksums,
            width=200,
        ).pack(pady=5, padx=12)

        ctk.CTkButton(
            tools_frame,
            text="Refresh Information",
            command=self.update_save_info,
            width=200,
        ).pack(pady=(5, 12), padx=12)

    def update_save_info(self):
        """Update save information display."""
        save_file = self.get_save_file()
        if not save_file:
            self.save_info_text.config(state="normal")
            self.save_info_text.delete("1.0", tk.END)
            self.save_info_text.insert("1.0", "No save file loaded")
            self.save_info_text.config(state="disabled")
            return

        try:
            info = []
            info.append("SAVE FILE INFORMATION")
            info.append("=" * 40)
            info.append(f"Platform: {'PlayStation' if save_file.is_ps else 'PC'}")
            info.append(f"Magic: {save_file.magic.hex()}")

            if save_file.user_data_10_parsed:
                ud10 = save_file.user_data_10_parsed
                info.append(f"SteamID: {ud10.steam_id}")

            active_slots = save_file.get_active_slots()
            info.append(f"Active Characters: {len(active_slots)}")

            # File size
            save_path = self.get_save_path()
            if save_path:
                size_mb = Path(save_path).stat().st_size / (1024 * 1024)
                info.append(f"File Size: {size_mb:.2f} MB")

            self.save_info_text.config(state="normal")
            self.save_info_text.delete("1.0", tk.END)
            self.save_info_text.insert("1.0", "\n".join(info))
            self.save_info_text.config(state="disabled")

        except Exception as e:
            self.save_info_text.config(state="normal")
            self.save_info_text.delete("1.0", tk.END)
            self.save_info_text.insert("1.0", f"Error loading info: {str(e)}")
            self.save_info_text.config(state="disabled")

    def validate_save(self):
        """Validate save file integrity."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        try:
            issues = []

            # Basic header presence check (avoid strict magic comparisons)
            try:
                _ = save_file.magic  # ensure attribute exists
            except Exception:
                issues.append("⚠ Missing/invalid file header (magic bytes)")

            # Check for empty slots
            active_slots = save_file.get_active_slots()
            if len(active_slots) == 0:
                issues.append("⚠ No active character slots found")

            # Check file size against in-memory data length instead of a fixed constant
            save_path = self.get_save_path()
            if save_path:
                from pathlib import Path

                size = Path(save_path).stat().st_size
                try:
                    expected_size = len(save_file.data)
                except Exception:
                    expected_size = None

                if expected_size is not None and size != expected_size:
                    issues.append(
                        f"⚠ File size {size} bytes (expected {expected_size})"
                    )

            # Check character data safely via accessors on UserDataX
            for i, slot in enumerate(save_file.characters):
                try:
                    if slot.is_empty():
                        continue
                except Exception:
                    continue

                # Name check
                name = None
                try:
                    name = slot.get_character_name()
                except Exception:
                    pass
                if not name:
                    issues.append(f"⚠ Slot {i + 1}: Character has no name")

                # Level check
                level = None
                try:
                    level = slot.get_level()
                except Exception:
                    pass
                if level is None or level <= 0:
                    issues.append(f"⚠ Slot {i + 1}: Character level is 0")

            if not issues:
                CTkMessageBox.showinfo(
                    "Validation Complete",
                    "✓ Save file validation passed!\n\nNo critical issues detected.",
                )
            else:
                message = "Validation found potential issues:\n\n" + "\n".join(issues)
                CTkMessageBox.showwarning("Validation Results", message)

        except Exception as e:
            CTkMessageBox.showerror(
                "Validation Error", f"Failed to validate save:\n{str(e)}"
            )

    def recalculate_checksums(self):
        """Recalculate all checksums in save file."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        try:
            # Always create a backup first (no confirmation requested)
            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description="before_checksum_recalc",
                    operation="advanced_recalculate_checksums",
                    save=save_file,
                )

            # Recalculate checksums and save back to file
            save_file.recalculate_checksums()

            if save_path:
                save_file.to_file(save_path)
                CTkMessageBox.showinfo(
                    "Success",
                    "✓ Backup created and checksums recalculated.\n\n"
                    "All save file checksums have been updated.",
                )
                # Refresh info panel
                self.reload_save()
                self.update_save_info()
            else:
                CTkMessageBox.showerror("Error", "Save path not available")

        except Exception as e:
            CTkMessageBox.showerror(
                "Recalculation Error", f"Failed to recalculate checksums:\n{str(e)}"
            )
