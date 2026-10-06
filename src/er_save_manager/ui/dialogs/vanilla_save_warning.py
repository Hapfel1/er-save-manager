"""Online ban warning shown before a vanilla (.sl2) save is loaded.

The ban rules differ per game, so each game key maps to its own text. The
lists summarize community testing (The Grand Archives for Elden Ring and
DS3, Atvaark's DS2 guide); none of it is official.
"""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.utils import center_window, force_render_dialog

# Extensions of saves that reach the official servers: .sl2 on PC, the
# PlayStation memory.dat export for Elden Ring. Seamless Co-op (.co2) saves
# never connect to them.
VANILLA_SUFFIXES = (".sl2", ".dat")

_GUARANTEE_NOTE = (
    "Nothing here is a 100% guarantee. These lists come from community "
    "testing, not from FromSoftware or Bandai Namco, and detection can change "
    "with any patch. If you think an edit might get you banned, it probably will."
)

# A bullet is its text, or (text, how the editor's validation blocks it)
# when the save manager cannot produce that edit.
_Bullet = str | tuple[str, str]

# (intro, [(section heading, [bullets])]) per game key.
_GAME_TEXT: dict[str, tuple[str, list[tuple[str, list[_Bullet]]]]] = {
    "elden_ring": (
        "Vanilla saves are the ones used on the official servers. Edits that "
        "stay in the save are checked once you play online with it.",
        [
            (
                "Generally safe",
                [
                    "Corruption fixes and teleports",
                    "Spawning normally obtainable items (key items included) "
                    "at any quantity, and runes",
                    "NG+ cycle, gestures, last grace, event flags and invasion zones",
                ],
            ),
            (
                "Known to ban",
                [
                    (
                        "Attributes that do not fit your level or starting class",
                        "attributes are limited to the class minimum and 99, "
                        "and the level is recalculated from them",
                    ),
                    (
                        "Equipping or using cut or unused content online",
                        "cut items and gestures are not offered",
                    ),
                    (
                        "Character names longer than 16 characters",
                        "names are limited to 16 characters",
                    ),
                ],
            ),
            (
                "Offline",
                ["Playing only offline with an edited save carries no ban risk."],
            ),
        ],
    ),
    "nightreign": (
        "Nightreign uses Easy Anti-Cheat like Elden Ring, but there is no "
        "confirmed list of what gets a save banned.",
        [
            (
                "Reported",
                [
                    "Relics with effect combinations the game cannot roll "
                    "(wrong effect for the slot color, duplicate or mixed "
                    "character-specific effects)",
                ],
            ),
            (
                "Offline",
                ["Playing only offline with an edited save carries no ban risk."],
            ),
        ],
    ),
    "dark_souls_3": (
        "The game checks stats, world flags and inventory when the save "
        "loads and every time it saves, offline included. A flagged save is "
        "soft banned on the next weekly wave (Wednesday 2:00 UTC) with no "
        "warning beforehand. The ban is tied to the Steam account, not the "
        "save, and can only be lifted by appealing to Bandai Namco support.",
        [
            (
                "Generally safe",
                [
                    "Spawning items, at any quantity or upgrade level (item "
                    "bans were disabled in early 2020)",
                    "Reviving bosses and changing character flags",
                ],
            ),
            (
                "Known to ban",
                [
                    "Attributes that do not fit your level or starting class",
                    "Attuning DLC spells without owning that DLC",
                    "Risky: world flags such as restoring fog walls",
                ],
            ),
        ],
    ),
    "dark_souls_2": (
        "The save is checked the next time you go online, so editing offline "
        "does not avoid a ban. Soft bans in Dark Souls II are permanent and "
        "apply to the whole Steam account: you only match with other banned "
        "players.",
        [
            (
                "Known to ban",
                [
                    "Editing attributes",
                    (
                        "Changing soul memory, or a soul level that does not "
                        "match soul memory",
                        "soul memory cannot be edited directly and is raised "
                        "to match the level when stats are saved",
                    ),
                    (
                        "Items with invalid infusions or upgrade levels",
                        "upgrades are capped at each item's maximum and only "
                        "infusions the weapon allows can be applied",
                    ),
                    "Items from areas you have not reached yet",
                ],
            ),
            (
                "Generally safe",
                ["No edit is confirmed safe for online play."],
            ),
        ],
    ),
    "dark_souls_remastered": (
        "Save data is checked when you go online. A soft ban limits "
        "matchmaking to other banned players.",
        [
            (
                "Reported to ban",
                [
                    "Attributes that do not fit your level or starting class",
                    "Cut content and other items that cannot be obtained "
                    "in normal play",
                    (
                        "Upgrade levels above an item's maximum",
                        "upgrades are capped at each item's maximum",
                    ),
                    (
                        "Quantities above the in-game maximum",
                        "quantities are capped at the in-game maximum",
                    ),
                ],
            ),
            (
                "Generally safe",
                [
                    "Normally obtainable items within their maximum quantity",
                ],
            ),
        ],
    ),
}


def is_vanilla_save(save_path: str) -> bool:
    return save_path.lower().endswith(VANILLA_SUFFIXES)


class VanillaSaveWarningDialog(ctk.CTkToplevel):
    """Per-game ban warning. show() returns True when the user continues."""

    def __init__(self, parent, game_key: str, game_name: str, file_name: str):
        super().__init__(parent)
        # Hidden until built to prevent a white flash on Windows.
        self.attributes("-alpha", 0)
        self.title("Vanilla Save File")
        self.resizable(False, False)
        self.transient(parent)

        self._continue = False
        self.dont_show_again = False
        self._dont_show_var = tk.BooleanVar(value=False)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._build_ui(game_key, game_name, file_name)

        center_window(self, 600, 640, parent=parent)
        force_render_dialog(self)
        self.attributes("-alpha", 1)
        self.grab_set()

    def _build_ui(self, game_key: str, game_name: str, file_name: str):
        intro, sections = _GAME_TEXT.get(game_key, ("", []))

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill=tk.X)
        ctk.CTkLabel(
            header,
            text="!",
            font=("Segoe UI Semibold", 32, "bold"),
            text_color=palette.PURPLE_TEXT,
            width=40,
        ).pack(side=tk.LEFT, anchor="n", padx=(0, 12))
        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkLabel(
            title_col,
            text=f"Vanilla {game_name} save",
            font=("Segoe UI Semibold", 18, "bold"),
            anchor="w",
        ).pack(fill=tk.X)
        ctk.CTkLabel(
            title_col,
            text=f"{file_name} - edits can get your account banned online.",
            font=("Segoe UI", 13),
            text_color=("gray40", "gray70"),
            anchor="w",
            wraplength=480,
            justify=tk.LEFT,
        ).pack(fill=tk.X)

        body = ctk.CTkScrollableFrame(main, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        wrap = 500

        if intro:
            ctk.CTkLabel(
                body,
                text=intro,
                font=("Segoe UI", 13),
                wraplength=wrap,
                justify=tk.LEFT,
                anchor="w",
            ).pack(fill=tk.X, pady=(0, 6))

        for heading, bullets in sections:
            ctk.CTkLabel(
                body,
                text=heading,
                font=("Segoe UI Semibold", 14, "bold"),
                anchor="w",
            ).pack(fill=tk.X, pady=(8, 2))
            for bullet in bullets:
                text, blocked = (bullet, None) if isinstance(bullet, str) else bullet
                ctk.CTkLabel(
                    body,
                    text=f"•  {text}",
                    font=("Segoe UI", 13),
                    wraplength=wrap - 16,
                    justify=tk.LEFT,
                    anchor="w",
                ).pack(fill=tk.X, padx=(8, 0))
                if blocked:
                    ctk.CTkLabel(
                        body,
                        text=f"Not possible with the save manager: {blocked}.",
                        font=("Segoe UI", 12),
                        text_color=palette.PURPLE_TEXT,
                        wraplength=wrap - 32,
                        justify=tk.LEFT,
                        anchor="w",
                    ).pack(fill=tk.X, padx=(24, 0), pady=(0, 2))

        ctk.CTkLabel(
            body,
            text=_GUARANTEE_NOTE,
            font=("Segoe UI", 12),
            text_color=palette.PURPLE_TEXT,
            wraplength=wrap,
            justify=tk.LEFT,
            anchor="w",
        ).pack(fill=tk.X, pady=(14, 0))

        ctk.CTkCheckBox(
            main,
            text="Don't show this warning again",
            variable=self._dont_show_var,
        ).pack(anchor="w", pady=(12, 0))

        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(pady=(12, 0))
        ctk.CTkButton(
            btn_row,
            text="Continue",
            command=self._on_continue,
            width=120,
            font=("Segoe UI Semibold", 18),
        ).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(
            btn_row,
            text="Cancel",
            command=self._on_cancel,
            width=120,
            font=("Segoe UI Semibold", 18),
        ).pack(side=tk.LEFT, padx=5)

    def _on_continue(self):
        self._continue = True
        self.dont_show_again = self._dont_show_var.get()
        self.destroy()

    def _on_cancel(self):
        self._continue = False
        self.destroy()

    def show(self) -> bool:
        self.wait_window()
        return self._continue
