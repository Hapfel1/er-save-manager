"""Hex Editor Tab (customtkinter version)."""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui.dialogs.add_bookmark import AddBookmarkDialog
from er_save_manager.ui.dialogs.hex_search import HexSearchDialog
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.widgets.bookmarks_manager import BookmarksManager
from er_save_manager.ui.widgets.bookmarks_panel import BookmarksPanel
from er_save_manager.ui.widgets.checksum_status_panel import ChecksumStatusPanel
from er_save_manager.ui.widgets.checksum_validator import ChecksumValidator
from er_save_manager.ui.widgets.data_inspector import DataInspectorWidget
from er_save_manager.ui.widgets.hex_editor_widget import HexEditorWidget
from er_save_manager.ui.widgets.structure_viewer import StructureViewerWidget


class HexEditorTab:
    """Tab for viewing and editing hex data of save files (customtkinter version)."""

    def __init__(self, parent, get_save_file_callback):
        """
        Initialize hex editor tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.hex_offset_var = None
        self.hex_editor = None
        self.data_inspector = None
        self.structure_viewer = None
        self.bookmarks_panel = None
        self.checksum_panel = None
        self.bookmarks_manager = BookmarksManager()
        self.checksum_validator = None
        self.original_save_data = None  # Track original data for modification detection
        self.loading_label = None
        self.refresh_button = None
        self.right_tabview = None

    def setup_ui(self):
        """Setup the hex editor tab UI."""
        # Title and info
        ctk.CTkLabel(
            self.parent,
            text="Hex Editor",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ctk.CTkLabel(
            self.parent,
            text="Advanced: View and edit raw save file data in hexadecimal format",
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        )
        info_text.pack(pady=5)

        # Warning
        warning_frame = ctk.CTkFrame(
            self.parent, corner_radius=8, fg_color=("#ffe6e6", "#4a2a2a")
        )
        warning_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            warning_frame,
            text="⚠️  Warning: Direct hex editing can corrupt your save file. Always backup first!",
            font=("Segoe UI", 12, "bold"),
            text_color=("#cc0000", "#ff8080"),
        ).pack(padx=10, pady=8)

        # Controls
        control_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(control_frame, text="Offset:", font=("Segoe UI", 12)).pack(
            side="left", padx=(0, 5)
        )

        self.hex_offset_var = tk.StringVar(value="0x0000")
        offset_entry = ctk.CTkEntry(
            control_frame,
            textvariable=self.hex_offset_var,
            font=("Consolas", 11),
            width=120,
        )
        offset_entry.pack(side="left", padx=5)

        ctk.CTkButton(
            control_frame,
            text="Go to Offset",
            command=self.hex_goto_offset,
            width=120,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            control_frame,
            text="Search",
            command=self.open_search,
            width=100,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            control_frame,
            text="Bookmark",
            command=self.add_bookmark,
            width=100,
        ).pack(side="left", padx=5)

        self.refresh_button = ctk.CTkButton(
            control_frame,
            text="Refresh",
            command=self.hex_refresh,
            width=100,
        )
        self.refresh_button.pack(side="left", padx=5)

        ctk.CTkButton(
            control_frame,
            text="Save Changes",
            command=self.save_changes,
            width=120,
        ).pack(side="left", padx=5)

        # Loading indicator
        self.loading_label = ctk.CTkLabel(
            control_frame,
            text="",
            font=("Segoe UI", 11),
            text_color=("gray50", "gray60"),
        )
        self.loading_label.pack(side="left", padx=10)

        # Hex editor widget
        hex_frame = ctk.CTkFrame(self.parent, corner_radius=12)
        hex_frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            hex_frame,
            text="Hex Data",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # Create main horizontal layout
        main_layout = ctk.CTkFrame(hex_frame, fg_color="transparent")
        main_layout.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Left side: Structure viewer
        structure_frame = ctk.CTkFrame(main_layout)
        structure_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))
        structure_frame.configure(width=300)

        self.structure_viewer = StructureViewerWidget(
            structure_frame, on_offset_click=self._on_structure_offset_click
        )
        self.structure_viewer.pack(fill="both", expand=True)

        # Middle: Hex editor
        hex_inner = ctk.CTkFrame(main_layout)
        hex_inner.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.hex_editor = HexEditorWidget(
            hex_inner, on_cursor_change=self._on_cursor_change
        )
        self.hex_editor.pack(fill="both", expand=True)

        # Right side: Tabbed view for Data Inspector and Bookmarks
        inspector_frame = ctk.CTkFrame(main_layout)
        inspector_frame.pack(side="right", fill="y", padx=(0, 0))
        inspector_frame.configure(width=300)

        # Create tabbed view
        self.right_tabview = ctk.CTkTabview(inspector_frame)
        self.right_tabview.pack(fill="both", expand=True, padx=5, pady=5)

        # Data Inspector tab
        inspector_tab = self.right_tabview.add("Data Inspector")
        self.data_inspector = DataInspectorWidget(inspector_tab)
        self.data_inspector.pack(fill="both", expand=True)

        # Bookmarks tab
        bookmarks_tab = self.right_tabview.add("Bookmarks")
        self.bookmarks_panel = BookmarksPanel(
            bookmarks_tab,
            self.bookmarks_manager,
            on_bookmark_click=self._on_bookmark_action,
        )
        self.bookmarks_panel.pack(fill="both", expand=True)

        # Checksums tab
        checksums_tab = self.right_tabview.add("Checksums")
        self.checksum_panel = ChecksumStatusPanel(
            checksums_tab,
            on_validate_click=self._on_validate_checksums,
            on_fix_click=self._on_fix_checksum,
            on_fix_all_click=self._on_fix_all_checksums,
        )
        self.checksum_panel.pack(fill="both", expand=True)

        # Set bookmarks manager in hex editor and load bookmarks
        self.hex_editor.set_bookmarks_manager(self.bookmarks_manager)
        self.bookmarks_manager.load_bookmarks()
        self.bookmarks_panel.refresh_bookmarks()

    def hex_goto_offset(self):
        """Jump to specific offset in hex view."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        offset_str = self.hex_offset_var.get().strip()
        try:
            if offset_str.startswith("0x"):
                offset = int(offset_str, 16)
            else:
                offset = int(offset_str)

            if offset >= len(self.hex_editor.data):
                CTkMessageBox.showerror(
                    "Invalid Offset",
                    f"Offset {offset} exceeds file size {len(self.hex_editor.data)}",
                )
                return

            # Move cursor to offset
            self.hex_editor.cursor_offset = offset
            self.hex_editor.refresh_view()

        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Offset", "Please enter a valid hex offset (e.g., 0x1000)"
            )

    def hex_refresh(self):
        """Refresh hex view."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        if hasattr(save_file, "_raw_data"):
            # Show loading feedback
            file_size = len(save_file._raw_data)
            size_mb = file_size / (1024 * 1024)
            self.loading_label.configure(text=f"Loading {size_mb:.1f} MB...")
            self.refresh_button.configure(state="disabled")

            # Store original data for modification tracking
            self.original_save_data = bytes(save_file._raw_data)

            # Initialize checksum validator
            self.checksum_validator = ChecksumValidator(save_file._raw_data)
            self.checksum_panel.set_validator(self.checksum_validator)

            # Load data asynchronously
            self.hex_editor.load_data(save_file._raw_data)

            # Load structure viewer
            self.structure_viewer.load_save_file(save_file, save_file._raw_data)

            # Clear loading message after a delay
            self.parent.after(1000, lambda: self.loading_label.configure(text=""))
            self.parent.after(
                1000, lambda: self.refresh_button.configure(state="normal")
            )

    def save_changes(self):
        """Save modifications back to the save file."""
        if not self.hex_editor.has_modifications():
            CTkMessageBox.showinfo("No Changes", "No modifications to save.")
            return

        save_file = self.get_save_file()
        if not save_file:
            return

        # Confirm
        result = CTkMessageBox.askyesno(
            "Save Changes",
            f"Save {len(self.hex_editor.modified_bytes)} modified bytes to the save file?\n\n"
            "This will overwrite the save file data. Make sure you have a backup!",
            icon="warning",
        )

        if result:
            # Update save file data
            save_file._raw_data = self.hex_editor.get_data()
            self.hex_editor.modified_bytes.clear()
            self.hex_editor.refresh_view()
            CTkMessageBox.showinfo("Saved", "Changes saved to save file!")

    def open_search(self):
        """Open search dialog."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        HexSearchDialog(self.parent, self.hex_editor)

    def _on_cursor_change(self, offset):
        """Handle cursor position change in hex editor."""
        if self.data_inspector and self.hex_editor.data:
            self.data_inspector.update_from_bytes(bytes(self.hex_editor.data), offset)

    def _on_structure_offset_click(self, offset):
        """Handle clicking on a structure field to jump to offset."""
        if self.hex_editor and self.hex_editor.data:
            # Update hex editor cursor
            self.hex_editor.cursor_offset = offset
            self.hex_editor.selection_start = None
            self.hex_editor.selection_end = None
            self.hex_editor.refresh_view()

            # Update offset entry
            if self.hex_offset_var:
                self.hex_offset_var.set(f"0x{offset:X}")

    def add_bookmark(self):
        """Add bookmark at current cursor position."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        # Get current offset
        current_offset = self.hex_editor.cursor_offset

        # Check if bookmark already exists
        existing = self.bookmarks_manager.get_bookmark_at_offset(current_offset)

        # Show dialog
        dialog = AddBookmarkDialog(
            self.parent, self.bookmarks_manager, current_offset, existing
        )
        self.parent.wait_window(dialog)

        # Refresh bookmarks and hex view
        if dialog.result:
            self.bookmarks_panel.refresh_bookmarks()
            self.hex_editor.refresh_view()

    def _on_bookmark_action(self, action, offset):
        """Handle bookmark panel actions."""
        if action == "add":
            self.add_bookmark()
        elif action == "navigate" and offset is not None:
            # Jump to bookmark offset
            self.hex_editor.cursor_offset = offset
            self.hex_editor.selection_start = None
            self.hex_editor.selection_end = None
            self.hex_editor.refresh_view()

            # Update offset entry
            if self.hex_offset_var:
                self.hex_offset_var.set(f"0x{offset:X}")

    def _on_validate_checksums(self):
        """Validate all checksums in the save file."""
        if not self.checksum_validator:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        # Update validator with current hex editor data
        current_data = self.hex_editor.get_data()
        self.checksum_validator.update_save_data(current_data)

        # Validate all checksums
        self.checksum_validator.validate_all()

        # Refresh checksum panel
        self.checksum_panel.refresh()

        # Show summary
        invalid = self.checksum_validator.get_invalid_checksums()
        if invalid:
            CTkMessageBox.showwarning(
                "Invalid Checksums",
                f"Found {len(invalid)} invalid checksum(s).\nUse 'Fix All Invalid' to repair them.",
            )
        else:
            CTkMessageBox.showinfo(
                "All Valid", "All checksums are valid!"
            )

    def _on_fix_checksum(self, slot_index: int):
        """Fix checksum for a specific slot."""
        if not self.checksum_validator:
            return

        # Get current hex editor data
        current_data = bytearray(self.hex_editor.get_data())
        self.checksum_validator.update_save_data(bytes(current_data))

        # Calculate correct checksum
        checksum_info = self.checksum_validator.get_checksum_info(slot_index)
        if not checksum_info:
            return

        correct_checksum = self.checksum_validator.calculate_checksum(slot_index)

        # Update checksum in data
        checksum_offset = checksum_info.checksum_offset
        for i, byte in enumerate(correct_checksum):
            current_data[checksum_offset + i] = byte

        # Update hex editor with new data
        self.hex_editor.load_data(bytes(current_data))

        # Re-validate
        self.checksum_validator.update_save_data(bytes(current_data))
        self.checksum_validator.validate_all()
        self.checksum_panel.refresh()

        CTkMessageBox.showinfo(
            "Checksum Fixed",
            f"Fixed checksum for Slot {slot_index}\nOffset: 0x{checksum_offset:X}",
        )

    def _on_fix_all_checksums(self):
        """Fix all invalid checksums in the save file."""
        if not self.checksum_validator:
            return

        # Get current hex editor data
        current_data = bytearray(self.hex_editor.get_data())
        self.checksum_validator.update_save_data(bytes(current_data))

        # Validate to find invalid checksums
        self.checksum_validator.validate_all()
        invalid = self.checksum_validator.get_invalid_checksums()

        if not invalid:
            CTkMessageBox.showinfo("Nothing to Fix", "All checksums are already valid!")
            return

        # Fix each invalid checksum
        fixed_count = 0
        for checksum_info in invalid:
            correct_checksum = self.checksum_validator.calculate_checksum(
                checksum_info.slot_index
            )

            # Update checksum in data
            checksum_offset = checksum_info.checksum_offset
            for i, byte in enumerate(correct_checksum):
                current_data[checksum_offset + i] = byte

            fixed_count += 1

        # Update hex editor with new data
        self.hex_editor.load_data(bytes(current_data))

        # Re-validate
        self.checksum_validator.update_save_data(bytes(current_data))
        self.checksum_validator.validate_all()
        self.checksum_panel.refresh()

        CTkMessageBox.showinfo(
            "Checksums Fixed",
            f"Successfully fixed {fixed_count} checksum(s)!",
        )
