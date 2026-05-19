"""
DSR Inventory Editor Tab

Left: current inventory. Right: item spawner.
All mutations (add, remove, repair) immediately create a backup then write the file.
No separate Save button.
"""

from __future__ import annotations

import json
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox

if TYPE_CHECKING:
    from er_save_manager.games.DSR.save import DSRSave

_DATA_DIR = Path(__file__).parent / "data"

_DB: dict | None = None
_LOOKUP: dict[tuple[int, int], dict] | None = None


def _ensure_db() -> tuple[dict, dict]:
    global _DB, _LOOKUP
    if _DB is None:
        _DB = json.loads((_DATA_DIR / "items.json").read_text(encoding="utf-8"))
        _LOOKUP = {}
        for cat_items in _DB.values():
            for item in cat_items:
                type_num = int(item["Type"], 16) // 0x10000000
                base_id = int(item["Id"], 16)
                item.setdefault("_cat", "")
                _LOOKUP[(type_num, base_id)] = item
        for cat_key, cat_items in _DB.items():
            for item in cat_items:
                item["_cat"] = cat_key
    return _DB, _LOOKUP  # type: ignore[return-value]


_CAT_LABELS: dict[str, str] = {
    "weapon_items": "Weapons",
    "ring_items": "Rings",
    "armor_items": "Armor",
    "key_items": "Key Items",
    "usable_items": "Usables",
    "ammunition_items": "Ammo",
    "material_items": "Materials",
    "magic_items": "Spells",
    "specials": "Special",
}

_INFUSION_NAMES = [
    "Standard",
    "Crystal",
    "Lightning",
    "Raw",
    "Magic",
    "Enchanted",
    "Divine",
    "Occult",
    "Fire",
    "Chaos",
]


def _resolve_name(type_num: int, base_id: int, item_id: int) -> str:
    _, lookup = _ensure_db()
    entry = lookup.get((type_num, base_id))
    if entry is None:
        return f"Unknown (type={type_num:#x} id={item_id:#x})"
    name = entry["Name"]
    if type_num == 0:
        ul = item_id % 100
        inf_idx = ((item_id - ul) % 1000) // 100
        if ul > 0:
            name += f" +{ul}"
        if inf_idx > 0:
            name += f" ({_INFUSION_NAMES[inf_idx]})"
    return name


def _backup_and_save(dsr_save: DSRSave, save_path: Path, operation: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=operation, save=None)
    dsr_save.save_to_file(save_path)


class DSRInventoryTab:
    """Inventory viewer and item spawner for a DSR character slot."""

    def __init__(
        self,
        parent: tk.Widget,
        get_dsr_save: Callable[[], DSRSave | None],
        get_save_path: Callable[[], Path | None],
        show_toast: Callable[[str], None],
    ) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._selected_slot_idx = -1

    def setup_ui(self) -> None:
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # Header matching ER editor style
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header, text="Inventory Editor", font=("Segoe UI", 16, "bold")
        ).pack(side="left")

        ctk.CTkFrame(header, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )

        ctk.CTkLabel(header, text="Slot:").pack(side="left", padx=(0, 6))
        self._slot_var = tk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header,
            variable=self._slot_var,
            values=[],
            state="readonly",
            width=220,
        )
        self._slot_combo.pack(side="left", padx=(0, 8))
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="left", padx=4
        )
        self._count_label = ctk.CTkLabel(
            header, text="", font=("Segoe UI", 10), text_color=("gray40", "gray70")
        )
        self._count_label.pack(side="right", padx=8)

        # Main two-panel area
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)

        self._build_inventory_panel(main)
        self._build_spawner_panel(main)

    def _build_inventory_panel(self, parent: tk.Widget) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="Current Inventory", font=("Segoe UI", 12, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(10, 4), padx=12, sticky="w")

        # Treeview (handles 500+ items without lag)
        tree_frame = tk.Frame(frame, bg="#2b2b2b")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._apply_treeview_style()

        self._inv_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "cat", "qty", "slot"),
            show="headings",
            style="DSR.Treeview",
            selectmode="browse",
        )
        self._inv_tree.heading("name", text="Item")
        self._inv_tree.heading("cat", text="Type")
        self._inv_tree.heading("qty", text="Qty")
        self._inv_tree.heading("slot", text="Slot")
        self._inv_tree.column("name", width=220, minwidth=150)
        self._inv_tree.column("cat", width=80, minwidth=60)
        self._inv_tree.column("qty", width=45, minwidth=40, anchor="center")
        self._inv_tree.column("slot", width=45, minwidth=40, anchor="center")
        self._inv_tree.grid(row=0, column=0, sticky="nsew")
        self._inv_tree.bind("<<TreeviewSelect>>", self._on_inv_select)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._inv_tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._inv_tree.configure(yscrollcommand=sb.set)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 10))
        ctk.CTkButton(
            btn_row,
            text="Remove Selected",
            command=self._remove_selected,
            width=130,
            fg_color=("#a03030", "#802020"),
            hover_color=("#c03030", "#a02020"),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row,
            text="Repair All Items",
            command=self._repair_all,
            width=120,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row,
            text="Refresh",
            command=self._refresh_inventory,
            width=80,
        ).pack(side="left", padx=4)

    def _build_spawner_panel(self, parent: tk.Widget) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Add Item", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, pady=(10, 6), padx=12, sticky="w"
        )

        filter_row = ctk.CTkFrame(frame, fg_color="transparent")
        filter_row.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        filter_row.grid_columnconfigure(1, weight=1)

        db, _ = _ensure_db()
        cat_options = ["All"] + [_CAT_LABELS.get(k, k) for k in db.keys()]
        self._cat_var = tk.StringVar(value="All")
        ctk.CTkComboBox(
            filter_row,
            variable=self._cat_var,
            values=cat_options,
            state="readonly",
            width=110,
            command=lambda _: self._rebuild_item_list(),
        ).grid(row=0, column=0, padx=(0, 6))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._rebuild_item_list())
        ctk.CTkEntry(
            filter_row,
            textvariable=self._search_var,
            placeholder_text="Search...",
            width=130,
        ).grid(row=0, column=1, sticky="ew")

        tree_frame = tk.Frame(frame, bg="#2b2b2b")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._spawn_tree = ttk.Treeview(
            tree_frame,
            columns=("name",),
            show="headings",
            style="DSR.Treeview",
            selectmode="browse",
        )
        self._spawn_tree.heading("name", text="Item Name")
        self._spawn_tree.column("name", width=220)
        self._spawn_tree.grid(row=0, column=0, sticky="nsew")
        self._spawn_tree.bind("<<TreeviewSelect>>", self._on_spawn_select)

        sb2 = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._spawn_tree.yview
        )
        sb2.grid(row=0, column=1, sticky="ns")
        self._spawn_tree.configure(yscrollcommand=sb2.set)

        cfg = ctk.CTkFrame(frame, fg_color="transparent")
        cfg.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 4))
        cfg.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(cfg, text="Qty:", width=30).grid(
            row=0, column=0, padx=(0, 2), pady=4
        )
        self._qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(cfg, textvariable=self._qty_var, width=50, justify="center").grid(
            row=0, column=1, padx=(0, 8)
        )
        self._upg_label = ctk.CTkLabel(cfg, text="Upgrade:", width=60)
        self._upg_label.grid(row=0, column=2, padx=(0, 2))
        self._upg_var = tk.StringVar(value="0")
        self._upg_entry = ctk.CTkEntry(
            cfg, textvariable=self._upg_var, width=40, justify="center"
        )
        self._upg_entry.grid(row=0, column=3, padx=(0, 8))

        self._inf_label = ctk.CTkLabel(cfg, text="Infusion:", width=60)
        self._inf_label.grid(row=0, column=4, padx=(0, 2))
        self._inf_var = tk.StringVar(value="Standard")
        self._inf_combo = ctk.CTkComboBox(
            cfg,
            variable=self._inf_var,
            values=_INFUSION_NAMES,
            state="readonly",
            width=100,
        )
        self._inf_combo.grid(row=0, column=5)

        ctk.CTkButton(
            frame,
            text="Add to Inventory",
            command=self._add_item,
            width=180,
        ).grid(row=4, column=0, pady=(2, 10))

        self._spawn_items: dict[str, dict] = {}
        self._selected_db_item: dict | None = None
        self._rebuild_item_list()

    # --- Treeview style ------------------------------------------------------- #

    @staticmethod
    def _apply_treeview_style() -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "DSR.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=22,
            borderwidth=0,
        )
        style.configure(
            "DSR.Treeview.Heading", background="#3b3b3b", foreground="white"
        )
        style.map("DSR.Treeview", background=[("selected", "#5a4a7a")])

    # --- Refresh -------------------------------------------------------------- #

    def refresh(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            self._slot_combo.configure(values=[])
            return
        options = []
        for i, char in enumerate(save.characters):
            label = f"Slot {i + 1} - {char.name}" if char else f"Slot {i + 1} - Empty"
            options.append(label)
        self._slot_combo.configure(values=options)
        self._slot_var.set(options[0] if options else "")

    def load_slot(self, slot_idx: int) -> None:
        save = self._get_dsr_save()
        if save is None:
            return
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._refresh_inventory()

    # --- Internal helpers ----------------------------------------------------- #

    def _load_selected(self) -> None:
        idx = self._slot_idx()
        if idx < 0:
            return
        save = self._get_dsr_save()
        if save is None:
            CTkMessageBox.showwarning(
                "No Save", "No DSR save loaded.", parent=self.parent
            )
            return
        if save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._refresh_inventory()

    def _refresh_inventory(self) -> None:
        if self._current_slot < 0:
            return
        save = self._get_dsr_save()
        char = save.characters[self._current_slot] if save else None
        if char is None:
            return
        _, lookup = _ensure_db()
        self._inv_tree.delete(*self._inv_tree.get_children())
        items = char.iter_items()
        for item in items:
            name = _resolve_name(item.category, item.base_item_id, item.item_id)
            db_entry = lookup.get((item.category, item.base_item_id))
            cat_label = (
                _CAT_LABELS.get(db_entry.get("_cat", ""), "?") if db_entry else "?"
            )
            self._inv_tree.insert(
                "",
                "end",
                iid=str(item.slot_index),
                values=(name, cat_label, item.quantity, item.slot_index),
            )
        self._count_label.configure(text=f"{len(items)} / 2048 slots")
        self._selected_slot_idx = -1

    def _rebuild_item_list(self) -> None:
        db, _ = _ensure_db()
        query = self._search_var.get().lower()
        cat_label = self._cat_var.get()
        cat_key = next((k for k, v in _CAT_LABELS.items() if v == cat_label), None)
        self._spawn_tree.delete(*self._spawn_tree.get_children())
        self._spawn_items.clear()
        for db_cat, cat_items in db.items():
            if cat_key and db_cat != cat_key:
                continue
            for item in cat_items:
                if query and query not in item["Name"].lower():
                    continue
                iid = f"{db_cat}:{item['Id']}"
                self._spawn_items[iid] = item
                self._spawn_tree.insert("", "end", iid=iid, values=(item["Name"],))
        self._selected_db_item = None

    def _on_inv_select(self, _event=None) -> None:
        sel = self._inv_tree.selection()
        self._selected_slot_idx = int(sel[0]) if sel else -1

    def _on_spawn_select(self, _event=None) -> None:
        sel = self._spawn_tree.selection()
        if not sel:
            self._selected_db_item = None
            return
        item = self._spawn_items.get(sel[0])
        self._selected_db_item = item
        if item is None:
            return
        type_num = int(item["Type"], 16) // 0x10000000
        is_weapon = type_num == 0
        max_up = item.get("MaxUpgrade")
        can_infuse = bool(item.get("CanInfuse")) and is_weapon
        upg_state = "normal" if (is_weapon and max_up) else "disabled"
        self._upg_entry.configure(state=upg_state)
        self._inf_combo.configure(state="readonly" if can_infuse else "disabled")
        if not can_infuse:
            self._inf_var.set("Standard")

    def _remove_selected(self) -> None:
        if self._selected_slot_idx < 0:
            CTkMessageBox.showwarning(
                "No Selection", "Select an item to remove.", parent=self.parent
            )
            return
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or self._current_slot < 0 or save_path is None:
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        item = char.read_item(self._selected_slot_idx)
        _, lookup = _ensure_db()
        db_entry = lookup.get((item.category, item.base_item_id))
        name = db_entry["Name"] if db_entry else f"slot {self._selected_slot_idx}"
        if not CTkMessageBox.askyesno(
            "Confirm Remove", f"Remove {name}?", parent=self.parent
        ):
            return
        char.remove_item(self._selected_slot_idx)
        try:
            _backup_and_save(
                save, save_path, f"inventory_remove_slot_{self._current_slot + 1}"
            )
            self._refresh_inventory()
            self._show_toast(f"Removed {name}. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _add_item(self) -> None:
        db_item = self._selected_db_item
        if db_item is None:
            CTkMessageBox.showwarning(
                "No Item", "Select an item from the list.", parent=self.parent
            )
            return
        if self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Slot", "Load a character slot first.", parent=self.parent
            )
            return
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        try:
            qty = int(self._qty_var.get())
            upg = int(self._upg_var.get())
            inf_name = self._inf_var.get()
            inf = _INFUSION_NAMES.index(inf_name) if inf_name in _INFUSION_NAMES else 0
        except ValueError as exc:
            CTkMessageBox.showerror("Invalid Value", str(exc), parent=self.parent)
            return
        max_up = db_item.get("MaxUpgrade") or 0
        if upg > max_up:
            CTkMessageBox.showerror(
                "Invalid Upgrade",
                f"Max upgrade for this item is +{max_up}.",
                parent=self.parent,
            )
            return
        slot = char.add_item(db_item, quantity=qty, upgrade=upg, infusion=inf)
        if slot < 0:
            CTkMessageBox.showerror(
                "Inventory Full", "No empty slots available.", parent=self.parent
            )
            return
        try:
            _backup_and_save(
                save, save_path, f"inventory_add_slot_{self._current_slot + 1}"
            )
            self._refresh_inventory()
            self._show_toast(f"Added {db_item['Name']}. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _repair_all(self) -> None:
        """Set all items with a durability value back to their base durability."""
        if self._current_slot < 0:
            CTkMessageBox.showwarning(
                "No Slot", "Load a character slot first.", parent=self.parent
            )
            return
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            return
        char = save.characters[self._current_slot]
        if char is None:
            return
        if not CTkMessageBox.askyesno(
            "Repair All",
            "Restore durability on all items?\n\nA backup will be created.",
            parent=self.parent,
        ):
            return
        _, lookup = _ensure_db()
        repaired = 0
        for item in char.iter_items():
            if item.durability == 0:
                continue
            db_entry = lookup.get((item.category, item.base_item_id))
            if db_entry and db_entry.get("Durability"):
                max_dur = int(db_entry["Durability"])
                # Crystal infusion halves base durability
                if item.infusion == 1:
                    max_dur = max_dur // 10
                if item.durability < max_dur:
                    item.durability = max_dur
                    char.write_item(item.slot_index, item)
                    repaired += 1
        if repaired == 0:
            self._show_toast("All items already at full durability.")
            return
        try:
            _backup_and_save(
                save, save_path, f"repair_all_slot_{self._current_slot + 1}"
            )
            self._refresh_inventory()
            self._show_toast(f"Repaired {repaired} items. Backup created.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
