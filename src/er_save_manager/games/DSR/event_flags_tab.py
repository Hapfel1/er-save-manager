"""
DSR Event Flags Tab - NPC States and World Flags.

Boss kills are edited in the NPCs & Bosses tab.
Sub-tabs: NPC States | World Flags.

Session/cycle flags in World Flags are marked with * and noted as set by event
scripts at session start. Their saved value is the between-session state.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.pending import save_writable, write_failed
from er_save_manager.ui.toast import notify
from er_save_manager.ui.utils import bind_mousewheel, game_blocks_write


def _game_blocks_write(parent) -> bool:
    return game_blocks_write(
        parent, "darksoulsremastered.exe", "Dark Souls: Remastered"
    )


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


def _state_color(on: bool) -> tuple[str, str]:
    """Badge text color: green for set flags and taught gestures, else muted."""
    return ds.FOUND if on else ds.MUTED


class DSREventFlagsTab:
    def __init__(self, parent, get_dsr_save, get_save_path, show_toast) -> None:
        self.parent = parent
        self._get_dsr_save = get_dsr_save
        self._get_save_path = get_save_path
        self._show_toast = show_toast
        self._current_slot = 0
        self._npc_built = False
        self._world_built = False
        self._lookup_id_var: tk.StringVar | None = None
        self._lookup_result_var: tk.StringVar | None = None

    def setup_ui(self) -> None:
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="Event Flags", font=("Inter", 16, "bold")).pack(
            side="left"
        )

        self._tabs = ctk.CTkTabview(
            outer,
            fg_color=("gray90", "gray20"),
            segmented_button_fg_color=("gray80", "gray35"),
            segmented_button_selected_color=palette.PURPLE,
            segmented_button_unselected_color=("gray70", "gray30"),
            command=self._on_tab_change,
        )
        self._tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._npc_parent = self._tabs.add("NPC States")
        self._world_parent = self._tabs.add("World Flags")
        self._lookup_parent = self._tabs.add("Flag Lookup")

        for p, t in [
            (self._npc_parent, "Load a character to view NPC state flags."),
            (self._world_parent, "Load a character to view world flags."),
        ]:
            ctk.CTkLabel(p, text=t, text_color=("gray50", "gray60")).pack(pady=40)

        self._build_lookup_ui()

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
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=12, pady=(8, 4))

        tf, self._npc_tree = ds.themed_tree(
            self._npc_parent,
            columns=("flag_id", "label", "state"),
            show="tree headings",
            selectmode="browse",
        )
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        self._npc_tree.heading("#0", text="NPC")
        self._npc_tree.heading("flag_id", text="ID")
        self._npc_tree.heading("label", text="Description")
        self._npc_tree.heading("state", text="State")
        self._npc_tree.column("#0", width=180, minwidth=120)
        self._npc_tree.column("flag_id", width=80, minwidth=60, anchor="center")
        self._npc_tree.column("label", width=260, minwidth=140)
        self._npc_tree.column("state", width=60, minwidth=50, anchor="center")
        self._npc_tree.bind("<<TreeviewSelect>>", self._on_npc_select)

        btn_row = ctk.CTkFrame(self._npc_parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkButton(
            btn_row, text="Toggle Selected", command=self._toggle_npc, width=140
        ).pack(side="left", padx=(0, 10))
        self._npc_sel_label = ctk.CTkLabel(
            btn_row, text="", font=("Inter", 10), text_color=("gray40", "gray70")
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
        if _game_blocks_write(self.parent):
            return

        sel = self._npc_tree.selection()
        if not sel or sel[0] not in self._npc_iid_map:
            notify(self.parent, "Select a flag row to toggle.", "warning")
            return
        save, save_path, char = self._get_char()
        if char is None or not save_writable():
            return
        fid, entry = self._npc_iid_map[sel[0]]
        new_val = not char.get_flag(fid)
        char.set_flag(fid, new_val)
        try:
            _backup_and_save(
                save, save_path, f"npc_flag_{fid}_slot_{self._current_slot + 1}"
            )
        except Exception as exc:
            write_failed(exc, self.parent)
            return
        state = "ON" if new_val else "OFF"
        self._npc_tree.set(sel[0], "state", state)
        self._npc_sel_label.configure(
            text=f"Flag {fid}  -  {entry['label']}  -  Now: {state}"
        )
        self._show_toast(f"Flag {fid} ({entry['label']}) -> {state}.")

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
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
            justify="left",
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
                self._world_scroll, text=group_name, font=("Inter", 11, "bold")
            ).pack(anchor="w", padx=12, pady=(10, 2))
            for entry in entries:
                session = entry.get("session", False)
                note = entry.get("note", "")
                display = ("* " if session else "") + entry["name"]
                self._world_row(char, entry["id"], display, note)

        ctk.CTkLabel(
            self._world_scroll,
            text="Gestures (CanLearn flags)",
            font=("Inter", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            self._world_scroll,
            text="1 = not yet taught by NPC.  0 = NPC has taught it.  Resets on NG+.",
            font=("Inter", 9),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", padx=12, pady=(0, 4))
        for entry in db["gestures"]:
            self._gesture_row(char, entry)

    def _world_row(self, char, flag_id: int, name: str, note: str = "") -> None:
        value = char.get_flag(flag_id)
        row = ctk.CTkFrame(self._world_scroll, fg_color=ds.ROW, corner_radius=6)
        row.pack(fill="x", padx=4, pady=2)
        row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            row,
            text=f"{flag_id}",
            font=ds.SMALL,
            text_color=ds.MUTED,
            width=65,
        ).grid(row=0, column=0, padx=(8, 4), pady=(6, 0 if note else 6))
        badge = ctk.CTkLabel(
            row,
            text="ON" if value else "OFF",
            text_color=_state_color(value),
            width=35,
            font=ds.BOLD,
        )
        badge.grid(row=0, column=1, padx=(0, 6), pady=(6, 0 if note else 6))
        ctk.CTkLabel(
            row,
            text=name,
            anchor="w",
            font=ds.FONT,
            text_color=ds.ROW_TEXT,
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
                font=ds.SMALL,
                text_color=ds.MUTED,
            ).grid(row=1, column=0, columnspan=3, sticky="w", padx=(8, 4), pady=(0, 4))

    def _gesture_row(self, char, entry: dict) -> None:
        fid = entry["id"]
        value = char.get_flag(fid)
        row = ctk.CTkFrame(self._world_scroll, fg_color=ds.ROW, corner_radius=6)
        row.pack(fill="x", padx=4, pady=2)
        row.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(
            row,
            text=f"{fid}",
            font=ds.SMALL,
            text_color=ds.MUTED,
            width=65,
        ).grid(row=0, column=0, padx=(8, 4), pady=6)
        badge = ctk.CTkLabel(
            row,
            text="AVAILABLE" if value else "TAUGHT",
            text_color=_state_color(not value),
            width=70,
            font=ds.BOLD,
        )
        badge.grid(row=0, column=1, padx=(0, 6), pady=6)
        ctk.CTkLabel(
            row,
            text=f"{entry['name']}  ({entry['teacher']})",
            anchor="w",
            font=ds.FONT,
            text_color=ds.ROW_TEXT,
        ).grid(row=0, column=2, sticky="w", padx=4, pady=6)
        ctk.CTkButton(
            row,
            text="Toggle",
            width=65,
            command=lambda f=fid, e=entry, b=badge: self._toggle_gesture(f, e, b),
        ).grid(row=0, column=3, padx=(0, 8), pady=6)

    def _toggle_world(self, flag_id: int, name: str, badge: ctk.CTkLabel) -> None:
        if _game_blocks_write(self.parent):
            return

        save, save_path, char = self._get_char()
        if char is None or not save_writable():
            return
        new_val = not char.get_flag(flag_id)
        char.set_flag(flag_id, new_val)
        try:
            _backup_and_save(
                save, save_path, f"flag_{flag_id}_slot_{self._current_slot + 1}"
            )
        except Exception as exc:
            write_failed(exc, self.parent)
            return
        badge.configure(
            text="ON" if new_val else "OFF",
            text_color=_state_color(new_val),
        )
        self._show_toast(f"{name.lstrip('* ')} -> {'ON' if new_val else 'OFF'}.")

    def _toggle_gesture(self, flag_id: int, entry: dict, badge: ctk.CTkLabel) -> None:
        if _game_blocks_write(self.parent):
            return

        save, save_path, char = self._get_char()
        if char is None or not save_writable():
            return
        new_val = not char.get_flag(flag_id)
        char.set_flag(flag_id, new_val)
        try:
            _backup_and_save(
                save, save_path, f"gesture_{flag_id}_slot_{self._current_slot + 1}"
            )
        except Exception as exc:
            write_failed(exc, self.parent)
            return
        badge.configure(
            text="AVAILABLE" if new_val else "TAUGHT",
            text_color=_state_color(not new_val),
        )
        self._show_toast(f"{entry['name']} -> {'AVAILABLE' if new_val else 'TAUGHT'}.")

    # --- Flag Lookup ---------------------------------------------------------- #

    def _build_lookup_ui(self) -> None:
        outer = ctk.CTkFrame(self._lookup_parent, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            outer,
            text="Read or write any event flag by numeric ID.",
            font=("Inter", 10),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", pady=(0, 8))

        input_row = ctk.CTkFrame(outer, fg_color="transparent")
        input_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(input_row, text="Flag ID:").pack(side="left", padx=(0, 6))
        self._lookup_id_var = tk.StringVar()
        ctk.CTkEntry(
            input_row,
            textvariable=self._lookup_id_var,
            width=120,
            placeholder_text="e.g. 11010000",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(input_row, text="Read", command=self._lookup_read, width=70).pack(
            side="left", padx=(0, 4)
        )
        ctk.CTkButton(
            input_row, text="Set ON", command=lambda: self._lookup_write(True), width=75
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            input_row,
            text="Set OFF",
            command=lambda: self._lookup_write(False),
            width=75,
        ).pack(side="left")

        self._lookup_result_var = tk.StringVar(value="")
        ctk.CTkLabel(
            outer,
            textvariable=self._lookup_result_var,
            font=("Consolas", 11),
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

    def _lookup_read(self) -> None:
        _, _, char = self._get_char()
        if char is None:
            self._lookup_result_var.set("No character loaded.")
            return
        try:
            fid = int(self._lookup_id_var.get().strip())
        except ValueError:
            self._lookup_result_var.set("Invalid flag ID.")
            return
        try:
            state = char.get_flag(fid)
            self._lookup_result_var.set(
                f"Flag {fid}  ->  {'ON (1)' if state else 'OFF (0)'}"
            )
        except Exception as exc:
            self._lookup_result_var.set(f"Error: {exc}")

    def _lookup_write(self, value: bool) -> None:
        if _game_blocks_write(self.parent):
            return

        save, save_path, char = self._get_char()
        if char is None:
            self._lookup_result_var.set("No character loaded.")
            return
        try:
            fid = int(self._lookup_id_var.get().strip())
        except ValueError:
            self._lookup_result_var.set("Invalid flag ID.")
            return
        if fid == 0:
            # Map scripts test flag 0 as an always-off condition; no event
            # sets it.
            self._lookup_result_var.set("Flag 0 is reserved by the game.")
            return
        if not save_writable():
            return
        try:
            char.set_flag(fid, value)
        except Exception as exc:
            self._lookup_result_var.set(f"Error: {exc}")
            return
        try:
            _backup_and_save(
                save, save_path, f"flag_{fid}_slot_{self._current_slot + 1}"
            )
        except Exception as exc:
            write_failed(exc, self.parent)
            return
        self._lookup_result_var.set(
            f"Flag {fid}  ->  set to {'ON (1)' if value else 'OFF (0)'}. Backup created."
        )
        self._show_toast(f"Flag {fid} -> {'ON' if value else 'OFF'}.")

    # --- Refresh / helpers ---------------------------------------------------- #

    def refresh(self) -> None:
        self.load_slot(self._current_slot)

    def load_slot(self, slot_idx: int) -> None:
        """Show the character in slot_idx; -1 or an empty slot clears the tab."""
        save = self._get_dsr_save()
        if save is None or not (
            0 <= slot_idx < len(save.characters) and save.characters[slot_idx]
        ):
            slot_idx = -1
        self._current_slot = slot_idx
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
