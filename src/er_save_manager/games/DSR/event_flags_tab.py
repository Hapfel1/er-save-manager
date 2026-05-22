"""
DSR Event Flags Tab - NPC States and World Flags.

Boss kill management has been moved to the NPCs & Bosses tab.
Sub-tabs: NPC States | World Flags.

Session/cycle flags in World Flags are marked with * and noted as set by event
scripts at session start. Their saved value is the between-session state.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

if TYPE_CHECKING:
    pass

_DATA_DIR = Path(__file__).parent / "data"
_FLAGS_DB: dict | None = None


def _load_flags_db() -> dict:
    global _FLAGS_DB
    if _FLAGS_DB is None:
        _FLAGS_DB = json.loads(
            (_DATA_DIR / "dsr_named_flags.json").read_text(encoding="utf-8")
        )
    return _FLAGS_DB


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
        "Flags.Treeview",
        background="#2b2b2b",
        foreground="white",
        fieldbackground="#2b2b2b",
        rowheight=24,
        borderwidth=0,
    )
    style.configure("Flags.Treeview.Heading", background="#3b3b3b", foreground="white")
    style.map("Flags.Treeview", background=[("selected", "#5a4a7a")])


class DSREventFlagsTab:
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
        self._npc_built = False
        self._world_built = False

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="Event Flags", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ctk.CTkButton(header, text="Load", command=self._load_selected, width=70).pack(
            side="right", padx=(6, 0)
        )
        self._slot_var = ctk.StringVar()
        self._slot_combo = ctk.CTkComboBox(
            header, variable=self._slot_var, values=[], state="readonly", width=220
        )
        self._slot_combo.pack(side="right")
        ctk.CTkLabel(header, text="Slot:").pack(side="right", padx=(0, 6))

        self._tabs = ctk.CTkTabview(
            outer,
            fg_color=("gray90", "gray20"),
            segmented_button_fg_color=("gray80", "gray35"),
            segmented_button_selected_color=("purple3", "#6a4b85"),
            segmented_button_unselected_color=("gray70", "gray30"),
            command=self._on_tab_change,
        )
        self._tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._npc_parent = self._tabs.add("NPC States")
        self._world_parent = self._tabs.add("World Flags")

        for p, t in [
            (self._npc_parent, "Load a character to view NPC state flags."),
            (self._world_parent, "Load a character to view world flags."),
        ]:
            ctk.CTkLabel(p, text=t, text_color=("gray50", "gray60")).pack(pady=40)

        _apply_treeview_style()

    def _on_tab_change(self) -> None:
        _, _, char = self._get_char()
        if char is None:
            return
        tab = self._tabs.get()
        if tab == "NPC States":
            if not self._npc_built:
                self._build_npc_ui()
            self._refresh_npc(char)
        elif tab == "World Flags":
            if not self._world_built:
                self._build_world_ui()
            self._refresh_world(char)

    # --- NPC States ----------------------------------------------------------- #

    def _build_npc_ui(self) -> None:
        self._npc_built = True
        for w in self._npc_parent.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self._npc_parent,
            text="Individual quest-state flags for all major NPCs. Select a row and click Toggle.",
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=12, pady=(8, 4))

        tf = tk.Frame(self._npc_parent, bg="#2b2b2b")
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        self._npc_tree = ttk.Treeview(
            tf,
            columns=("flag_id", "label", "state"),
            show="tree headings",
            style="Flags.Treeview",
            selectmode="browse",
        )
        self._npc_tree.heading("#0", text="NPC")
        self._npc_tree.heading("flag_id", text="ID")
        self._npc_tree.heading("label", text="Description")
        self._npc_tree.heading("state", text="State")
        self._npc_tree.column("#0", width=180, minwidth=120)
        self._npc_tree.column("flag_id", width=80, minwidth=60, anchor="center")
        self._npc_tree.column("label", width=260, minwidth=140)
        self._npc_tree.column("state", width=60, minwidth=50, anchor="center")
        self._npc_tree.grid(row=0, column=0, sticky="nsew")
        self._npc_tree.bind("<<TreeviewSelect>>", self._on_npc_select)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self._npc_tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._npc_tree.configure(yscrollcommand=sb.set)

        btn_row = ctk.CTkFrame(self._npc_parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkButton(
            btn_row, text="Toggle Selected", command=self._toggle_npc, width=140
        ).pack(side="left", padx=(0, 10))
        self._npc_sel_label = ctk.CTkLabel(
            btn_row, text="", font=("Segoe UI", 10), text_color=("gray40", "gray70")
        )
        self._npc_sel_label.pack(side="left")
        self._npc_iid_map: dict[str, tuple[int, dict]] = {}

    def _refresh_npc(self, char) -> None:
        self._npc_tree.delete(*self._npc_tree.get_children())
        self._npc_iid_map.clear()
        for npc_name, flags in _load_flags_db()["npc_states"].items():
            parent_iid = self._npc_tree.insert(
                "", "end", text=npc_name, values=("", "", ""), open=False
            )
            for flag_entry in flags:
                fid = flag_entry["id"]
                state = "ON" if char.get_flag(fid) else "OFF"
                iid = f"f{fid}"
                self._npc_tree.insert(
                    parent_iid, "end", iid=iid, values=(fid, flag_entry["label"], state)
                )
                self._npc_iid_map[iid] = (fid, flag_entry)
        self._npc_sel_label.configure(text="")

    def _on_npc_select(self, _event=None) -> None:
        sel = self._npc_tree.selection()
        if not sel or sel[0] not in self._npc_iid_map:
            self._npc_sel_label.configure(text="")
            return
        fid, entry = self._npc_iid_map[sel[0]]
        _, _, char = self._get_char()
        state = "ON" if (char and char.get_flag(fid)) else "OFF"
        self._npc_sel_label.configure(
            text=f"Flag {fid}  -  {entry['label']}  -  Currently: {state}"
        )

    def _toggle_npc(self) -> None:
        sel = self._npc_tree.selection()
        if not sel or sel[0] not in self._npc_iid_map:
            CTkMessageBox.showwarning(
                "No Selection", "Select a flag row to toggle.", parent=self.parent
            )
            return
        save, save_path, char = self._get_char()
        if char is None:
            return
        fid, entry = self._npc_iid_map[sel[0]]
        new_val = not char.get_flag(fid)
        char.set_flag(fid, new_val)
        try:
            _backup_and_save(
                save, save_path, f"npc_flag_{fid}_slot_{self._current_slot + 1}"
            )
            state = "ON" if new_val else "OFF"
            self._npc_tree.set(sel[0], "state", state)
            self._npc_sel_label.configure(
                text=f"Flag {fid}  -  {entry['label']}  -  Now: {state}"
            )
            self._show_toast(f"Flag {fid} ({entry['label']}) -> {state}.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- World Flags ---------------------------------------------------------- #

    def _build_world_ui(self) -> None:
        self._world_built = True
        for w in self._world_parent.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self._world_parent,
            text=(
                "Persistent: Rite of Kindling, Bottomless Box, Sin flags.\n"
                "Session/cycle flags (*): reset on NG+ or set by event scripts at load. "
                "Editing still takes effect in-game."
            ),
            font=("Segoe UI", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self._world_scroll = ctk.CTkScrollableFrame(
            self._world_parent, corner_radius=10
        )
        self._world_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        bind_mousewheel(self._world_scroll)

    def _refresh_world(self, char) -> None:
        for w in self._world_scroll.winfo_children():
            w.destroy()
        db = _load_flags_db()

        by_group: dict[str, list] = {}
        for f in db["utility"]:
            by_group.setdefault(f.get("group", "Other"), []).append(f)

        for group_name, entries in by_group.items():
            ctk.CTkLabel(
                self._world_scroll, text=group_name, font=("Segoe UI", 11, "bold")
            ).pack(anchor="w", padx=12, pady=(10, 2))
            for entry in entries:
                session = entry.get("session", False)
                note = entry.get("note", "")
                display = ("* " if session else "") + entry["name"]
                self._world_row(char, entry["id"], display, note)

        ctk.CTkLabel(
            self._world_scroll,
            text="Gestures (CanLearn flags)",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            self._world_scroll,
            text="1 = not yet taught by NPC.  0 = NPC has taught it.  Resets on NG+.",
            font=("Segoe UI", 9),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", padx=12, pady=(0, 4))
        for entry in db["gestures"]:
            self._gesture_row(char, entry)

    def _world_row(self, char, flag_id: int, name: str, note: str = "") -> None:
        value = char.get_flag(flag_id)
        row = ctk.CTkFrame(
            self._world_scroll, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
        )
        row.pack(fill="x", padx=4, pady=2)
        row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            row,
            text=f"{flag_id}",
            font=("Consolas", 9),
            text_color=("gray50", "gray60"),
            width=65,
        ).grid(row=0, column=0, padx=(8, 4), pady=(6, 0 if note else 6))
        badge_color = ("#2a6e2a", "#1e7e1e") if value else ("#555", "#444")
        badge = ctk.CTkLabel(
            row,
            text="ON" if value else "OFF",
            fg_color=badge_color,
            corner_radius=4,
            width=35,
            font=("Segoe UI", 8, "bold"),
        )
        badge.grid(row=0, column=1, padx=(0, 6), pady=(6, 0 if note else 6))
        ctk.CTkLabel(
            row,
            text=name,
            anchor="w",
            font=("Segoe UI", 10),
            text_color=("#333333", "#cccccc"),
        ).grid(row=0, column=2, sticky="w", padx=4, pady=(6, 0 if note else 6))
        ctk.CTkButton(
            row,
            text="Toggle",
            width=65,
            command=lambda fid=flag_id, n=name, b=badge: self._toggle_world(fid, n, b),
        ).grid(row=0, column=3, rowspan=(2 if note else 1), padx=(0, 8), pady=6)
        if note:
            ctk.CTkLabel(
                row,
                text=note,
                anchor="w",
                font=("Segoe UI", 8),
                text_color=("gray50", "gray60"),
            ).grid(row=1, column=0, columnspan=3, sticky="w", padx=(8, 4), pady=(0, 4))

    def _gesture_row(self, char, entry: dict) -> None:
        fid = entry["id"]
        value = char.get_flag(fid)
        badge_color = ("#555", "#444") if value else ("#2a6e2a", "#1e7e1e")
        row = ctk.CTkFrame(
            self._world_scroll, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
        )
        row.pack(fill="x", padx=4, pady=2)
        row.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(
            row,
            text=f"{fid}",
            font=("Consolas", 9),
            text_color=("gray50", "gray60"),
            width=65,
        ).grid(row=0, column=0, padx=(8, 4), pady=6)
        badge = ctk.CTkLabel(
            row,
            text="AVAILABLE" if value else "TAUGHT",
            fg_color=badge_color,
            corner_radius=4,
            width=70,
            font=("Segoe UI", 8, "bold"),
        )
        badge.grid(row=0, column=1, padx=(0, 6), pady=6)
        ctk.CTkLabel(
            row,
            text=f"{entry['name']}  ({entry['teacher']})",
            anchor="w",
            font=("Segoe UI", 10),
            text_color=("#333333", "#cccccc"),
        ).grid(row=0, column=2, sticky="w", padx=4, pady=6)
        ctk.CTkButton(
            row,
            text="Toggle",
            width=65,
            command=lambda f=fid, e=entry, b=badge: self._toggle_gesture(f, e, b),
        ).grid(row=0, column=3, padx=(0, 8), pady=6)

    def _toggle_world(self, flag_id: int, name: str, badge: ctk.CTkLabel) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        new_val = not char.get_flag(flag_id)
        char.set_flag(flag_id, new_val)
        try:
            _backup_and_save(
                save, save_path, f"flag_{flag_id}_slot_{self._current_slot + 1}"
            )
            badge.configure(
                text="ON" if new_val else "OFF",
                fg_color=("#2a6e2a", "#1e7e1e") if new_val else ("#555", "#444"),
            )
            self._show_toast(f"{name.lstrip('* ')} -> {'ON' if new_val else 'OFF'}.")
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    def _toggle_gesture(self, flag_id: int, entry: dict, badge: ctk.CTkLabel) -> None:
        save, save_path, char = self._get_char()
        if char is None:
            return
        new_val = not char.get_flag(flag_id)
        char.set_flag(flag_id, new_val)
        try:
            _backup_and_save(
                save, save_path, f"gesture_{flag_id}_slot_{self._current_slot + 1}"
            )
            badge.configure(
                text="AVAILABLE" if new_val else "TAUGHT",
                fg_color=("#555", "#444") if new_val else ("#2a6e2a", "#1e7e1e"),
            )
            self._show_toast(
                f"{entry['name']} -> {'AVAILABLE' if new_val else 'TAUGHT'}."
            )
        except Exception as exc:
            CTkMessageBox.showerror("Save Failed", str(exc), parent=self.parent)

    # --- Refresh / helpers ---------------------------------------------------- #

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
        self._slot_var.set(options[0] if options else "")
        self._current_slot = 0
        self._on_tab_change()

    def load_slot(self, slot_idx: int) -> None:
        options = self._slot_combo.cget("values")
        if options and slot_idx < len(options):
            self._slot_var.set(options[slot_idx])
        self._current_slot = slot_idx
        self._on_tab_change()

    def _load_selected(self) -> None:
        save = self._get_dsr_save()
        if save is None:
            CTkMessageBox.showwarning(
                "No Save", "No DSR save loaded.", parent=self.parent
            )
            return
        idx = self._slot_idx()
        if idx < 0:
            return
        if save.characters[idx] is None:
            CTkMessageBox.showwarning(
                "Empty Slot", f"Slot {idx + 1} is empty.", parent=self.parent
            )
            return
        self._current_slot = idx
        self._on_tab_change()

    def _get_char(self):
        save = self._get_dsr_save()
        save_path = self._get_save_path()
        if save is None or save_path is None:
            return None, None, None
        char = (
            save.characters[self._current_slot]
            if 0 <= self._current_slot < len(save.characters)
            else None
        )
        return save, save_path, char

    def _slot_idx(self) -> int:
        val = self._slot_var.get()
        if not val:
            return -1
        try:
            return int(val.split(" - ")[0].replace("Slot", "").strip()) - 1
        except (ValueError, IndexError):
            return -1
