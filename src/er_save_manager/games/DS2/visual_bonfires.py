"""
Visual bonfire popup for DS2.

Shows every bonfire of the slot as its picture, with unlit ones greyed out.
Selecting pictures selects the matching rows in the bonfire panel's own tree,
and the actions run the panel's own handlers, so the confirmation, backup,
write and the last rested rule stay in one place.
"""

from __future__ import annotations

import tkinter as tk
from collections import deque
from typing import TYPE_CHECKING

import customtkinter as ctk

from er_save_manager.games.DS2.bonfire_database import BONFIRES
from er_save_manager.games.DS2.save import BONFIRE_MAX_INTENSITY
from er_save_manager.ui import palette
from er_save_manager.ui.utils import center_window, debounced_trace

if TYPE_CHECKING:
    from PIL import Image as PILImage

    from er_save_manager.games.DS2.bonfire_tab import DS2BonfirePanel

# The stored pictures are 147x82.
_IMAGE_SIZE = (147, 82)
_CELL_W = 172
_CELL_H = 138
_CELL_PAD = 4
_SCROLLBAR_W = 24
_DEFAULT_COLS = 4
_BATCH = 12
_DELAY_MS = 8
# Brightness left on an unlit bonfire's greyed picture.
_UNLIT_BRIGHTNESS = 0.45
_SELECTED_BORDER = palette.PURPLE_TEXT
_FILTERS = ("All", "Lit", "Unlit")
# Bit of a Tk event's state that is set while Ctrl is held.
_CONTROL_MASK = 0x4


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
        self._cols = _DEFAULT_COLS
        self._buttons: dict[int, ctk.CTkButton] = {}  # bonfire id -> cell
        # (lit, intensity, last rested) each cell currently shows, and its image
        self._cell_state: dict[int, tuple[bool, int, bool]] = {}
        self._cell_images: dict[int, ctk.CTkImage | None] = {}
        self._order: list[int] = []  # shown bonfire ids, in grid order
        self._selected: set[int] = set()
        self._ctk_images: list = []
        self._pending: deque[int] = deque()
        self._batch_job: str | None = None
        self._resize_job: str | None = None
        self._grid_count = 0

        w = _DEFAULT_COLS * (_CELL_W + _CELL_PAD * 2) + 12 + _SCROLLBAR_W + 30
        self.title("Visual Bonfires")
        self.geometry(f"{w}x760")
        self.minsize(520, 480)
        self.transient(parent)
        self.attributes("-alpha", 0)
        self.update_idletasks()
        center_window(self, w, 760, parent=parent, align_top=True)
        self.attributes("-alpha", 1)
        self.lift()
        self.focus_force()

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
        """Follow a panel refresh. When the same bonfires are still shown,
        only cells whose state changed are updated; rebuilding every button
        stalls the window (and the toast the panel shows) for ~0.3s."""
        self._refresh_job = None
        if not self.winfo_exists():
            return
        if self._batch_job is not None or self._visible_ids() != self._order:
            self._rebuild()
            return
        for bonfire_id, button in self._buttons.items():
            if self._cell_state.get(bonfire_id) != self._panel_state(bonfire_id):
                text, text_color, image = self._cell_content(bonfire_id)
                button.configure(text=text, text_color=text_color, image=image)
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

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self._scroll.bind("<Configure>", self._on_scroll_resize)

        bar = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        bar.pack(fill="x", padx=6, pady=(0, 8))

        self._sel_lbl = ctk.CTkLabel(
            bar,
            text="No bonfire selected",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            text_color=("gray50", "gray60"),
        )
        self._sel_lbl.pack(fill="x", padx=10, pady=(8, 4))

        actions = ctk.CTkFrame(bar, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 4))
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
        ctk.CTkComboBox(
            actions,
            variable=self._panel._intensity_var,
            values=[str(n) for n in range(1, BONFIRE_MAX_INTENSITY + 1)],
            state="readonly",
            width=70,
            command=lambda _v: self._sync_buttons(),
        ).pack(side="left")
        self._intensity_btn = ctk.CTkButton(
            actions, text="Set Intensity", width=100, command=self._do_set_intensity
        )
        self._intensity_btn.pack(side="left", padx=4)
        self._unlock_btn = ctk.CTkButton(
            actions, text="Unlock All", width=100, command=self._do_unlock_all
        )
        self._unlock_btn.pack(side="right")

        ctk.CTkLabel(
            bar,
            text="Click selects a bonfire, Ctrl+click adds or removes one.",
            text_color=("gray40", "gray60"),
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 8))

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

    def _rebuild(self) -> None:
        """Rebuild the grid from the panel's current bonfire data. Selected
        bonfires that are still shown stay selected."""
        if self._batch_job is not None:
            self.after_cancel(self._batch_job)
            self._batch_job = None
        for button in self._buttons.values():
            button.destroy()
        self._buttons.clear()
        self._ctk_images.clear()
        self._cell_state.clear()
        self._cell_images.clear()

        self._order = self._visible_ids()
        self._selected &= set(self._order)
        self._grid_count = 0
        self._pending = deque(self._order)
        self._build_next_batch()
        self._sync_selection()

    def _build_next_batch(self) -> None:
        if not self.winfo_exists():
            return

        for _ in range(_BATCH):
            if not self._pending:
                break
            bonfire_id = self._pending.popleft()
            text, text_color, ctk_img = self._cell_content(bonfire_id)
            button = ctk.CTkButton(
                self._scroll,
                image=ctk_img,
                text=text,
                compound="top",
                width=_CELL_W,
                height=_CELL_H,
                font=("Segoe UI", 10),
                fg_color=("gray82", "gray18"),
                hover_color=("gray70", "gray28"),
                text_color=text_color,
                border_color=_SELECTED_BORDER,
                border_width=0,
                anchor="center",
            )
            if getattr(button, "_text_label", None) is not None:
                button._text_label.configure(wraplength=_CELL_W - 8, justify="center")
            button.bind(
                "<Button-1>", lambda e, b=bonfire_id: self._on_click(b, e), add="+"
            )
            self._buttons[bonfire_id] = button
            row, col = divmod(self._grid_count, self._cols)
            button.grid(
                row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew"
            )
            self._grid_count += 1
            self._paint_selection(bonfire_id)

        if self._pending:
            self._batch_job = self.after(_DELAY_MS, self._build_next_batch)
        else:
            self._batch_job = None
            self._layout_grid()

    def _panel_state(self, bonfire_id: int) -> tuple[bool, int, bool]:
        return (
            self._panel._lit[bonfire_id],
            self._panel._intensities[bonfire_id],
            bonfire_id == self._panel._last_rested,
        )

    def _cell_content(self, bonfire_id: int):
        """Text, text color and image for a cell, from the panel's state.
        The image is only rebuilt when the bonfire's lit state changed."""
        from er_save_manager.games.DS2.icon_manager import get_bonfire_icon

        lit, intensity, last_rested = self._panel_state(bonfire_id)
        previous = self._cell_state.get(bonfire_id)
        if previous is not None and previous[0] == lit:
            ctk_img = self._cell_images[bonfire_id]
        else:
            img = get_bonfire_icon(bonfire_id)
            ctk_img = None
            if img is not None:
                if not lit:
                    img = _unlit_picture(img)
                ctk_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=_IMAGE_SIZE
                )
                self._ctk_images.append(ctk_img)
            self._cell_images[bonfire_id] = ctk_img
        self._cell_state[bonfire_id] = (lit, intensity, last_rested)
        text = f"{BONFIRES[bonfire_id]}\n{_state_text(lit, intensity, last_rested)}"
        text_color = ("gray10", "gray90") if lit else ("gray40", "gray55")
        return text, text_color, ctk_img

    def _layout_grid(self) -> None:
        for index, bonfire_id in enumerate(self._order):
            button = self._buttons.get(bonfire_id)
            if button is None:
                continue
            row, col = divmod(index, self._cols)
            button.grid(
                row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew"
            )
        self._scroll.update_idletasks()
        canvas = self._scroll._parent_canvas
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_scroll_resize(self, _event) -> None:
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._reflow)

    def _reflow(self) -> None:
        self._resize_job = None
        available = max(1, self._scroll.winfo_width() - _SCROLLBAR_W)
        new_cols = max(1, available // (_CELL_W + _CELL_PAD * 2))
        if new_cols != self._cols:
            self._cols = new_cols
            self._layout_grid()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_click(self, bonfire_id: int, event) -> None:
        if event.state & _CONTROL_MASK:
            self._selected ^= {bonfire_id}
        else:
            self._selected = {bonfire_id}
        for shown in self._order:
            self._paint_selection(shown)
        self._sync_selection()

    def _paint_selection(self, bonfire_id: int) -> None:
        button = self._buttons.get(bonfire_id)
        if button is not None:
            button.configure(border_width=2 if bonfire_id in self._selected else 0)

    def _sync_selection(self) -> None:
        """Select the same bonfires in the panel's tree and update the label
        and buttons from the panel's state."""
        panel = self._panel
        rows = panel._tree.get_children()
        panel._tree.selection_set(
            [rows[panel._ids.index(b)] for b in self._selected if b in panel._ids]
        )
        panel._on_selection()

        if not self._selected:
            self._sel_lbl.configure(
                text="No bonfire selected", text_color=("gray50", "gray60")
            )
        else:
            names = [BONFIRES[b] for b in self._order if b in self._selected]
            text = names[0] if len(names) == 1 else f"{len(names)} bonfires"
            self._sel_lbl.configure(
                text=f"Selected: {text}", text_color=_SELECTED_BORDER
            )
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
