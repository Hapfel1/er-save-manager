"""Dialog for fixing a save/game version mismatch."""

from pathlib import Path

import customtkinter as ctk

from er_save_manager.fixes.version_mismatch import (
    apply_version_downgrade,
    get_version_info,
)
from er_save_manager.ui.messagebox import CTkMessageBox

RECOMMENDED_VERSION = 252
RECOMMENDED_GAME_LABEL = "1.16.2"
MIN_VALID_VERSION = 1
MAX_VALID_VERSION = 9999


class VersionMismatchDialog(ctk.CTkToplevel):
    """
    Explains the save/game version mismatch issue and lets the user
    rewrite every version stamp in the save to a target value so an
    older game build will load it again.
    """

    def __init__(self, parent, save_file, save_path, reload_callback):
        super().__init__(parent)
        self.title("Mismatched Game/Save Version")
        self.resizable(False, False)
        self.transient(parent)

        self._save_file = save_file
        self._save_path = save_path
        self._reload_callback = reload_callback

        self._target_var = ctk.StringVar(value=str(RECOMMENDED_VERSION))
        self._status_var = ctk.StringVar(value="")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build_ui()

        width, height = 520, 420
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{px}+{py}")

        from er_save_manager.ui.utils import force_render_dialog

        force_render_dialog(self)
        self.grab_set()

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            main,
            text="Mismatched Game/Save Version",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            main,
            text=(
                "Elden Ring stamps a version number into the save the moment "
                "it is opened by a newer game build, even without loading a "
                "character into gameplay. If the game is later downpatched to "
                "an older build, that save is refused with a version-"
                "incompatible message.\n\n"
                "This rewrites the version stamps back down so the save "
                "opens on an older build again. A backup is made first."
            ),
            font=("Segoe UI", 11),
            justify="left",
            wraplength=470,
        ).pack(anchor="w", pady=(8, 12))

        detected_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray20"))
        detected_frame.pack(fill="x", pady=(0, 12))

        detected_text = self._describe_detected_versions()
        ctk.CTkLabel(
            detected_frame,
            text=detected_text,
            font=("Courier", 11),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=8)

        target_row = ctk.CTkFrame(main, fg_color="transparent")
        target_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(target_row, text="Target version:").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(target_row, textvariable=self._target_var, width=80).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(
            target_row,
            text=f"Use Recommended ({RECOMMENDED_VERSION} / game {RECOMMENDED_GAME_LABEL})",
            command=self._use_recommended,
            width=240,
        ).pack(side="left")

        ctk.CTkLabel(
            main,
            textvariable=self._status_var,
            font=("Segoe UI", 11),
            text_color=("#b00020", "#ff6b6b"),
            justify="left",
            wraplength=470,
        ).pack(anchor="w", pady=(4, 8))

        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")
        ctk.CTkButton(
            btn_row,
            text="Cancel",
            command=self.destroy,
            fg_color=("gray70", "gray35"),
            width=100,
        ).pack(side="right")
        ctk.CTkButton(
            btn_row,
            text="Apply Fix",
            command=self._on_apply,
            width=140,
        ).pack(side="right", padx=(0, 8))

    def _describe_detected_versions(self) -> str:
        info = get_version_info(self._save_file)
        lines = [f"Global save version: {info.user_data_10_version}"]
        for s in info.slots:
            lines.append(f"Slot {s.slot_index + 1:2d}: version={s.version}")
        return "\n".join(lines)

    def _use_recommended(self):
        self._target_var.set(str(RECOMMENDED_VERSION))

    def _validate_target(self) -> int | None:
        raw = self._target_var.get().strip()
        if not raw.isdigit():
            self._status_var.set("Target version must be a whole number.")
            return None
        value = int(raw)
        if not (MIN_VALID_VERSION <= value <= MAX_VALID_VERSION):
            self._status_var.set(
                f"Target version must be between {MIN_VALID_VERSION} and {MAX_VALID_VERSION}."
            )
            return None
        self._status_var.set("")
        return value

    def _on_apply(self):
        target_version = self._validate_target()
        if target_version is None:
            return

        try:
            if self._save_path:
                from er_save_manager.backup.manager import BackupManager

                manager = BackupManager(Path(self._save_path))
                manager.create_backup(
                    description="before_version_mismatch_fix",
                    operation="version_mismatch_fix",
                    save=self._save_file,
                )

            result = apply_version_downgrade(self._save_file, target_version)

            if not result.applied:
                self._status_var.set(result.description)
                return

            if self._save_path:
                self._save_file.to_file(Path(self._save_path))

            if self._reload_callback:
                self._reload_callback()

            parent = self.master
            self.destroy()
            CTkMessageBox.showinfo(
                "Version Fixed",
                f"{result.description}\n\nThe save file has been updated.",
                parent=parent,
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to apply version fix:\n{e}", parent=self
            )
