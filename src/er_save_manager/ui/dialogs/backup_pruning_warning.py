"""Backup pruning warning dialog."""

import customtkinter as ctk

from er_save_manager.backup.manager import BackupMetadata
from er_save_manager.ui import dialog_style as ds


class BackupPruningWarningDialog(ctk.CTkToplevel):
    """
    Shown before the oldest backup is deleted due to the backup limit.

    Result is one of:
      "delete"   - proceed with deletion (Close button)
      "raised"   - user raised the limit, skip deletion
      "silent"   - same as delete but don't show again was checked
    """

    def __init__(self, parent, oldest_backup: BackupMetadata, max_backups: int):
        super().__init__(parent)
        # Hidden until built to prevent a white flash on Windows.
        self.withdraw()
        self.attributes("-alpha", 0)
        self.title("Backup Limit Reached")
        self.resizable(False, False)
        self.transient(parent)

        self._result = "delete"
        self._dont_show_var = ctk.BooleanVar(value=False)
        self._oldest = oldest_backup
        self._max_backups = max_backups
        self._new_limit_var = ctk.StringVar(value=str(max_backups + 10))

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

        ds.finish(self, parent, min_width=440)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)

        ds.button_row(
            main,
            [
                {
                    "text": "Delete Oldest",
                    "command": self._on_close,
                    "primary": False,
                    "width": 120,
                }
            ],
        )

        ds.header(main, "Backup limit reached", icon="⚠")
        ctk.CTkLabel(
            main,
            text=(
                f"The limit of {self._max_backups} backups has been reached. "
                "The oldest backup will be deleted:"
            ),
            font=ds.FONT,
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(10, 4))
        ctk.CTkLabel(
            main, text=self._oldest.filename, font=ds.SMALL, text_color=ds.MUTED
        ).pack(anchor="w", pady=(0, 10))

        limit_box = ds.box(main, pady=(0, 10))
        ctk.CTkLabel(limit_box, text="Raise the limit to", font=ds.FONT).pack(
            side="left", padx=(12, 8), pady=10
        )
        ctk.CTkEntry(
            limit_box, textvariable=self._new_limit_var, width=70, font=ds.FONT
        ).pack(side="left", padx=(0, 8), pady=10)
        ds.button(limit_box, "Raise and Keep", self._on_raise_limit, width=120).pack(
            side="right", padx=12, pady=10
        )

        ctk.CTkCheckBox(
            main,
            text="Don't show this warning again",
            font=ds.FONT,
            variable=self._dont_show_var,
        ).pack(anchor="w")

    def _on_raise_limit(self):
        try:
            new_limit = int(self._new_limit_var.get())
        except ValueError:
            return
        if new_limit <= self._max_backups:
            return

        from er_save_manager.ui.settings import get_settings

        settings = get_settings()
        settings.set("max_backups", new_limit)
        if self._dont_show_var.get():
            settings.set("show_backup_pruning_warning", False)
        settings.save()

        self._result = "raised"
        self.destroy()

    def _on_close(self):
        if self._dont_show_var.get():
            from er_save_manager.ui.settings import get_settings

            settings = get_settings()
            settings.set("show_backup_pruning_warning", False)
            settings.save()
            self._result = "silent"
        else:
            self._result = "delete"
        self.destroy()

    def show(self) -> str:
        """Block until closed. Returns 'delete', 'raised', or 'silent'."""
        self.wait_window()
        return self._result
