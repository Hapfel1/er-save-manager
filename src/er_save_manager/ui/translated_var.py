"""Variable that holds a translated label while reading and writing English keys.

Combobox and option menu entries double as lookup keys throughout the codebase,
so translating the ``values=`` list alone would break every comparison against
them. Tk needs the bound variable to hold the string it draws, so the mapping
belongs in the variable rather than the widget.

    self.filter_var = TranslatedVar(choices=[N_("All"), N_("Held")])
    ctk.CTkComboBox(parent, values=self.filter_var.labels,
                    variable=self.filter_var)

    self.filter_var.get()        # returns "All", not the translation
    self.filter_var.set("Held")  # accepts the English key

Values outside ``choices`` pass through untouched, so a list that mixes fixed
options with game data (category or item names, which stay untranslated) works
without special handling.
"""

from __future__ import annotations

import tkinter as tk

from er_save_manager.i18n import t


class TranslatedVar(tk.StringVar):
    """StringVar that displays translated labels and exposes English keys."""

    def __init__(
        self,
        master=None,
        value: str | None = None,
        *,
        choices: list[str] | tuple[str, ...] = (),
        name: str | None = None,
    ):
        # Built before super().__init__ because Variable.__init__ calls set()
        self._label_by_key: dict[str, str] = {}
        self._key_by_label: dict[str, str] = {}
        for key in choices:
            label = t(key)
            # Two keys translating alike would make the label ambiguous, so the
            # second one keeps its English text
            if label in self._key_by_label and self._key_by_label[label] != key:
                label = key
            self._label_by_key[key] = label
            self._key_by_label[label] = key

        # Variable.__init__ would route the initial value through
        # Variable.initialize, which is bound to the base set() and would skip
        # the mapping, so the value is applied afterwards
        super().__init__(master, None, name)
        if value is not None:
            self.set(value)

    @property
    def labels(self) -> list[str]:
        """Display labels in the order the choices were given."""
        return list(self._label_by_key.values())

    def label_for(self, key: str) -> str:
        """Return the display label for an English key."""
        return self._label_by_key.get(key, key)

    def key_for(self, label: str) -> str:
        """Return the English key for a display label."""
        return self._key_by_label.get(label, label)

    def get(self) -> str:
        return self.key_for(super().get())

    def set(self, value: str) -> None:
        super().set(self.label_for(value))

    # Tk binds initialize to Variable.set at class definition time, so the
    # override has to be reasserted for it
    initialize = set
