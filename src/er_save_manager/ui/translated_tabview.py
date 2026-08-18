"""Tab widget that displays translated labels while keying on English names.

CustomTkinter's CTkTabview uses the tab name as both the visible label and the
lookup key, so translating a tab name would break every ``tab()``, ``set()``
and ``get()`` call, along with the dictionaries elsewhere that are keyed by tab
name. This subclass keeps the English name as the key and translates only what
is drawn, so existing call sites keep working unchanged.

    tabs = TranslatedTabview(parent)
    tabs.add("World State")          # displays the translation
    frame = tabs.tab("World State")  # still resolves by English name
    if tabs.get() == "World State":  # still compares against English
        ...

Only ``add`` and ``insert`` take an untranslated name; every other method
accepts either the English key or the translated label.
"""

from __future__ import annotations

import customtkinter as ctk

from er_save_manager.i18n import t


class TranslatedTabview(ctk.CTkTabview):
    """CTkTabview that maps English tab keys to translated display labels."""

    def __init__(self, *args, **kwargs):
        # Populated before super().__init__ because CTkTabview may call back
        # into get() while building its segmented button
        self._label_by_key: dict[str, str] = {}
        self._key_by_label: dict[str, str] = {}
        super().__init__(*args, **kwargs)

    def _register_key(self, key: str) -> str:
        """Return the display label for a tab key, assigning one if needed.

        Falls back to the English key when a translation collides with a label
        already in use, since CTkTabview requires unique names.
        """
        if key in self._label_by_key:
            return self._label_by_key[key]
        # Already a registered display label, for example when a caller passes
        # the value it previously read back from get()
        if key in self._key_by_label:
            return key

        label = t(key)
        if label in self._key_by_label and self._key_by_label[label] != key:
            label = key

        self._label_by_key[key] = label
        self._key_by_label[label] = key
        return label

    def _label(self, name: str) -> str:
        """Resolve a key or an already translated label to the display label."""
        if name in self._label_by_key:
            return self._label_by_key[name]
        return name

    def _key(self, label: str) -> str:
        """Resolve a display label back to its English key."""
        return self._key_by_label.get(label, label)

    def add(self, name: str) -> ctk.CTkFrame:
        # Mirrors CTkTabview.add. Delegating to self.insert rather than
        # super().add keeps registration in one place, since super().add would
        # re-enter insert with an already translated label.
        return self.insert(len(self._tab_dict), name)

    def insert(self, index: int, name: str) -> ctk.CTkFrame:
        return super().insert(index, self._register_key(name))

    def tab(self, name: str) -> ctk.CTkFrame:
        return super().tab(self._label(name))

    def set(self, name: str) -> None:
        super().set(self._label(name))

    def _display_order(self) -> list[str]:
        """Labels in the order they are drawn.

        Authoritative for index lookups. CTkTabview's _name_list is not
        reordered by move() and rename() appends to it, so it can disagree with
        what the user sees.
        """
        return list(self._segmented_button.cget("values"))

    def get(self, index: int | None = None) -> str:
        # Index handled here because CTkTabview.get accepts one only from 6.0.0
        # onward, while the project supports 5.2.2
        if index is None:
            return self._key(super().get())
        return self._key(self._display_order()[index])

    def index(self, name: str | None = None) -> int:
        # CTkTabview.index requires a name in 5.2.2 and defaults to the current
        # tab from 6.0.0, so both cases are resolved here
        label = super().get() if name is None else self._label(name)
        return self._display_order().index(label)

    def move(self, new_index: int, name: str) -> None:
        super().move(new_index, self._label(name))

    def delete(self, name: str) -> None:
        label = self._label(name)
        super().delete(label)
        key = self._key_by_label.pop(label, None)
        if key is not None:
            self._label_by_key.pop(key, None)

    def rename(self, old_name: str, new_name: str) -> None:
        old_label = self._label(old_name)
        old_key = self._key_by_label.pop(old_label, old_name)
        self._label_by_key.pop(old_key, None)
        super().rename(old_label, self._register_key(new_name))
