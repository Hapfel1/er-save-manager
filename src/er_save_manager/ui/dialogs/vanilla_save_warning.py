"""Online ban warning shown before a vanilla (.sl2) save is loaded.

The ban rules differ per game, so each game key maps to its own text. The
lists summarize community testing (The Grand Archives for Elden Ring and
DS3, Atvaark's DS2 guide); none of it is official.
"""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette

# Extensions of saves that reach the official servers: .sl2 on PC, the
# PlayStation memory.dat export for Elden Ring and Nightreign. DS3 PS4
# userdata files have no extension and are matched by is_ps_userdata.
# Seamless Co-op (.co2) saves never connect to them.
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
                    (
                        "Relics with effect combinations the game cannot roll "
                        "(an effect the relic's slot cannot roll, duplicate or "
                        "mixed character-specific effects)",
                        "spawned and imported relics must fit the game's own "
                        "roll tables (the effect pool of each slot, no "
                        "duplicate or second character-specific effect, "
                        "curses only where the game adds them), edits cannot "
                        "add such problems, and chalices only take relics of "
                        "the slot's color",
                    ),
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
                    (
                        "Attributes that do not fit your starting class",
                        "attributes are limited to the class minimum and 99",
                    ),
                    "A level that does not match your attributes",
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
                    (
                        "Attributes that do not fit your level or starting class",
                        "attributes are limited to the class minimum and 99, "
                        "and the level is recalculated from them",
                    ),
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


# Same checks on PS4; the ban lands on the PlayStation Network account.
_GAME_TEXT["dark_souls_3_ps4"] = (
    "The game checks stats, world flags and inventory when the save "
    "loads and every time it saves, offline included. A flagged save is "
    "soft banned with no warning beforehand. The ban is tied to the "
    "PlayStation Network account, not the save, and can only be lifted "
    "by appealing to Bandai Namco support.",
    _GAME_TEXT["dark_souls_3"][1],
)


def is_vanilla_save(save_path: str) -> bool:
    from er_save_manager.games.DS3.parser import is_ps_userdata

    return save_path.lower().endswith(VANILLA_SUFFIXES) or is_ps_userdata(save_path)


def warning_key(game_key: str, save_path: str) -> str:
    """_GAME_TEXT key for a save: DS3 PS4 userdata files get their own text."""
    from er_save_manager.games.DS3.parser import is_ps_userdata

    if game_key == "dark_souls_3" and is_ps_userdata(save_path):
        return "dark_souls_3_ps4"
    return game_key


class VanillaSaveWarningDialog(ctk.CTkToplevel):
    """Per-game ban warning. show() returns True when the user continues."""

    def __init__(self, parent, game_key: str, game_name: str, file_name: str):
        super().__init__(parent)
        # Hidden until built to prevent a white flash on Windows.
        self.withdraw()
        self.attributes("-alpha", 0)
        self.title("Vanilla Save File")
        self.resizable(False, False)
        self.transient(parent)

        self._continue = False
        self.dont_show_again = False
        self._dont_show_var = tk.BooleanVar(value=False)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._build_ui(game_key, game_name, file_name)

        ds.finish(self, parent)

    def _build_ui(self, game_key: str, game_name: str, file_name: str):
        intro, sections = _GAME_TEXT.get(game_key, ("", []))
        wrap = 520

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        ds.button_row(
            main,
            [
                {"text": "Continue", "command": self._on_continue},
                {"text": "Cancel", "command": self._on_cancel, "primary": False},
            ],
        )
        ctk.CTkCheckBox(
            main,
            text="Don't show this warning again",
            font=ds.FONT,
            variable=self._dont_show_var,
        ).pack(side=tk.BOTTOM, anchor="w", pady=(12, 0))

        ds.header(
            main, f"Vanilla {game_name} save", icon=".", icon_color=palette.PURPLE_TEXT
        )
        ctk.CTkLabel(
            main,
            text=f"{file_name} - edits can get your account banned online.",
            font=ds.FONT,
            text_color=ds.MUTED,
            anchor="w",
            wraplength=wrap,
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(4, 0))

        def build(body):
            if intro:
                ctk.CTkLabel(
                    body,
                    text=intro,
                    font=ds.FONT,
                    wraplength=wrap,
                    justify=tk.LEFT,
                    anchor="w",
                ).pack(fill=tk.X, pady=(0, 4))

            for heading, bullets in sections:
                ctk.CTkLabel(body, text=heading, font=ds.BOLD, anchor="w").pack(
                    fill=tk.X, pady=(8, 2)
                )
                group = ctk.CTkFrame(body, fg_color=ds.BOX, corner_radius=8)
                group.pack(fill=tk.X)
                for i, bullet in enumerate(bullets):
                    text, blocked = (
                        (bullet, None) if isinstance(bullet, str) else bullet
                    )
                    top = 8 if i == 0 else 2
                    bottom = 8 if i == len(bullets) - 1 else 2
                    ctk.CTkLabel(
                        group,
                        text=f"•  {text}",
                        font=ds.FONT,
                        wraplength=wrap - 24,
                        justify=tk.LEFT,
                        anchor="w",
                    ).pack(fill=tk.X, padx=12, pady=(top, 0 if blocked else bottom))
                    if blocked:
                        ctk.CTkLabel(
                            group,
                            text=f"Not possible with the save manager: {blocked}.",
                            font=ds.SMALL,
                            text_color=palette.PURPLE_TEXT,
                            wraplength=wrap - 48,
                            justify=tk.LEFT,
                            anchor="w",
                        ).pack(fill=tk.X, padx=(28, 12), pady=(0, bottom))

            ctk.CTkLabel(
                body,
                text=_GUARANTEE_NOTE,
                font=ds.SMALL,
                text_color=palette.PURPLE_TEXT,
                wraplength=wrap,
                justify=tk.LEFT,
                anchor="w",
            ).pack(fill=tk.X, pady=(12, 0))

        ds.content(main, build, max_height=460, width=wrap + 10, pady=(12, 0))

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
