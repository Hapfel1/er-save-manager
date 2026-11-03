"""
DS2 invader panel: shows which NPC invaders and Forlorn are marked killed and
resets them so they invade again.
"""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.games.DS2.npc_tab import DS2NpcPanel
from er_save_manager.games.DS2.save import DS2Save, InvaderState, SlotState
from er_save_manager.games.DS2.wording import counted
from er_save_manager.games.DS2.world_flags import area_name
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip


def _state_text(state: InvaderState) -> str:
    if state.killed is None:
        return "Area not reached"
    return "Killed" if state.killed else "Not killed"


class DS2InvaderPanel(DS2NpcPanel):
    """Same arguments as DS2NpcPanel."""

    def setup_ui(self) -> None:
        header = ctk.CTkFrame(self.parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="Invaders", font=("Inter", 13, "bold")).pack(
            side="left"
        )
        self._summary_label = ctk.CTkLabel(header, text="")
        self._summary_label.pack(side="left", padx=(12, 0))

        buttons = ctk.CTkFrame(self.parent, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=10, pady=(6, 10))
        self._reset_button = ctk.CTkButton(
            buttons, text="Reset Selected", command=self._on_reset, height=32
        )
        self._reset_button.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            self.parent,
            text=(
                "Reset clears the invader's kill count in that area, so the "
                "invasion can happen again."
            ),
            text_color=("gray40", "gray60"),
            font=("Inter", 11),
            wraplength=900,
            justify="left",
        ).pack(side="bottom", anchor="w", padx=10)

        box, self._tree = ds.themed_tree(
            self.parent,
            columns=("name", "area", "state", "condition"),
            show="headings",
            height=8,
            selectmode="extended",
        )
        for column, text, width in (
            ("name", "Invader", 220),
            ("area", "Area", 200),
            ("state", "State", 120),
            ("condition", "Condition", 260),
        ):
            self._tree.heading(column, text=text)
            self._tree.column(column, width=width)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        add_tooltip(self._tree, MULTI_SELECT_TIP)
        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._update_buttons())

        self._states: list[InvaderState] = []
        self._has_character = False
        self.refresh()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        save: DS2Save | None = self.get_save()
        npcs = save.npcs(self.get_slot_index()) if save is not None else None

        self._states = []
        if npcs is None:
            self._summary_label.configure(text="No invader data in this slot")
            self._update_buttons()
            return

        self._states = npcs.invader_states()
        for state in self._states:
            invader = state.invader
            self._tree.insert(
                "",
                "end",
                values=(
                    invader.name,
                    area_name(invader.map_id),
                    _state_text(state),
                    invader.condition,
                ),
            )
        killed = sum(1 for s in self._states if s.killed)
        self._summary_label.configure(text=f"{killed} killed")

        slot = self.get_slot_index()
        self._has_character = (
            save.slot_state(slot) is SlotState.CHARACTER
            and save.slot_lock_reason(slot) is None
        )
        self._update_buttons()

    def _update_buttons(self) -> None:
        enabled = self._has_character and any(s.killed for s in self._selected())
        self._reset_button.configure(state="normal" if enabled else "disabled")

    def _on_reset(self) -> None:
        invaders = [s.invader for s in self._selected() if s.killed]
        self._apply(
            "Reset Invaders",
            f"Reset {counted(len(invaders), 'selected invader')}?\n\n"
            "A backup is made first. In game, rest at a bonfire or reload the "
            "area, then enter it in human form.",
            "reset_invaders",
            lambda npcs: npcs.reset_invaders(invaders),
            "invader",
        )
