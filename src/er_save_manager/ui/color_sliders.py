"""Red, green and blue sliders (0-255) with a swatch, as in the games' menus."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _to_rgb(rgba: tuple[float, ...]) -> list[int]:
    return [max(0, min(255, round(v * 255))) for v in rgba[:3]]


class ColorSliders:
    """rgb()/set_rgb() use u8 values; rgba()/set_rgba() floats from 0 to 1."""

    def __init__(self, parent, title: str) -> None:
        self.alpha = 1.0
        self._loaded: tuple[float, float, float, float] | None = None
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        head = ctk.CTkFrame(self.frame, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text=title, font=ds.BOLD).pack(side="left")
        self.swatch = ctk.CTkFrame(
            head, width=48, height=20, corner_radius=4, border_width=1
        )
        self.swatch.pack(side="left", padx=10)
        self.vars = []
        for name in ("Red", "Green", "Blue"):
            row = ctk.CTkFrame(self.frame, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=name, width=60, anchor="w").pack(side="left")
            var = tk.IntVar(value=0)
            ctk.CTkSlider(
                row,
                from_=0,
                to=255,
                number_of_steps=255,
                variable=var,
                command=lambda _v: self._update_swatch(),
                width=220,
            ).pack(side="left", padx=6)
            ctk.CTkLabel(row, textvariable=var, width=36, anchor="e").pack(side="left")
            self.vars.append(var)

    def _update_swatch(self) -> None:
        self.swatch.configure(fg_color=_rgb_hex(self.rgb()))

    def rgb(self) -> tuple[int, int, int]:
        return tuple(int(v.get()) for v in self.vars)

    def set_rgb(self, rgb) -> None:
        for var, value in zip(self.vars, rgb, strict=True):
            var.set(int(value))
        self._update_swatch()

    def rgba(self) -> tuple[float, float, float, float]:
        # Unmoved sliders keep the stored floats instead of re-rounding them.
        if self._loaded is not None and list(self.rgb()) == _to_rgb(self._loaded):
            return self._loaded
        return (*(v / 255 for v in self.rgb()), self.alpha)

    def set_rgba(self, rgba) -> None:
        self._loaded = tuple(rgba)
        self.alpha = rgba[3]
        self.set_rgb(_to_rgb(rgba))
