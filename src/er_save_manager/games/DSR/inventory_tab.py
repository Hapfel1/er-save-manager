"""
DSR Inventory tab.

Left: item spawner over the game's item list (data/items.csv), with an
infusion choice for weapons and a visual picker. Right: the character's
inventory with quantity, upgrade and infusion edits, removal and a visual
editor. Every action works on one or more selected rows (Ctrl or Shift
click), checks each item against its limits, and writes once with one
backup. Equipped items cannot be removed; Seamless Co-op goods are offered
only for .co2 saves.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.games.DS3.tabs.inventory import enable
from er_save_manager.games.DSR import catalog
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(
        parent, "darksoulsremastered.exe", "Dark Souls: Remastered"
    )


_HINT = ("gray40", "gray60")
_ALL = "All"
_CONFIRM_SPAWN_COUNT = 25


def _backup_and_save(dsr_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    dsr_save.save_to_file(save_path)


def _apply_treeview_style() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "DSR.Treeview",
        background="#2b2b2b",
        foreground="white",
        fieldbackground="#2b2b2b",
        rowheight=22,
        borderwidth=0,
    )
    style.configure("DSR.Treeview.Heading", background="#3b3b3b", foreground="white")
    style.map("DSR.Treeview", background=[("selected", "#5a4a7a")])


def _summary(done: str, count: int, skipped: list[str], capped: int = 0) -> str:
    parts = [done] if count else []
    if capped:
        parts.append(f"{capped} capped at their limits")
    if skipped:
        shown = ", ".join(skipped[:3]) + (" and more" if len(skipped) > 3 else "")
        parts.append(f"skipped {shown}")
    return ". ".join(parts) + "." if parts else "Nothing changed."


def _tree(parent, columns, height: int = 10) -> ttk.Treeview:
    frame = tk.Frame(parent, bg="#2b2b2b")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    tree = ttk.Treeview(
        frame,
        columns=[c[0] for c in columns],
        show="headings",
        style="DSR.Treeview",
        height=height,
        selectmode="extended",
    )
    for col, label, width, anchor in columns:
        tree.heading(col, text=label)
        tree.column(col, width=width, anchor=anchor, stretch=col == columns[0][0])
    tree.grid(row=0, column=0, sticky="nsew")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    sb.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=sb.set)
    tree.frame = frame
    return tree


class DSRInventoryTab:
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        # Inventory rows: (slot, name, category label, qty, item type, item id)
        self._all_items: list[tuple] = []
        self._sort_col: str | None = None
        self._sort_asc = True
        # Spawn tree row id -> (representative item, infusion variants)
        self._spawn_rows: dict[str, tuple[dict, list[dict]]] = {}
        self._visible_spawn: list[tuple[str, dict, list[dict]]] = []
        self._spawn_variants: list[dict] = []
        self._selected_item: dict | None = None
        self._spawn_seamless = False
        self._spawn_job: str | None = None
        # Slots the last batch left its entries at, for popups to reselect.
        self.last_offsets: list[int] = []
        # Called after every save write, so open popups can reload.
        self.listeners: list = []

    # --- Layout ------------------------------------------------------------ #

    def setup_ui(self) -> None:
        _apply_treeview_style()
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header, text="Inventory Editor", font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = tk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header, variable=self._slot_var, values=[], state="readonly", width=220
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.grid_columnconfigure((0, 1), weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._build_spawner(body)
        self._build_inventory(body)
        self._apply_edit_states()
        self._apply_spawn_states()

    def _build_spawner(self, parent) -> None:
        left = ctk.CTkFrame(parent, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(left, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkLabel(head, text="Spawn Items", font=("Segoe UI", 12, "bold")).pack(
            side="left"
        )
        self._show_cut = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            head,
            text="Cut content",
            variable=self._show_cut,
            command=self._refresh_spawn_tree,
        ).pack(side="left", padx=(16, 0))
        ctk.CTkButton(
            head, text="Visual Picker", width=110, command=self._open_picker
        ).pack(side="right")

        frow = ctk.CTkFrame(left, fg_color="transparent")
        frow.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        self._spawn_cat_var = tk.StringVar(value=_ALL)
        self._spawn_cat_combo = ctk.CTkComboBox(
            frow,
            variable=self._spawn_cat_var,
            values=self.category_options(),
            state="readonly",
            width=130,
            command=lambda _: self._refresh_spawn_tree(),
        )
        self._spawn_cat_combo.pack(side="left", padx=(0, 6))
        self._spawn_search_var = tk.StringVar()
        self._spawn_search_var.trace_add("write", lambda *_: self._refresh_spawn_tree())
        ctk.CTkEntry(
            frow, textvariable=self._spawn_search_var, placeholder_text="Search..."
        ).pack(side="left", fill="x", expand=True)

        self._spawn_tree = _tree(
            left, [("name", "Item (Ctrl or Shift click for several)", 260, "w")]
        )
        self._spawn_tree.frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self._spawn_tree.bind("<<TreeviewSelect>>", self._on_spawn_select)

        inf_row = ctk.CTkFrame(left, fg_color="transparent")
        inf_row.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 2))
        ctk.CTkLabel(inf_row, text="Infusion:").pack(side="left", padx=(0, 4))
        self._spawn_inf_var = tk.StringVar(value="")
        self._spawn_inf_combo = ctk.CTkComboBox(
            inf_row,
            variable=self._spawn_inf_var,
            values=[],
            state="readonly",
            width=140,
            command=self._on_spawn_infusion,
        )
        self._spawn_inf_combo.pack(side="left")

        ctrl = ctk.CTkFrame(left, fg_color="transparent")
        ctrl.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkLabel(ctrl, text="Qty:").grid(row=0, column=0, padx=(0, 2), pady=4)
        self._spawn_qty_var = tk.StringVar(value="1")
        self._spawn_qty_entry = ctk.CTkEntry(
            ctrl, textvariable=self._spawn_qty_var, width=55
        )
        self._spawn_qty_entry.grid(row=0, column=1, padx=(0, 8), pady=4)
        ctk.CTkLabel(ctrl, text="Upgrade:").grid(row=0, column=2, padx=(0, 2), pady=4)
        self._spawn_upg_var = tk.StringVar(value="0")
        self._spawn_upg_entry = ctk.CTkEntry(
            ctrl, textvariable=self._spawn_upg_var, width=45
        )
        self._spawn_upg_entry.grid(row=0, column=3, padx=(0, 8), pady=4)
        buttons = ctk.CTkFrame(ctrl, fg_color="transparent")
        buttons.grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 2))
        self._spawn_btn = ctk.CTkButton(
            buttons, text="Spawn Selected", width=130, command=self._spawn_selected
        )
        self._spawn_btn.pack(side="left", padx=(0, 6))
        self._spawn_all_btn = ctk.CTkButton(
            buttons, text="Spawn All Listed", width=130, command=self._spawn_all
        )
        self._spawn_all_btn.pack(side="left")
        self._spawn_info = ctk.CTkLabel(
            ctrl, text="", font=("Segoe UI", 9), text_color=_HINT
        )
        self._spawn_info.grid(row=2, column=0, columnspan=4, sticky="w")

    def _build_inventory(self, parent) -> None:
        right = ctk.CTkFrame(parent, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(right, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkLabel(head, text="Inventory", font=("Segoe UI", 12, "bold")).pack(
            side="left"
        )
        self._count_label = ctk.CTkLabel(
            head, text="", font=("Segoe UI", 10), text_color=_HINT
        )
        self._count_label.pack(side="left", padx=10)
        ctk.CTkButton(
            head, text="Visual Editor", width=110, command=self._open_editor
        ).pack(side="right")

        frow = ctk.CTkFrame(right, fg_color="transparent")
        frow.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        self._inv_search_var = tk.StringVar()
        self._inv_search_var.trace_add("write", lambda *_: self._refresh_inv_tree())
        ctk.CTkEntry(
            frow, textvariable=self._inv_search_var, placeholder_text="Search..."
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._inv_cat_var = tk.StringVar(value=_ALL)
        ctk.CTkComboBox(
            frow,
            variable=self._inv_cat_var,
            values=self.category_options(include_seamless=True),
            state="readonly",
            width=130,
            command=lambda _: self._refresh_inv_tree(),
        ).pack(side="left")

        self._inv_tree = _tree(
            right,
            [
                ("name", "Item", 220, "w"),
                ("cat", "Type", 95, "center"),
                ("qty", "Qty", 50, "center"),
                ("slot", "Slot", 50, "center"),
            ],
        )
        for col in ("name", "cat", "qty", "slot"):
            self._inv_tree.heading(col, command=lambda c=col: self._sort_by(c))
        self._inv_tree.frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self._inv_tree.bind("<<TreeviewSelect>>", self._on_inv_select)

        edits = ctk.CTkFrame(right, fg_color="transparent")
        edits.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 2))
        self._edit_qty_var = tk.StringVar(value="1")
        self._edit_upg_var = tk.StringVar(value="0")
        self._edit_inf_var = tk.StringVar(value="")
        qty_row = ctk.CTkFrame(edits, fg_color="transparent")
        qty_row.pack(fill="x", pady=2)
        ctk.CTkLabel(qty_row, text="Qty:", width=60, anchor="w").pack(side="left")
        self._edit_qty_entry = ctk.CTkEntry(
            qty_row, textvariable=self._edit_qty_var, width=55
        )
        self._edit_qty_entry.pack(side="left", padx=(0, 6))
        self._set_qty_btn = ctk.CTkButton(
            qty_row,
            text="Set Quantity",
            width=110,
            command=lambda: self._read_and(
                self._edit_qty_var, "Quantity", self.set_quantity
            ),
        )
        self._set_qty_btn.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(qty_row, text="Upgrade:").pack(side="left", padx=(0, 4))
        self._edit_upg_entry = ctk.CTkEntry(
            qty_row, textvariable=self._edit_upg_var, width=45
        )
        self._edit_upg_entry.pack(side="left", padx=(0, 6))
        self._set_upg_btn = ctk.CTkButton(
            qty_row,
            text="Set Upgrade",
            width=110,
            command=lambda: self._read_and(
                self._edit_upg_var, "Upgrade", self.set_upgrade
            ),
        )
        self._set_upg_btn.pack(side="left")

        inf_row = ctk.CTkFrame(edits, fg_color="transparent")
        inf_row.pack(fill="x", pady=2)
        ctk.CTkLabel(inf_row, text="Infusion:", width=60, anchor="w").pack(side="left")
        self._edit_inf_combo = ctk.CTkComboBox(
            inf_row,
            variable=self._edit_inf_var,
            values=catalog.INFUSIONS,
            state="readonly",
            width=140,
        )
        self._edit_inf_combo.pack(side="left", padx=(0, 6))
        self._set_inf_btn = ctk.CTkButton(
            inf_row,
            text="Set Infusion",
            width=110,
            command=lambda: self.set_infusion(
                self.selected_offsets(), self._edit_inf_var.get()
            ),
        )
        self._set_inf_btn.pack(side="left")

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=8, pady=(2, 2))
        self._remove_btn = ctk.CTkButton(
            btn_row,
            text="Remove Selected",
            width=130,
            fg_color=("gray60", "gray35"),
            hover_color=("gray50", "gray25"),
            command=lambda: self.remove_entries(self.selected_offsets()),
        )
        self._remove_btn.pack(side="left", padx=(0, 4))
        self._repair_btn = ctk.CTkButton(
            btn_row, text="Repair All", width=100, command=self._repair_all
        )
        self._repair_btn.pack(side="left")
        self._edit_info = ctk.CTkLabel(
            right, text="", font=("Segoe UI", 9), text_color=_HINT, anchor="w"
        )
        self._edit_info.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 8))

    # --- Categories -------------------------------------------------------- #

    def category_options(self, include_seamless: bool = False) -> list[str]:
        labels = [
            label
            for key, label in catalog.CATEGORY_LABELS.items()
            if key != "seamless" or include_seamless or self._seamless_save()
        ]
        return [_ALL, *labels]

    def _category_key(self, label: str) -> str | None:
        return next((k for k, v in catalog.CATEGORY_LABELS.items() if v == label), None)

    def category(self) -> str:
        return self._spawn_cat_var.get()

    def set_category(self, label: str) -> None:
        self._spawn_cat_var.set(label)
        self._refresh_spawn_tree()

    def _seamless_save(self) -> bool:
        path = self._get_save_path()
        return path is not None and Path(path).suffix.lower() == ".co2"

    # --- Slots ------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = [
            f"Slot {i + 1} - {c.name}" if c else f"Slot {i + 1} - Empty"
            for i, c in enumerate(save.characters)
        ]
        self._slot_combo.configure(values=options)
        if not (
            0 <= self._current_slot < len(options)
            and save.characters[self._current_slot]
        ):
            self._current_slot = next(
                (i for i, c in enumerate(save.characters) if c is not None), -1
            )
        self._slot_var.set(
            options[self._current_slot] if self._current_slot >= 0 else ""
        )
        self._spawn_cat_combo.configure(values=self.category_options())
        if self._spawn_cat_var.get() not in self.category_options():
            self._spawn_cat_var.set(_ALL)
        self._reload_inventory()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._reload_inventory()

    def _load_selected(self) -> None:
        val = self._slot_var.get()
        try:
            idx = int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return
        save = self._get_dsr_save()
        if save is None or save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._reload_inventory()

    def current_character(self):
        save = self._get_dsr_save()
        if save is None or self._current_slot < 0:
            return None
        return save.characters[self._current_slot]

    # --- Inventory list ---------------------------------------------------- #

    def _reload_inventory(self) -> None:
        char = self.current_character()
        self._all_items = []
        if char is not None:
            for item in char.iter_items():
                if (item.category, item.item_id) in catalog.PLACEHOLDERS:
                    continue
                hit = catalog.lookup(item.category, item.item_id)
                cat = (
                    catalog.CATEGORY_LABELS.get(hit[0]["category"], "?") if hit else "?"
                )
                self._all_items.append(
                    (
                        item.slot_index,
                        catalog.display_name(item.category, item.item_id),
                        cat,
                        item.quantity,
                        item.category,
                        item.item_id,
                    )
                )
        if self._spawn_seamless != self._seamless_save() or not self._visible_spawn:
            self.parent.after(0, self._refresh_spawn_tree)
        self._refresh_inv_tree()

    def inventory_rows(self, query: str = "", category: str = _ALL) -> list[tuple]:
        return [
            r
            for r in self._all_items
            if (category == _ALL or r[2] == category)
            and (not query or query in r[1].lower())
        ]

    def row_for(self, slot: int) -> tuple | None:
        return next((r for r in self._all_items if r[0] == slot), None)

    def _refresh_inv_tree(self) -> None:
        selected = {str(s) for s in self._inv_tree.selection()} | {
            str(s) for s in self.last_offsets
        }
        self._inv_tree.delete(*self._inv_tree.get_children())
        rows = self.inventory_rows(
            self._inv_search_var.get().strip().lower(), self._inv_cat_var.get()
        )
        col = {"name": 1, "cat": 2, "qty": 3, "slot": 0}.get(self._sort_col or "")
        if col is not None:
            rows = sorted(rows, key=lambda r: r[col], reverse=not self._sort_asc)
        for slot, name, cat, qty, _t, _i in rows:
            self._inv_tree.insert(
                "", "end", iid=str(slot), values=(name, cat, qty, slot)
            )
        keep = [iid for iid in self._inv_tree.get_children() if iid in selected]
        if keep:
            self._inv_tree.selection_set(keep)
        self._count_label.configure(text=f"{len(self._all_items)} items")
        self._on_inv_select(None)

    def _sort_by(self, col: str) -> None:
        self._sort_asc = not self._sort_asc if self._sort_col == col else True
        self._sort_col = col
        self._refresh_inv_tree()

    def selected_offsets(self) -> list[int]:
        return [int(i) for i in self._inv_tree.selection()]

    def edit_options(self, slot: int) -> dict:
        """What one inventory row allows: limits, infusion variants, level."""
        row = self.row_for(slot)
        hit = catalog.lookup(row[4], row[5]) if row else None
        if hit is None:
            return {}
        entry, level = hit
        return {
            "item": entry,
            "level": level,
            "limits": catalog.limits(entry),
            "quantity": entry["max_quantity"] > 1 and not entry["spell"],
            "upgrade": entry["max_upgrade"] > 0,
            "variants": [v for v in catalog.infusion_variants(entry) if v["infusion"]]
            if entry["infusion"]
            else [],
        }

    def applicable_edits(self, slots: list[int]) -> dict[str, bool]:
        """Which edits apply: one row enables what it supports, several rows
        enable everything (each item is capped or skipped on its own)."""
        opts = self.edit_options(slots[0]) if len(slots) == 1 else {}
        if opts:
            edits = {
                "quantity": opts["quantity"],
                "upgrade": opts["upgrade"],
                "infusion": len(opts["variants"]) > 1,
                "remove": True,
            }
        else:
            edits = dict.fromkeys(
                ("quantity", "upgrade", "infusion", "remove"), len(slots) > 1
            )
        return edits

    def _apply_edit_states(self) -> None:
        edits = self.applicable_edits(self.selected_offsets())
        for widget, key in (
            (self._edit_qty_entry, "quantity"),
            (self._set_qty_btn, "quantity"),
            (self._edit_upg_entry, "upgrade"),
            (self._set_upg_btn, "upgrade"),
            (self._edit_inf_combo, "infusion"),
            (self._set_inf_btn, "infusion"),
            (self._remove_btn, "remove"),
        ):
            enable(widget, edits[key])

    def _on_inv_select(self, _event) -> None:
        self._apply_edit_states()
        slots = self.selected_offsets()
        if len(slots) != 1:
            self._edit_info.configure(
                text=f"{len(slots)} items selected" if slots else ""
            )
            return
        opts = self.edit_options(slots[0])
        row = self.row_for(slots[0])
        if not opts or row is None:
            self._edit_info.configure(text="Unknown item")
            return
        self._edit_qty_var.set(str(row[3]))
        self._edit_upg_var.set(str(opts["level"]))
        if opts["variants"]:
            self._edit_inf_combo.configure(
                values=[v["infusion"] for v in opts["variants"]]
            )
            self._edit_inf_var.set(opts["item"]["infusion"])
        lim = opts["limits"]
        info = [row[1]]
        if opts["quantity"]:
            info.append(f"max {lim.max_quantity}")
        if lim.max_upgrade:
            info.append(f"max +{lim.max_upgrade}")
        char = self.current_character()
        if char is not None and slots[0] in char.equipped_slots():
            info.append("equipped")
        self._edit_info.configure(text=", ".join(info))

    # --- Batch edits ------------------------------------------------------- #

    def _read_and(self, var: tk.StringVar, what: str, action) -> None:
        try:
            value = int(var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value", f"{what} must be a whole number.", parent=self.parent
            )
            return
        action(self.selected_offsets(), value)

    def _begin(self, slots: list[int], parent):
        if not slots:
            CTkMessageBox.showwarning(
                "No Selection", "Select one or more items first.", parent=parent
            )
            return None, None, None
        if _game_blocks_write(parent):
            return None, None, None
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        char = self.current_character()
        if save is None or save_path is None or char is None:
            return None, None, None
        return save, save_path, char

    def _finish(self, save, save_path, op: str, message: str, changed: int) -> bool:
        if not changed:
            self._show_toast(message)
            return False
        try:
            _backup_and_save(save, save_path, f"{op}_slot_{self._current_slot + 1}")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)
            return False
        self._reload_inventory()
        self._show_toast(message)
        for listener in list(self.listeners):
            listener()
        return True

    def set_quantity(self, slots: list[int], quantity: int, parent=None) -> bool:
        parent = parent or self.parent
        save, save_path, char = self._begin(slots, parent)
        if char is None:
            return False
        changed, capped, skipped = 0, 0, []
        for slot in slots:
            opts = self.edit_options(slot)
            if not opts or not opts["quantity"]:
                skipped.append(
                    self.row_for(slot)[1] if self.row_for(slot) else str(slot)
                )
                continue
            qty = max(1, min(quantity, opts["limits"].max_quantity))
            capped += qty != quantity
            item = char.read_item(slot)
            item.quantity = qty
            char.write_item(slot, item)
            changed += 1
        self.last_offsets = list(slots)
        return self._finish(
            save,
            save_path,
            "dsr_set_quantity",
            _summary(f"Set quantity on {changed} item(s)", changed, skipped, capped),
            changed,
        )

    def set_upgrade(self, slots: list[int], level: int, parent=None) -> bool:
        parent = parent or self.parent
        save, save_path, char = self._begin(slots, parent)
        if char is None:
            return False
        changed, capped, skipped = 0, 0, []
        for slot in slots:
            opts = self.edit_options(slot)
            if not opts or not opts["upgrade"]:
                skipped.append(
                    self.row_for(slot)[1] if self.row_for(slot) else str(slot)
                )
                continue
            entry = opts["item"]
            lvl = max(0, min(level, entry["max_upgrade"]))
            capped += lvl != level
            char.set_item_id(slot, catalog.item_id_at(entry, lvl))
            changed += 1
        if changed:
            char.calibrate_weapon_level()
        self.last_offsets = list(slots)
        return self._finish(
            save,
            save_path,
            "dsr_set_upgrade",
            _summary(f"Set upgrade on {changed} item(s)", changed, skipped, capped),
            changed,
        )

    def set_infusion(self, slots: list[int], infusion: str, parent=None) -> bool:
        parent = parent or self.parent
        save, save_path, char = self._begin(slots, parent)
        if char is None:
            return False
        changed, capped, skipped = 0, 0, []
        for slot in slots:
            opts = self.edit_options(slot)
            target = next(
                (
                    v
                    for v in (opts or {}).get("variants", [])
                    if v["infusion"] == infusion
                ),
                None,
            )
            row = self.row_for(slot)
            if target is None:
                skipped.append(row[1] if row else str(slot))
                continue
            level = min(opts["level"], target["max_upgrade"])
            capped += level != opts["level"]
            # A new path has its own durability (Crystal is a tenth).
            char.set_item_id(
                slot, catalog.item_id_at(target, level), durability=target["durability"]
            )
            changed += 1
        if changed:
            char.calibrate_weapon_level()
        self.last_offsets = list(slots)
        return self._finish(
            save,
            save_path,
            "dsr_set_infusion",
            _summary(
                f"Infused {changed} weapon(s) {infusion}", changed, skipped, capped
            ),
            changed,
        )

    def remove_entries(self, slots: list[int], parent=None) -> bool:
        parent = parent or self.parent
        save, save_path, char = self._begin(slots, parent)
        if char is None:
            return False
        equipped = char.equipped_slots()
        targets = [s for s in slots if s not in equipped]
        skipped = [
            f"{self.row_for(s)[1]} (equipped)"
            for s in slots
            if s in equipped and self.row_for(s)
        ]
        if not targets:
            CTkMessageBox.showwarning(
                "Equipped",
                "The selected items are equipped. Unequip them in game first.",
                parent=parent,
            )
            return False
        what = (
            self.row_for(targets[0])[1]
            if len(targets) == 1
            else f"{len(targets)} items"
        )
        if not CTkMessageBox.askyesno("Remove", f"Remove {what}?", parent=parent):
            return False
        for slot in targets:
            char.remove_item(slot)
        char.calibrate_weapon_level()
        self.last_offsets = []
        return self._finish(
            save,
            save_path,
            "dsr_remove_items",
            _summary(f"Removed {len(targets)} item(s)", len(targets), skipped),
            len(targets),
        )

    def _repair_all(self) -> None:
        save, save_path, char = self._begin([0], self.parent)
        if char is None:
            return
        repaired = 0
        for item in char.iter_items():
            hit = catalog.lookup(item.category, item.item_id)
            if hit and hit[0]["durability"] and item.durability < hit[0]["durability"]:
                item.durability = hit[0]["durability"]
                char.write_item(item.slot_index, item)
                repaired += 1
        self._finish(
            save,
            save_path,
            "dsr_repair_all",
            f"Repaired {repaired} item(s)."
            if repaired
            else "Everything is at full durability.",
            repaired,
        )

    # --- Spawner ----------------------------------------------------------- #

    def _refresh_spawn_tree(self) -> None:
        if self._spawn_job is not None:
            self.parent.after_cancel(self._spawn_job)
            self._spawn_job = None
        self._spawn_tree.delete(*self._spawn_tree.get_children())
        self._spawn_rows.clear()
        self._spawn_variants = []
        self.select_item(None)
        self._spawn_seamless = self._seamless_save()
        query = self._spawn_search_var.get().strip().lower()
        cat_key = self._category_key(self._spawn_cat_var.get())
        # A search also finds cut content (labelled), so it can be found by name.
        show_cut = self._show_cut.get() or bool(query)

        def label(item: dict) -> str:
            return item["name"] if item["obtainable"] else f"{item['name']} (cut)"

        rows: list[tuple[str, dict, list[dict]]] = []
        seen_families: set[int] = set()
        for item in catalog.items():
            if item["hidden"] or (item["type"], item["id"]) in catalog.PLACEHOLDERS:
                continue
            if item["seamless"] and not self._spawn_seamless:
                continue
            if cat_key and item["category"] != cat_key:
                continue
            if not show_cut and not item["obtainable"]:
                continue
            if not item["infusion"]:
                if not query or query in item["name"].lower():
                    rows.append((label(item), item, []))
                continue
            family = item["id"] // catalog.WEAPON_FAMILY
            if family in seen_families:
                continue
            seen_families.add(family)
            variants = [
                v
                for v in catalog.infusion_variants(item)
                if show_cut or v["obtainable"]
            ]
            matching = [v for v in variants if not query or query in v["name"].lower()]
            if not matching:
                continue
            first = matching[0] if query else variants[0]
            ordered = [first] + [v for v in variants if v is not first]
            rows.append(
                (label(variants[0]), first, ordered if len(ordered) > 1 else [])
            )
        self._visible_spawn = rows
        self._insert_spawn_batch(rows, 0)

    _SPAWN_BATCH = 300

    def _insert_spawn_batch(self, rows: list, start: int) -> None:
        end = min(start + self._SPAWN_BATCH, len(rows))
        for text, item, variants in rows[start:end]:
            iid = self._spawn_tree.insert("", "end", values=(text,))
            self._spawn_rows[iid] = (item, variants)
        self._spawn_job = (
            self.parent.after(0, lambda: self._insert_spawn_batch(rows, end))
            if end < len(rows)
            else None
        )

    def visible_spawn_items(self) -> list[tuple[str, dict, list[dict]]]:
        return list(self._visible_spawn)

    def _on_spawn_select(self, _event) -> None:
        sel = self._spawn_tree.selection()
        if len(sel) != 1:
            self._spawn_variants = []
            self.select_item(None)
            if sel:
                self._spawn_info.configure(
                    text=f"{len(sel)} items selected; each is capped at its own limits"
                )
            return
        item, variants = self._spawn_rows[sel[0]]
        self._spawn_variants = variants
        if variants:
            self._spawn_inf_combo.configure(values=[v["infusion"] for v in variants])
            self._spawn_inf_var.set(item["infusion"])
        self.select_item(item)

    def _on_spawn_infusion(self, label: str) -> None:
        item = next((v for v in self._spawn_variants if v["infusion"] == label), None)
        if item is not None:
            self.select_item(item)

    def select_item(self, item: dict | None) -> None:
        self._selected_item = item
        if item is None or not self._spawn_variants:
            self._spawn_inf_var.set("")
        if item is None:
            self._spawn_info.configure(text="")
        else:
            lim = catalog.limits(item)
            info = [f"Max stack: {lim.max_quantity}"]
            if lim.max_upgrade:
                info.append(f"Max upgrade: +{lim.max_upgrade}")
            if item["key_item"]:
                info.append("Key item")
            if not item["obtainable"]:
                info.append("Cut content")
            self._spawn_info.configure(text="  ".join(info))
        self._apply_spawn_states()

    def _apply_spawn_states(self) -> None:
        item = self._selected_item
        single = len(self._spawn_tree.selection()) == 1 and item is not None
        enable(self._spawn_qty_entry, not single or item["max_quantity"] > 1)
        enable(self._spawn_upg_entry, not single or item["max_upgrade"] > 0)
        enable(self._spawn_inf_combo, single and bool(self._spawn_variants))

    def _spawn_selected(self) -> None:
        sel = self._spawn_tree.selection()
        if len(sel) == 1 and self._selected_item is not None:
            items = [self._selected_item]
        else:
            items = [self._spawn_rows[i][0] for i in sel]
        self.spawn_items(items)

    def _spawn_all(self) -> None:
        self.spawn_items([item for _, item, _ in self._visible_spawn])

    def spawn_items(
        self,
        items: list[dict],
        quantity: int | None = None,
        upgrade: int | None = None,
        parent=None,
    ) -> bool:
        """Spawn catalog items with one backup and save. Quantity and upgrade
        (read from the spawner's fields when not given) are capped per item."""
        parent = parent or self.parent
        if not items:
            CTkMessageBox.showwarning(
                "No Item", "Select one or more items to spawn first.", parent=parent
            )
            return False
        save, save_path, char = self._begin([0], parent)
        if char is None:
            return False
        try:
            quantity = int(self._spawn_qty_var.get()) if quantity is None else quantity
            upgrade = int(self._spawn_upg_var.get()) if upgrade is None else upgrade
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Value",
                "Quantity and upgrade must be whole numbers.",
                parent=parent,
            )
            return False
        if len(items) > _CONFIRM_SPAWN_COUNT and not CTkMessageBox.askyesno(
            "Spawn Items", f"Spawn {len(items)} items?", parent=parent
        ):
            return False
        cut = [i["name"] for i in items if not i["obtainable"]]
        if cut and not CTkMessageBox.askyesno(
            "Cut Content",
            f"{', '.join(cut[:5])}{' and more' if len(cut) > 5 else ''} cannot be "
            "obtained in the game. Cut items can behave oddly and are likely to be "
            "flagged online.\n\nSpawn anyway?",
            parent=parent,
        ):
            return False

        held = {(i.category, i.item_id) for i in char.iter_items()}
        has_estus = any(
            t == catalog.TYPE_GOODS and i in catalog.ESTUS_IDS for t, i in held
        )
        spawned, capped, skipped = [], 0, []
        for item in items:
            lim = catalog.limits(item)
            if catalog.is_single(item):
                if has_estus:
                    skipped.append(f"{item['name']} (already has an Estus Flask)")
                    continue
                has_estus = True
            level = max(0, min(upgrade, lim.max_upgrade))
            capped += lim.max_upgrade > 0 and level != upgrade
            qty = max(1, min(quantity, lim.max_quantity))
            capped += lim.max_quantity > 1 and qty != quantity
            slot = char.add_item(
                item["type"],
                catalog.item_id_at(item, level),
                qty,
                sort_key=catalog.sort_key(item, level),
                durability=lim.durability,
                max_quantity=lim.max_quantity,
                key_item=item["key_item"],
            )
            if slot < 0:
                skipped.append(f"{item['name']} (inventory full)")
                continue
            spawned.append(
                catalog.display_name(item["type"], catalog.item_id_at(item, level))
            )
        if spawned:
            char.calibrate_weapon_level()
        done = (
            f"Spawned {spawned[0]}"
            if len(spawned) == 1
            else f"Spawned {len(spawned)} items"
        )
        return self._finish(
            save,
            save_path,
            "dsr_spawn_items",
            _summary(done, len(spawned), skipped, capped),
            len(spawned),
        )

    # --- Popups ------------------------------------------------------------ #

    def _require_character(self) -> bool:
        if self.current_character() is None:
            CTkMessageBox.showwarning(
                "No Character", "Load a character first.", parent=self.parent
            )
            return False
        return True

    def _open_picker(self) -> None:
        if self._require_character():
            from er_save_manager.games.DSR.icon_browser import DSRIconBrowser

            DSRIconBrowser(self.parent.winfo_toplevel(), self)

    def _open_editor(self) -> None:
        if self._require_character():
            from er_save_manager.games.DSR.visual_inventory import DSRVisualInventory

            DSRVisualInventory(self.parent.winfo_toplevel(), self)
