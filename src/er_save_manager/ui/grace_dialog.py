"""
Sites of Grace Dialog
Unlock or lock sites of grace via their event flags.
"""

import tkinter as tk
import tkinter.ttk as ttk

import customtkinter as ctk

from er_save_manager.data.grace_data import Grace, get_graces
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import force_render_dialog

_ALL = "All"
_SCOPES = (_ALL, "Base Game", "DLC")
_STATES = (_ALL, "Unlocked", "Locked")
_EVENT_FLAGS_SIZE = 0x1BF99F


class GraceDialog:
    """
    Dialog for unlocking and locking sites of grace.

    Reads/writes event flags via an accessor that has get_flag(id) -> bool
    and set_flag(id, state) methods. Graces that only exist in Convergence
    saves are listed only when save_file.is_convergence is True.
    """

    @staticmethod
    def open(
        parent,
        event_flag_accessor,
        save_file,
        save_path,
        slot_idx,
        reload_callback,
        show_toast,
    ):
        graces = get_graces(include_convergence=bool(save_file.is_convergence))
        graces_by_iid = {str(g.flag_id): g for g in graces}

        dialog = ctk.CTkToplevel(parent)
        dialog.title("Sites of Grace")
        width, height = 860, 700
        dialog.transient(parent)
        dialog.update_idletasks()
        parent.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.resizable(True, True)
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Sites of Grace",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(15, 2), padx=15)

        ctk.CTkLabel(
            dialog,
            text="Unlock or lock sites of grace for the loaded character",
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 10), padx=15)

        # ---- Filters ----
        filter_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        filter_frame.pack(fill=tk.X, padx=15, pady=(0, 8))

        scope_var = tk.StringVar(value=_ALL)
        region_var = tk.StringVar(value=_ALL)
        state_var = tk.StringVar(value=_ALL)
        search_var = tk.StringVar()

        ctk.CTkLabel(filter_frame, text="Scope:").pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkComboBox(
            filter_frame,
            variable=scope_var,
            values=list(_SCOPES),
            state="readonly",
            width=120,
            command=lambda _v: _on_scope_changed(),
        ).pack(side=tk.LEFT, padx=(0, 14))

        ctk.CTkLabel(filter_frame, text="Region:").pack(side=tk.LEFT, padx=(0, 8))
        region_combo = ctk.CTkComboBox(
            filter_frame,
            variable=region_var,
            values=[_ALL],
            state="readonly",
            width=230,
            command=lambda _v: _refresh(),
        )
        region_combo.pack(side=tk.LEFT, padx=(0, 14))

        ctk.CTkLabel(filter_frame, text="Show:").pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkComboBox(
            filter_frame,
            variable=state_var,
            values=list(_STATES),
            state="readonly",
            width=110,
            command=lambda _v: _refresh(),
        ).pack(side=tk.LEFT)

        search_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=15, pady=(0, 8))
        ctk.CTkEntry(
            search_frame,
            textvariable=search_var,
            placeholder_text="Search graces or regions...",
        ).pack(fill=tk.X)

        summary_label = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 11))
        summary_label.pack(pady=(0, 4), padx=15, anchor="w")

        # ---- Grace list ----
        tree_frame = tk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        tree = ttk.Treeview(
            tree_frame,
            columns=("state", "grace", "region"),
            show="headings",
            selectmode="extended",
        )
        tree.heading("state", text="State")
        tree.heading("grace", text="Grace")
        tree.heading("region", text="Region")
        tree.column("state", width=90, anchor="w", stretch=False)
        tree.column("grace", width=360, anchor="w")
        tree.column("region", width=260, anchor="w")

        tree.tag_configure("unlocked", foreground="#4caf50")
        tree.tag_configure("locked", foreground="#9e9e9e")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tracks current sort: col -> ascending bool
        sort_state: dict[str, bool] = {}

        def _sort(col: str):
            asc = not sort_state.get(col, False)
            sort_state[col] = asc
            rows = [(tree.set(iid, col), iid) for iid in tree.get_children()]
            rows.sort(key=lambda r: r[0].lower(), reverse=not asc)
            for i, (_, iid) in enumerate(rows):
                tree.move(iid, "", i)

        tree.heading("state", text="State", command=lambda: _sort("state"))
        tree.heading("grace", text="Grace", command=lambda: _sort("grace"))
        tree.heading("region", text="Region", command=lambda: _sort("region"))

        # ---- Flag access ----
        def _is_unlocked(flag_id: int) -> bool:
            try:
                return bool(event_flag_accessor.get_flag(flag_id))
            except (ValueError, KeyError):
                return False

        # ---- Filtering ----
        def _in_scope(grace: Grace) -> bool:
            scope = scope_var.get()
            if scope == "DLC":
                return grace.is_dlc
            if scope == "Base Game":
                return not grace.is_dlc
            return True

        def _on_scope_changed():
            regions = sorted({g.region for g in graces if _in_scope(g)})
            region_combo.configure(values=[_ALL] + regions)
            if region_var.get() not in regions:
                region_var.set(_ALL)
            _refresh()

        def _shown_graces() -> list[Grace]:
            region = region_var.get()
            state = state_var.get()
            query = search_var.get().strip().lower()
            shown = []
            for grace in graces:
                if not _in_scope(grace):
                    continue
                if region != _ALL and grace.region != region:
                    continue
                unlocked = _is_unlocked(grace.flag_id)
                if state == "Unlocked" and not unlocked:
                    continue
                if state == "Locked" and unlocked:
                    continue
                if (
                    query
                    and query not in grace.name.lower()
                    and query not in grace.region.lower()
                ):
                    continue
                shown.append(grace)
            return shown

        def _refresh(*_args):
            tree.delete(*tree.get_children())
            shown = _shown_graces()
            for grace in shown:
                unlocked = _is_unlocked(grace.flag_id)
                tree.insert(
                    "",
                    "end",
                    iid=str(grace.flag_id),
                    values=(
                        "Unlocked" if unlocked else "Locked",
                        grace.name,
                        grace.region,
                    ),
                    tags=("unlocked" if unlocked else "locked",),
                )
            unlocked_total = sum(1 for g in graces if _is_unlocked(g.flag_id))
            summary_label.configure(
                text=f"{unlocked_total} / {len(graces)} unlocked"
                f"  -  showing {len(shown)}"
            )
            sort_state.clear()

        # ---- Applying changes ----
        def _apply(targets: list[Grace], state: bool):
            action = "Unlock" if state else "Lock"
            if not targets:
                CTkMessageBox.showinfo(
                    "No Selection", "No sites of grace selected.", parent=dialog
                )
                return

            changed = [g for g in targets if _is_unlocked(g.flag_id) != state]
            if not changed:
                CTkMessageBox.showinfo(
                    "Nothing to Change",
                    f"All {len(targets)} selected sites of grace are already "
                    f"{'unlocked' if state else 'locked'}.",
                    parent=dialog,
                )
                return

            if not CTkMessageBox.askyesno(
                "Confirm",
                f"{action} {len(changed)} site(s) of grace on "
                f"Slot {slot_idx + 1}?\n\n"
                "A backup will be created automatically.",
                parent=dialog,
            ):
                return

            _backup()

            failed = []
            for grace in changed:
                try:
                    event_flag_accessor.set_flag(grace.flag_id, state)
                except (ValueError, KeyError):
                    failed.append(grace)

            _write_and_reload()

            done = len(changed) - len(failed)
            if show_toast:
                show_toast(
                    f"{action}ed {done} site(s) of grace on Slot {slot_idx + 1}",
                    duration=2500,
                )
            if failed:
                CTkMessageBox.showwarning(
                    "Some Flags Skipped",
                    f"{len(failed)} flag(s) could not be written:\n\n"
                    + "\n".join(f"{g.flag_id}: {g.name}" for g in failed[:10]),
                    parent=dialog,
                )
            _refresh()

        def _backup():
            from er_save_manager.backup.manager import BackupManager

            if not (save_path and save_path.is_file()):
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup because the save path is not a file."
                    " Proceeding without backup.",
                    parent=dialog,
                )
                return
            try:
                BackupManager(save_path).create_backup(
                    description=f"Before grace edit (Slot {slot_idx + 1})",
                    operation="grace_edit",
                    save=save_file,
                )
            except PermissionError:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup (permission denied)."
                    " Continuing without backup.",
                    parent=dialog,
                )

        def _write_and_reload():
            """Write the event flags buffer back, recalculate checksums, save."""
            slot = save_file.character_slots[slot_idx]
            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                off = slot.event_flags_offset
                save_file._raw_data[off : off + _EVENT_FLAGS_SIZE] = slot.event_flags

            save_file.recalculate_checksums()
            if save_path and save_path.is_file():
                save_file.to_file(save_path)

            if reload_callback:
                reload_callback()

        def _selected_graces() -> list[Grace]:
            return [graces_by_iid[iid] for iid in tree.selection()]

        # ---- Action buttons ----
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="Unlock Selected",
            command=lambda: _apply(_selected_graces(), True),
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="Lock Selected",
            command=lambda: _apply(_selected_graces(), False),
            width=120,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray25"),
        ).pack(side=tk.LEFT, padx=(0, 16))

        ctk.CTkButton(
            btn_frame,
            text="Unlock All Shown",
            command=lambda: _apply(_shown_graces(), True),
            width=140,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="Lock All Shown",
            command=lambda: _apply(_shown_graces(), False),
            width=130,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray25"),
        ).pack(side=tk.LEFT)

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.RIGHT
        )

        search_var.trace_add("write", _refresh)
        _on_scope_changed()
