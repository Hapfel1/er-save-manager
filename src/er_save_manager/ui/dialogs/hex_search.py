"""Hex Editor Search Dialog."""

import tkinter as tk
from tkinter import ttk


class HexSearchDialog(tk.Toplevel):
    """Search dialog for hex editor."""

    def __init__(self, parent, hex_editor_widget):
        super().__init__(parent)

        self.hex_editor = hex_editor_widget
        self.search_results = []
        self.current_result_index = -1

        self.title("Search Hex Data")
        self.geometry("500x300")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        self._setup_ui()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """Create search dialog UI."""
        # Search type
        type_frame = ttk.Frame(self)
        type_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(type_frame, text="Search Type:").pack(side="left")

        self.search_type = tk.StringVar(value="hex")
        ttk.Radiobutton(
            type_frame, text="Hex Pattern", variable=self.search_type, value="hex"
        ).pack(side="left", padx=10)

        ttk.Radiobutton(
            type_frame, text="ASCII Text", variable=self.search_type, value="ascii"
        ).pack(side="left", padx=10)

        ttk.Radiobutton(
            type_frame, text="AOB Pattern", variable=self.search_type, value="aob"
        ).pack(side="left", padx=10)

        # Search input
        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Search For:").pack(anchor="w")

        self.search_entry = ttk.Entry(input_frame, font=("Consolas", 10))
        self.search_entry.pack(fill="x", pady=5)
        self.search_entry.bind("<Return>", lambda e: self.find_all())

        # Help text
        help_frame = ttk.Frame(self)
        help_frame.pack(fill="x", padx=10, pady=5)

        help_text = ttk.Label(
            help_frame,
            text="Hex: e.g., 'FF 00 12 34'  |  ASCII: normal text  |  AOB: use ?? for wildcards (e.g., 'FF ?? 12 34')",
            font=("Segoe UI", 9),
            foreground="gray",
        )
        help_text.pack(anchor="w")

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(button_frame, text="Find All", command=self.find_all).pack(
            side="left", padx=5
        )

        ttk.Button(button_frame, text="Find Next", command=self.find_next).pack(
            side="left", padx=5
        )

        ttk.Button(button_frame, text="Find Previous", command=self.find_previous).pack(
            side="left", padx=5
        )

        # Results
        results_frame = ttk.LabelFrame(self, text="Results")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Results listbox
        self.results_listbox = tk.Listbox(
            results_frame, font=("Consolas", 10), height=6
        )
        self.results_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.results_listbox.bind("<Double-Button-1>", self._on_result_double_click)

        # Result count label
        self.result_count_label = ttk.Label(results_frame, text="No results")
        self.result_count_label.pack(anchor="w", padx=5, pady=2)

    def find_all(self):
        """Find all occurrences of the search pattern."""
        search_text = self.search_entry.get().strip()
        if not search_text:
            return

        search_type = self.search_type.get()

        # Parse search pattern
        if search_type == "hex":
            pattern = self._parse_hex_pattern(search_text)
        elif search_type == "ascii":
            pattern = [ord(c) for c in search_text]
        elif search_type == "aob":
            pattern = self._parse_aob_pattern(search_text)
        else:
            return

        if not pattern:
            self.result_count_label.config(text="Invalid search pattern")
            return

        # Search for pattern
        self.search_results = []
        data = self.hex_editor.data

        if search_type == "aob":
            # AOB search with wildcards
            for i in range(len(data) - len(pattern) + 1):
                if self._match_aob_pattern(data, i, pattern):
                    self.search_results.append(i)
        else:
            # Exact pattern search
            for i in range(len(data) - len(pattern) + 1):
                if all(data[i + j] == pattern[j] for j in range(len(pattern))):
                    self.search_results.append(i)

        # Display results
        self.results_listbox.delete(0, tk.END)
        for offset in self.search_results:
            # Show offset and surrounding bytes
            preview = " ".join(
                f"{data[offset + j]:02X}" for j in range(min(8, len(pattern)))
            )
            self.results_listbox.insert(tk.END, f"0x{offset:08X}: {preview}...")

        self.result_count_label.config(
            text=f"Found {len(self.search_results)} occurrence(s)"
        )
        self.current_result_index = 0 if self.search_results else -1

        # Jump to first result
        if self.search_results:
            self._jump_to_result(0)

    def find_next(self):
        """Find next occurrence."""
        if not self.search_results:
            self.find_all()
            return

        if self.search_results:
            self.current_result_index = (self.current_result_index + 1) % len(
                self.search_results
            )
            self._jump_to_result(self.current_result_index)

    def find_previous(self):
        """Find previous occurrence."""
        if not self.search_results:
            self.find_all()
            return

        if self.search_results:
            self.current_result_index = (self.current_result_index - 1) % len(
                self.search_results
            )
            self._jump_to_result(self.current_result_index)

    def _jump_to_result(self, index):
        """Jump to a search result."""
        if 0 <= index < len(self.search_results):
            offset = self.search_results[index]
            self.hex_editor.cursor_offset = offset

            # Select the matched pattern
            self.search_type.get()
            pattern_length = len(self._get_current_pattern())
            self.hex_editor.selection_start = offset
            self.hex_editor.selection_end = offset + pattern_length - 1

            self.hex_editor.refresh_view()

            # Highlight in results list
            self.results_listbox.selection_clear(0, tk.END)
            self.results_listbox.selection_set(index)
            self.results_listbox.see(index)

    def _on_result_double_click(self, event):
        """Handle double-click on result."""
        selection = self.results_listbox.curselection()
        if selection:
            self.current_result_index = selection[0]
            self._jump_to_result(self.current_result_index)

    def _get_current_pattern(self):
        """Get the current search pattern as bytes."""
        search_text = self.search_entry.get().strip()
        search_type = self.search_type.get()

        if search_type == "hex":
            return self._parse_hex_pattern(search_text)
        elif search_type == "ascii":
            return [ord(c) for c in search_text]
        elif search_type == "aob":
            return self._parse_aob_pattern(search_text)
        return []

    def _parse_hex_pattern(self, text):
        """Parse hex pattern like 'FF 00 12 34'."""
        try:
            hex_bytes = text.replace(" ", "").replace("0x", "")
            if len(hex_bytes) % 2 != 0:
                return None
            return [int(hex_bytes[i : i + 2], 16) for i in range(0, len(hex_bytes), 2)]
        except ValueError:
            return None

    def _parse_aob_pattern(self, text):
        """Parse AOB pattern like 'FF ?? 12 34'."""
        try:
            parts = text.split()
            pattern = []
            for part in parts:
                if part == "??":
                    pattern.append(None)  # Wildcard
                else:
                    pattern.append(int(part, 16))
            return pattern
        except ValueError:
            return None

    def _match_aob_pattern(self, data, offset, pattern):
        """Check if AOB pattern matches at offset (with wildcards)."""
        if offset + len(pattern) > len(data):
            return False

        for i, byte_val in enumerate(pattern):
            if byte_val is not None and data[offset + i] != byte_val:
                return False
        return True
