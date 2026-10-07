"""
Item Pickups Dialog
Checklist of world item pickups, collected or missed, from their item lot
event flags. Clearing a world pickup's flag makes the game place it again.
"""

import tkinter as tk
import tkinter.ttk as ttk

import customtkinter as ctk

from er_save_manager.data.grace_data import get_graces
from er_save_manager.data.item_pickups import (
    ITEM_TYPES,
    SOURCE_LABELS,
    Pickup,
    get_pickups,
)
from er_save_manager.data.locations import get_name_for_map_id
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import (
    center_window,
    force_render_dialog,
    patch_combo_scroll,
)

_ALL = "All"
_SCOPES = (_ALL, "Base Game", "DLC")
_MISSING = "Missing"
_COLLECTED = "Collected"
_STATES = (_MISSING, _COLLECTED, _ALL)
_EVENT_FLAGS_SIZE = 0x1BF99F


class ItemPickupsDialog:
    """
    Checklist of item pickups for the loaded character.

    Reads/writes event flags via an accessor that has get_flag(id) -> bool
    and set_flag(id, state) methods. A set flag means the game treats the lot
    as collected. Only world pickups can be respawned: boss, NPC and enemy
    rewards are awarded by scripts that a cleared flag does not rerun.
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
        pickups = get_pickups()
        graces = {g.flag_id: g for g in get_graces(include_convergence=False)}

        def _region(p: Pickup) -> str:
            grace = graces.get(p.grace_flag)
            if grace:
                return grace.region
            return get_name_for_map_id(p.map_id) if p.map_id else ""

        def _grace_name(p: Pickup) -> str:
            grace = graces.get(p.grace_flag)
            return grace.name if grace else ""

        def _collected(flag_id: int) -> bool:
            try:
                return bool(event_flag_accessor.get_flag(flag_id))
            except (ValueError, KeyError):
                return False

        state_by_flag = {p.flag_id: _collected(p.flag_id) for p in pickups}

        dialog = ctk.CTkToplevel(parent)
        dialog.title("Item Pickups")
        width, height = 1100, 720
        dialog.transient(parent)
        dialog.update_idletasks()
        parent.update_idletasks()
        center_window(dialog, width, height, parent=parent)
        dialog.resizable(True, True)
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Item Pickups",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(15, 2), padx=15)

        ctk.CTkLabel(
            dialog,
            text="World items, drops and rewards the loaded character has "
            "collected or missed",
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 4), padx=15)

        if save_file is not None and save_file.is_convergence:
            ctk.CTkLabel(
                dialog,
                text="Item locations are from the base game; "
                "Convergence moves or replaces some of them.",
                text_color=("#b26a00", "#ffb74d"),
            ).pack(pady=(0, 4), padx=15)

        # ---- Filters ----
        filter_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        filter_frame.pack(fill=tk.X, padx=15, pady=(6, 8))

        scope_var = tk.StringVar(value=_ALL)
        region_var = tk.StringVar(value=_ALL)
        type_var = tk.StringVar(value=_ALL)
        state_var = tk.StringVar(value=_MISSING)
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
        patch_combo_scroll(region_combo)
        region_combo.pack(side=tk.LEFT, padx=(0, 14))

        ctk.CTkLabel(filter_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 8))
        type_combo = ctk.CTkComboBox(
            filter_frame,
            variable=type_var,
            values=[_ALL] + ITEM_TYPES,
            state="readonly",
            width=210,
            command=lambda _v: _refresh(),
        )
        patch_combo_scroll(type_combo)
        type_combo.pack(side=tk.LEFT, padx=(0, 14))

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
            placeholder_text="Search items, graces or regions...",
        ).pack(fill=tk.X)

        summary_label = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 11))
        summary_label.pack(pady=(0, 4), padx=15, anchor="w")

        # ---- Pickup list ----
        tree_frame = tk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        columns = {
            "state": ("State", 90, False),
            "item": ("Item", 380, True),
            "region": ("Region", 220, True),
            "grace": ("Nearest Grace", 260, True),
            "source": ("Source", 130, False),
        }
        tree = ttk.Treeview(
            tree_frame,
            columns=tuple(columns),
            show="headings",
            selectmode="extended",
        )
        for col, (title, col_width, stretch) in columns.items():
            tree.heading(col, text=title, command=lambda c=col: _sort(c))
            tree.column(col, width=col_width, anchor="w", stretch=stretch)

        tree.tag_configure("collected", foreground="#4caf50")
        tree.tag_configure("missing", foreground="#e57373")

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

        # ---- Filtering ----
        def _in_scope(p: Pickup) -> bool:
            scope = scope_var.get()
            if scope == "DLC":
                return p.is_dlc
            if scope == "Base Game":
                return not p.is_dlc
            return True

        def _on_scope_changed():
            regions = sorted({_region(p) for p in pickups if _in_scope(p)} - {""})
            region_combo.configure(values=[_ALL] + regions)
            if region_var.get() not in regions:
                region_var.set(_ALL)
            _refresh()

        def _matches(p: Pickup) -> bool:
            if not _in_scope(p):
                return False
            region = region_var.get()
            if region != _ALL and _region(p) != region:
                return False
            item_type = type_var.get()
            return item_type == _ALL or p.item_type == item_type

        def _refresh(*_args):
            tree.delete(*tree.get_children())
            state = state_var.get()
            query = search_var.get().strip().lower()
            in_filter = [p for p in pickups if _matches(p)]
            shown = 0
            for p in in_filter:
                collected = state_by_flag[p.flag_id]
                if state == _MISSING and collected:
                    continue
                if state == _COLLECTED and not collected:
                    continue
                values = (
                    _COLLECTED if collected else _MISSING,
                    p.item_label,
                    _region(p),
                    _grace_name(p),
                    SOURCE_LABELS[p.source],
                )
                if query and not any(query in v.lower() for v in values[1:]):
                    continue
                tree.insert(
                    "",
                    "end",
                    iid=str(p.flag_id),
                    values=values,
                    tags=("collected" if collected else "missing",),
                )
                shown += 1
            collected_total = sum(state_by_flag[p.flag_id] for p in in_filter)
            summary_label.configure(
                text=f"{collected_total} / {len(in_filter)} collected"
                f"  -  showing {shown}"
            )
            sort_state.clear()

        # ---- Respawning ----
        pickups_by_iid = {str(p.flag_id): p for p in pickups}

        def _respawn_selected():
            selected = [pickups_by_iid[iid] for iid in tree.selection()]
            if not selected:
                CTkMessageBox.showinfo(
                    "No Selection", "No item pickups selected.", parent=dialog
                )
                return
            targets = [
                p for p in selected if p.source == "pickup" and state_by_flag[p.flag_id]
            ]
            skipped = sum(1 for p in selected if p.source != "pickup")
            if not targets:
                CTkMessageBox.showinfo(
                    "Nothing to Respawn",
                    "None of the selected entries is a collected world pickup."
                    + (
                        f"\n\n{skipped} reward(s) or drop(s) cannot be respawned."
                        if skipped
                        else ""
                    ),
                    parent=dialog,
                )
                return

            note = (
                f"\n\n{skipped} reward(s) or drop(s) will be skipped; "
                "only world pickups can be respawned."
                if skipped
                else ""
            )
            if not CTkMessageBox.askyesno(
                "Confirm",
                f"Respawn {len(targets)} item pickup(s) on Slot {slot_idx + 1}?\n\n"
                "The items appear in the world again after the area reloads. "
                "Items already in the inventory are kept."
                f"{note}\n\nA backup will be created automatically.",
                parent=dialog,
            ):
                return

            _backup()

            failed = []
            for p in targets:
                try:
                    event_flag_accessor.set_flag(p.flag_id, False)
                    state_by_flag[p.flag_id] = False
                except (ValueError, KeyError):
                    failed.append(p)

            _write_and_reload()

            done = len(targets) - len(failed)
            if show_toast:
                show_toast(
                    f"Respawned {done} item pickup(s) on Slot {slot_idx + 1}",
                    duration=2500,
                )
            if failed:
                CTkMessageBox.showwarning(
                    "Some Flags Skipped",
                    f"{len(failed)} flag(s) could not be written:\n\n"
                    + "\n".join(f"{p.flag_id}: {p.item_label}" for p in failed[:10]),
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
                    description=f"Before item pickup respawn (Slot {slot_idx + 1})",
                    operation="item_pickup_respawn",
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

        # ---- Buttons ----
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="Respawn Selected",
            command=_respawn_selected,
            width=140,
        ).pack(side=tk.LEFT)

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.RIGHT
        )

        search_var.trace_add("write", _refresh)
        _on_scope_changed()
