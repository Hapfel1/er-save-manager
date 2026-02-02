"""Hex Editor Widget - Editable hex/ASCII view with full editing capabilities."""

import threading
import tkinter as tk
from tkinter import font as tkfont

import customtkinter as ctk


class HexEditorWidget(tk.Frame):
    """
    Full-featured hex editor widget with editing capabilities.

    Features:
    - Dual hex/ASCII panes
    - Editable bytes
    - Cursor navigation
    - Selection support
    - Modified byte tracking
    """

    def __init__(self, parent, on_cursor_change=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Data
        self.data = bytearray()
        self.modified_bytes = set()  # Track which bytes were modified
        self.undo_stack = []
        self.redo_stack = []

        # View settings
        self.bytes_per_row = 16
        self.current_offset = 0

        # Cursor & selection
        self.cursor_offset = 0
        self.selection_start = None
        self.selection_end = None
        self.edit_mode = "hex"  # "hex" or "ascii"
        self.insert_mode = False  # False = overwrite, True = insert
        self.hex_nibble = 0  # 0 or 1 for which hex digit we're editing

        # Callback for cursor changes
        self.on_cursor_change = on_cursor_change

        # Bookmarks
        self.bookmarks_manager = None

        # Loading state
        self.is_loading = False

        # UI Components
        self._setup_ui()
        self._update_theme()

    def set_bookmarks_manager(self, bookmarks_manager):
        """Set the bookmarks manager for this hex editor."""
        self.bookmarks_manager = bookmarks_manager

    def _setup_ui(self):
        """Create the hex editor UI."""
        # Create scrollbar with CustomTkinter for proper theming
        self.scrollbar = ctk.CTkScrollbar(self)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create text widget
        mono_font = tkfont.Font(family="Consolas", size=10)

        self.text_widget = tk.Text(
            self,
            font=mono_font,
            yscrollcommand=self.scrollbar.set,
            wrap=tk.NONE,
            width=80,
            height=25,
            insertwidth=2,
            spacing1=2,
            spacing3=2,
        )
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.configure(command=self.text_widget.yview)

        # Bind events
        self.text_widget.bind("<Button-1>", self._on_click)
        self.text_widget.bind("<B1-Motion>", self._on_drag)
        self.text_widget.bind("<KeyPress>", self._on_key_press)
        self.text_widget.bind("<Control-z>", lambda e: self.undo())
        self.text_widget.bind("<Control-y>", lambda e: self.redo())
        self.text_widget.bind("<Control-c>", lambda e: self.copy())
        self.text_widget.bind("<Control-v>", lambda e: self.paste())

        # Prevent default text widget editing
        self.text_widget.bind(
            "<Key>",
            lambda e: "break"
            if e.keysym not in ["Control_L", "Control_R", "Shift_L", "Shift_R"]
            else None,
            "+",
        )

    def _update_theme(self):
        """Update colors based on CustomTkinter theme."""
        appearance = ctk.get_appearance_mode()

        if appearance == "Dark":
            bg_color = "#1a1a1a"
            fg_color = "#e0e0e0"
            offset_color = "#707070"
            hex_color = "#4EC9B0"
            ascii_color = "#9CDCFE"
            modified_bg = "#4a4a2a"
            selection_bg = "#264F78"
            cursor_bg = "#3a3a3a"
        else:
            bg_color = "#ffffff"
            fg_color = "#1a1a1a"
            offset_color = "#888888"
            hex_color = "#008800"
            ascii_color = "#0066cc"
            modified_bg = "#ffffaa"
            selection_bg = "#0078D7"
            cursor_bg = "#cccccc"

        # Update text widget colors
        self.text_widget.config(
            bg=bg_color,
            fg=fg_color,
            insertbackground=fg_color,
        )

        # Configure tags for styling
        self.text_widget.tag_config("offset", foreground=offset_color)
        self.text_widget.tag_config("hex", foreground=hex_color)
        self.text_widget.tag_config("ascii", foreground=ascii_color)
        self.text_widget.tag_config("modified", background=modified_bg)
        self.text_widget.tag_config(
            "selection", background=selection_bg, foreground="white"
        )
        self.text_widget.tag_config("cursor", background=cursor_bg)

    def load_data(self, data: bytes):
        """Load data into the hex editor asynchronously."""
        if self.is_loading:
            return

        self.is_loading = True

        # Show loading message
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", "Loading...")
        self.text_widget.config(state=tk.DISABLED)

        # Load data in background thread
        def load_thread():
            self.data = bytearray(data)
            self.modified_bytes.clear()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.cursor_offset = 0
            self.selection_start = None
            self.selection_end = None
            self.current_offset = 0

            # Schedule refresh on main thread
            self.after(0, self._finish_loading)

        threading.Thread(target=load_thread, daemon=True).start()

    def _finish_loading(self):
        """Finish loading and refresh view on main thread."""
        self.refresh_view()
        self.is_loading = False

    def refresh_view(self):
        """Refresh the hex editor display (optimized for large files)."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)

        if not self.data:
            self.text_widget.insert("1.0", "No data loaded")
            self.text_widget.config(state=tk.DISABLED)
            return

        # For very large files, only render first 10000 rows (640KB)
        # User can navigate with Go to Offset
        max_rows = min(
            10000, (len(self.data) + self.bytes_per_row - 1) // self.bytes_per_row
        )
        max_offset = max_rows * self.bytes_per_row

        if len(self.data) > max_offset:
            info_text = f"Showing first {max_offset} bytes of {len(self.data)} bytes. Use 'Go to Offset' to view other sections.\n"
            self.text_widget.insert(tk.END, info_text, "offset")
            self.text_widget.insert(tk.END, "\n")

        # Render hex view
        for row_offset in range(0, min(max_offset, len(self.data)), self.bytes_per_row):
            self._render_row(row_offset)

        # Apply highlighting
        self._update_highlights()
        self.text_widget.config(state=tk.DISABLED)

        # Notify cursor change
        if self.on_cursor_change:
            self.on_cursor_change(self.cursor_offset)

    def _render_row(self, offset):
        """Render a single row of hex data."""
        # Offset column
        offset_str = f"{offset:08X}: "
        self.text_widget.insert(tk.END, offset_str, "offset")

        # Hex bytes
        hex_bytes = []
        ascii_chars = []
        for i in range(self.bytes_per_row):
            if offset + i < len(self.data):
                byte = self.data[offset + i]
                hex_bytes.append(f"{byte:02X}")
                ascii_chars.append(chr(byte) if 32 <= byte < 127 else ".")
            else:
                hex_bytes.append("  ")
                ascii_chars.append(" ")

            # Add extra space in middle
            if i == 7:
                hex_bytes.append("")

        hex_str = " ".join(hex_bytes)
        self.text_widget.insert(tk.END, hex_str, "hex")

        # Separator
        self.text_widget.insert(tk.END, "  ")

        # ASCII column
        ascii_str = "".join(ascii_chars)
        self.text_widget.insert(tk.END, ascii_str, "ascii")
        self.text_widget.insert(tk.END, "\n")

    def _update_highlights(self):
        """Update cursor, selection, modified byte, and bookmark highlighting."""
        # Clear previous highlights
        self.text_widget.tag_remove("selection", "1.0", tk.END)
        self.text_widget.tag_remove("cursor", "1.0", tk.END)

        # Highlight bookmarks first (so they can be overridden)
        if self.bookmarks_manager:
            for bookmark in self.bookmarks_manager.get_all_bookmarks():
                if bookmark.offset < len(self.data):
                    # Configure bookmark tag with color
                    tag_name = f"bookmark_{bookmark.offset}"
                    self.text_widget.tag_config(tag_name, background=bookmark.color)
                    self._highlight_byte(bookmark.offset, tag_name)

        # Highlight selection
        if self.selection_start is not None and self.selection_end is not None:
            start = min(self.selection_start, self.selection_end)
            end = max(self.selection_start, self.selection_end)
            for offset in range(start, end + 1):
                if offset < len(self.data):
                    self._highlight_byte(offset, "selection")

        # Highlight cursor
        if self.cursor_offset < len(self.data):
            self._highlight_byte(self.cursor_offset, "cursor")

        # Highlight modified bytes
        for offset in self.modified_bytes:
            if offset < len(self.data):
                self._highlight_byte(offset, "modified")

    def _highlight_byte(self, offset, tag):
        """Highlight a specific byte at given offset."""
        row = offset // self.bytes_per_row
        col = offset % self.bytes_per_row

        # Calculate text widget position for hex view
        line = row + 1  # 1-based
        # Offset column (10 chars) + hex position
        hex_col = 10 + (col * 3) + (1 if col > 7 else 0)

        # Highlight in hex view
        start_pos = f"{line}.{hex_col}"
        end_pos = f"{line}.{hex_col + 2}"
        self.text_widget.tag_add(tag, start_pos, end_pos)

        # Calculate position for ASCII view
        ascii_col = 10 + (self.bytes_per_row * 3) + 2 + col
        start_pos_ascii = f"{line}.{ascii_col}"
        end_pos_ascii = f"{line}.{ascii_col + 1}"
        self.text_widget.tag_add(tag, start_pos_ascii, end_pos_ascii)

    def _on_click(self, event):
        """Handle mouse click to position cursor."""
        # Get click position
        index = self.text_widget.index(f"@{event.x},{event.y}")
        line, col = map(int, index.split("."))

        offset = self._position_to_offset(line, col)
        if offset is not None:
            self.cursor_offset = offset
            if not (event.state & 0x1):  # No shift key
                self.selection_start = None
                self.selection_end = None
            else:
                if self.selection_start is None:
                    self.selection_start = self.cursor_offset
                self.selection_end = offset
            self.refresh_view()
        return "break"

    def _on_drag(self, event):
        """Handle mouse drag for selection."""
        index = self.text_widget.index(f"@{event.x},{event.y}")
        line, col = map(int, index.split("."))

        offset = self._position_to_offset(line, col)
        if offset is not None:
            if self.selection_start is None:
                self.selection_start = self.cursor_offset
            self.selection_end = offset
            self.cursor_offset = offset
            self.refresh_view()
        return "break"

    def _position_to_offset(self, line, col):
        """Convert text widget position to byte offset."""
        row = line - 1

        # Check if click is in hex area
        if 10 <= col < 10 + (self.bytes_per_row * 3):
            relative_col = col - 10
            byte_col = relative_col // 3
            if byte_col > 7:
                byte_col -= 1  # Account for extra space
            if byte_col >= self.bytes_per_row:
                return None
            offset = row * self.bytes_per_row + byte_col
            self.edit_mode = "hex"
            return offset if offset < len(self.data) else None

        # Check if click is in ASCII area
        ascii_start = 10 + (self.bytes_per_row * 3) + 2
        if ascii_start <= col < ascii_start + self.bytes_per_row:
            byte_col = col - ascii_start
            offset = row * self.bytes_per_row + byte_col
            self.edit_mode = "ascii"
            return offset if offset < len(self.data) else None

        return None

    def _on_key_press(self, event):
        """Handle keyboard input for editing."""
        # Navigation keys
        if event.keysym == "Left":
            self.move_cursor(-1)
        elif event.keysym == "Right":
            self.move_cursor(1)
        elif event.keysym == "Up":
            self.move_cursor(-self.bytes_per_row)
        elif event.keysym == "Down":
            self.move_cursor(self.bytes_per_row)
        elif event.keysym == "Page_Up":
            self.move_cursor(-self.bytes_per_row * 10)
        elif event.keysym == "Page_Down":
            self.move_cursor(self.bytes_per_row * 10)
        elif event.keysym == "Home":
            self.cursor_offset = (
                self.cursor_offset // self.bytes_per_row
            ) * self.bytes_per_row
            self.refresh_view()
        elif event.keysym == "End":
            row_end = (
                (self.cursor_offset // self.bytes_per_row) + 1
            ) * self.bytes_per_row - 1
            self.cursor_offset = min(row_end, len(self.data) - 1)
            self.refresh_view()
        elif event.keysym == "Delete":
            self.delete_byte()
        elif event.keysym == "Insert":
            self.insert_mode = not self.insert_mode
            # TODO: Update cursor visual
        # Editing in hex mode
        elif self.edit_mode == "hex" and event.char in "0123456789ABCDEFabcdef":
            self.edit_hex_byte(event.char.upper())
        # Editing in ASCII mode
        elif (
            self.edit_mode == "ascii"
            and len(event.char) == 1
            and event.char.isprintable()
        ):
            self.edit_ascii_byte(event.char)

        return "break"

    def move_cursor(self, delta):
        """Move cursor by delta bytes."""
        new_offset = self.cursor_offset + delta
        if 0 <= new_offset < len(self.data):
            self.cursor_offset = new_offset
            self.hex_nibble = 0  # Reset nibble position
            # Clear selection unless shift is held
            # (would need to track shift state)
            self.selection_start = None
            self.selection_end = None
            self.refresh_view()

    def edit_hex_byte(self, hex_char):
        """Edit a byte in hex mode."""
        if self.cursor_offset >= len(self.data):
            return

        # Save state for undo
        old_value = self.data[self.cursor_offset]

        # Get current byte value
        current_byte = self.data[self.cursor_offset]

        # Edit appropriate nibble
        if self.hex_nibble == 0:
            # Editing high nibble
            new_value = (int(hex_char, 16) << 4) | (current_byte & 0x0F)
            self.hex_nibble = 1
        else:
            # Editing low nibble
            new_value = (current_byte & 0xF0) | int(hex_char, 16)
            self.hex_nibble = 0
            # Move to next byte after completing both nibbles
            self.cursor_offset = min(self.cursor_offset + 1, len(self.data) - 1)

        # Apply change
        self.data[
            self.cursor_offset if self.hex_nibble == 1 else self.cursor_offset - 1
        ] = new_value

        # Track modification
        modified_offset = (
            self.cursor_offset if self.hex_nibble == 1 else self.cursor_offset - 1
        )
        self.modified_bytes.add(modified_offset)

        # Add to undo stack
        self._add_undo_action("edit", modified_offset, old_value, new_value)

        self.refresh_view()

    def edit_ascii_byte(self, char):
        """Edit a byte in ASCII mode."""
        if self.cursor_offset >= len(self.data):
            return

        # Save state for undo
        old_value = self.data[self.cursor_offset]
        new_value = ord(char)

        # Apply change
        self.data[self.cursor_offset] = new_value
        self.modified_bytes.add(self.cursor_offset)

        # Add to undo stack
        self._add_undo_action("edit", self.cursor_offset, old_value, new_value)

        # Move to next byte
        self.cursor_offset = min(self.cursor_offset + 1, len(self.data) - 1)
        self.refresh_view()

    def delete_byte(self):
        """Delete byte at cursor (shrink file)."""
        if self.cursor_offset >= len(self.data):
            return

        # Save state for undo
        old_value = self.data[self.cursor_offset]

        # Remove byte
        del self.data[self.cursor_offset]

        # Track all subsequent bytes as modified
        for i in range(self.cursor_offset, len(self.data)):
            self.modified_bytes.add(i)

        # Add to undo stack
        self._add_undo_action("delete", self.cursor_offset, old_value, None)

        self.refresh_view()

    def _add_undo_action(self, action_type, offset, old_value, new_value):
        """Add an action to the undo stack."""
        self.undo_stack.append(
            {"type": action_type, "offset": offset, "old": old_value, "new": new_value}
        )
        # Clear redo stack on new edit
        self.redo_stack.clear()

        # Limit undo stack size
        if len(self.undo_stack) > 1000:
            self.undo_stack.pop(0)

    def undo(self):
        """Undo last edit."""
        if not self.undo_stack:
            return

        action = self.undo_stack.pop()

        if action["type"] == "edit":
            # Restore old value
            self.data[action["offset"]] = action["old"]
            if action["old"] == action["new"]:
                self.modified_bytes.discard(action["offset"])
        elif action["type"] == "delete":
            # Reinsert deleted byte
            self.data.insert(action["offset"], action["old"])

        # Add to redo stack
        self.redo_stack.append(action)

        self.refresh_view()

    def redo(self):
        """Redo last undone edit."""
        if not self.redo_stack:
            return

        action = self.redo_stack.pop()

        if action["type"] == "edit":
            # Reapply new value
            self.data[action["offset"]] = action["new"]
            self.modified_bytes.add(action["offset"])
        elif action["type"] == "delete":
            # Re-delete byte
            del self.data[action["offset"]]

        # Add back to undo stack
        self.undo_stack.append(action)

        self.refresh_view()

    def copy(self):
        """Copy selection to clipboard."""
        if self.selection_start is None or self.selection_end is None:
            # Copy current byte
            if self.cursor_offset < len(self.data):
                byte = self.data[self.cursor_offset]
                self.clipboard_clear()
                self.clipboard_append(f"{byte:02X}")
            return

        # Copy selected bytes
        start = min(self.selection_start, self.selection_end)
        end = max(self.selection_start, self.selection_end)

        hex_str = " ".join(f"{self.data[i]:02X}" for i in range(start, end + 1))
        self.clipboard_clear()
        self.clipboard_append(hex_str)

    def paste(self):
        """Paste from clipboard."""
        try:
            clipboard = self.clipboard_get()
            # Parse hex bytes from clipboard
            hex_bytes = clipboard.replace(" ", "").replace("\n", "")

            # Validate hex string
            if not all(c in "0123456789ABCDEFabcdef" for c in hex_bytes):
                return

            # Parse bytes
            if len(hex_bytes) % 2 != 0:
                return

            bytes_to_paste = []
            for i in range(0, len(hex_bytes), 2):
                bytes_to_paste.append(int(hex_bytes[i : i + 2], 16))

            # Paste bytes
            for i, byte in enumerate(bytes_to_paste):
                offset = self.cursor_offset + i
                if offset < len(self.data):
                    old_value = self.data[offset]
                    self.data[offset] = byte
                    self.modified_bytes.add(offset)
                    self._add_undo_action("edit", offset, old_value, byte)

            self.cursor_offset = min(
                self.cursor_offset + len(bytes_to_paste), len(self.data) - 1
            )
            self.refresh_view()

        except Exception:
            pass

    def get_data(self) -> bytes:
        """Get current data (including modifications)."""
        return bytes(self.data)

    def has_modifications(self) -> bool:
        """Check if data has been modified."""
        return len(self.modified_bytes) > 0
