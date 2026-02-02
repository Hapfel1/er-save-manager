"""Structure Viewer Widget - Shows parsed save file structure in tree view."""

from tkinter import ttk

import customtkinter as ctk


class StructureViewerWidget(ctk.CTkFrame):
    """Widget that shows parsed save file structure in a tree view."""

    def __init__(self, parent, on_offset_click=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Callback for when user clicks on a structure field
        self.on_offset_click = on_offset_click

        # Current save file
        self.save_file = None

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Create the structure viewer UI."""
        # Title label
        ctk.CTkLabel(
            self,
            text="Save Structure",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Info label
        self.info_label = ctk.CTkLabel(
            self,
            text="No save file loaded",
            font=("Segoe UI", 9),
            text_color=("gray50", "gray60"),
        )
        self.info_label.pack(anchor="w", padx=10, pady=(0, 5))

        # Tree frame
        tree_frame = ctk.CTkFrame(self, fg_color=("gray95", "gray10"))
        tree_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Create Treeview with scrollbar
        scrollbar = ctk.CTkScrollbar(tree_frame)
        scrollbar.pack(side="right", fill="y")

        # Style for the treeview
        style = ttk.Style()

        # Configure for dark mode
        appearance = ctk.get_appearance_mode()
        if appearance == "Dark":
            bg_color = "#1a1a1a"
            fg_color = "#e0e0e0"
            field_color = "#2a2a2a"
            select_bg = "#264F78"
            select_fg = "#ffffff"
        else:
            bg_color = "#ffffff"
            fg_color = "#1a1a1a"
            field_color = "#f5f5f5"
            select_bg = "#0078D7"
            select_fg = "#ffffff"

        style.theme_use("default")
        style.configure(
            "Structure.Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=field_color,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Structure.Treeview.Heading",
            background=field_color,
            foreground=fg_color,
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Structure.Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)],
        )

        # Create treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "offset", "size", "value"),
            style="Structure.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )

        # Configure columns
        self.tree.heading("#0", text="Field")
        self.tree.heading("type", text="Type")
        self.tree.heading("offset", text="Offset")
        self.tree.heading("size", text="Size")
        self.tree.heading("value", text="Value")

        self.tree.column("#0", width=200, minwidth=150)
        self.tree.column("type", width=100, minwidth=80)
        self.tree.column("offset", width=80, minwidth=60)
        self.tree.column("size", width=60, minwidth=40)
        self.tree.column("value", width=200, minwidth=100)

        self.tree.pack(fill="both", expand=True, padx=2, pady=2)
        scrollbar.configure(command=self.tree.yview)

        # Bind click event
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

    def load_save_file(self, save_file, raw_data):
        """Load and parse save file structure."""
        self.save_file = save_file
        self.raw_data = raw_data

        # Clear existing tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not save_file:
            self.info_label.configure(text="No save file loaded")
            return

        # Update info
        file_size = len(raw_data)
        size_mb = file_size / (1024 * 1024)
        self.info_label.configure(
            text=f"File Size: {size_mb:.2f} MB ({file_size:,} bytes)"
        )

        # Build tree structure
        self._build_tree()

    def _build_tree(self):
        """Build the tree view from save file structure."""
        if not self.save_file:
            return

        offset = 0

        # Magic bytes
        magic_node = self.tree.insert(
            "",
            "end",
            text="Magic",
            values=(
                "bytes[4]",
                f"0x{offset:08X}",
                "4",
                self.save_file.magic.decode("latin1", errors="replace"),
            ),
            tags=("offset",),
        )
        self.tree.set(magic_node, "#1", offset)  # Store offset in hidden column
        offset += 4

        # Header
        header_size = 0x2FC if not self.save_file.is_ps else 0x6C
        header_node = self.tree.insert(
            "",
            "end",
            text="Header",
            values=("bytes", f"0x{offset:08X}", f"{header_size}", "..."),
            tags=("offset",),
        )
        self.tree.set(header_node, "#1", offset)
        offset += header_size

        # Character slots
        slots_node = self.tree.insert(
            "",
            "end",
            text="Character Slots",
            values=("UserDataX[10]", f"0x{offset:08X}", "", ""),
        )

        for i, slot in enumerate(self.save_file.character_slots):
            slot_offset = offset

            # Checksum (PC only)
            if not self.save_file.is_ps:
                checksum_node = self.tree.insert(
                    slots_node,
                    "end",
                    text=f"Slot {i} Checksum",
                    values=("MD5[16]", f"0x{slot_offset:08X}", "16", "..."),
                    tags=("offset",),
                )
                self.tree.set(checksum_node, "#1", slot_offset)
                slot_offset += 16

            # Slot data
            slot_data_size = 0x27FFF0 if not self.save_file.is_ps else 0x280000
            slot_node = self.tree.insert(
                slots_node,
                "end",
                text=f"Slot {i} Data",
                values=("UserDataX", f"0x{slot_offset:08X}", f"{slot_data_size}", ""),
                tags=("offset",),
            )
            self.tree.set(slot_node, "#1", slot_offset)

            # Add character details if parsed
            if slot and hasattr(slot, "character") and slot.character:
                char = slot.character

                # Character name
                if hasattr(char, "name"):
                    name_node = self.tree.insert(
                        slot_node,
                        "end",
                        text="Character Name",
                        values=(
                            "string",
                            f"0x{slot_offset + 0x1F0:08X}",
                            "32",
                            char.name or "<empty>",
                        ),
                        tags=("offset",),
                    )
                    self.tree.set(name_node, "#1", slot_offset + 0x1F0)

                # Level
                if hasattr(char, "level"):
                    level_node = self.tree.insert(
                        slot_node,
                        "end",
                        text="Level",
                        values=(
                            "uint32",
                            f"0x{slot_offset + 0x70:08X}",
                            "4",
                            str(char.level),
                        ),
                        tags=("offset",),
                    )
                    self.tree.set(level_node, "#1", slot_offset + 0x70)

                # Runes
                if hasattr(char, "runes"):
                    runes_node = self.tree.insert(
                        slot_node,
                        "end",
                        text="Runes",
                        values=(
                            "uint32",
                            f"0x{slot_offset + 0x74:08X}",
                            "4",
                            f"{char.runes:,}",
                        ),
                        tags=("offset",),
                    )
                    self.tree.set(runes_node, "#1", slot_offset + 0x74)

            offset += (16 if not self.save_file.is_ps else 0) + slot_data_size

        # USER_DATA_10
        if self.save_file.user_data_10_parsed:
            ud10 = self.save_file.user_data_10_parsed
            ud10_node = self.tree.insert(
                "",
                "end",
                text="USER_DATA_10 (Common)",
                values=(
                    "UserData10",
                    f"0x{offset:08X}",
                    f"{len(self.save_file.user_data_10)}",
                    "",
                ),
                tags=("offset",),
            )
            self.tree.set(ud10_node, "#1", offset)

            # Steam ID
            if hasattr(ud10, "steam_id"):
                steam_node = self.tree.insert(
                    ud10_node,
                    "end",
                    text="Steam ID",
                    values=(
                        "uint64",
                        f"0x{offset + 0x00:08X}",
                        "8",
                        str(ud10.steam_id),
                    ),
                    tags=("offset",),
                )
                self.tree.set(steam_node, "#1", offset + 0x00)

        offset += len(self.save_file.user_data_10)

        # USER_DATA_11
        if self.save_file.user_data_11:
            ud11_node = self.tree.insert(
                "",
                "end",
                text="USER_DATA_11 (Regulation)",
                values=(
                    "bytes",
                    f"0x{offset:08X}",
                    f"{len(self.save_file.user_data_11)}",
                    "...",
                ),
                tags=("offset",),
            )
            self.tree.set(ud11_node, "#1", offset)

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item to jump to offset."""
        item = self.tree.selection()
        if not item:
            return

        # Get offset from item
        try:
            offset_str = self.tree.set(item[0], "offset")
            if offset_str and offset_str.startswith("0x"):
                offset = int(offset_str, 16)

                # Call callback to jump to offset
                if self.on_offset_click:
                    self.on_offset_click(offset)
        except (ValueError, IndexError):
            pass
