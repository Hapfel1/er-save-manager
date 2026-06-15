"""Backup pruning warning dialog."""

import customtkinter as ctk

from er_save_manager.backup.manager import BackupMetadata


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

        self.geometry("480x280")
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 480) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 280) // 2
        self.geometry(f"480x280+{px}+{py}")

        from er_save_manager.ui.utils import force_render_dialog

        force_render_dialog(self)
        self.grab_set()

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            main,
            text="Backup Limit Reached",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            main,
            text=(
                f"The backup limit ({self._max_backups}) has been reached.\n"
                f"The oldest backup will be deleted:\n\n"
                f"  {self._oldest.filename}"
            ),
            font=("Segoe UI", 11),
            justify="left",
        ).pack(anchor="w", pady=(8, 12))

        # Raise limit row
        limit_row = ctk.CTkFrame(main, fg_color="transparent")
        limit_row.pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(limit_row, text="Set new limit:").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(limit_row, textvariable=self._new_limit_var, width=70).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(
            limit_row,
            text="Apply and Keep Backup",
            width=160,
            command=self._on_raise_limit,
        ).pack(side="left")

        ctk.CTkCheckBox(
            main,
            text="Don't show this warning again",
            variable=self._dont_show_var,
        ).pack(anchor="w", pady=(0, 12))

        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(fill="x")
        ctk.CTkButton(
            btn_row,
            text="Close (Delete Oldest)",
            command=self._on_close,
            fg_color=("gray70", "gray35"),
            width=160,
        ).pack(side="right")

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
