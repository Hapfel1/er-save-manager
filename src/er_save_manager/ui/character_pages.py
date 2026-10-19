"""Top-level tab made of pages that follow the main window's character bar.

Used where a game's pages are grouped differently from the shared tab layout
(Character Editor, Appearance, World State, NPCs & Bosses, Event Flags), so
existing page classes can be placed under a new top-level tab unchanged.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from er_save_manager.ui import palette


class CharacterPagesTab:
    """
    Args:
        parent: the top-level tab frame.
        title: header text.
        pages: (sub-tab name, build) pairs; build(parent) returns a page with
            load_slot(slot_index) and setup_steps() or setup_ui(). A single
            page is placed without a sub-tab row.
    """

    def __init__(
        self,
        parent,
        title: str,
        pages: list[tuple[str, Callable[[object], object]]],
    ) -> None:
        self.parent = parent
        self._title = title
        self._builders = pages
        self.pages: dict[str, object] = {}
        self.tabview: ctk.CTkTabview | None = None
        self._slot = -1

    def setup_ui(self) -> None:
        for _ in self.setup_steps():
            pass

    def setup_steps(self):
        """Build one page per stage (gui.py resumes it one stage per turn)."""
        outer = ctk.CTkFrame(self.parent, corner_radius=12)
        outer.pack(fill="both", expand=True, pady=(0, 10))
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text=self._title, font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        if len(self._builders) > 1:
            self.tabview = ctk.CTkTabview(
                outer,
                fg_color=("gray90", "gray20"),
                segmented_button_fg_color=("gray80", "gray35"),
                segmented_button_selected_color=palette.PURPLE,
                segmented_button_unselected_color=("gray70", "gray30"),
            )
            self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for name, build in self._builders:
            if self.tabview is not None:
                parent = self.tabview.add(name)
            else:
                parent = ctk.CTkFrame(outer, fg_color="transparent")
                parent.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            page = build(parent)
            steps = getattr(page, "setup_steps", None)
            if steps is not None:
                yield from steps()
            else:
                page.setup_ui()
            self.pages[name] = page
            # A character may have been picked while the tab was building.
            page.load_slot(self._slot)
            yield

    def load_slot(self, slot_index: int) -> None:
        self._slot = slot_index
        for page in self.pages.values():
            page.load_slot(slot_index)

    def select(self, name: str) -> None:
        if self.tabview is not None:
            self.tabview.set(name)
