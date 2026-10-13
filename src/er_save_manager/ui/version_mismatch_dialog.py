"""Dialog for fixing a save/game version mismatch."""

from pathlib import Path

import customtkinter as ctk

from er_save_manager.fixes.version_mismatch import (
    apply_version_downgrade,
    get_version_info,
)
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox

RECOMMENDED_VERSION = 252
RECOMMENDED_GAME_LABEL = "1.16.2"
MIN_VALID_VERSION = 1
MAX_VALID_VERSION = 9999

# Save-version -> game-version mapping. Elden Ring reserves a block of 10
# save-version numbers per minor game version release: the tens/hundreds
# digits identify the minor version, the last digit is the patch level
# within it (e.g. 260 = 1.17, 261 = 1.17.1).
SAVE_VERSION_TABLE: list[tuple[int, str]] = [
    (261, "1.17.1"),
    (260, "1.17"),
    (252, "1.16.2"),
    (251, "1.16.1"),
    (250, "1.16"),
    (240, "1.15"),
    (230, "1.14"),
    (222, "1.13.2"),
    (220, "1.13"),
    (213, "1.12.3"),
    (212, "1.12.2"),
    (210, "1.12"),
    (190, "1.10"),
    (181, "1.09.1"),
    (180, "1.09"),
    (171, "1.08.1"),
    (170, "1.08"),
    (161, "1.07.1"),
    (160, "1.07"),
    (150, "1.06"),
    (140, "1.05"),
    (131, "1.04.1"),
    (130, "1.04"),
    (123, "1.03.3"),
    (120, "1.03"),
    (113, "1.02.3"),
    (112, "1.02.2"),
    (111, "1.02.1"),
    (110, "1.02"),
]


class VersionInfoDialog(ctk.CTkToplevel):
    """Reference popup listing known save-version / game-version pairs."""

    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.attributes("-alpha", 0)
        self.title("Save Version Reference")
        self.resizable(False, False)
        self.transient(parent)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)

        ds.button_row(main, [{"text": "Close", "command": self.destroy}])
        ds.header(main, "Save Version Reference")
        ctk.CTkLabel(
            main,
            text=(
                "Elden Ring reserves a block of 10 save-version numbers per "
                "minor game version: the tens/hundreds digits identify the "
                "minor version, the last digit is the patch level within it "
                "(e.g. 260 = 1.17, 261 = 1.17.1)."
            ),
            font=ds.FONT,
            justify="left",
            wraplength=380,
        ).pack(anchor="w", pady=(6, 10))

        table = ctk.CTkScrollableFrame(main, fg_color=ds.BOX, height=300)
        table.pack(fill="both", expand=True)
        for col, text in enumerate(("Save version", "Game version")):
            ctk.CTkLabel(table, text=text, font=ds.BOLD, anchor="w").grid(
                row=0, column=col, sticky="w", padx=(12, 24), pady=(6, 2)
            )
        for row, (version, game) in enumerate(SAVE_VERSION_TABLE, start=1):
            for col, text in enumerate((str(version), game)):
                ctk.CTkLabel(table, text=text, font=ds.FONT, anchor="w").grid(
                    row=row, column=col, sticky="w", padx=(12, 24), pady=1
                )

        ds.finish(self, parent)


class VersionMismatchDialog(ctk.CTkToplevel):
    """
    Explains the save/game version mismatch issue and lets the user
    rewrite every version stamp in the save to a target value so an
    older game build will load it again.
    """

    def __init__(self, parent, save_file, save_path, reload_callback):
        super().__init__(parent)
        self.withdraw()
        self.attributes("-alpha", 0)
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

        ds.finish(self, parent)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)

        ds.button_row(
            main,
            [
                {"text": "Apply Fix", "command": self._on_apply},
                {"text": "Cancel", "command": self.destroy, "primary": False},
            ],
        )

        header_row = ds.header(main, "Mismatched game/save version", icon="⚠")
        ds.button(
            header_row,
            "Version Info",
            self._show_version_info,
            primary=False,
            width=110,
            height=28,
        ).pack(side="right")

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
            font=ds.FONT,
            justify="left",
            wraplength=480,
        ).pack(anchor="w", pady=(10, 12))

        ctk.CTkLabel(main, text="Detected versions", font=ds.BOLD).pack(anchor="w")
        detected = ds.box(main, pady=(4, 12))
        rows = self._detected_versions()
        for i, (label, version) in enumerate(rows):
            pady = (8 if i == 0 else 1, 8 if i == len(rows) - 1 else 1)
            ctk.CTkLabel(detected, text=label, font=ds.FONT).grid(
                row=i, column=0, sticky="w", padx=(12, 24), pady=pady
            )
            ctk.CTkLabel(detected, text=str(version), font=ds.FONT).grid(
                row=i, column=1, sticky="w", padx=(0, 12), pady=pady
            )

        target_row = ctk.CTkFrame(main, fg_color="transparent")
        target_row.pack(fill="x")
        ctk.CTkLabel(target_row, text="Target version", font=ds.FONT).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkEntry(
            target_row, textvariable=self._target_var, width=70, font=ds.FONT
        ).pack(side="left", padx=(0, 8))
        ds.button(
            target_row,
            "Use Recommended",
            self._use_recommended,
            primary=False,
            width=140,
        ).pack(side="left")
        ctk.CTkLabel(
            main,
            text=f"Recommended: {RECOMMENDED_VERSION} (game {RECOMMENDED_GAME_LABEL})",
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkLabel(
            main,
            textvariable=self._status_var,
            font=ds.FONT,
            text_color=ds.ERROR,
            justify="left",
            wraplength=480,
        ).pack(anchor="w")

    def _detected_versions(self) -> list[tuple[str, int]]:
        info = get_version_info(self._save_file)
        rows = [("Global save version", info.user_data_10_version)]
        rows += [(f"Slot {s.slot_index + 1}", s.version) for s in info.slots]
        return rows

    def _use_recommended(self):
        self._target_var.set(str(RECOMMENDED_VERSION))

    def _show_version_info(self):
        VersionInfoDialog(self)

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
