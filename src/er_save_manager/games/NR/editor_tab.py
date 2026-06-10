"""
Nightreign Slot Editor Tab

Sub-tabs:
  Overview - player name, murk, sovereign sigils
  Relics   - searchable treeview, edit panel with name pickers, spawner, remove
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

_EMPTY_EFFECT = 0xFFFFFFFF


def _backup_and_save(nr_save, save_path: Path, op: str) -> None:
    from er_save_manager.backup.manager import BackupManager

    BackupManager(save_path).create_backup(operation=op, save=None)
    nr_save.write_file(save_path)


def _parse_int(s: str) -> int:
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def _fmt_effect(effect_id: int) -> str:
    from er_save_manager.games.NR.item_db import effect_name

    return effect_name(effect_id)


class _PickerDialog(ctk.CTkToplevel):
    """Modal searchable list for picking a relic or effect ID."""

    def __init__(
        self, parent, title: str, items: list[tuple[int, str]], current: int = -1
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("520x480")
        self.transient(parent)
        self.resizable(True, True)

        self.result: int | None = None
        self._items = items

        search_var = tk.StringVar()
        search_var.trace_add("write", lambda *_: self._filter(search_var.get()))
        ctk.CTkEntry(
            self, textvariable=search_var, placeholder_text="Search...", width=480
        ).pack(padx=12, pady=(10, 4))

        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        self._lb = tk.Listbox(
            frame,
            selectmode="single",
            activestyle="none",
            font=("Segoe UI", 10),
            relief="flat",
            borderwidth=0,
            background="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            foreground="#dce4ee" if ctk.get_appearance_mode() == "Dark" else "#1a1a1a",
            selectbackground="#6f42c1"
            if ctk.get_appearance_mode() == "Dark"
            else "#9b72d0",
            selectforeground="#ffffff",
            highlightthickness=0,
        )
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._lb.yview)
        self._lb.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._lb.pack(side="left", fill="both", expand=True)
        self._lb.bind("<Double-Button-1>", self._on_confirm)
        bind_mousewheel(self._lb)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkButton(btn_row, text="Select", command=self._on_confirm, width=100).pack(
            side="left"
        )
        ctk.CTkButton(
            btn_row, text="Clear / Empty", command=self._on_clear, width=120
        ).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy, width=80).pack(
            side="right"
        )

        self._render(items)

        # Pre-select current item
        if current >= 0:
            for idx, (iid, _) in enumerate(self._filtered):
                if iid == current:
                    self._lb.selection_set(idx)
                    self._lb.see(idx)
                    break

        self.update_idletasks()
        self.grab_set()
        self.focus_set()
        self.wait_window()

    def _render(self, items: list[tuple[int, str]]) -> None:
        self._filtered = items
        self._lb.delete(0, "end")
        for _, name in items:
            self._lb.insert("end", name)

    def _filter(self, q: str) -> None:
        q = q.lower()
        filtered = [
            (iid, name)
            for iid, name in self._items
            if not q or q in name.lower() or q in str(iid)
        ]
        self._render(filtered)

    def _on_confirm(self, _event=None) -> None:
        sel = self._lb.curselection()
        if sel:
            self.result = self._filtered[sel[0]][0]
        self.destroy()

    def _on_clear(self) -> None:
        self.result = _EMPTY_EFFECT
        self.destroy()


class NREditorTab:
    def __init__(
        self,
        parent,
        get_nr_save: Callable,
        get_save_path: Callable,
        show_toast: Callable,
    ) -> None:
        self.parent = parent
        self._get_nr_save = get_nr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = -1
        self._name_var = tk.StringVar()
        self._murk_var = tk.StringVar()
        self._mon_var = tk.StringVar()

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="Slot Editor", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(
            header, text="Load Slot", command=self._load_selected, width=120
        ).pack(side="right", padx=(6, 0))
        self._slot_var = tk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header,
            variable=self._slot_var,
            values=[],
            state="readonly",
            width=220,
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        self._tabs = ctk.CTkTabview(outer, corner_radius=10)
        self._tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for name in ("Overview", "Relics"):
            self._tabs.add(name)

        self._build_overview(self._tabs.tab("Overview"))
        self._build_relics(self._tabs.tab("Relics"))

    # ------------------------------------------------------------------
    # Slot selector
    # ------------------------------------------------------------------

    def refresh_slot_list(self) -> None:
        save = self._get_nr_save()
        if save is None:
            return
        options = [
            f"{i + 1} - {slot.player_name}" if slot.player_name else f"{i + 1} - Empty"
            for i, slot in enumerate(save.slots)
        ]
        self._slot_combo.configure(values=options)
        if options:
            self._slot_combo.set(options[0])

    def load_slot(self, slot_index: int) -> None:
        save = self._get_nr_save()
        if save is None:
            return
        self._current_slot = slot_index
        vals = list(self._slot_combo.cget("values") or [])
        if slot_index < len(vals):
            self._slot_combo.set(vals[slot_index])
        slot = save.slots[slot_index]
        self._populate_overview(slot)
        self._populate_relics(slot)

    def refresh(self) -> None:
        save = self._get_nr_save()
        if save is None:
            return
        self.refresh_slot_list()
        if self._current_slot >= 0:
            self.load_slot(self._current_slot)

    def _load_selected(self) -> None:
        val = self._slot_var.get()
        if not val:
            return
        try:
            idx = int(val.split(" - ")[0]) - 1
        except (ValueError, IndexError):
            return
        self.load_slot(idx)

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def _build_overview(self, parent) -> None:
        f = ctk.CTkFrame(parent, corner_radius=10, fg_color=("gray86", "gray22"))
        f.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f, text="Character Overview", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(anchor="nw", padx=14)

        for row, (label, var) in enumerate(
            [
                ("Player Name:", self._name_var),
                ("Murk:", self._murk_var),
                ("Sovereign Sigils:", self._mon_var),
            ]
        ):
            ctk.CTkLabel(grid, text=label, anchor="w", width=150).grid(
                row=row, column=0, sticky="w", pady=4
            )
            ctk.CTkEntry(grid, textvariable=var, width=200).grid(
                row=row, column=1, padx=(6, 0), pady=4
            )

        ctk.CTkButton(f, text="Apply", command=self._apply_overview, width=100).pack(
            anchor="w", padx=14, pady=(12, 4)
        )

    def _populate_overview(self, slot) -> None:
        self._name_var.set(slot.player_name)
        self._murk_var.set(str(slot.murk))
        self._mon_var.set(str(slot.marks_of_night))

    def _apply_overview(self) -> None:
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        slot = save.slots[self._current_slot]
        try:
            murk = int(self._murk_var.get())
            mon = int(self._mon_var.get())
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Input",
                "murk and Sovereign Sigils must be integers.",
                parent=self.parent,
            )
            return
        if murk < 0 or mon < 0:
            CTkMessageBox.showerror(
                "Invalid Input", "Values must be >= 0.", parent=self.parent
            )
            return
        slot.murk = murk
        slot.marks_of_night = mon
        name = self._name_var.get().strip()
        if name:
            if len(name) > 16:
                CTkMessageBox.showerror(
                    "Name Too Long",
                    "Player name cannot exceed 16 characters.",
                    parent=self.parent,
                )
                return
            slot.player_name = name
        try:
            _backup_and_save(save, self._get_save_path(), "nr_overview")
            self._show_toast("Overview saved.")
        except Exception as e:
            CTkMessageBox.showerror("Save Failed", str(e), parent=self.parent)

    # ------------------------------------------------------------------
    # Relics
    # ------------------------------------------------------------------

    def _build_relics(self, parent) -> None:
        from er_save_manager.games.NR.item_db import (
            effects_for_curse_slot,
            effects_for_slot,
            relics_sorted,
        )

        # Cached option lists for pickers (populated once, tier-filtered lists built on demand)
        self._all_relic_opts: list[tuple[int, str, bool]] = relics_sorted()
        self._normal_effect_opts: list[tuple[int, str]] = effects_for_slot(False)
        self._deep_effect_opts: list[tuple[int, str]] = effects_for_slot(True)
        self._curse_opts: list[tuple[int, str]] = effects_for_curse_slot()

        # Search bar
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(top, text="Relics", font=("Segoe UI", 14, "bold")).pack(
            side="left"
        )
        self._relic_search_var = tk.StringVar()
        self._relic_search_var.trace_add("write", lambda *_: self._filter_relics())
        ctk.CTkEntry(
            top,
            textvariable=self._relic_search_var,
            placeholder_text="Search name...",
            width=240,
        ).pack(side="right")
        ctk.CTkLabel(top, text="Search:").pack(side="right", padx=(0, 4))

        # Treeview
        tree_frame = ctk.CTkFrame(parent, corner_radius=8)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        self._relic_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "deep", "e1", "e2", "e3"),
            show="headings",
            selectmode="browse",
            height=10,
        )
        for col, label, w in [
            ("name", "Relic Name", 200),
            ("deep", "Deep", 45),
            ("e1", "Effect 1", 220),
            ("e2", "Effect 2", 220),
            ("e3", "Effect 3", 220),
        ]:
            self._relic_tree.heading(col, text=label)
            self._relic_tree.column(
                col, width=w, minwidth=40, anchor="w", stretch=False
            )

        vsb = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._relic_tree.yview
        )
        hsb = ttk.Scrollbar(
            tree_frame, orient="horizontal", command=self._relic_tree.xview
        )
        self._relic_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._relic_tree.pack(side="left", fill="both", expand=True)
        self._relic_tree.bind("<<TreeviewSelect>>", self._on_relic_select)
        self._tree_ga_map: dict[str, int] = {}

        # Sub-tabs: Edit | Spawn
        action_tabs = ctk.CTkTabview(parent, corner_radius=8, height=185)
        action_tabs.pack(fill="x", padx=10, pady=(0, 6))
        action_tabs.add("Edit")
        action_tabs.add("Spawn")
        _edit_parent = action_tabs.tab("Edit")
        _spawn_parent = action_tabs.tab("Spawn")

        # Edit panel
        self._edit_panel = ctk.CTkFrame(
            _edit_parent, corner_radius=10, fg_color=("gray84", "gray24")
        )
        self._edit_panel.pack(fill="x", padx=4, pady=(4, 4))

        ep_title = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        ep_title.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            ep_title, text="Edit selected relic:", font=("Segoe UI", 11, "bold")
        ).pack(side="left")
        ep_btns = ctk.CTkFrame(ep_title, fg_color="transparent")
        ep_btns.pack(side="right")
        ctk.CTkButton(
            ep_btns, text="Apply Edit", command=self._apply_relic_edit, width=100
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            ep_btns,
            text="Remove",
            command=self._remove_selected_relic,
            width=80,
            fg_color=("gray65", "gray35"),
        ).pack(side="left")

        # Relic type row
        relic_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        relic_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(relic_row, text="Relic type:", width=90, anchor="w").pack(
            side="left"
        )
        self._re_item_label = ctk.CTkLabel(
            relic_row, text="(none selected)", anchor="w", width=280
        )
        self._re_item_label.pack(side="left", padx=(4, 6))
        ctk.CTkButton(
            relic_row,
            text="Browse",
            command=self._browse_relic_type,
            width=70,
            height=26,
        ).pack(side="left")
        self._re_item_var = tk.StringVar(value="-1")

        # Effect / curse rows
        self._re_effect_vars = [
            tk.StringVar(value=str(_EMPTY_EFFECT)) for _ in range(3)
        ]
        self._re_curse_vars = [tk.StringVar(value=str(_EMPTY_EFFECT)) for _ in range(3)]
        self._re_effect_labels = []
        self._re_curse_labels = []

        slots_frame = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        slots_frame.pack(fill="x", padx=8, pady=(2, 6))

        for j in range(3):
            row = ctk.CTkFrame(slots_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            # Effect
            ctk.CTkLabel(row, text=f"E{j + 1}:", width=28, anchor="w").pack(side="left")
            lbl_e = ctk.CTkLabel(
                row,
                text="(empty)",
                anchor="w",
                width=240,
                font=("Segoe UI", 10),
                wraplength=238,
            )
            lbl_e.pack(side="left", padx=(2, 4))
            ctk.CTkButton(
                row,
                text="Browse",
                width=65,
                height=24,
                command=lambda jj=j: self._browse_effect(jj),
            ).pack(side="left", padx=(0, 16))
            # Curse
            ctk.CTkLabel(row, text=f"C{j + 1}:", width=28, anchor="w").pack(side="left")
            lbl_c = ctk.CTkLabel(
                row,
                text="(empty)",
                anchor="w",
                width=240,
                font=("Segoe UI", 10),
                wraplength=238,
            )
            lbl_c.pack(side="left", padx=(2, 4))
            ctk.CTkButton(
                row,
                text="Browse",
                width=65,
                height=24,
                command=lambda jj=j: self._browse_curse(jj),
            ).pack(side="left")
            self._re_effect_labels.append(lbl_e)
            self._re_curse_labels.append(lbl_c)

        # Spawner
        spawn_outer = ctk.CTkFrame(
            _spawn_parent, corner_radius=10, fg_color=("gray84", "gray24")
        )
        spawn_outer.pack(fill="x", padx=4, pady=(4, 4))

        spawn_title = ctk.CTkFrame(spawn_outer, fg_color="transparent")
        spawn_title.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            spawn_title, text="Spawn Relic", font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        ctk.CTkButton(
            spawn_title, text="Spawn", command=self._spawn_relic, width=80
        ).pack(side="right")

        # Spawn relic type
        sr_row = ctk.CTkFrame(spawn_outer, fg_color="transparent")
        sr_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(sr_row, text="Relic type:", width=90, anchor="w").pack(side="left")
        self._spawn_relic_label = ctk.CTkLabel(
            sr_row, text="(none selected)", anchor="w", width=280
        )
        self._spawn_relic_label.pack(side="left", padx=(4, 6))
        ctk.CTkButton(
            sr_row, text="Browse", command=self._browse_spawn_relic, width=70, height=26
        ).pack(side="left")
        self._spawn_relic_id = tk.IntVar(value=-1)

        # Spawn effect / curse rows
        self._spawn_effect_vars = [
            tk.StringVar(value=str(_EMPTY_EFFECT)) for _ in range(3)
        ]
        self._spawn_curse_vars = [
            tk.StringVar(value=str(_EMPTY_EFFECT)) for _ in range(3)
        ]
        self._spawn_effect_labels = []
        self._spawn_curse_labels = []

        spawn_slots = ctk.CTkFrame(spawn_outer, fg_color="transparent")
        spawn_slots.pack(fill="x", padx=8, pady=(2, 8))

        for j in range(3):
            row = ctk.CTkFrame(spawn_slots, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"E{j + 1}:", width=28, anchor="w").pack(side="left")
            lbl_e = ctk.CTkLabel(
                row,
                text="(empty)",
                anchor="w",
                width=240,
                font=("Segoe UI", 10),
                wraplength=238,
            )
            lbl_e.pack(side="left", padx=(2, 4))
            ctk.CTkButton(
                row,
                text="Browse",
                width=65,
                height=24,
                command=lambda jj=j: self._browse_spawn_effect(jj),
            ).pack(side="left", padx=(0, 16))
            ctk.CTkLabel(row, text=f"C{j + 1}:", width=28, anchor="w").pack(side="left")
            lbl_c = ctk.CTkLabel(
                row,
                text="(empty)",
                anchor="w",
                width=240,
                font=("Segoe UI", 10),
                wraplength=238,
            )
            lbl_c.pack(side="left", padx=(2, 4))
            ctk.CTkButton(
                row,
                text="Browse",
                width=65,
                height=24,
                command=lambda jj=j: self._browse_spawn_curse(jj),
            ).pack(side="left")
            self._spawn_effect_labels.append(lbl_e)
            self._spawn_curse_labels.append(lbl_c)

        self._selected_relic_ga: int | None = None
        self._all_relic_data: list = []

    # ------------------------------------------------------------------
    # Picker helpers
    # ------------------------------------------------------------------

    def _relic_picker_items(self) -> list[tuple[int, str]]:
        return [
            (rid, f"{'[Deep] ' if deep else ''}{name}")
            for rid, name, deep in self._all_relic_opts
        ]

    def _effect_picker_items(self, is_deep: bool) -> list[tuple[int, str]]:
        opts = self._deep_effect_opts if is_deep else self._normal_effect_opts
        return [(_EMPTY_EFFECT, "(empty)")] + opts

    def _curse_picker_items(self) -> list[tuple[int, str]]:
        return [(_EMPTY_EFFECT, "(empty)")] + self._curse_opts

    def _current_is_deep(self) -> bool:
        """Return whether the currently-selected relic type is deep."""
        from er_save_manager.games.NR.item_db import get_relic

        try:
            rid = int(self._re_item_var.get())
        except ValueError:
            return False
        r = get_relic(rid)
        return r["deep"] if r else False

    def _spawn_is_deep(self) -> bool:
        from er_save_manager.games.NR.item_db import get_relic

        rid = self._spawn_relic_id.get()
        r = get_relic(rid) if rid >= 0 else None
        return r["deep"] if r else False

    # Edit panel pickers

    def _browse_relic_type(self) -> None:
        try:
            cur = int(self._re_item_var.get())
        except ValueError:
            cur = -1
        dlg = _PickerDialog(
            self.parent, "Select Relic Type", self._relic_picker_items(), cur
        )
        if dlg.result is not None and dlg.result != _EMPTY_EFFECT:
            from er_save_manager.games.NR.item_db import relic_name

            self._re_item_var.set(str(dlg.result))
            self._re_item_label.configure(text=relic_name(dlg.result))

    def _browse_effect(self, idx: int) -> None:
        try:
            cur = int(self._re_effect_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        items = self._effect_picker_items(self._current_is_deep())
        dlg = _PickerDialog(self.parent, f"Select Effect {idx + 1}", items, cur)
        if dlg.result is not None:
            self._re_effect_vars[idx].set(str(dlg.result))
            self._re_effect_labels[idx].configure(text=_fmt_effect(dlg.result))

    def _browse_curse(self, idx: int) -> None:
        try:
            cur = int(self._re_curse_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        dlg = _PickerDialog(
            self.parent, f"Select Curse {idx + 1}", self._curse_picker_items(), cur
        )
        if dlg.result is not None:
            self._re_curse_vars[idx].set(str(dlg.result))
            self._re_curse_labels[idx].configure(text=_fmt_effect(dlg.result))

    # Spawn pickers

    def _browse_spawn_relic(self) -> None:
        cur = self._spawn_relic_id.get()
        dlg = _PickerDialog(
            self.parent, "Select Relic Type", self._relic_picker_items(), cur
        )
        if dlg.result is not None and dlg.result != _EMPTY_EFFECT:
            from er_save_manager.games.NR.item_db import relic_name

            self._spawn_relic_id.set(dlg.result)
            self._spawn_relic_label.configure(text=relic_name(dlg.result))

    def _browse_spawn_effect(self, idx: int) -> None:
        try:
            cur = int(self._spawn_effect_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        items = self._effect_picker_items(self._spawn_is_deep())
        dlg = _PickerDialog(self.parent, f"Select Effect {idx + 1}", items, cur)
        if dlg.result is not None:
            self._spawn_effect_vars[idx].set(str(dlg.result))
            self._spawn_effect_labels[idx].configure(text=_fmt_effect(dlg.result))

    def _browse_spawn_curse(self, idx: int) -> None:
        try:
            cur = int(self._spawn_curse_vars[idx].get())
        except ValueError:
            cur = _EMPTY_EFFECT
        dlg = _PickerDialog(
            self.parent, f"Select Curse {idx + 1}", self._curse_picker_items(), cur
        )
        if dlg.result is not None:
            self._spawn_curse_vars[idx].set(str(dlg.result))
            self._spawn_curse_labels[idx].configure(text=_fmt_effect(dlg.result))

    # ------------------------------------------------------------------
    # Relic list
    # ------------------------------------------------------------------

    def _populate_relics(self, slot) -> None:
        from er_save_manager.games.NR.item_db import effect_name, relic_name

        for iid in self._relic_tree.get_children():
            self._relic_tree.delete(iid)
        self._tree_ga_map.clear()
        self._selected_relic_ga = None
        self._all_relic_data = list(slot.relic_states.values())
        for rs in sorted(
            self._all_relic_data, key=lambda r: relic_name(r.real_item_id)
        ):
            iid = self._relic_tree.insert(
                "",
                "end",
                values=(
                    relic_name(rs.real_item_id),
                    "Y" if rs.is_deep else "N",
                    effect_name(rs.effect_1),
                    effect_name(rs.effect_2),
                    effect_name(rs.effect_3),
                ),
            )
            self._tree_ga_map[iid] = rs.ga_handle

    def _filter_relics(self) -> None:
        from er_save_manager.games.NR.item_db import effect_name, relic_name

        q = self._relic_search_var.get().strip().lower()
        for iid in self._relic_tree.get_children():
            self._relic_tree.delete(iid)
        self._tree_ga_map.clear()
        for rs in sorted(
            self._all_relic_data, key=lambda r: relic_name(r.real_item_id)
        ):
            name = relic_name(rs.real_item_id)
            e1 = effect_name(rs.effect_1)
            e2 = effect_name(rs.effect_2)
            e3 = effect_name(rs.effect_3)
            if q and not (
                q in name.lower()
                or q in e1.lower()
                or q in e2.lower()
                or q in e3.lower()
            ):
                continue
            iid = self._relic_tree.insert(
                "",
                "end",
                values=(
                    name,
                    "Y" if rs.is_deep else "N",
                    e1,
                    e2,
                    e3,
                ),
            )
            self._tree_ga_map[iid] = rs.ga_handle

    def _on_relic_select(self, _event=None) -> None:
        from er_save_manager.games.NR.item_db import effect_name, relic_name

        sel = self._relic_tree.selection()
        if not sel:
            return
        ga = self._tree_ga_map.get(sel[0])
        if ga is None:
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        rs = save.slots[self._current_slot].relic_states.get(ga)
        if rs is None:
            return
        self._selected_relic_ga = ga
        # Populate edit panel with names
        self._re_item_var.set(str(rs.real_item_id))
        self._re_item_label.configure(text=relic_name(rs.real_item_id))
        effects = rs.effects_list()
        for j in range(3):
            self._re_effect_vars[j].set(str(effects[j]))
            self._re_effect_labels[j].configure(text=effect_name(effects[j]))
            self._re_curse_vars[j].set(str(effects[j + 3]))
            self._re_curse_labels[j].configure(text=effect_name(effects[j + 3]))

    # ------------------------------------------------------------------
    # Edit / remove
    # ------------------------------------------------------------------

    def _apply_relic_edit(self) -> None:
        if self._selected_relic_ga is None:
            CTkMessageBox.showinfo(
                "No Selection", "Select a relic row first.", parent=self.parent
            )
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        try:
            real_id = int(self._re_item_var.get())
            effects = [int(v.get()) for v in self._re_effect_vars]
            curses = [int(v.get()) for v in self._re_curse_vars]
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Input", "Could not parse IDs.", parent=self.parent
            )
            return

        from er_save_manager.games.NR.item_db import (
            get_relic,
            validate_curse,
            validate_effect,
        )

        relic_row = get_relic(real_id)
        is_deep = relic_row["deep"] if relic_row else False
        errors = []
        for i, ef in enumerate(effects):
            err = validate_effect(ef, is_deep)
            if err:
                errors.append(f"E{i + 1}: {err}")
        for i, ef in enumerate(curses):
            err = validate_curse(ef)
            if err:
                errors.append(f"C{i + 1}: {err}")
        if errors and not CTkMessageBox.askyesno(
            "Validation Warning",
            "Issues found:\n" + "\n".join(errors) + "\n\nApply anyway?",
            parent=self.parent,
        ):
            return

        try:
            save.modify_relic(
                self._current_slot,
                self._selected_relic_ga,
                relic_id=real_id,
                effect_1=effects[0],
                effect_2=effects[1],
                effect_3=effects[2],
                curse_1=curses[0],
                curse_2=curses[1],
                curse_3=curses[2],
            )
            _backup_and_save(save, self._get_save_path(), "nr_relic_edit")
            self._populate_relics(save.slots[self._current_slot])
            self._show_toast("Relic saved.")
        except Exception as e:
            CTkMessageBox.showerror("Save Failed", str(e), parent=self.parent)

    def _remove_selected_relic(self) -> None:
        if self._selected_relic_ga is None:
            CTkMessageBox.showinfo(
                "No Selection", "Select a relic row first.", parent=self.parent
            )
            return
        if not CTkMessageBox.askyesno(
            "Confirm Remove", "Remove this relic permanently?", parent=self.parent
        ):
            return
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            return
        try:
            from er_save_manager.games.NR.relic_ops import remove_relic

            remove_relic(save.slots[self._current_slot], self._selected_relic_ga)
            _backup_and_save(save, self._get_save_path(), "nr_relic_remove")
            self._selected_relic_ga = None
            self._populate_relics(save.slots[self._current_slot])
            self._show_toast("Relic removed.")
        except Exception as e:
            CTkMessageBox.showerror("Remove Failed", str(e), parent=self.parent)

    # ------------------------------------------------------------------
    # Spawn
    # ------------------------------------------------------------------

    def _spawn_relic(self) -> None:
        save = self._get_nr_save()
        if save is None or self._current_slot < 0:
            CTkMessageBox.showinfo("No Slot", "Load a slot first.", parent=self.parent)
            return
        rid = self._spawn_relic_id.get()
        if rid < 0:
            CTkMessageBox.showinfo(
                "No Relic", "Select a relic type first.", parent=self.parent
            )
            return
        try:
            effects = [int(v.get()) for v in self._spawn_effect_vars]
            curses = [int(v.get()) for v in self._spawn_curse_vars]
        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Input", "Could not parse IDs.", parent=self.parent
            )
            return
        try:
            from er_save_manager.games.NR.relic_ops import spawn_relic

            spawn_relic(
                save.slots[self._current_slot],
                real_item_id=rid,
                effect_1=effects[0],
                effect_2=effects[1],
                effect_3=effects[2],
                curse_1=curses[0],
                curse_2=curses[1],
                curse_3=curses[2],
            )
            _backup_and_save(save, self._get_save_path(), "nr_relic_spawn")
            self._populate_relics(save.slots[self._current_slot])
            self._show_toast("Relic spawned.")
        except Exception as e:
            CTkMessageBox.showerror("Spawn Failed", str(e), parent=self.parent)
