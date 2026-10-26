"""Equipment panel shared by the DS3, DSR and DS2 character editors.

Each game supplies an EquipAdapter over one character: its slots, the
carried items each slot can take, and how a set of slot changes is written.
The panel stages picks per slot and hands them to the game tab on Apply.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Protocol

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.tooltip import add_tooltip
from er_save_manager.ui.utils import bind_mousewheel, patch_combo_scroll
from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

# Groups per row of section boxes.
_GROUPS_PER_ROW = 2
_NAME_WIDTH = 240
_EMPTY_TEXT = "(empty)"


@dataclass(frozen=True)
class EquipChoice:
    """One carried item a slot can hold. key identifies the inventory entry
    to the adapter; icon returns a PIL image or None."""

    key: Hashable
    name: str
    category: str
    icon: Callable[[], object]


@dataclass(frozen=True)
class EquipSlot:
    key: Hashable
    label: str
    group: str
    # Read-only slots show their item with this tooltip instead of a picker.
    read_only_reason: str = ""


class EquipAdapter(Protocol):
    def slots(self) -> list[EquipSlot]: ...

    def current(self, slot_key: Hashable) -> EquipChoice | None:
        """Item in the slot, None when empty."""

    def choices(self, slot_key: Hashable) -> list[EquipChoice]:
        """Carried items that fit the slot."""

    def clear_choice(self, slot_key: Hashable) -> EquipChoice | None:
        """What Clear Slot puts in: a placeholder (Fists, bare armor) or None
        for an empty slot. Raises ValueError with the reason when the slot
        cannot be emptied."""

    def shared(self, choice_key: Hashable) -> bool:
        """True for entries several slots may hold at once (placeholders)."""


class EquipPickerDialog:
    """Search, list or icon grid of the items a slot can take."""

    def __init__(
        self,
        parent,
        slot_label: str,
        choices: list[EquipChoice],
        on_select: Callable[[EquipChoice], None],
        on_clear: Callable[[], None] | None,
    ) -> None:
        self._choices = sorted(choices, key=lambda c: (c.name.lower(), c.category))
        self._visible: list[EquipChoice] = []
        self._on_select = on_select
        self._on_clear = on_clear

        self.dialog = dialog = ds.create(parent, "Select Item")
        dialog.resizable(True, True)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        # Packed before the list so short windows shrink the list, not these.
        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        ds.header(main, "Select Item", font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main, text=f"Slot: {slot_label}", font=ds.FONT, text_color=ds.MUTED
        ).pack(anchor="w")

        top = ctk.CTkFrame(main, fg_color="transparent")
        top.pack(fill=tk.X, pady=(10, 6))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())
        search = ctk.CTkEntry(
            top,
            textvariable=self._search_var,
            placeholder_text="Search",
            height=32,
            font=ds.FONT,
        )
        search.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._view_var = ctk.StringVar(value="List")
        ctk.CTkSegmentedButton(
            top,
            values=["List", "Icons"],
            variable=self._view_var,
            command=lambda _v: self._show_view(),
            font=ds.FONT,
            selected_color=palette.PURPLE,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self._cat_var = ctk.StringVar(value="All")
        categories = sorted({c.category for c in self._choices})
        if len(categories) > 1:
            row = ctk.CTkFrame(main, fg_color="transparent")
            row.pack(fill=tk.X, pady=(0, 8))
            ctk.CTkLabel(row, text="Category", font=ds.FONT).pack(
                side=tk.LEFT, padx=(0, 6)
            )
            combo = ctk.CTkComboBox(
                row,
                values=["All", *categories],
                variable=self._cat_var,
                state="readonly",
                width=180,
                font=ds.FONT,
                dropdown_font=ds.FONT,
                command=lambda _v: self._filter(),
            )
            combo.pack(side=tk.LEFT)
            patch_combo_scroll(combo)

        if not self._choices:
            ctk.CTkLabel(
                main,
                text="No carried item fits this slot.",
                font=ds.FONT,
                text_color=ds.MUTED,
            ).pack(anchor="w", pady=(0, 6))

        self._views = ctk.CTkFrame(main, fg_color="transparent")
        self._views.pack(fill=tk.BOTH, expand=True)
        self._rows = ds.RowList(
            self._views, icon_space=30, on_activate=lambda _i: self._confirm()
        )
        self._grid = VirtualIconGrid(
            self._views,
            lambda _keys: None,
            on_activate=lambda _k: self._confirm(),
        )

        if on_clear is not None:
            ds.button(btn_row, "Clear Slot", self._clear, primary=False).pack(
                side=tk.LEFT
            )
        ds.button(btn_row, "Cancel", dialog.destroy, primary=False).pack(side=tk.RIGHT)
        ds.button(btn_row, "Select", self._confirm).pack(side=tk.RIGHT, padx=(0, 8))
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        self._show_view()
        ds.finish(dialog, parent, width=520, height=600)
        search.focus_set()

    def _show_view(self) -> None:
        icons = self._view_var.get() == "Icons"
        (self._rows if icons else self._grid).pack_forget()
        (self._grid if icons else self._rows).pack(fill=tk.BOTH, expand=True)
        self._filter()

    def _filter(self) -> None:
        query = self._search_var.get().lower().strip()
        category = self._cat_var.get()
        self._visible = [
            c
            for c in self._choices
            if query in c.name.lower() and category in ("All", c.category)
        ]
        if self._view_var.get() == "Icons":
            self._grid.set_entries(
                [
                    GridEntry(i, c.name, c.name.lower(), c.icon)
                    for i, c in enumerate(self._visible)
                ]
            )
        else:
            visible = self._visible
            self._rows.set_rows([c.name for c in visible])
            self._rows.load_icons(lambda i: visible[i].icon())

    def _selected(self) -> EquipChoice | None:
        if self._view_var.get() == "Icons":
            index = self._grid.selected[0] if self._grid.selected else None
        else:
            index = self._rows.selected
        if index is None or index >= len(self._visible):
            return None
        return self._visible[index]

    def _confirm(self) -> None:
        choice = self._selected()
        if choice is None:
            return
        self.dialog.destroy()
        self._on_select(choice)

    def _clear(self) -> None:
        self.dialog.destroy()
        if self._on_clear is not None:
            self._on_clear()


class EquipmentPanel:
    """Equip slots in section boxes with a picker per slot. Picks are staged
    ({slot key: EquipChoice or None}, see staged) until the main window's
    Apply All, which has the game tab write them. build_extra(body) adds
    game-specific sections below the slots."""

    def __init__(
        self,
        parent,
        build_extra: Callable[[ctk.CTkFrame], None] | None = None,
    ) -> None:
        self.parent = parent
        self._build_extra = build_extra
        self.adapter: EquipAdapter | None = None
        self._staged: dict[Hashable, EquipChoice | None] = {}
        self._name_labels: dict[Hashable, ctk.CTkLabel] = {}
        self._slots: dict[Hashable, EquipSlot] = {}
        self._layout: tuple[EquipSlot, ...] | None = None
        # Called after any staged change and after Reset, for extra sections
        # that depend on the equipment (DS2 attunement slots).
        self.on_change: Callable[[], None] | None = None
        self.on_reset: Callable[[], None] | None = None

        self.body = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.body.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(self.body)
        self._slots_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self._slots_frame.pack(fill=tk.X)
        self._placeholder = ctk.CTkLabel(
            self._slots_frame,
            text="Load a character to edit its equipment.",
            text_color=ds.MUTED,
        )
        self._placeholder.pack(anchor="w", padx=10, pady=10)
        if build_extra is not None:
            build_extra(self.body)

    # ---- loading -------------------------------------------------------------

    def load(self, adapter: EquipAdapter | None, message: str = "") -> None:
        """Show a character's equipment; None (with a message) shows no
        slots."""
        self.adapter = adapter
        self._staged = {}
        layout = tuple(adapter.slots()) if adapter is not None else None
        # Same slots as the shown rows (switching characters of one game):
        # keep the rows and refresh their text instead of rebuilding them.
        if layout is not None and layout == self._layout:
            for key in self._name_labels:
                self._refresh_slot(key)
            if self.on_change is not None:
                self.on_change()
            return
        self._layout = layout
        for child in self._slots_frame.winfo_children():
            child.destroy()
        self._name_labels = {}
        self._slots = {}
        if adapter is None:
            ctk.CTkLabel(
                self._slots_frame,
                text=message or "Load a character to edit its equipment.",
                text_color=ds.MUTED,
                wraplength=600,
                justify=tk.LEFT,
            ).pack(anchor="w", padx=10, pady=10)
            if self.on_change is not None:
                self.on_change()
            return
        groups: dict[str, list[EquipSlot]] = {}
        for slot in layout:
            groups.setdefault(slot.group, []).append(slot)
            self._slots[slot.key] = slot
        names = list(groups)
        for start in range(0, len(names), _GROUPS_PER_ROW):
            row = ctk.CTkFrame(self._slots_frame, fg_color="transparent")
            row.pack(fill=tk.X, pady=5)
            # Equal columns, so a lone last section keeps the others' width.
            row.grid_columnconfigure(
                tuple(range(_GROUPS_PER_ROW)), weight=1, uniform="section"
            )
            for column, name in enumerate(names[start : start + _GROUPS_PER_ROW]):
                self._build_section(row, column, name, groups[name])
        if self.on_change is not None:
            self.on_change()

    def reset(self) -> None:
        self._staged = {}
        for key in self._name_labels:
            self._refresh_slot(key)
        if self.on_reset is not None:
            self.on_reset()
        if self.on_change is not None:
            self.on_change()

    def _build_section(
        self, parent, column: int, title: str, slots: list[EquipSlot]
    ) -> None:
        frame = ctk.CTkFrame(parent, fg_color=("gray86", "gray25"))
        frame.grid(row=0, column=column, sticky="nsew", padx=4)
        ctk.CTkLabel(frame, text=title, font=("Inter", 12, "bold")).pack(
            anchor="w", padx=8, pady=(6, 0)
        )
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        for i, slot in enumerate(slots):
            ctk.CTkLabel(grid, text=f"{slot.label}:").grid(
                row=i, column=0, sticky="w", padx=4, pady=3
            )
            editable = not slot.read_only_reason
            label = ctk.CTkLabel(
                grid,
                text=_EMPTY_TEXT,
                width=_NAME_WIDTH,
                anchor="w",
                text_color=palette.BLUE_TEXT if editable else ds.MUTED,
                cursor="hand2" if editable else "",
            )
            label.grid(row=i, column=1, sticky="w", padx=4, pady=3)
            self._name_labels[slot.key] = label
            if editable:
                label.bind("<Button-1>", lambda _e, k=slot.key: self._pick(k))
                ctk.CTkButton(
                    grid,
                    text="...",
                    width=28,
                    height=24,
                    command=lambda k=slot.key: self._pick(k),
                ).grid(row=i, column=2, padx=(0, 4), pady=3)
            else:
                add_tooltip(label, slot.read_only_reason)
            self._refresh_slot(slot.key)

    # ---- staging -------------------------------------------------------------

    def value(self, slot_key: Hashable) -> EquipChoice | None:
        """Staged choice of a slot, else its current item."""
        if slot_key in self._staged:
            return self._staged[slot_key]
        return self.adapter.current(slot_key) if self.adapter else None

    @property
    def staged(self) -> dict[Hashable, EquipChoice | None]:
        return dict(self._staged)

    def details(self) -> list[tuple[str, str, str]]:
        """(slot label, current item, staged item) per staged slot."""
        adapter = self.adapter
        if adapter is None:
            return []
        rows = []
        for key, choice in self._staged.items():
            slot = self._slots.get(key)
            current = adapter.current(key)
            rows.append(
                (
                    slot.label if slot is not None else str(key),
                    current.name if current is not None else _EMPTY_TEXT,
                    choice.name if choice is not None else _EMPTY_TEXT,
                )
            )
        return rows

    def _refresh_slot(self, slot_key: Hashable) -> None:
        label = self._name_labels.get(slot_key)
        if label is None:
            return
        choice = self.value(slot_key)
        text = choice.name if choice is not None else _EMPTY_TEXT
        if slot_key in self._staged:
            text += " *"
        label.configure(text=text)

    def _stage(self, slot_key: Hashable, choice: EquipChoice | None) -> None:
        current = self.adapter.current(slot_key)
        if (None if choice is None else choice.key) == (
            None if current is None else current.key
        ):
            self._staged.pop(slot_key, None)
        else:
            self._staged[slot_key] = choice
        self._refresh_slot(slot_key)
        if self.on_change is not None:
            self.on_change()

    def _pick(self, slot_key: Hashable) -> None:
        adapter = self.adapter
        if adapter is None:
            return
        # One carried entry fills one slot; placeholders are shared.
        in_use = {
            choice.key
            for key in self._slots
            if key != slot_key and (choice := self.value(key)) is not None
        }
        choices = [
            c
            for c in adapter.choices(slot_key)
            if c.key not in in_use or adapter.shared(c.key)
        ]
        EquipPickerDialog(
            self.parent.winfo_toplevel(),
            self._slots[slot_key].label,
            choices,
            lambda choice: self._stage(slot_key, choice),
            lambda: self._clear(slot_key),
        )

    def _clear(self, slot_key: Hashable) -> None:
        try:
            choice = self.adapter.clear_choice(slot_key)
        except ValueError as exc:
            CTkMessageBox.showwarning(
                "Slot Cannot Be Emptied", str(exc), parent=self.parent
            )
            return
        self._stage(slot_key, choice)


class AttunementAdapter(Protocol):
    """Attunement half of an adapter. Spell keys identify a spell to the
    adapter; spells is the staged list, written by the adapter's apply."""

    spells: list[Hashable]
    loaded_spells: list[Hashable]

    def spell_choices(self) -> list[EquipChoice]:
        """Spells the character can attune that are not in the staged list."""

    def spell_name(self, key: Hashable) -> str: ...

    def spell_cost(self, key: Hashable) -> int | None: ...

    def attunement_budget(self, staged: dict) -> int | None:
        """Attunement slots with the staged equipment, None when unknown."""


def check_attunement(
    cost: int, budget: int | None, loaded_budget: int | None, spells_changed: bool
) -> None:
    """Raise ValueError when the spells take more slots than the staged
    equipment gives. A character already over its slots may still change
    other equipment as long as that does not lower the slot count."""
    grew_tighter = spells_changed or (
        loaded_budget is not None and budget is not None and budget < loaded_budget
    )
    if budget is not None and cost > budget and grew_tighter:
        raise ValueError(
            f"The attuned spells take {cost} slots, the character has {budget} "
            "with this equipment."
        )


class AttunementSection:
    """Attunement list under the equipment slots: add, remove and reorder
    spells, with the slot count of the staged equipment."""

    def __init__(self, max_spells: int) -> None:
        self.max_spells = max_spells
        self.panel: EquipmentPanel | None = None
        self._list: tk.Listbox | None = None
        self._budget_label: ctk.CTkLabel | None = None

    def attach(self, panel: EquipmentPanel) -> None:
        """Hook into a panel created with build as its build_extra."""
        self.panel = panel
        panel.on_change = self.refresh
        panel.on_reset = self._reset

    def build(self, body) -> None:
        frame = ctk.CTkFrame(body, fg_color=("gray86", "gray25"))
        frame.pack(fill=tk.X, padx=4, pady=5)
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill=tk.X, padx=8, pady=(6, 0))
        ctk.CTkLabel(head, text="Attunement", font=("Inter", 12, "bold")).pack(
            side=tk.LEFT
        )
        self._budget_label = ctk.CTkLabel(head, text="")
        self._budget_label.pack(side=tk.RIGHT)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill=tk.X, padx=6, pady=6)
        buttons = ctk.CTkFrame(row, fg_color="transparent")
        buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        for text, command in (
            ("Add Spell", self._add),
            ("Remove", self._remove),
            ("Move Up", lambda: self._move(-1)),
            ("Move Down", lambda: self._move(1)),
        ):
            ctk.CTkButton(buttons, text=text, command=command, width=110).pack(pady=2)
        box, self._list = ds.themed_listbox(row, height=8)
        box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ctk.CTkLabel(
            frame,
            text="Spells are kept in this order, packed from the first slot as "
            "the game stores them.",
            text_color=ds.MUTED,
        ).pack(anchor="w", padx=8, pady=(0, 6))

    @property
    def _adapter(self):
        adapter = self.panel.adapter if self.panel is not None else None
        return adapter if hasattr(adapter, "spells") else None

    def changed(self) -> bool:
        adapter = self._adapter
        return adapter is not None and adapter.spells != adapter.loaded_spells

    def details(self) -> list[tuple[str, str, str]]:
        """Spells attuned or removed; one row when only the order changed."""
        adapter = self._adapter
        if adapter is None or not self.changed():
            return []
        before, after = adapter.loaded_spells, adapter.spells
        rows = [
            (adapter.spell_name(key), "", "Attuned")
            for key in after
            if key not in before
        ] + [
            (adapter.spell_name(key), "", "Removed from attunement")
            for key in before
            if key not in after
        ]
        return rows or [("Attunement", "", "Reordered")]

    def refresh(self) -> None:
        if self._list is None:
            return
        adapter = self._adapter
        self._list.delete(0, tk.END)
        if adapter is None:
            self._budget_label.configure(text="", text_color=ds.MUTED)
            return
        cost = 0
        for key in adapter.spells:
            slots = adapter.spell_cost(key) or 0
            cost += slots
            self._list.insert(
                tk.END,
                f"{adapter.spell_name(key)}  ({slots} slot{'s' if slots != 1 else ''})",
            )
        budget = adapter.attunement_budget(self.panel.staged)
        text = f"Slots used: {cost} / {budget if budget is not None else '?'}"
        if self.changed():
            text += " *"
        over = budget is not None and cost > budget
        self._budget_label.configure(
            text=text, text_color=ds.WARNING if over else ds.MUTED
        )

    def _reset(self) -> None:
        adapter = self._adapter
        if adapter is not None:
            adapter.spells = list(adapter.loaded_spells)

    def _add(self) -> None:
        adapter = self._adapter
        if adapter is None:
            return
        if len(adapter.spells) >= self.max_spells:
            CTkMessageBox.showwarning(
                "Attunement Full",
                f"At most {self.max_spells} spells can be attuned.",
                parent=self.panel.parent,
            )
            return

        def on_select(choice: EquipChoice) -> None:
            adapter.spells.append(choice.key)
            self.refresh()

        EquipPickerDialog(
            self.panel.parent.winfo_toplevel(),
            "Spell",
            adapter.spell_choices(),
            on_select,
            None,
        )

    def _selected(self) -> int | None:
        sel = self._list.curselection() if self._list else ()
        return sel[0] if sel else None

    def _remove(self) -> None:
        adapter = self._adapter
        index = self._selected()
        if adapter is None or index is None:
            return
        del adapter.spells[index]
        self.refresh()

    def _move(self, step: int) -> None:
        adapter = self._adapter
        index = self._selected()
        if adapter is None or index is None:
            return
        target = index + step
        if not 0 <= target < len(adapter.spells):
            return
        spells = adapter.spells
        spells[index], spells[target] = spells[target], spells[index]
        self.refresh()
        self._list.selection_set(target)
