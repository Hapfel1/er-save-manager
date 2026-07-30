"""
Character Loadout Tab.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.editors.save_type_utils import confirm_convergence_mismatch
from er_save_manager.parser import character_loadout_ops
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.settings import Settings, get_loadouts_path
from er_save_manager.ui.utils import bind_mousewheel, pick_file

_SECTIONS = ("stats", "info", "equipment", "inventory")
_SECTION_LABELS = {
    "stats": "Character Stats",
    "info": "Character Info",
    "equipment": "Equipment Loadout",
    "inventory": "Inventory Loadout",
}


def _center_over(window, parent, w: int, h: int) -> None:
    window.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    window.geometry(f"{w}x{h}+{x}+{y}")


class _CategoryChecklistDialog(ctk.CTkToplevel):


    def __init__(
        self,
        parent,
        title: str,
        apply_mode: bool,
        entry: dict | None,
        equipment_names: list[str],
        inventory_names: list[str],
        on_confirm,
    ):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self._on_confirm = on_confirm
        self._check_vars: dict[str, tk.BooleanVar] = {}
        self._source_vars: dict[str, tk.StringVar] = {}
        self._name_vars: dict[str, tk.StringVar] = {}
        entry = entry or {}

        _center_over(self, parent, 400, 380)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill=ctk.BOTH, expand=True, padx=15, pady=15)

        for section in _SECTIONS:
            present = section in entry and entry[section] is not None
            if apply_mode and not present:
                continue

            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill=ctk.X, pady=4)

            checked = present if (apply_mode or entry) else True
            var = tk.BooleanVar(value=checked)
            self._check_vars[section] = var
            ctk.CTkCheckBox(
                row, text=_SECTION_LABELS[section], variable=var, width=170
            ).pack(side=ctk.LEFT)

            if apply_mode or section not in ("equipment", "inventory"):
                continue

            names = equipment_names if section == "equipment" else inventory_names
            source_var = tk.StringVar(value="current")
            name_var = tk.StringVar(value=names[0] if names else "(none saved)")
            self._source_vars[section] = source_var
            self._name_vars[section] = name_var

            src_row = ctk.CTkFrame(frame, fg_color="transparent")
            src_row.pack(fill=ctk.X, padx=(24, 0), pady=(0, 4))
            ctk.CTkRadioButton(
                src_row,
                text="Current Slot",
                variable=source_var,
                value="current",
                width=110,
            ).pack(side=ctk.LEFT)
            ctk.CTkRadioButton(
                src_row, text="From DB:", variable=source_var, value="db", width=80
            ).pack(side=ctk.LEFT, padx=(10, 4))
            ctk.CTkComboBox(
                src_row,
                values=names or ["(none saved)"],
                variable=name_var,
                width=150,
                state="readonly",
            ).pack(side=ctk.LEFT)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill=ctk.X, padx=15, pady=(0, 15))
        ctk.CTkButton(btn_row, text="Confirm", command=self._confirm, width=120).pack(
            side=ctk.LEFT, padx=(0, 6)
        )
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy, width=100).pack(
            side=ctk.LEFT
        )

    def _confirm(self):
        result = {section: var.get() for section, var in self._check_vars.items()}
        for section, source_var in self._source_vars.items():
            source = source_var.get()
            name = self._name_vars[section].get()
            result[f"{section}_source"] = source
            result[f"{section}_db_name"] = None if name.startswith("(none") else name
        self.destroy()
        self._on_confirm(result)


class _LoadoutDetailDialog(ctk.CTkToplevel):
    """Read-only scrollable view of everything captured in a loadout."""

    def __init__(self, parent, name: str, summary_text: str):
        super().__init__(parent)
        self.title(f"Loadout: {name}")
        self.resizable(True, True)
        self.transient(parent)

        _center_over(self, parent, 480, 520)
        self.grab_set()

        box = ctk.CTkTextbox(self, font=("Consolas", 11), wrap="word")
        box.pack(fill=ctk.BOTH, expand=True, padx=12, pady=(12, 6))
        box.insert("1.0", summary_text)
        box.configure(state="disabled")

        ctk.CTkButton(self, text="Close", command=self.destroy, width=100).pack(
            pady=(0, 12)
        )


class CharacterLoadoutTab:
    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_toast_callback,
        equipment_editor,
        inventory_editor,
        set_char_slot_callback,
    ):
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_toast = show_toast_callback
        self.equipment_editor = equipment_editor
        self.inventory_editor = inventory_editor
        self.set_char_slot = set_char_slot_callback

        self.current_slot: int | None = None
        self.slot_combo = None
        self.loaded_label = None
        self.db_listbox = None
        self._db_names: list[str] = []

    # ---- slot handling ----------------------------------------------------

    def _get_slot_display_names(self) -> list[str]:
        save_file = self.get_save_file()
        if not save_file:
            return [str(i) for i in range(1, 11)]

        profiles = None
        try:
            if save_file.user_data_10_parsed:
                profiles = save_file.user_data_10_parsed.profile_summary.profiles
        except Exception:
            pass

        names = []
        for i in range(10):
            char = save_file.characters[i]
            if char.is_empty():
                names.append(f"{i + 1} - Empty")
                continue
            char_name = "Unknown"
            if profiles and i < len(profiles):
                try:
                    char_name = profiles[i].character_name or "Unknown"
                except Exception:
                    pass
            names.append(f"{i + 1} - {char_name}")
        return names

    def refresh_slot_names(self):
        if self.slot_combo is not None:
            names = self._get_slot_display_names()
            self.slot_combo.configure(values=names)
            self.slot_combo.set(names[0])
            self.load_slot(silent=True)

    def load_slot(self, silent: bool = False):
        save_file = self.get_save_file()
        if not save_file:
            if not silent:
                CTkMessageBox.showwarning(
                    "No Save", "Please load a save file first.", parent=self.parent
                )
            return
        try:
            slot_idx = int(self.slot_combo.get().split(" - ")[0]) - 1
        except (ValueError, AttributeError):
            return
        if save_file.characters[slot_idx].is_empty():
            if not silent:
                CTkMessageBox.showwarning(
                    "Empty Slot", f"Slot {slot_idx + 1} is empty.", parent=self.parent
                )
            return
        self.current_slot = slot_idx
        self.loaded_label.configure(text=f"Loaded: Slot {slot_idx + 1}")

    # ---- ui -----------------------------------------------------------------

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ctk.CTkLabel(
            main_frame, text="Character Loadouts", font=("Segoe UI", 18, "bold")
        ).pack(pady=(15, 5), padx=15, anchor="w")
        ctk.CTkLabel(
            main_frame,
            text="Save and apply a combination of stats, info, equipment,"
            " and inventory as one named loadout.",
            font=("Segoe UI", 11),
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 12), padx=15, anchor="w")

        slot_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        slot_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        ctk.CTkLabel(slot_frame, text="Character Slot:", font=("Segoe UI", 11)).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        self.slot_combo = ctk.CTkComboBox(
            slot_frame,
            values=self._get_slot_display_names(),
            width=220,
            state="readonly",
            command=lambda _choice: self.load_slot(),
        )
        self.slot_combo.pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(
            slot_frame, text="Load Slot", command=self.load_slot, width=110
        ).pack(side=tk.LEFT, padx=(0, 12))
        self.loaded_label = ctk.CTkLabel(
            slot_frame,
            text="No slot loaded",
            font=("Segoe UI", 10),
            text_color=("gray50", "gray70"),
        )
        self.loaded_label.pack(side=tk.LEFT)

        # ---- inline loadout browser ----
        db_section = ctk.CTkFrame(
            main_frame, fg_color=("gray86", "gray17"), corner_radius=8
        )
        db_section.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))
        ctk.CTkLabel(
            db_section, text="Saved Loadouts", font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=12, pady=(10, 6))

        body = ctk.CTkFrame(db_section, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        lb_frame = ctk.CTkFrame(body, fg_color=("gray82", "gray14"), corner_radius=6)
        lb_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mode = ctk.get_appearance_mode()
        lb_bg = "#1a1a24" if mode == "Dark" else "#f0f0f0"
        lb_fg = "#d4d4e8" if mode == "Dark" else "#111111"
        lb_sel = "#7c4dac" if mode == "Dark" else "#b8a0d0"
        sb = tk.Scrollbar(lb_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.db_listbox = tk.Listbox(
            lb_frame,
            yscrollcommand=sb.set,
            font=("Consolas", 11),
            bg=lb_bg,
            fg=lb_fg,
            selectbackground=lb_sel,
            relief=tk.FLAT,
            borderwidth=0,
            activestyle="none",
        )
        self.db_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        sb.config(command=self.db_listbox.yview)
        bind_mousewheel(self.db_listbox)
        self.db_listbox.bind("<Double-Button-1>", lambda _e: self._view_selected())

        btn_col = ctk.CTkFrame(body, fg_color="transparent")
        btn_col.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        ctk.CTkButton(
            btn_col, text="New...", command=self._new_loadout, width=130
        ).pack(pady=2, fill=tk.X)
        ctk.CTkButton(
            btn_col, text="View", command=self._view_selected, width=130
        ).pack(pady=2, fill=tk.X)
        ctk.CTkButton(
            btn_col, text="Edit...", command=self._edit_selected, width=130
        ).pack(pady=2, fill=tk.X)
        ctk.CTkButton(
            btn_col, text="Apply", command=self._apply_selected, width=130
        ).pack(pady=2, fill=tk.X)
        ctk.CTkButton(
            btn_col,
            text="Delete",
            command=self._delete_selected,
            width=130,
            fg_color=("gray70", "gray35"),
        ).pack(pady=2, fill=tk.X)

        # ---- export / import / share, bottom of tab ----
        bottom_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        bottom_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        ctk.CTkButton(
            bottom_frame, text="Export JSON...", command=self.export_json, width=140
        ).pack(side=tk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            bottom_frame, text="Import JSON...", command=self.import_json, width=140
        ).pack(side=tk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            bottom_frame, text="Share Code...", command=self.share_code, width=130
        ).pack(side=tk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            bottom_frame, text="Import Code...", command=self.import_code, width=130
        ).pack(side=tk.LEFT)

        self.refresh_loadout_list()

    # ---- store --------------------------------------------------------------

    def _store_path(self) -> Path:
        return Settings._get_default_settings_path().parent / "character_loadouts.json"

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_store(self, store: dict) -> None:
        path = self._store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)

    def _equipment_names(self) -> list[str]:
        if not self.equipment_editor:
            return []
        return sorted(self.equipment_editor._read_loadout_store().keys())

    def _inventory_names(self) -> list[str]:
        return sorted(self._read_json(get_loadouts_path()).keys())

    # ---- browser / new / edit ------------------------------------------------

    def refresh_loadout_list(self):
        store = self._read_json(self._store_path())
        self._db_names = sorted(store.keys())
        if self.db_listbox is not None:
            self.db_listbox.delete(0, tk.END)
            for name in self._db_names:
                self.db_listbox.insert(tk.END, name)

    def _selected_db_name(self) -> str | None:
        if self.db_listbox is None:
            return None
        sel = self.db_listbox.curselection()
        if not sel:
            return None
        return self._db_names[sel[0]]

    def _view_selected(self):
        name = self._selected_db_name()
        if not name:
            CTkMessageBox.showwarning(
                "Selection", "Select a loadout first.", parent=self.parent
            )
            return
        store = self._read_json(self._store_path())
        entry = store.get(name)
        if entry is None:
            return
        _LoadoutDetailDialog(
            self.parent, name, self._format_loadout_summary(name, entry)
        )

    def _edit_selected(self):
        name = self._selected_db_name()
        if not name:
            CTkMessageBox.showwarning(
                "Selection", "Select a loadout first.", parent=self.parent
            )
            return
        self._edit_loadout(name)

    def _apply_selected(self):
        name = self._selected_db_name()
        if not name:
            CTkMessageBox.showwarning(
                "Selection", "Select a loadout first.", parent=self.parent
            )
            return
        self._apply_loadout(name)

    def _delete_selected(self):
        name = self._selected_db_name()
        if not name:
            CTkMessageBox.showwarning(
                "Selection", "Select a loadout first.", parent=self.parent
            )
            return
        if not CTkMessageBox.askyesno(
            "Delete Loadout", f"Delete loadout '{name}'?", parent=self.parent
        ):
            return
        store = self._read_json(self._store_path())
        store.pop(name, None)
        self._write_store(store)
        self.refresh_loadout_list()

    def _ask_text(self, title: str, prompt: str) -> str | None:
        result = [None]
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        _center_over(dialog, self.parent, 360, 140)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=prompt, font=("Segoe UI", 11)).pack(pady=(15, 6))
        var = tk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=var, width=280, justify="center")
        entry.pack(pady=(0, 12))
        entry.focus_set()

        def confirm(_event=None):
            result[0] = var.get().strip()
            dialog.destroy()

        entry.bind("<Return>", confirm)
        entry.bind("<Escape>", lambda _e: dialog.destroy())

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack()
        ctk.CTkButton(btn_row, text="OK", command=confirm, width=100).pack(
            side=tk.LEFT, padx=5
        )
        ctk.CTkButton(btn_row, text="Cancel", command=dialog.destroy, width=100).pack(
            side=tk.LEFT, padx=5
        )

        self.parent.wait_window(dialog)
        return result[0]

    def _new_loadout(self):
        if self.current_slot is None:
            CTkMessageBox.showwarning(
                "No Slot Loaded",
                "Load a character slot first, then create a loadout.",
                parent=self.parent,
            )
            return
        name = self._ask_text("New Loadout", "Loadout name:")
        if not name:
            return
        store = self._read_json(self._store_path())
        if name in store:
            CTkMessageBox.showwarning(
                "Name Exists",
                f"A loadout named '{name}' already exists.",
                parent=self.parent,
            )
            return

        def on_confirm(selections):
            entry = self._build_entry(selections)
            if entry is None:
                return
            store[name] = entry
            self._write_store(store)
            self.refresh_loadout_list()
            self.show_toast(f"Loadout '{name}' saved.", duration=2500)

        _CategoryChecklistDialog(
            self.parent,
            "New Loadout",
            apply_mode=False,
            entry=None,
            equipment_names=self._equipment_names(),
            inventory_names=self._inventory_names(),
            on_confirm=on_confirm,
        )

    def _edit_loadout(self, name: str):
        store = self._read_json(self._store_path())
        entry = store.get(name)
        if entry is None:
            return

        def on_confirm(selections):
            new_entry = self._build_entry(selections)
            if new_entry is None:
                return
            store[name] = new_entry
            self._write_store(store)
            self.refresh_loadout_list()
            self.show_toast(f"Loadout '{name}' updated.", duration=2500)

        _CategoryChecklistDialog(
            self.parent,
            f"Edit '{name}'",
            apply_mode=False,
            entry=entry,
            equipment_names=self._equipment_names(),
            inventory_names=self._inventory_names(),
            on_confirm=on_confirm,
        )

    def _resolve_equipment_name(self, key: str, raw: int) -> str:
        """Best-effort friendly name for an equipment slot value. Falls back
        to the raw hex id if the item database can't resolve it."""
        try:
            from er_save_manager.ui.editors.equipment_editor import _resolve_name

            return _resolve_name(key, raw)
        except Exception:
            return f"0x{raw:X}" if isinstance(raw, int) else str(raw)

    def _tag_suffix(self, tag: dict | None) -> str:
        if not tag:
            return ""
        parts = []
        if tag.get("convergence"):
            parts.append("Convergence")
        if tag.get("seamless"):
            parts.append("Seamless Co-op")
        return f"  [{' + '.join(parts)}]" if parts else ""

    def _format_loadout_summary(self, name: str, entry: dict) -> str:
        lines = [f"Loadout: {name}", ""]
        source_types = entry.get("source_types", {})

        if entry.get("stats"):
            s = entry["stats"]
            lines.append(f"Stats:{self._tag_suffix(source_types.get('stats'))}")
            lines.append(
                f"  Vigor {s.get('vigor')}  Mind {s.get('mind')}  Endurance {s.get('endurance')}"
            )
            lines.append(
                f"  Strength {s.get('strength')}  Dexterity {s.get('dexterity')}"
                f"  Intelligence {s.get('intelligence')}"
            )
            lines.append(f"  Faith {s.get('faith')}  Arcane {s.get('arcane')}")
            lines.append(f"  Level {s.get('level')}   Runes {s.get('runes')}")
            lines.append(
                f"  Matchmaking Weapon Level {s.get('matchmaking_weapon_level')}"
            )
            lines.append("")

        if entry.get("info"):
            i = entry["info"]
            lines.append(f"Info:{self._tag_suffix(source_types.get('info'))}")
            lines.append(f"  Name: {i.get('character_name')}")
            lines.append(
                f"  Gender: {i.get('gender')}   Archetype: {i.get('archetype')}"
                f"   Voice: {i.get('voice_type')}   Gift: {i.get('gift')}"
            )
            lines.append(
                f"  Talisman Slots: {i.get('additional_talisman_slot_count')}"
                f"   Spirit Level: {i.get('summon_spirit_level')}"
            )
            lines.append(
                f"  Crimson Flasks: {i.get('max_crimson_flask_count')}"
                f"   Cerulean Flasks: {i.get('max_cerulean_flask_count')}"
            )
            lines.append(f"  NG+ Level: {i.get('ng_level')}")
            lines.append(
                f"  Playtime: {i.get('playtime_h', 0)}h {i.get('playtime_m', 0)}m"
                f" {i.get('playtime_s', 0)}s"
            )
            lines.append("")

        if entry.get("equipment"):
            eq = entry["equipment"]
            filled = {k: v for k, v in eq.items() if v}
            tag_suffix = self._tag_suffix(source_types.get("equipment"))
            lines.append(f"Equipment ({len(filled)} slot(s) equipped):{tag_suffix}")
            for key, raw in sorted(filled.items()):
                lines.append(f"  {key}: {self._resolve_equipment_name(key, raw)}")
            lines.append("")

        if entry.get("inventory"):
            items = entry["inventory"]
            tag_suffix = self._tag_suffix(source_types.get("inventory"))
            lines.append(f"Inventory ({len(items)} item(s)):{tag_suffix}")
            for it in items:
                label = it.get("name_label", it.get("base_name", "item"))
                loc = it.get("location", "?").upper()
                lines.append(f"  [{loc}] {label} x{it.get('qty', 1)}")
            lines.append("")

        if len(lines) <= 2:
            lines.append("(empty loadout)")
        return "\n".join(lines)

    def _build_entry(self, selections: dict) -> dict | None:
        """Capture the checked sections. Equipment/Inventory are embedded as
        data copies, either from the currently loaded slot or from an
        existing named loadout in their respective databases. Every section
        is tagged with the Convergence/Seamless type of wherever it came
        from, in entry["source_types"]."""
        from er_save_manager.editors.save_type_utils import detect_save_type

        entry: dict = {}
        source_types: dict = {}
        needs_slot = any(selections.get(s) for s in ("stats", "info"))
        needs_live_equipment = (
            selections.get("equipment")
            and selections.get("equipment_source") == "current"
        )
        needs_live_inventory = (
            selections.get("inventory")
            and selections.get("inventory_source") == "current"
        )

        save_file = None
        current_tag: dict = {}
        if needs_slot or needs_live_equipment or needs_live_inventory:
            save_file = self.get_save_file()
            if not save_file or self.current_slot is None:
                CTkMessageBox.showwarning(
                    "No Slot Loaded",
                    "Load a character slot first to capture live data.",
                    parent=self.parent,
                )
                return None
            current_tag = detect_save_type(save_file, self.get_save_path())
        slot_idx = self.current_slot

        # Equipment/Inventory read and write through the live editor
        # instances, which key off the Character Editor's own slot selector
        # (self.set_char_slot) - sync it now so a live capture reflects the
        # Loadout tab's selected slot rather than whatever slot those
        # editors last had loaded.
        if needs_live_equipment or needs_live_inventory:
            self.set_char_slot(slot_idx)

        if selections.get("stats"):
            entry["stats"] = character_loadout_ops.collect_stats(save_file, slot_idx)
            source_types["stats"] = current_tag
        if selections.get("info"):
            entry["info"] = character_loadout_ops.collect_info(save_file, slot_idx)
            source_types["info"] = current_tag

        if selections.get("equipment"):
            if selections.get("equipment_source") == "current":
                # Refresh equipment_vars from the actual save data for this
                # slot first - otherwise _collect_state() would capture
                # whatever slot the Equipment tab last had loaded (or empty
                # defaults if it was never opened this session).
                self.equipment_editor.load_equipment()
                entry["equipment"] = self.equipment_editor._collect_state()
                source_types["equipment"] = current_tag
            else:
                data = self._copy_from_db(
                    self.equipment_editor._read_loadout_store(),
                    selections.get("equipment_db_name"),
                    "equipment",
                )
                if data is None:
                    return None
                slots, tag = self.equipment_editor._unwrap_loadout_entry(data)
                entry["equipment"] = slots
                source_types["equipment"] = tag

        if selections.get("inventory"):
            if selections.get("inventory_source") == "current":
                entry["inventory"] = self._capture_current_inventory(slot_idx)
                source_types["inventory"] = current_tag
            else:
                data = self._copy_from_db(
                    self._read_json(get_loadouts_path()),
                    selections.get("inventory_db_name"),
                    "inventory",
                )
                if data is None:
                    return None
                items, tag = self._unwrap_inventory_db_entry(data)
                entry["inventory"] = items
                source_types["inventory"] = tag

        entry["source_types"] = source_types
        return entry

    def _unwrap_inventory_db_entry(self, data) -> tuple[list, dict]:
        """Support both the current {"items":..., "save_type":...} format
        and the old flat items-list format for backward compatibility."""
        if isinstance(data, dict):
            return data.get("items") or [], data.get("save_type") or {}
        return data or [], {}

    def _copy_from_db(self, store: dict, name: str | None, label: str):
        if not name or name not in store:
            CTkMessageBox.showwarning(
                "Not Found",
                f"Select an existing {label} loadout, or save one first in the"
                f" {label.capitalize()} editor.",
                parent=self.parent,
            )
            return None
        return json.loads(json.dumps(store[name]))  # plain deep copy

    def _capture_current_inventory(self, slot_idx: int) -> list[dict]:
        """Snapshot the full held+storage inventory via InventoryEditor.

        Temporarily clears the editor's own working loadout and location
        filter to capture everything, then restores both so the user's
        in-progress inventory loadout work is untouched. Flasks and key
        items are excluded - see _filter_capturable_items.
        """
        editor = self.inventory_editor
        if not editor:
            return []
        saved_loadout = editor.loadout
        saved_filter = editor.inv_filter_var.get() if editor.inv_filter_var else "All"
        editor.loadout = []
        if editor.inv_filter_var:
            editor.inv_filter_var.set("All")
        try:
            editor.refresh_inventory()
            editor._add_inventory_to_loadout()
            captured = list(editor.loadout)
        finally:
            editor.loadout = saved_loadout
            if editor.inv_filter_var:
                editor.inv_filter_var.set(saved_filter)
            editor.refresh_inventory()
        return self._filter_capturable_items(captured)

    def _filter_capturable_items(self, items: list[dict]) -> list[dict]:
        """Drop flasks and key items from an inventory list before it's
        stored or applied.

        Flasks duplicate rather than move when added through the item
        tools (the same reason the Equipment editor skips them for quick
        items/pouch). Key items are permanent/unique per character - every
        save already has its own Memory of Grace, Spectral Steed Whistle,
        Finger Severer, tutorial/lore entries ("About Sites of Grace" and
        friends), etc., so a loadout should never try to re-grant them.

        _is_key_item() only covers a narrow hardcoded list of quest-
        critical items (it exists to decide which on-disk list an item
        being added belongs in, not to identify everything that's
        permanent), so it misses things like the tutorial/lore entries -
        those are caught here by the broader "Key Items" database
        category instead. Applied both when capturing and when applying,
        so older loadouts saved before this filter existed are also safe.
        """
        from er_save_manager.data.item_database import get_item_database
        from er_save_manager.parser.inventory_ops import _is_key_item

        db = get_item_database()
        filtered = []
        for item_info in items:
            full_id = item_info.get("full_id")
            if full_id is None:
                continue
            if _is_key_item(full_id):
                continue
            item = db.items_by_id.get(full_id)
            category = getattr(item, "category_name", "") if item is not None else ""
            if category in ("Flasks", "Key Items"):
                continue
            filtered.append(item_info)
        return filtered

    # ---- apply ----------------------------------------------------------------

    def _apply_loadout(self, name: str):
        store = self._read_json(self._store_path())
        entry = store.get(name)
        if entry is None:
            return

        def on_confirm(selections):
            self._do_apply(entry, selections)

        _CategoryChecklistDialog(
            self.parent,
            f"Apply '{name}'",
            apply_mode=True,
            entry=entry,
            equipment_names=self._equipment_names(),
            inventory_names=self._inventory_names(),
            on_confirm=on_confirm,
        )

    def _do_apply(self, entry: dict, selections: dict) -> None:
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning(
                "No Save", "Please load a save file first.", parent=self.parent
            )
            return
        if self.current_slot is None:
            CTkMessageBox.showwarning(
                "No Slot Loaded", "Load a character slot first.", parent=self.parent
            )
            return
        slot_idx = self.current_slot
        save_path = self.get_save_path()
        source_types = entry.get("source_types", {})

        sections_to_check = [s for s in _SECTIONS if selections.get(s) and entry.get(s)]
        convergence_sections = [
            s for s in sections_to_check if source_types.get(s, {}).get("convergence")
        ]
        # Only Equipment/Inventory can carry actual items, so only those two
        # matter for the Seamless-exclusive-item check and the ban-risk note.
        item_sections = [
            s for s in sections_to_check if s in ("equipment", "inventory")
        ]
        seamless_item_sections = [
            s for s in item_sections if source_types.get(s, {}).get("seamless")
        ]

        if convergence_sections or seamless_item_sections:
            affected = [
                s
                for s in _SECTIONS
                if s in convergence_sections or s in seamless_item_sections
            ]
            combined_tag = {
                "convergence": bool(convergence_sections),
                "seamless": bool(seamless_item_sections),
            }
            if not confirm_convergence_mismatch(
                self.parent,
                combined_tag,
                save_file,
                save_path,
                extra_text=f"Affected: {', '.join(_SECTION_LABELS[s] for s in affected)}.",
                check_seamless=bool(item_sections),
            ):
                return

        self.set_char_slot(slot_idx)

        if isinstance(save_file._raw_data, bytes):
            save_file._raw_data = bytearray(save_file._raw_data)
        if save_path:
            BackupManager(Path(save_path)).create_backup(
                description=f"before_loadout_apply_slot_{slot_idx + 1}",
                operation=f"loadout_apply_slot_{slot_idx + 1}",
                save=save_file,
            )

        applied: list[str] = []
        notes: list[str] = []

        core_selected = any(
            selections.get(s) and entry.get(s) for s in ("stats", "info")
        )
        if core_selected:
            if selections.get("stats") and entry.get("stats"):
                character_loadout_ops.apply_stats(save_file, slot_idx, entry["stats"])
                applied.append("Stats")
            if selections.get("info") and entry.get("info"):
                character_loadout_ops.apply_info(save_file, slot_idx, entry["info"])
                applied.append("Info")
            character_loadout_ops.finalize_slot(
                save_file, slot_idx, Path(save_path) if save_path else None
            )

        # The mismatch check above already covered these; pass an empty tag
        # down so the delegated apply calls don't prompt a second time.
        if selections.get("inventory") and entry.get("inventory"):
            success, errors, cancelled = self._apply_inventory_data(
                entry["inventory"], slot_idx, save_file, save_path, {}
            )
            if not cancelled:
                applied.append("Inventory")
                if errors:
                    shown = errors[:10]
                    note = (
                        f"Inventory: added {success}, {len(errors)} failed:\n  "
                        + "\n  ".join(shown)
                    )
                    if len(errors) > len(shown):
                        note += f"\n  ... and {len(errors) - len(shown)} more"
                    notes.append(note)

        if selections.get("equipment") and entry.get("equipment"):
            skipped, cancelled = self._apply_equipment_data(entry["equipment"], {})
            if not cancelled:
                applied.append("Equipment")
                if skipped:
                    notes.append(
                        f"Equipment: {len(skipped)} item(s) not owned, skipped: "
                        + ", ".join(skipped)
                    )

        self.reload_save()

        if not applied:
            CTkMessageBox.showinfo(
                "Loadout Not Applied", "No sections were applied.", parent=self.parent
            )
            return

        summary = f"Applied to Slot {slot_idx + 1}: " + ", ".join(applied) + "."
        if notes:
            summary += "\n\n" + "\n".join(notes)
            CTkMessageBox.showwarning("Loadout Applied", summary, parent=self.parent)
        else:
            CTkMessageBox.showinfo("Loadout Applied", summary, parent=self.parent)

    def _apply_equipment_data(
        self, slots: dict, save_type: dict | None
    ) -> tuple[list[str], bool]:
        """Equip owned items, offering to spawn any missing ones (mirrors the
        Equipment editor's own loadout apply flow). Returns (skipped_keys,
        cancelled). Runs silently: the backup and result popup for this
        whole loadout apply are handled once in _do_apply, but the
        Convergence/Seamless-mismatch prompt (if any) still shows since it's a
        real decision point."""
        if not self.equipment_editor:
            return [], True
        # Refresh equipment_vars/handles from this slot's actual equipped
        # state first. Without this, any key not present in `slots` would
        # keep whatever the Equipment tab last had loaded (a different
        # slot, or empty defaults), silently unequipping it.
        self.equipment_editor.load_equipment()
        wrapped = {"slots": slots, "save_type": save_type or {}}
        result = self.equipment_editor._apply_loadout_data(wrapped, silent=True)
        if result.get("cancelled"):
            return [], True
        self.equipment_editor.apply_changes(create_backup=False, silent=True)
        return result.get("skipped", []), False

    def _apply_inventory_data(
        self,
        items: list[dict],
        slot_idx: int,
        save_file,
        save_path,
        save_type: dict | None,
    ) -> tuple[int, list[str], bool]:
        """Add owned-quantity-validated items via the Inventory editor's own
        add/validation path. Returns (success_count, errors, cancelled).
        Runs silently: the backup and result popup for this whole loadout
        apply are handled once in _do_apply, but the Convergence/Seamless
        mismatch prompt (if any) still shows since it's a real decision point."""
        if not self.inventory_editor:
            return 0, [], True
        if not confirm_convergence_mismatch(
            self.parent, save_type, save_file, save_path, check_seamless=True
        ):
            return 0, [], True

        editor = self.inventory_editor
        editor.ensure_mutable()
        slot = save_file.characters[slot_idx]

        original_create_backup = editor._create_backup
        editor._create_backup = lambda *args, **kwargs: None
        try:
            success, errors = 0, []
            for item_info in self._filter_capturable_items(items):
                try:
                    location = editor._resolve_add_location(
                        save_file, slot_idx, item_info.get("location", "held")
                    )
                    to_add = (
                        item_info
                        if location == item_info.get("location")
                        else {**item_info, "location": location}
                    )
                    editor._process_single_add(save_file, slot_idx, slot, to_add)
                    success += 1
                except Exception as ex:
                    label = item_info.get(
                        "name_label", item_info.get("base_name", "item")
                    )
                    errors.append(f"{label}: {ex}")
        finally:
            editor._create_backup = original_create_backup

        save_file.recalculate_checksums()
        if save_path:
            save_file.to_file(Path(save_path))
        editor.refresh_inventory()
        if editor._on_inventory_changed:
            editor._on_inventory_changed()

        return success, errors, False

    # ---- export / import / share ----------------------------------------------

    def export_json(self):
        store = self._read_json(self._store_path())
        name = self._selected_db_name()
        if not name or name not in store:
            CTkMessageBox.showwarning(
                "Selection", "Select a loadout in the list first.", parent=self.parent
            )
            return
        path = pick_file(
            title="Export Character Loadout",
            save=True,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        data = {
            "format": "er-save-manager-character-loadout",
            "version": 1,
            "name": name,
            "loadout": store[name],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.show_toast("Loadout exported.", duration=2500)

    def import_json(self):
        path = pick_file(
            title="Import Character Loadout",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            loadout = data.get("loadout", data) if isinstance(data, dict) else None
            default_name = (
                data.get("name", Path(path).stem)
                if isinstance(data, dict)
                else Path(path).stem
            )
        except Exception as e:
            CTkMessageBox.showerror(
                "Error", f"Failed to import loadout:\n{e}", parent=self.parent
            )
            return
        if not isinstance(loadout, dict):
            CTkMessageBox.showerror(
                "Invalid File",
                "File does not contain a valid loadout.",
                parent=self.parent,
            )
            return

        name = self._ask_text("Import Loadout", "Save as name:") or default_name
        store = self._read_json(self._store_path())
        store[name] = loadout
        self._write_store(store)
        self.refresh_loadout_list()
        self.show_toast(f"Loadout imported as '{name}'.", duration=2500)

    def share_code(self):
        store = self._read_json(self._store_path())
        name = self._selected_db_name()
        if not name or name not in store:
            CTkMessageBox.showwarning(
                "Selection", "Select a loadout in the list first.", parent=self.parent
            )
            return

        from er_save_manager.data.character_loadout_sharing import share_loadout

        code = share_loadout(store[name], name=name)
        if not code:
            CTkMessageBox.showerror(
                "Error",
                "Failed to share loadout. Check your connection.",
                parent=self.parent,
            )
            return
        self._show_share_code(code)

    def import_code(self):
        code = self._ask_text("Import via Code", "Paste share code:")
        if not code:
            return

        from er_save_manager.data.character_loadout_sharing import fetch_loadout

        loadout = fetch_loadout(code)
        if loadout is None:
            CTkMessageBox.showerror(
                "Not Found",
                "No loadout found for that code, or the connection failed.",
                parent=self.parent,
            )
            return

        name = self._ask_text("Import via Code", "Save as name:")
        if not name:
            return
        store = self._read_json(self._store_path())
        store[name] = loadout
        self._write_store(store)
        self.refresh_loadout_list()
        self.show_toast(f"Loadout imported as '{name}'.", duration=2500)

    def _show_share_code(self, code: str):
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Share Code")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        _center_over(dialog, self.parent, 420, 190)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Loadout shared", font=("Segoe UI", 13, "bold")).pack(
            pady=(15, 5)
        )
        ctk.CTkLabel(
            dialog,
            text="Send this code to share it:",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(pady=(0, 10))

        code_entry = ctk.CTkEntry(
            dialog, width=300, justify="center", font=("Consolas", 12)
        )
        code_entry.pack(pady=(0, 15))
        code_entry.insert(0, code)
        code_entry.configure(state="readonly")

        def copy_code():
            dialog.clipboard_clear()
            dialog.clipboard_append(code)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()
        ctk.CTkButton(btn_frame, text="Copy Code", command=copy_code, width=120).pack(
            side=tk.LEFT, padx=5
        )
        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.LEFT, padx=5
        )
