"""
DS2 World Flags pages: doors, item and chest respawn, and event flags.
"""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from er_save_manager.games.DS2.item_database import build_item_db
from er_save_manager.games.DS2.save import (
    CHEST_CLOSED_STATE,
    CHEST_OPEN_STATE,
    DS2Save,
    SlotState,
    Treasure,
)
from er_save_manager.games.DS2.wording import counted
from er_save_manager.games.DS2.world_flags import (
    DOORS,
    Door,
    DoorStatus,
    area_name,
    door_status,
    flag_labels,
    flag_map,
    set_doors,
)
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import save_writable, write_failed
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import game_blocks_write, patch_combo_scroll
from er_save_manager.validation.numbers import parse_whole

_ALL_AREAS = "All areas"


class _Page:
    """Shared header, area filter, list and write path of the pages.

    Args:
        parent: parent widget the panel is built into.
        get_save: callable returning the current DS2Save, or None if unloaded.
        get_slot_index: callable returning the currently selected slot index.
        get_save_path: callable returning the current save file path.
        show_toast: callable(message, duration) for transient status messages.
    """

    title = ""

    def __init__(
        self, parent, get_save, get_slot_index, get_save_path, show_toast
    ) -> None:
        self.parent = parent
        self.get_save = get_save
        self.get_slot_index = get_slot_index
        self.get_save_path = get_save_path
        self.show_toast = show_toast
        self._has_character = False

    def _header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text=self.title, font=("Inter", 13, "bold")).pack(
            side="left"
        )
        self._summary_label = ctk.CTkLabel(header, text="")
        self._summary_label.pack(side="left", padx=(12, 0))
        return header

    def _area_filter(self, header: ctk.CTkFrame, tip: str) -> None:
        self._area_var = ctk.StringVar(value=_ALL_AREAS)
        self._area_combo = ctk.CTkComboBox(
            header,
            values=[_ALL_AREAS],
            variable=self._area_var,
            state="readonly",
            width=260,
            command=lambda _v: self.refresh(),
        )
        self._area_combo.pack(side="right")
        patch_combo_scroll(self._area_combo)
        add_tooltip(self._area_combo, tip)
        ctk.CTkLabel(header, text="Area:").pack(side="right", padx=(0, 6))

    def _set_areas(self, names: list[str]) -> None:
        values = [_ALL_AREAS, *names]
        self._area_combo.configure(values=values)
        if self._area_var.get() not in values:
            self._area_var.set(_ALL_AREAS)

    def _area_matches(self, map_id: int | None) -> bool:
        picked = self._area_var.get()
        if picked == _ALL_AREAS:
            return True
        return map_id is not None and area_name(map_id) == picked

    def _note(self, text: str) -> None:
        ctk.CTkLabel(
            self.parent,
            text=text,
            text_color=("gray40", "gray60"),
            font=("Inter", 11),
            wraplength=900,
            justify="left",
        ).pack(side="bottom", anchor="w", padx=10)

    def _tree(self, columns: dict[str, tuple[str, int]]):
        box, tree = ds.themed_tree(
            self.parent,
            columns=tuple(columns),
            show="headings",
            height=10,
            selectmode="extended",
        )
        for key, (heading, width) in columns.items():
            tree.heading(key, text=heading)
            tree.column(key, width=width)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        add_tooltip(tree, MULTI_SELECT_TIP)
        tree.bind("<<TreeviewSelect>>", lambda _e: self._update_buttons())
        return tree

    def _button(self, row, text: str, command, first: bool = False):
        button = ctk.CTkButton(row, text=text, command=command, height=32)
        button.pack(side="left", fill="x", expand=True, padx=(0, 3) if first else 3)
        return button

    def _check_character(self, save: DS2Save | None) -> None:
        self._has_character = (
            save is not None
            and save.slot_state(self.get_slot_index()) is SlotState.CHARACTER
            and save.slot_lock_reason(self.get_slot_index()) is None
        )

    def _enable(self, *pairs) -> None:
        for button, enabled in pairs:
            button.configure(
                state="normal" if enabled and self._has_character else "disabled"
            )

    def _update_buttons(self) -> None:
        raise NotImplementedError

    def refresh(self) -> None:
        raise NotImplementedError

    def _apply(self, title: str, message: str, operation: str, mutate, done) -> None:
        """Confirm, then run mutate(save, slot) to change the slot, back up and
        write. mutate returns how many things it changed; done(n) gives the
        toast text for that count."""
        if game_blocks_write(self.parent, "darksoulsii.exe", "Dark Souls II"):
            return
        save: DS2Save | None = self.get_save()
        if save is None:
            self.show_toast("No save file loaded", duration=2000)
            return
        reason = save.slot_lock_reason(self.get_slot_index())
        if reason:
            CTkMessageBox.showerror("Slot Locked", reason, parent=self.parent)
            return
        if not CTkMessageBox.askyesno(title, message, parent=self.parent):
            return
        if not save_writable():
            return
        changed = mutate(save, self.get_slot_index())
        save_path = self.get_save_path()
        if save_path and changed:
            from er_save_manager.backup.manager import BackupManager

            try:
                try:
                    BackupManager(Path(save_path)).create_backup(
                        description=f"before_{operation}", operation=operation
                    )
                except Exception as exc:
                    raise RuntimeError(f"Backup failed: {exc}") from exc
                save.save_to_file(save_path)
            except Exception as exc:
                write_failed(exc, self.parent)
                return
        self.refresh()
        self.show_toast(done(changed), duration=2500)


class DS2DoorsPanel(_Page):
    title = "Doors"

    def setup_ui(self) -> None:
        self._area_filter(
            self._header(), "Lists only the areas that have doors this page can open."
        )
        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        self._open_button = self._button(
            buttons, "Open Selected", lambda: self._on_set(True), first=True
        )
        self._close_button = self._button(
            buttons, "Close Selected", lambda: self._on_set(False)
        )
        self._note(
            "Opening a door sets its event flag and the door object's open "
            "state, as the game does when it is unlocked; the key is not "
            "used up. Closing returns both to their initial values. Partly "
            "open means only one of the two is set."
        )
        self._tree_widget = self._tree(
            {
                "area": ("Area", 200),
                "door": ("Door", 340),
                "near": ("Near Bonfire", 220),
                "state": ("State", 120),
            }
        )
        self._rows: list[Door] = []
        self.refresh()

    def refresh(self) -> None:
        tree = self._tree_widget
        tree.delete(*tree.get_children())
        self._rows = []
        save: DS2Save | None = self.get_save()
        slot = self.get_slot_index()
        flags = save.event_flags(slot) if save is not None else None
        objects = save.world_objects(slot) if save is not None else None
        self._check_character(save)
        if flags is None or objects is None:
            self._summary_label.configure(text="No door data in this slot")
            self._set_areas([])
            self._update_buttons()
            return
        statuses = {door: door_status(door, flags, objects) for door in DOORS}
        present = [d for d, s in statuses.items() if s is not DoorStatus.MISSING]
        self._set_areas(list(dict.fromkeys(area_name(d.map_id) for d in present)))
        for door in present:
            if not self._area_matches(door.map_id):
                continue
            self._rows.append(door)
            tree.insert(
                "",
                "end",
                values=(
                    area_name(door.map_id),
                    door.label,
                    door.near or "",
                    statuses[door].value,
                ),
            )
        opened = sum(1 for d in present if statuses[d] is DoorStatus.OPEN)
        self._summary_label.configure(text=f"{opened} of {len(present)} open")
        self._statuses = statuses
        self._update_buttons()

    def _selected(self) -> list[Door]:
        tree = self._tree_widget
        return [self._rows[tree.index(row)] for row in tree.selection()]

    def _update_buttons(self) -> None:
        picked = self._selected()
        statuses = getattr(self, "_statuses", {})
        self._enable(
            (
                self._open_button,
                any(statuses.get(d) is not DoorStatus.OPEN for d in picked),
            ),
            (
                self._close_button,
                any(statuses.get(d) is not DoorStatus.CLOSED for d in picked),
            ),
        )

    def _on_set(self, opened: bool) -> None:
        doors = self._selected()
        verb = "Open" if opened else "Close"

        def mutate(save: DS2Save, slot: int) -> int:
            return set_doors(
                doors, opened, save.event_flags(slot), save.world_objects(slot)
            )

        self._apply(
            f"{verb} Doors",
            f"{verb} {counted(len(doors), 'selected door')}?\n\nA backup is made first.",
            f"{verb.lower()}_doors",
            mutate,
            lambda n: f"{'Opened' if opened else 'Closed'} {counted(n, 'door')}",
        )


class DS2ItemsPanel(_Page):
    title = "Item Pickups"

    def setup_ui(self) -> None:
        self._items = build_item_db()
        self._area_filter(
            self._header(),
            "Areas appear here once the character has entered them. The game "
            "records an area's pickups on the first visit; lighting its "
            "bonfires in an editor does not count.",
        )
        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        self._respawn_button = self._button(
            buttons, "Respawn Selected", self._on_respawn_selected, first=True
        )
        self._respawn_all_button = self._button(
            buttons, "Respawn All in Area", self._on_respawn_all
        )
        self._note(
            "Lists the item pickups and chest contents of the areas the "
            "character has entered. Respawn puts a taken pickup back where it "
            "lay and closes its chest, so it can be picked up again. Enemy "
            "drops are not included."
        )
        self._tree_widget = self._tree(
            {
                "area": ("Area", 200),
                "items": ("Items", 420),
                "kind": ("Kind", 90),
                "state": ("State", 100),
            }
        )
        self._rows: list[Treasure] = []
        self.refresh()

    def _item_names(self, save: DS2Save, treasure: Treasure) -> list[str]:
        names = []
        for item_id, count in save.regulation.treasure_items(treasure.instance_id):
            name = self._items.get(item_id, (f"Item {item_id}", ""))[0]
            names.append(f"{name} x{count}" if count > 1 else name)
        return names or [f"Treasure {treasure.instance_id}"]

    def _has_key_item(self, save: DS2Save, treasure: Treasure) -> bool:
        return any(
            self._items.get(item_id, ("", ""))[1] == "keys"
            for item_id, _count in save.regulation.treasure_items(treasure.instance_id)
        )

    def refresh(self) -> None:
        tree = self._tree_widget
        tree.delete(*tree.get_children())
        self._rows = []
        save: DS2Save | None = self.get_save()
        objects = save.world_objects(self.get_slot_index()) if save else None
        self._check_character(save)
        if objects is None:
            self._summary_label.configure(text="No pickup data in this slot")
            self._set_areas([])
            self._update_buttons()
            return
        treasures = objects.treasures()
        self._set_areas(list(dict.fromkeys(area_name(t.map_id) for t in treasures)))
        for treasure in treasures:
            if not self._area_matches(treasure.map_id):
                continue
            chest = objects.object_state(treasure.instance_id) in (
                CHEST_CLOSED_STATE,
                CHEST_OPEN_STATE,
            )
            self._rows.append(treasure)
            tree.insert(
                "",
                "end",
                values=(
                    area_name(treasure.map_id),
                    ", ".join(self._item_names(save, treasure)),
                    "Chest" if chest else "Pickup",
                    "Taken" if treasure.taken else "In place",
                ),
            )
        taken = sum(1 for t in treasures if t.taken)
        self._summary_label.configure(text=f"{taken} of {len(treasures)} taken")
        self._update_buttons()

    def _selected(self) -> list[Treasure]:
        tree = self._tree_widget
        return [self._rows[tree.index(row)] for row in tree.selection()]

    def _update_buttons(self) -> None:
        self._enable(
            (self._respawn_button, any(t.taken for t in self._selected())),
            (self._respawn_all_button, any(t.taken for t in self._rows)),
        )

    def _respawn(self, treasures: list[Treasure]) -> None:
        treasures = [t for t in treasures if t.taken]
        save: DS2Save | None = self.get_save()
        if save is None or not treasures:
            return
        message = f"Respawn {counted(len(treasures), 'taken pickup')}?"
        keys = [t for t in treasures if self._has_key_item(save, t)]
        if keys:
            names = ", ".join(", ".join(self._item_names(save, t)) for t in keys)
            message += (
                f"\n\nThis includes key items ({names}). Picking one up again "
                "gives a second copy, and the game's records of the first "
                "pickup stay set."
            )
        message += "\n\nA backup is made first."
        ids = [t.instance_id for t in treasures]
        self._apply(
            "Respawn Pickups",
            message,
            "respawn_pickups",
            lambda s, slot: s.world_objects(slot).respawn(ids),
            lambda n: f"Respawned {counted(n, 'pickup')}",
        )

    def _on_respawn_selected(self) -> None:
        self._respawn(self._selected())

    def _on_respawn_all(self) -> None:
        self._respawn(list(self._rows))


class DS2FlagsPanel(_Page):
    title = "Event Flags"

    def setup_ui(self) -> None:
        self._labels = flag_labels()
        header = self._header()
        self._area_filter(
            header,
            "Lists only the areas that have named flags (doors and fog gates). "
            "Any other flag can be read and changed with the flag id field.",
        )
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(
            header,
            textvariable=self._search_var,
            placeholder_text="Search names",
            width=200,
        ).pack(side="right", padx=(0, 12))

        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        self._set_button = self._button(
            buttons, "Set Selected", lambda: self._on_set_selected(True), first=True
        )
        self._clear_button = self._button(
            buttons, "Clear Selected", lambda: self._on_set_selected(False)
        )

        id_row = ctk.CTkFrame(self.parent, fg_color="transparent")
        id_row.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(id_row, text="Flag id:").pack(side="left", padx=(0, 4))
        self._id_var = ctk.StringVar()
        self._id_var.trace_add("write", lambda *_: self._on_id_typed())
        self._checked_id: int | None = None
        id_entry = ctk.CTkEntry(id_row, textvariable=self._id_var, width=130)
        id_entry.pack(side="left")
        id_entry.bind("<Return>", lambda _e: self._on_check_id())
        ctk.CTkButton(id_row, text="Check", width=80, command=self._on_check_id).pack(
            side="left", padx=(6, 0)
        )
        self._id_state = ctk.CTkLabel(id_row, text="")
        self._id_state.pack(side="left", padx=8)
        self._id_clear = ctk.CTkButton(
            id_row, text="Clear", width=80, command=lambda: self._on_set_id(False)
        )
        self._id_clear.pack(side="right")
        self._id_set = ctk.CTkButton(
            id_row, text="Set", width=80, command=lambda: self._on_set_id(True)
        )
        self._id_set.pack(side="right", padx=6)

        self._tree_widget = self._tree(
            {
                "flag": ("Flag", 110),
                "area": ("Area", 200),
                "name": ("Name", 460),
                "state": ("State", 80),
            }
        )
        self._rows: list[int] = []
        self.refresh()

    def _flags(self):
        save: DS2Save | None = self.get_save()
        return save.event_flags(self.get_slot_index()) if save is not None else None

    def refresh(self) -> None:
        tree = self._tree_widget
        tree.delete(*tree.get_children())
        self._rows = []
        save: DS2Save | None = self.get_save()
        flags = self._flags()
        self._check_character(save)
        if flags is None:
            self._summary_label.configure(text="No event flag data in this slot")
            self._set_areas([])
            self._update_buttons()
            self._update_id()
            return
        stored = [f for f in self._labels if flags.is_stored(f)]
        self._set_areas(
            list(dict.fromkeys(area_name(m) for f in stored if (m := flag_map(f))))
        )
        query = self._search_var.get().strip().lower()
        for flag in stored:
            map_id = flag_map(flag)
            label = self._labels[flag]
            if not self._area_matches(map_id) or query not in label.lower():
                continue
            self._rows.append(flag)
            tree.insert(
                "",
                "end",
                values=(
                    flag,
                    area_name(map_id) if map_id is not None else "Global",
                    label,
                    "Set" if flags.get_flag(flag) else "Clear",
                ),
            )
        self._summary_label.configure(text=f"{len(self._rows)} named flags")
        self._update_buttons()
        self._update_id()

    def _selected(self) -> list[int]:
        tree = self._tree_widget
        return [self._rows[tree.index(row)] for row in tree.selection()]

    def _update_buttons(self) -> None:
        flags = self._flags()
        picked = self._selected()
        self._enable(
            (
                self._set_button,
                flags is not None and any(not flags.get_flag(f) for f in picked),
            ),
            (
                self._clear_button,
                flags is not None and any(flags.get_flag(f) for f in picked),
            ),
        )

    def _id_value(self) -> int | None:
        try:
            return parse_whole(self._id_var.get())
        except ValueError:
            return None

    def _on_id_typed(self) -> None:
        self._checked_id = None
        self._update_id()

    def _on_check_id(self) -> None:
        self._checked_id = self._id_value()
        if self._checked_id is None and self._id_var.get().strip():
            self._id_state.configure(text="Not a flag id")
            return
        self._update_id()

    def _update_id(self) -> None:
        """Show the checked flag's state; Set and Clear act on it."""
        flags = self._flags()
        flag = self._checked_id
        stored = flags is not None and flag is not None and flags.is_stored(flag)
        if flag is None or flags is None:
            text = ""
        elif not stored:
            text = "Not stored in the save"
        else:
            text = "Set" if flags.get_flag(flag) else "Clear"
            if flag in self._labels:
                text += f" - {self._labels[flag]}"
        self._id_state.configure(text=text)
        self._enable(
            (self._id_set, stored and not flags.get_flag(flag)),
            (self._id_clear, stored and flags.get_flag(flag)),
        )

    def _write(self, ids: list[int], value: bool, title: str) -> None:
        def mutate(save: DS2Save, slot: int) -> int:
            flags = save.event_flags(slot)
            changed = [f for f in ids if flags.get_flag(f) != value]
            for flag in changed:
                flags.set_flag(flag, value)
            return len(changed)

        verb = "Set" if value else "Clear"
        self._apply(
            title,
            f"{verb} {counted(len(ids), 'event flag')}?\n\nA backup is made first.",
            "set_event_flags" if value else "clear_event_flags",
            mutate,
            lambda n: f"{'Set' if value else 'Cleared'} {counted(n, 'event flag')}",
        )

    def _on_set_selected(self, value: bool) -> None:
        self._write(
            self._selected(), value, "Set Event Flags" if value else "Clear Event Flags"
        )

    def _on_set_id(self, value: bool) -> None:
        flag = self._checked_id
        if flag is not None:
            self._write(
                [flag], value, "Set Event Flag" if value else "Clear Event Flag"
            )
