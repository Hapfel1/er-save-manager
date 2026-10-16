"""Message manager: the character's own messages (protect, delete) and cached ones (read-only)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.editors.blood_messages import BloodMessage, BloodMessageEditor
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import (
    center_window,
    force_render_dialog,
    style_window_frame,
)

_OWN = "My Messages"
_CACHED = "Cached Messages"


class MessageManagerDialog:
    """Lists the messages stored in a slot and edits the player's own ones."""

    def __init__(
        self,
        parent,
        slot_index: int,
        get_save_file,
        get_save_path,
        reload_save,
        show_toast,
    ):
        self.parent = parent
        self.slot_index = slot_index
        self.get_save_file = get_save_file
        self.get_save_path = get_save_path
        self.reload_save = reload_save
        self.show_toast = show_toast
        self.messages: list[BloodMessage] = []

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Messages")
        self.dialog.transient(parent)
        center_window(self.dialog, 1000, 600, parent=parent)
        self.dialog.resizable(True, True)
        style_window_frame(self.dialog, dialog=False)
        force_render_dialog(self.dialog)
        self.dialog.grab_set()
        self._build()
        self._refresh()

    def _editor(self) -> BloodMessageEditor | None:
        save = self.get_save_file()
        return BloodMessageEditor(save, self.slot_index) if save else None

    def _build(self):
        body = ctk.CTkFrame(self.dialog, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        ds.header(body, f"Messages - Slot {self.slot_index + 1}", font=ds.TITLE_LARGE)

        self.view_var = tk.StringVar(value=_OWN)
        ctk.CTkSegmentedButton(
            body,
            values=[_OWN, _CACHED],
            variable=self.view_var,
            command=lambda _v: self._refresh(),
        ).pack(anchor="w", pady=(12, 6))

        self.info_label = ctk.CTkLabel(
            body, text="", font=ds.SMALL, text_color=ds.INFO, anchor="w", justify="left"
        )
        self.info_label.pack(fill=tk.X, pady=(0, 6))

        tree_frame, self.tree = ds.themed_tree(
            body, show="headings", selectmode="extended"
        )
        add_tooltip(self.tree, MULTI_SELECT_TIP)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._update_buttons())

        _, buttons = ds.button_row(
            body,
            [
                {
                    "text": "Protect",
                    "command": lambda: self._protect(True),
                    "width": 110,
                },
                {
                    "text": "Unprotect",
                    "command": lambda: self._protect(False),
                    "width": 110,
                },
                {"text": "Delete", "command": self._delete, "width": 110},
                {"text": "Close", "command": self.dialog.destroy, "primary": False},
            ],
        )
        self.edit_buttons = buttons[:3]
        # After the button row, so a short window shrinks the list, not the buttons
        tree_frame.pack(fill=tk.BOTH, expand=True)

    def _columns(self, own: bool) -> dict[str, tuple[str, int, bool]]:
        cols = {
            "text": ("Message", 360, True),
            "gesture": ("Gesture", 150, False),
            "location": ("Location", 260, True),
        }
        if own:
            cols["protected"] = ("Protected", 90, False)
        else:
            cols["author"] = ("Author", 160, False)
        return cols

    def _refresh(self):
        editor = self._editor()
        problems = editor.problems() if editor else ["No save loaded"]
        own_view = self.view_var.get() == _OWN
        self.messages = [] if problems else editor.messages()
        shown = [m for m in self.messages if m.is_own == own_view]

        cols = self._columns(own_view)
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(columns=tuple(cols))
        for col, (title, width, stretch) in cols.items():
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w", stretch=stretch)

        for i, msg in enumerate(self.messages):
            if msg.is_own != own_view:
                continue
            values = [msg.text, msg.gesture_name, msg.map_name]
            values.append(("Yes" if msg.protected else "") if own_view else msg.author)
            self.tree.insert("", "end", iid=str(i), values=values)

        if problems:
            info = "Message data cannot be read: " + "; ".join(problems)
        elif own_view:
            info = (
                f"{len(shown)} of 10 messages. Changes only last in offline play:"
                " online, the game restores your messages from its server."
            )
        else:
            info = (
                f"{len(shown)} messages of other players cached for the area the"
                " character is in. The game refreshes this list during online play."
            )
        self.info_label.configure(text=info)
        self._update_buttons()

    def _selected(self) -> list[BloodMessage]:
        return [self.messages[int(iid)] for iid in self.tree.selection()]

    def _update_buttons(self):
        own_view = self.view_var.get() == _OWN
        state = "normal" if own_view and self.tree.selection() else "disabled"
        for btn in self.edit_buttons:
            btn.configure(state=state)

    def _backup(self, operation: str) -> None:
        save_path = self.get_save_path()
        if not save_path:
            return
        try:
            BackupManager(Path(save_path)).create_backup(
                description=f"before_{operation}",
                operation=f"message_manager_{operation}",
                save=self.get_save_file(),
            )
        except PermissionError:
            CTkMessageBox.showwarning(
                "Backup Skipped",
                "Could not create a backup (permission denied). Continuing without one.",
                parent=self.dialog,
            )

    def _apply(self, operation: str, targets: list[BloodMessage], change) -> int:
        """Run change(editor, msg) for each target, newest offset first, then save."""
        self._backup(operation)
        editor = self._editor()
        done, errors = 0, []
        # Later entries first: a delete moves every entry after it
        for msg in sorted(targets, key=lambda m: m.offset, reverse=True):
            ok, text = change(editor, msg)
            if ok:
                done += 1
            else:
                errors.append(text)
        if done:
            save = self.get_save_file()
            save.recalculate_checksums()
            save_path = self.get_save_path()
            if save_path:
                save.to_file(save_path)
                self.reload_save()
        if errors:
            CTkMessageBox.showerror(
                "Messages Not Saved", "\n".join(errors), parent=self.dialog
            )
        self._refresh()
        return done

    def _protect(self, protected: bool):
        targets = [m for m in self._selected() if m.protected != protected]
        if not targets:
            return
        done = self._apply(
            "protect" if protected else "unprotect",
            targets,
            lambda ed, m: ed.set_protected(m, protected),
        )
        if done:
            verb = "Protected" if protected else "Unprotected"
            self.show_toast(f"{verb} {done} message(s)", duration=2500)

    def _delete(self):
        targets = self._selected()
        if not targets:
            return
        protected = sum(m.protected for m in targets)
        if not CTkMessageBox.askyesno(
            "Delete Messages",
            f"Delete {len(targets)} message(s) from Slot {self.slot_index + 1}?\n\n"
            + (f"{protected} of them are protected.\n\n" if protected else "")
            + "A backup will be created automatically.",
            parent=self.dialog,
        ):
            return
        done = self._apply("delete", targets, lambda ed, m: ed.delete(m))
        if done:
            self.show_toast(f"Deleted {done} message(s)", duration=2500)
