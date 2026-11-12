"""Copy the loaded save to another mod extension (.sl2, .co2, .cnv, .cnvco2)
or another platform (PlayStation, Switch 2).

Shared by every game's Character Management tab. The checks and file writes
live in games/extension_copy.py.
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from er_save_manager.games import extension_copy as ec
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import guard_before_write
from er_save_manager.ui.toast import notify
from er_save_manager.ui.utils import patch_combo_scroll, pick_folder

_WRAP = 520


_CUSTOM = "Custom..."
_OTHER_ACCOUNT = "Other SteamID..."


def _target_label(flavor: ec.Flavor) -> str:
    if flavor.platform == ec.PC:
        return f"{flavor.ext}  ({flavor.label})"
    return flavor.label


class ExtensionCopyDialog:
    def __init__(
        self,
        parent,
        game_key: str,
        source: Path,
        on_done: Callable[[str], None] | None = None,
    ):
        self.parent = parent
        self.game_key = game_key
        self.source = Path(source)
        self.on_done = on_done
        self.plan: ec.Plan | None = None
        self.vars: dict[int, tk.BooleanVar] = {}
        self.dests: dict[int, tk.StringVar] = {}
        self.dest_combos: dict[int, ctk.CTkComboBox] = {}
        self.slot_of_choice: dict[str, int] = {}
        self.limit_label = None
        self._pending = None
        self._busy = False

        self.source_platform = ec.source_platform(self.source)
        self.choices = ec.targets(game_key, self.source)
        self.key_of_label = {_target_label(f): f.ext for f in self.choices}
        # Chosen folder per target platform; the source's folder until changed
        self.folders: dict[str, Path] = {}
        self._accounts: list[tuple[str, int]] | None = None
        self.account_of_label: dict[str, int] = {}

        self.dialog = ds.create(parent, "Copy to Another Extension")
        main = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        _, (self.replace_btn, self.copy_btn, _cancel) = ds.button_row(
            main,
            [
                {
                    "text": "Replace Whole File",
                    "command": self._replace,
                    "primary": False,
                    "width": 150,
                },
                {"text": "Copy", "command": self._copy, "width": 120},
                {"text": "Cancel", "command": self.dialog.destroy, "primary": False},
            ],
        )

        ds.header(main, "Copy to Another Extension", font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main,
            text=self._intro(),
            font=ds.SMALL,
            text_color=ds.MUTED,
            wraplength=_WRAP,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(6, 10))

        row = ctk.CTkFrame(main, fg_color="transparent")
        row.pack(fill=tk.X)
        ctk.CTkLabel(row, text="Copy to:", font=ds.FONT).pack(side=tk.LEFT)
        labels = list(self.key_of_label) + [_CUSTOM]
        self.ext_var = tk.StringVar(value=labels[0])
        combo = ctk.CTkComboBox(
            row,
            variable=self.ext_var,
            values=labels,
            state="readonly",
            width=320,
            height=32,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            command=lambda _v: self._on_choice(),
        )
        combo.pack(side=tk.LEFT, padx=(10, 0))
        patch_combo_scroll(combo)
        self.custom_var = tk.StringVar()
        self.custom_entry = ctk.CTkEntry(
            row,
            textvariable=self.custom_var,
            placeholder_text=".co3",
            width=120,
            height=32,
            font=ds.FONT,
        )
        self.custom_entry.bind("<KeyRelease>", lambda _e: self._schedule_rebuild())

        self.options_host = ctk.CTkFrame(main, fg_color="transparent")
        self.options_host.pack(fill=tk.X)
        self._build_folder_row()
        self._build_account_row()

        self.body_host = ctk.CTkFrame(main, fg_color="transparent")
        self.body_host.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.dialog.bind("<Escape>", lambda _e: self.dialog.destroy())
        self._rebuild(refit=False)
        ds.finish(self.dialog, parent, min_width=600)

    def _intro(self) -> str:
        pc = [f for f in self.choices if f.platform == ec.PC]
        consoles = [
            "Switch 2" if f.platform == ec.SWITCH2 else f.label.split()[0]
            for f in ec.CONSOLE_TARGETS.get(self.game_key, {}).values()
        ]
        text = (
            "The game picks the save by extension: "
            + ", ".join(
                f"{e} {ec.FLAVORS[e].label}"
                for e in ec.target_extensions(self.game_key)
            )
            + ". Custom is for an extension set in the mod's own settings."
        )
        if pc and consoles:
            text += f" {' and '.join(consoles)} copies go into a folder you choose."
        return text + " The current file stays as it is."

    # ---- option rows ---------------------------------------------------

    def _build_folder_row(self) -> None:
        self.folder_row = ctk.CTkFrame(self.options_host, fg_color="transparent")
        ctk.CTkLabel(self.folder_row, text="Folder:", font=ds.FONT).pack(side=tk.LEFT)
        ds.button(
            self.folder_row, "Change Folder", self._choose_folder, width=130
        ).pack(side=tk.RIGHT)
        self.folder_label = ctk.CTkLabel(
            self.folder_row,
            text="",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
            justify=tk.LEFT,
            wraplength=_WRAP - 220,
        )
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 8))

    def _build_account_row(self) -> None:
        self.account_row = ctk.CTkFrame(self.options_host, fg_color="transparent")
        ctk.CTkLabel(self.account_row, text="Steam account:", font=ds.FONT).pack(
            side=tk.LEFT
        )
        self.account_var = tk.StringVar()
        self.account_combo = ctk.CTkComboBox(
            self.account_row,
            variable=self.account_var,
            values=[_OTHER_ACCOUNT],
            state="readonly",
            width=250,
            height=32,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            command=lambda _v: self._on_account(),
        )
        self.account_combo.pack(side=tk.LEFT, padx=(10, 0))
        patch_combo_scroll(self.account_combo)
        self.other_id_var = tk.StringVar()
        self.other_id_entry = ctk.CTkEntry(
            self.account_row,
            textvariable=self.other_id_var,
            placeholder_text="SteamID or profile link",
            width=190,
            height=32,
            font=ds.FONT,
        )

    def _target_platform(self) -> str | None:
        try:
            return ec.target_flavor(self.game_key, self._ext()).platform
        except ec.ExtensionCopyError:
            return None

    def _folder(self) -> Path | None:
        """Target folder, None for a copy next to the source."""
        platform = self._target_platform()
        if platform is None or platform == self.source_platform:
            return None
        return self.folders.get(platform, self.source.parent)

    def _choose_folder(self) -> None:
        platform = self._target_platform()
        if platform is None:
            return
        current = self.folders.get(platform, self.source.parent)
        chosen = pick_folder("Choose the Folder for the Copy", str(current))
        if chosen:
            self.folders[platform] = Path(chosen)
            self._rebuild()

    def _update_option_rows(self) -> None:
        folder = self._folder()
        if folder is not None:
            self.folder_label.configure(text=str(folder))
            self.folder_row.pack(fill=tk.X, pady=(8, 0))
        else:
            self.folder_row.pack_forget()
        plan = self.plan
        if plan is not None and plan.needs_steam_id and not plan.merges:
            self._fill_accounts(plan)
            self.account_row.pack(fill=tk.X, pady=(8, 0))
        else:
            self.account_row.pack_forget()

    def _load_accounts(self) -> list[tuple[str, int]]:
        if self._accounts is None:
            from er_save_manager.platform import PlatformUtils

            try:
                found = PlatformUtils.get_loginusers_steam_accounts()
            except Exception:
                found = []
            self._accounts = [(f"{name} ({sid})", sid) for sid, name in found]
        return self._accounts

    def _fill_accounts(self, plan: ec.Plan) -> None:
        from er_save_manager.games.game_profiles import (
            PROFILES_BY_KEY,
            _folder_name_to_steam64,
        )

        accounts = list(self._load_accounts())
        folder_id = _folder_name_to_steam64(
            plan.target.parent.name, PROFILES_BY_KEY[self.game_key]
        )
        if folder_id and folder_id not in {sid for _, sid in accounts}:
            accounts.insert(0, (f"Account {folder_id} (save folder)", folder_id))
        self.account_of_label = dict(accounts)
        labels = [label for label, _ in accounts] + [_OTHER_ACCOUNT]
        self.account_combo.configure(values=labels)
        if self.account_var.get() not in labels:
            default = next(
                (label for label, sid in accounts if sid == folder_id),
                labels[0],
            )
            self.account_var.set(default)
        self._on_account(rebuild=False)

    def _on_account(self, rebuild: bool = True) -> None:
        if self.account_var.get() == _OTHER_ACCOUNT:
            self.other_id_entry.pack(side=tk.LEFT, padx=(10, 0))
        else:
            self.other_id_entry.pack_forget()
        if rebuild:
            ds.refit(self.dialog)

    def _with_steam_id(self, then: Callable[[int | None], None]) -> None:
        """Call then with the chosen SteamID64, None when none is needed.
        A vanity profile link is looked up first, off the UI thread."""
        from er_save_manager.ui.tabs.steamid_patcher_tab import (
            fetch_vanity_steamid,
            parse_steam_input,
        )

        plan = self.plan
        if plan is None or not plan.needs_steam_id:
            then(None)
            return
        if self.account_var.get() not in self.account_of_label:
            # Replace Whole File on a target with characters: the row was
            # hidden, so the account of the target's folder is used.
            self._fill_accounts(plan)
        label = self.account_var.get()
        if label in self.account_of_label:
            then(self.account_of_label[label])
            return
        steamid, vanity, error = parse_steam_input(
            self.other_id_var.get(), "Steam account"
        )
        if error:
            CTkMessageBox.showerror("Invalid SteamID", error, parent=self.dialog)
            return
        if steamid:
            then(int(steamid))
            return

        self._busy = True
        self.copy_btn.configure(state="disabled")

        def finish(found: str | None, failure: Exception | None) -> None:
            self._busy = False
            self._update_buttons()
            if failure is not None or not found:
                CTkMessageBox.showerror(
                    "Steam Profile Not Found",
                    f"Could not look up the Steam profile {vanity}. Enter the "
                    "SteamID or a /profiles/ link instead."
                    + (f"\n\n{failure}" if failure else ""),
                    parent=self.dialog,
                )
                return
            self.other_id_var.set(found)
            then(int(found))

        def run() -> None:
            found = failure = None
            try:
                found = fetch_vanity_steamid(vanity)
            except Exception as e:
                failure = e
            try:
                self.dialog.after(0, lambda: finish(found, failure))
            except (RuntimeError, tk.TclError):
                pass

        threading.Thread(target=run, daemon=True).start()

    # ---- state ---------------------------------------------------------

    def _ext(self) -> str:
        if self.ext_var.get() == _CUSTOM:
            return self.custom_var.get()
        return self.key_of_label[self.ext_var.get()]

    def _on_choice(self) -> None:
        if self.ext_var.get() == _CUSTOM:
            self.custom_entry.pack(side=tk.LEFT, padx=(10, 0))
            self.custom_entry.focus_set()
        else:
            self.custom_entry.pack_forget()
        self._rebuild()

    def _schedule_rebuild(self) -> None:
        if self._pending is not None:
            self.dialog.after_cancel(self._pending)
        self._pending = self.dialog.after(400, self._rebuild)

    def _rebuild(self, refit: bool = True) -> None:
        self._pending = None
        for child in self.body_host.winfo_children():
            child.destroy()
        if self.ext_var.get() == _CUSTOM and not self.custom_var.get().strip():
            self.plan = None
            self._update_option_rows()
            self._update_buttons()
            if refit:
                ds.refit(self.dialog)
            return
        try:
            self.plan = ec.make_plan(
                self.game_key, self.source, self._ext(), self._folder()
            )
            error = None
        except ec.ExtensionCopyError as e:
            self.plan, error = None, str(e)
        self._update_option_rows()
        ds.content(self.body_host, lambda f: self._build_body(f, error), max_height=420)
        self._update_buttons()
        if refit:
            ds.refit(self.dialog)

    def _selected(self) -> list[int]:
        return [i for i, v in self.vars.items() if v.get()]

    def _pairs(self) -> list[tuple[int, int]]:
        """(source slot, target slot) for every checked character."""
        return [(i, self.slot_of_choice[self.dests[i].get()]) for i in self._selected()]

    def _duplicate_target(self) -> int | None:
        seen = set()
        for _, j in self._pairs():
            if j in seen:
                return j
            seen.add(j)
        return None

    def _update_buttons(self) -> None:
        plan = self.plan
        ok = plan is not None and not self._busy
        if plan is not None:
            n = len(self._selected())
            ok = ok and n > 0
            problem = ""
            if plan.merges:
                for i, combo in self.dest_combos.items():
                    combo.configure(
                        state="readonly" if self.vars[i].get() else "disabled"
                    )
                dup = self._duplicate_target()
                if dup is not None:
                    ok = False
                    problem = f"Two characters are set to go to slot {dup + 1}."
            if self.limit_label is not None:
                self.limit_label.configure(text=problem)
        self.copy_btn.configure(state="normal" if ok else "disabled")
        if plan is not None and plan.target_exists:
            self.replace_btn.pack(side=tk.RIGHT, padx=(8, 0), after=self.copy_btn)
        else:
            self.replace_btn.pack_forget()

    # ---- body ----------------------------------------------------------

    def _label(self, parent, text, color=None, font=None, pady=(0, 6), padx=0):
        ctk.CTkLabel(
            parent,
            text=text,
            font=font or ds.FONT,
            text_color=color,
            wraplength=_WRAP - padx,
            justify=tk.LEFT,
            anchor="w",
        ).pack(anchor="w", fill=tk.X, pady=pady, padx=(padx, 0))

    def _build_body(self, frame, error: str | None) -> None:
        # ds.content can call this twice (plain, then scrolling).
        self.vars = {}
        self.dests = {}
        self.dest_combos = {}
        self.slot_of_choice = {}
        self.limit_label = None
        if error is not None:
            self._label(frame, error, color=ds.ERROR)
            return
        plan = self.plan
        if not plan.cross_platform:
            # A copy to another platform shows its folder in the folder row.
            self._label(frame, str(plan.target), color=ds.MUTED, font=ds.SMALL)
        self._label(frame, self._target_status(plan), color=ds.INFO)
        flavor = plan.target_flavor
        if flavor.platform == ec.PC and flavor.ext not in ec.FLAVORS:
            self._label(
                frame,
                f"Checked as {flavor.label.lower()}: modded saves stay "
                "off the official servers, so Seamless Co-op items are allowed.",
                color=ds.MUTED,
                font=ds.SMALL,
            )
        if plan.cross_platform and not plan.merges:
            self._label(
                frame,
                self._platform_note(plan),
                color=ds.MUTED,
                font=ds.SMALL,
            )

        if not plan.characters:
            self._label(frame, "The save holds no characters.", color=ds.MUTED)
            return

        if plan.blocked:
            self._label(frame, ec.BAN_NOTE, color=ds.WARNING, pady=(4, 2))
        ctk.CTkLabel(frame, text="Characters", font=ds.BOLD).pack(
            anchor="w", pady=(6, 2)
        )
        box = ds.box(frame)
        # Copyable characters first, so the ones to pick are on top.
        for char in plan.copyable + plan.blocked:
            self._character_row(box, char)

        self.limit_label = ctk.CTkLabel(
            frame, text="", font=ds.FONT, text_color=ds.WARNING
        )
        self.limit_label.pack(anchor="w")

        if plan.merges and plan.free_slot_notes:
            self._label(
                frame,
                next(iter(plan.free_slot_notes.values())),
                color=ds.WARNING,
            )

    @staticmethod
    def _platform_note(plan: ec.Plan) -> str:
        if plan.target_flavor.platform == ec.PC:
            return (
                "The copy is a PC save. PC-only options (window size, keyboard "
                "keys) start at their defaults."
                if plan.game_key in ("elden_ring", "nightreign")
                else "The copy is a PC save."
            )
        return (
            "The copy is a console save, without the Steam account. Put it "
            "back on the console with the tool used to export the save."
        )

    def _target_status(self, plan: ec.Plan) -> str:
        name = plan.target_name
        if not plan.target_exists:
            return f"{name} does not exist yet; it is created."
        if not plan.merges:
            return (
                f"{name} exists and holds no characters; it is replaced "
                "(a backup is made first)."
            )
        names = ec.short_list([n for _, n in plan.target_characters])
        count = len(plan.target_characters)
        noun = "character" if count == 1 else "characters"
        free = len(plan.free_slots)
        free_text = (
            "no free slots"
            if not free
            else f"{free} free slot" + ("" if free == 1 else "s")
        )
        return (
            f"{name} holds {count} {noun} ({names}) and has {free_text}. "
            "Pick a slot for each character: a free one, or a character to "
            "replace. Its other characters stay (a backup is made first)."
        )

    def _choices(self) -> list[str]:
        """Target slot labels; fills slot_of_choice."""
        plan = self.plan
        occupied = dict(plan.target_characters)
        labels = []
        for j in range(ec.CHARACTER_SLOTS):
            if j in occupied:
                label = f"Slot {j + 1}: replace {occupied[j]}"
            else:
                label = f"Slot {j + 1} (free)"
            self.slot_of_choice[label] = j
            labels.append(label)
        return labels

    def _default_target(self) -> tuple[int, bool]:
        """(target slot, checked) for the next character: the next unused
        free slot, else the first unused occupied slot, unchecked."""
        used = {self.slot_of_choice[v.get()] for v in self.dests.values()}
        for j in self.plan.free_slots:
            if j not in used:
                return j, True
        for j, _ in self.plan.target_characters:
            if j not in used:
                return j, False
        return 0, False

    def _character_row(self, parent, char: ec.SourceCharacter) -> None:
        plan = self.plan
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, padx=12, pady=(8, 0))
        blocked = bool(char.blockers)
        default = not blocked
        line = ctk.CTkFrame(row, fg_color="transparent")
        line.pack(fill=tk.X)
        if plan.merges and not blocked:
            labels = self._choices()
            target, default = self._default_target()
            dest = tk.StringVar(value=labels[target])
            combo = ctk.CTkComboBox(
                line,
                variable=dest,
                values=labels,
                state="readonly",
                width=250,
                height=28,
                font=ds.SMALL,
                dropdown_font=ds.SMALL,
                command=lambda _v: self._update_buttons(),
            )
            combo.pack(side=tk.RIGHT)
            patch_combo_scroll(combo)
            ctk.CTkLabel(line, text="to", font=ds.SMALL, text_color=ds.MUTED).pack(
                side=tk.RIGHT, padx=8
            )
            self.dests[char.slot] = dest
            self.dest_combos[char.slot] = combo
        var = tk.BooleanVar(value=default)
        ctk.CTkCheckBox(
            line,
            text=f"Slot {char.slot + 1}: {char.name}",
            font=ds.FONT,
            variable=var,
            state="disabled" if blocked else "normal",
            command=self._update_buttons,
        ).pack(side=tk.LEFT)
        if not blocked:
            self.vars[char.slot] = var
        for reason in char.blockers:
            self._label(row, reason, color=ds.WARNING, font=ds.SMALL, padx=30)
        for note in char.notes:
            self._label(row, note, color=ds.MUTED, font=ds.SMALL, padx=30)
        ctk.CTkFrame(parent, fg_color="transparent", height=4).pack()

    # ---- actions -------------------------------------------------------

    def _finish(self, message: str) -> None:
        self.dialog.destroy()
        if self.on_done:
            self.on_done(message)

    def _fail(self, e: Exception) -> None:
        CTkMessageBox.showerror(
            "Copy Failed", f"The copy could not be written:\n{e}", parent=self.dialog
        )

    def _copy(self) -> None:
        plan = self.plan
        if plan is None:
            return
        if plan.merges:
            self._merge(plan)
            return
        slots = self._selected()

        def write(steam_id: int | None) -> None:
            try:
                ec.write_copy(plan, slots, steam_id)
                self._finish(f"Copied to {plan.target_name}")
            except Exception as e:
                self._fail(e)

        self._with_steam_id(write)

    def _merge(self, plan: ec.Plan) -> None:
        try:
            pairs = self._pairs()
            occupied = dict(plan.target_characters)
            replaced = [
                f"slot {j + 1} ({occupied[j]})" for _, j in pairs if j in occupied
            ]
            if replaced and not CTkMessageBox.askyesno(
                "Replace Characters",
                f"These characters in {plan.target_name} are overwritten: "
                + ", ".join(replaced)
                + ". A backup is made first.",
                parent=self.dialog,
            ):
                return
            ec.write_merge(plan, pairs)
            where = ", ".join(str(j + 1) for _, j in pairs)
            noun = "character" if len(pairs) == 1 else "characters"
            self._finish(
                f"Copied {len(pairs)} {noun} into {plan.target_name} (slots {where})"
            )
        except Exception as e:
            self._fail(e)

    def _replace(self) -> None:
        plan = self.plan
        if plan is None or not plan.target_exists:
            return
        # Ticked characters, or every character that can be copied.
        slots = self._selected() or [c.slot for c in plan.copyable]
        if not slots:
            CTkMessageBox.showerror(
                "Nothing to Copy",
                f"None of the characters can be copied to {plan.target_name}.",
                parent=self.dialog,
            )
            return
        names = ec.short_list(
            [c.name for c in plan.characters if c.slot in slots], shown=6
        )
        removed = ""
        if plan.target_characters:
            count = len(plan.target_characters)
            noun = "character" if count == 1 else "characters"
            removed = f" Its {count} {noun} are removed."
        if not CTkMessageBox.askyesno(
            "Replace Whole File",
            f"Replace all of {plan.target_name} with a copy of this save holding "
            f"{names}?{removed} A backup is made first.",
            parent=self.dialog,
        ):
            return

        def write(steam_id: int | None) -> None:
            try:
                ec.write_copy(plan, slots, steam_id)
                self._finish(f"Replaced {plan.target_name}")
            except Exception as e:
                self._fail(e)

        self._with_steam_id(write)


def open_extension_copy(
    parent,
    game_key: str,
    save_path,
    on_done: Callable[[str], None] | None = None,
    is_game_running: Callable[[], bool] | None = None,
) -> None:
    """Entry point for the header button and the Character Management tabs."""
    if not guard_before_write("copy the save to another extension"):
        return
    if not save_path:
        notify(parent, "Load a save file first.", "warning")
        return
    if is_game_running and is_game_running():
        return
    ExtensionCopyDialog(parent, game_key, Path(save_path), on_done)
