"""
Checksum Status Panel for Hex Editor

Displays checksum validation status and provides fix options.
"""

import customtkinter as ctk
from tkinter import ttk
from typing import Callable, Optional

from .checksum_validator import ChecksumValidator, ChecksumInfo


class ChecksumStatusPanel(ctk.CTkFrame):
    """Panel displaying checksum status and validation controls."""

    def __init__(
        self,
        parent,
        on_validate_click: Optional[Callable] = None,
        on_fix_click: Optional[Callable[[int], None]] = None,
        on_fix_all_click: Optional[Callable] = None,
        **kwargs,
    ):
        """
        Initialize checksum status panel.

        Args:
            parent: Parent widget
            on_validate_click: Callback when validate button is clicked
            on_fix_click: Callback when fix button is clicked for a slot
            on_fix_all_click: Callback when fix all button is clicked
        """
        super().__init__(parent, **kwargs)

        self.on_validate_click = on_validate_click
        self.on_fix_click = on_fix_click
        self.on_fix_all_click = on_fix_all_click
        self.validator: Optional[ChecksumValidator] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        # Title label
        title_label = ctk.CTkLabel(
            self, text="Checksum Status", font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(10, 5), padx=10, anchor="w")

        # Control buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        validate_btn = ctk.CTkButton(
            button_frame,
            text="Validate All",
            command=self._on_validate_clicked,
            width=100,
        )
        validate_btn.pack(side="left", padx=(0, 5))

        fix_all_btn = ctk.CTkButton(
            button_frame,
            text="Fix All Invalid",
            command=self._on_fix_all_clicked,
            width=110,
        )
        fix_all_btn.pack(side="left")

        # Status tree view
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Create Treeview with columns
        columns = ("slot", "offset", "status", "action")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=12
        )

        # Configure columns
        self.tree.heading("slot", text="Slot")
        self.tree.heading("offset", text="Offset")
        self.tree.heading("status", text="Status")
        self.tree.heading("action", text="Action")

        self.tree.column("slot", width=50, anchor="center")
        self.tree.column("offset", width=80)
        self.tree.column("status", width=100)
        self.tree.column("action", width=70)

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind double-click to fix action
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        # Apply dark theme styling
        self._apply_tree_styling()

        # Summary label
        self.summary_label = ctk.CTkLabel(
            self, text="No checksums validated yet", font=("Arial", 11)
        )
        self.summary_label.pack(pady=(0, 10), padx=10)

    def _apply_tree_styling(self):
        """Apply dark theme styling to the tree view."""
        style = ttk.Style()

        # Get current theme colors
        bg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        if isinstance(bg_color, tuple):
            bg_color = bg_color[1]  # Use dark mode color

        text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        if isinstance(text_color, tuple):
            text_color = text_color[1]

        # Configure treeview style
        style.configure(
            "Treeview",
            background=bg_color,
            foreground=text_color,
            fieldbackground=bg_color,
            borderwidth=0,
        )
        style.configure("Treeview.Heading", background=bg_color, foreground=text_color)
        style.map("Treeview", background=[("selected", "#1f538d")])

    def set_validator(self, validator: Optional[ChecksumValidator]):
        """
        Set the checksum validator.

        Args:
            validator: ChecksumValidator instance or None
        """
        self.validator = validator
        self.refresh()

    def refresh(self):
        """Refresh the checksum status display."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.validator:
            self.summary_label.configure(text="No save file loaded")
            return

        # Add checksum info to tree
        valid_count = 0
        invalid_count = 0
        not_checked_count = 0

        for info in self.validator.checksums:
            slot_text = f"Slot {info.slot_index}"
            offset_text = f"0x{info.checksum_offset:X}"

            if info.is_valid is None:
                status_text = "Not Checked"
                action_text = "-"
                not_checked_count += 1
                tag = "not_checked"
            elif info.is_valid:
                status_text = "✓ Valid"
                action_text = "-"
                valid_count += 1
                tag = "valid"
            else:
                status_text = "✗ Invalid"
                action_text = "Fix"
                invalid_count += 1
                tag = "invalid"

            self.tree.insert(
                "",
                "end",
                values=(slot_text, offset_text, status_text, action_text),
                tags=(tag,),
            )

        # Apply tag colors
        self.tree.tag_configure("valid", foreground="#4ade80")  # Green
        self.tree.tag_configure("invalid", foreground="#f87171")  # Red
        self.tree.tag_configure("not_checked", foreground="#94a3b8")  # Gray

        # Update summary
        total = len(self.validator.checksums)
        if not_checked_count == total:
            summary = "No checksums validated yet"
        else:
            summary = f"Valid: {valid_count} | Invalid: {invalid_count} | Total: {total}"

        self.summary_label.configure(text=summary)

    def _on_validate_clicked(self):
        """Handle validate button click."""
        if self.on_validate_click:
            self.on_validate_click()

    def _on_fix_all_clicked(self):
        """Handle fix all button click."""
        if self.on_fix_all_click:
            self.on_fix_all_click()

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item to fix checksum."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.tree.item(item, "values")

        if len(values) >= 4 and values[3] == "Fix":
            # Extract slot index from "Slot X" text
            slot_text = values[0]
            try:
                slot_index = int(slot_text.split()[1])
                if self.on_fix_click:
                    self.on_fix_click(slot_index)
            except (IndexError, ValueError):
                pass
