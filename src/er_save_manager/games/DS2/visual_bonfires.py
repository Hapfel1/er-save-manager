"""
Visual bonfire popup for DS2.

Shows every bonfire of the slot as its picture, with unlit ones greyed out.
Selecting pictures selects the matching rows in the bonfire panel's own tree,
and the actions run the panel's own handlers, so the confirmation, backup,
write and the last rested rule stay in one place.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS2.bonfire_database import BONFIRES
from er_save_manager.ui import palette
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import (
    center_window,
    debounced_trace,
    raise_after_ctk_refocus,
)
from er_save_manager.ui.virtual_grid import GridEntry, VirtualIconGrid

if TYPE_CHECKING:
    from PIL import Image as PILImage

    from er_save_manager.games.DS2.bonfire_tab import DS2BonfirePanel

# The stored pictures are 147x82.
_IMAGE_SIZE = (147, 82)
_CELL_W = 172
_CELL_H = 152
_CELL_PAD = 4
_SCROLLBAR_W = 24
_DEFAULT_COLS = 4
# Brightness left on an unlit bonfire's greyed picture.
_UNLIT_BRIGHTNESS = 0.45
_SELECTED_TEXT = palette.PURPLE_TEXT
_FILTERS = ("All", "Lit", "Unlit")


def _state_text(lit: bool, intensity: int, last_rested: bool) -> str:
    text = f"Lit, intensity {intensity}" if lit else "Unlit"
    return f"{text}, last rested" if last_rested else text


def _unlit_picture(img: PILImage.Image) -> PILImage.Image:
    """The picture in darkened greyscale, transparency kept."""
    from PIL import ImageEnhance, ImageOps

    grey = ImageOps.grayscale(img).convert("RGBA")
    grey = ImageEnhance.Brightness(grey).enhance(_UNLIT_BRIGHTNESS)
    grey.putalpha(img.getchannel("A"))
    return grey


class VisualBonfireBrowser(ctk.CTkToplevel):
    """Picture grid of the current slot's bonfires."""

    def __init__(self, parent, panel: DS2BonfirePanel):
        super().__init__(parent)
        self._panel = panel
        # (lit, intensity, last rested) per shown bonfire id, in grid order
        self._shown: dict[int, tuple[bool, int, bool]] = {}

        w = _DEFAULT_COLS * (_CELL_W + _CELL_PAD * 2) + 12 + _SCROLLBAR_W + 30
        self.title("Visual Bonfires")
        self.geometry(f"{w}x760")
        self.minsize(520, 480)
        self.attributes("-alpha", 0)
        self.update_idletasks()
        center_window(self, w, 760, parent=parent, align_top=True)
        self.attributes("-alpha", 1)
        self.lift()
        self.focus_force()
        raise_after_ctk_refocus(self)

        self._build_ui()
        self._rebuild()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        # Rebuild after any panel refresh: edits here or in the panel, or
        # another character loaded.
        self._refresh_job: str | None = None
        panel.listeners.append(self._on_panel_refresh)
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, event) -> None:
        if event.widget is self and self._on_panel_refresh in self._panel.listeners:
            self._panel.listeners.remove(self._on_panel_refresh)

    def _on_panel_refresh(self) -> None:
        if self._refresh_job is None:
            self._refresh_job = self.after_idle(self._refresh_from_panel)

    def _refresh_from_panel(self) -> None:
        """Follow a panel refresh; the grid only rebuilds the cells on screen."""
        self._refresh_job = None
        if not self.winfo_exists():
            return
        self._intensity_combo.configure(values=self._panel.intensity_choices())
        if self._current_state() != self._shown:
            self._rebuild()
        self._sync_selection()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Show:").pack(side="left")
        self._show_var = tk.StringVar(value=_FILTERS[0])
        ctk.CTkComboBox(
            top,
            variable=self._show_var,
            values=list(_FILTERS),
            state="readonly",
            width=90,
            command=lambda _v: self._rebuild(),
        ).pack(side="left", padx=(4, 8))

        ctk.CTkLabel(top, text="Filter:").pack(side="left")
        self._filter_var = tk.StringVar()
        debounced_trace(self, self._filter_var, self._rebuild)
        ctk.CTkEntry(top, textvariable=self._filter_var).pack(
            side="left", fill="x", expand=True, padx=(4, 8)
        )
        ctk.CTkButton(
            top,
            text="Close",
            width=64,
            height=28,
            fg_color=("gray70", "gray35"),
            command=self.destroy,
        ).pack(side="right")

        self._grid = VirtualIconGrid(
            self,
            self._on_grid_select,
            multi=True,
            cell_w=_CELL_W,
            cell_h=_CELL_H,
            pad=_CELL_PAD,
            icon_size=_IMAGE_SIZE[0],
            icon_height=_IMAGE_SIZE[1],
        )
        self._grid.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        add_tooltip(self._grid._canvas, MULTI_SELECT_TIP)

        bar = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        bar.pack(fill="x", padx=6, pady=(0, 8))

        self._sel_lbl = ctk.CTkLabel(
            bar,
            text="No bonfire selected",
            font=("Inter", 10, "bold"),
            anchor="w",
            text_color=("gray50", "gray60"),
        )
        self._sel_lbl.pack(fill="x", padx=10, pady=(8, 4))

        actions = ctk.CTkFrame(bar, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 10))
        self._light_btn = ctk.CTkButton(
            actions, text="Light", width=80, command=self._do_light
        )
        self._light_btn.pack(side="left", padx=(0, 4))
        self._unlight_btn = ctk.CTkButton(
            actions, text="Unlight", width=80, command=self._do_unlight
        )
        self._unlight_btn.pack(side="left", padx=4)
        ctk.CTkLabel(actions, text="Intensity:").pack(side="left", padx=(12, 4))
        # Shares the panel's variable, so both show the same intensity.
        self._intensity_combo = ctk.CTkComboBox(
            actions,
            variable=self._panel._intensity_var,
            values=self._panel.intensity_choices(),
            state="readonly",
            width=70,
            command=lambda _v: self._sync_buttons(),
        )
        self._intensity_combo.pack(side="left")
        self._intensity_btn = ctk.CTkButton(
            actions, text="Set Intensity", width=100, command=self._do_set_intensity
        )
        self._intensity_btn.pack(side="left", padx=4)
        self._unlock_btn = ctk.CTkButton(
            actions, text="Unlock All", width=100, command=self._do_unlock_all
        )
        self._unlock_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Grid
    # ------------------------------------------------------------------

    def _visible_ids(self) -> list[int]:
        show = self._show_var.get()
        query = self._filter_var.get().strip().lower()
        ids = []
        for bonfire_id in self._panel._ids:
            lit = self._panel._lit[bonfire_id]
            if (show == "Lit" and not lit) or (show == "Unlit" and lit):
                continue
            if query and query not in BONFIRES[bonfire_id].lower():
                continue
            ids.append(bonfire_id)
        return ids

    def _current_state(self) -> dict[int, tuple[bool, int, bool]]:
        panel = self._panel
        return {
            bonfire_id: (
                panel._lit[bonfire_id],
                panel._intensities[bonfire_id],
                bonfire_id == panel._last_rested,
            )
            for bonfire_id in self._visible_ids()
        }

    def _rebuild(self) -> None:
        """Rebuild the grid from the panel's current bonfire data. Selected
        bonfires that are still shown stay selected."""
        self._shown = self._current_state()
        entries = []
        for bonfire_id, (lit, intensity, last_rested) in self._shown.items():
            name = BONFIRES[bonfire_id]
            entries.append(
                GridEntry(
                    bonfire_id,
                    f"{name}\n{_state_text(lit, intensity, last_rested)}",
                    name.lower(),
                    lambda b=bonfire_id, lit=lit: self._picture(b, lit),
                )
            )
        self._grid.set_entries(entries, keep_selection=True)

    @staticmethod
    def _picture(bonfire_id: int, lit: bool):
        from er_save_manager.games.DS2.icon_manager import get_bonfire_icon

        img = get_bonfire_icon(bonfire_id)
        if img is not None and not lit:
            img = _unlit_picture(img)
        return img

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_grid_select(self, _keys: list) -> None:
        self._sync_selection()

    def _sync_selection(self) -> None:
        """Select the same bonfires in the panel's tree and update the label
        and buttons from the panel's state."""
        panel = self._panel
        rows = panel._tree.get_children()
        selected = self._grid.selected
        panel._tree.selection_set(
            [rows[panel._ids.index(b)] for b in selected if b in panel._ids]
        )
        panel._on_selection()

        if not selected:
            self._sel_lbl.configure(
                text="No bonfire selected", text_color=("gray50", "gray60")
            )
        else:
            names = [BONFIRES[b] for b in selected]
            text = names[0] if len(names) == 1 else f"{len(names)} bonfires"
            self._sel_lbl.configure(text=f"Selected: {text}", text_color=_SELECTED_TEXT)
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        """Mirror the enabled state of the panel's matching buttons."""
        panel = self._panel
        panel._update_buttons()
        for mine, theirs in (
            (self._light_btn, panel._light_button),
            (self._unlight_btn, panel._unlight_button),
            (self._intensity_btn, panel._set_intensity_button),
            (self._unlock_btn, panel._unlock_button),
        ):
            mine.configure(state=theirs.cget("state"))

    # ------------------------------------------------------------------
    # Actions, delegated to the panel's own handlers
    # ------------------------------------------------------------------

    # The panel refreshes after a change, which rebuilds this view.
    def _do_light(self) -> None:
        self._panel._on_light_selected()

    def _do_unlight(self) -> None:
        self._panel._on_unlight_selected()

    def _do_set_intensity(self) -> None:
        self._panel._on_set_intensity()

    def _do_unlock_all(self) -> None:
        self._panel._on_unlock_all()
