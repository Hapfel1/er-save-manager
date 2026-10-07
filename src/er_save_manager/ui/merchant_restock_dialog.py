"""
Merchant Restock Dialog
Lists limited merchant stock with how much the loaded character has bought,
and restocks rows by clearing their purchase counters.
"""

import tkinter as tk
import tkinter.ttk as ttk

import customtkinter as ctk

from er_save_manager.data.grace_data import get_graces
from er_save_manager.data.shop_stock import StockRow, bought, get_stock
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import (
    center_window,
    force_render_dialog,
    patch_combo_scroll,
)

_ALL = "All"
_SCOPES = (_ALL, "Base Game", "DLC")
_BOUGHT = "Any Bought"
_PARTLY = "Partly Bought"
_SOLD_OUT = "Sold Out"
_STATES = (_BOUGHT, _PARTLY, _SOLD_OUT, _ALL)
_EVENT_FLAGS_SIZE = 0x1BF99F


class MerchantRestockDialog:
    """
    Limited merchant stock for the loaded character.

    Reads/writes event flags via an accessor that has get_flag(id) -> bool
    and set_flag(id, state) methods.
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
        is_convergence = bool(save_file is not None and save_file.is_convergence)
        stock = get_stock(is_convergence)
        graces = {g.flag_id: g for g in get_graces(include_convergence=is_convergence)}

        def _get_flag(flag_id: int) -> bool:
            try:
                return bool(event_flag_accessor.get_flag(flag_id))
            except (ValueError, KeyError):
                return False

        bought_by_flag = {r.flag_id: bought(r, _get_flag) for r in stock}

        def _region(r: StockRow) -> str:
            grace = graces.get(r.grace_flag)
            return grace.region if grace else ""

        def _grace_name(r: StockRow) -> str:
            grace = graces.get(r.grace_flag)
            return grace.name if grace else ""

        dialog = ctk.CTkToplevel(parent)
        dialog.title("Merchant Restock")
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
            text="Merchant Restock",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(15, 2), padx=15)

        ctk.CTkLabel(
            dialog,
            text="Limited merchant stock the loaded character has bought",
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 4), padx=15)

        # ---- Filters ----
        filter_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        filter_frame.pack(fill=tk.X, padx=15, pady=(6, 8))

        scope_var = tk.StringVar(value=_ALL)
        merchant_var = tk.StringVar(value=_ALL)
        state_var = tk.StringVar(value=_BOUGHT)
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

        ctk.CTkLabel(filter_frame, text="Merchant:").pack(side=tk.LEFT, padx=(0, 8))
        merchant_combo = ctk.CTkComboBox(
            filter_frame,
            variable=merchant_var,
            values=[_ALL],
            state="readonly",
            width=260,
            command=lambda _v: _refresh(),
        )
        patch_combo_scroll(merchant_combo)
        merchant_combo.pack(side=tk.LEFT, padx=(0, 14))

        ctk.CTkLabel(filter_frame, text="Show:").pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkComboBox(
            filter_frame,
            variable=state_var,
            values=list(_STATES),
            state="readonly",
            width=140,
            command=lambda _v: _refresh(),
        ).pack(side=tk.LEFT)

        search_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=15, pady=(0, 8))
        ctk.CTkEntry(
            search_frame,
            textvariable=search_var,
            placeholder_text="Search items, merchants or graces...",
        ).pack(fill=tk.X)

        summary_label = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 11))
        summary_label.pack(pady=(0, 4), padx=15, anchor="w")

        # ---- Stock list ----
        tree_frame = tk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        columns = {
            "bought": ("Bought", 90, False),
            "item": ("Item", 300, True),
            "merchant": ("Merchant", 220, True),
            "region": ("Region", 180, True),
            "grace": ("Nearest Grace", 220, True),
            "price": ("Price", 80, False),
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

        tree.tag_configure("sold_out", foreground="#e57373")
        tree.tag_configure("bought", foreground="#ffb74d")
        tree.tag_configure("in_stock", foreground="#4caf50")

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
            if col == "price":
                rows.sort(key=lambda r: int(r[0]), reverse=not asc)
            else:
                rows.sort(key=lambda r: r[0].lower(), reverse=not asc)
            for i, (_, iid) in enumerate(rows):
                tree.move(iid, "", i)

        # ---- Filtering ----
        def _in_scope(r: StockRow) -> bool:
            scope = scope_var.get()
            if scope == "DLC":
                return r.is_dlc
            if scope == "Base Game":
                return not r.is_dlc
            return True

        def _on_scope_changed():
            merchants = sorted({r.merchant for r in stock if _in_scope(r)})
            merchant_combo.configure(values=[_ALL] + merchants)
            if merchant_var.get() not in merchants:
                merchant_var.set(_ALL)
            _refresh()

        def _refresh(*_args):
            tree.delete(*tree.get_children())
            state = state_var.get()
            merchant = merchant_var.get()
            query = search_var.get().strip().lower()
            shown = 0
            for r in stock:
                if not _in_scope(r) or (merchant != _ALL and r.merchant != merchant):
                    continue
                count = bought_by_flag[r.flag_id]
                sold_out = count >= r.quantity
                if state == _BOUGHT and count == 0:
                    continue
                if state == _PARTLY and (count == 0 or sold_out):
                    continue
                if state == _SOLD_OUT and not sold_out:
                    continue
                values = (
                    f"{count} / {r.quantity}",
                    r.item_name,
                    r.merchant,
                    _region(r),
                    _grace_name(r),
                    str(r.price),
                )
                if query and not any(query in v.lower() for v in values[1:5]):
                    continue
                tag = "sold_out" if sold_out else "bought" if count else "in_stock"
                tree.insert("", "end", iid=str(r.flag_id), values=values, tags=(tag,))
                shown += 1
            sold_total = sum(bought_by_flag[r.flag_id] >= r.quantity for r in stock)
            summary_label.configure(
                text=f"{sold_total} / {len(stock)} sold out  -  showing {shown}"
            )
            sort_state.clear()

        # ---- Restocking ----
        stock_by_iid = {str(r.flag_id): r for r in stock}

        def _restock(iids, scope: str):
            targets = [
                stock_by_iid[iid] for iid in iids if bought_by_flag[int(iid)] > 0
            ]
            if not targets:
                CTkMessageBox.showinfo(
                    "Nothing to Restock",
                    f"None of the {scope} items has been bought.",
                    parent=dialog,
                )
                return
            if not CTkMessageBox.askyesno(
                "Confirm",
                f"Restock {len(targets)} item(s) on Slot {slot_idx + 1}?\n\n"
                "Merchants sell the full quantity again. "
                "Items already bought are kept.\n\n"
                "A backup will be created automatically.",
                parent=dialog,
            ):
                return

            _backup()

            failed = []
            for r in targets:
                try:
                    for flag_id in r.counter_flags:
                        event_flag_accessor.set_flag(flag_id, False)
                    bought_by_flag[r.flag_id] = 0
                except (ValueError, KeyError):
                    failed.append(r)

            _write_and_reload()

            done = len(targets) - len(failed)
            if show_toast:
                show_toast(
                    f"Restocked {done} item(s) on Slot {slot_idx + 1}",
                    duration=2500,
                )
            if failed:
                CTkMessageBox.showwarning(
                    "Some Flags Skipped",
                    f"{len(failed)} item(s) could not be restocked:\n\n"
                    + "\n".join(f"{r.flag_id}: {r.item_name}" for r in failed[:10]),
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
                    description=f"Before merchant restock (Slot {slot_idx + 1})",
                    operation="merchant_restock",
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
            text="Restock Selected",
            command=lambda: _restock(tree.selection(), "selected"),
            width=140,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="Restock All Shown",
            command=lambda: _restock(tree.get_children(), "shown"),
            width=150,
        ).pack(side=tk.LEFT)

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.RIGHT
        )

        search_var.trace_add("write", _refresh)
        _on_scope_changed()
