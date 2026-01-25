"""Hex Editor Tab (customtkinter version)."""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox


class HexEditorTab:
    """Tab for viewing hex data of save files (customtkinter version)."""

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
        self.hex_text = None

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
            text="Advanced: View and edit raw save file data in hexadecimal format\n(Full editing coming soon)",
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
            text="⚠️  Warning: Direct hex editing can corrupt your save file. Use with caution!",
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
            text="Refresh",
            command=self.hex_refresh,
            width=100,
        ).pack(side="left", padx=5)

        # Hex viewer
        hex_frame = ctk.CTkFrame(self.parent, corner_radius=12)
        hex_frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            hex_frame,
            text="Hex Data",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # Hex text display (using tk.Text since CTk doesn't have native text widget)
        hex_inner = ctk.CTkFrame(hex_frame)
        hex_inner.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        scrollbar = ctk.CTkScrollbar(hex_inner)
        scrollbar.pack(side="right", fill="y")

        appearance = ctk.get_appearance_mode()
        hex_bg = "#1f1f28" if appearance == "Dark" else "#f5f5f5"
        hex_fg = "#e5e5f5" if appearance == "Dark" else "#1f1f28"

        self.hex_text = tk.Text(
            hex_inner,
            height=20,
            width=60,
            font=("Consolas", 11),
            yscrollcommand=scrollbar.set,
            wrap="none",
            bg=hex_bg,
            fg=hex_fg,
            insertbackground=hex_fg,
        )
        self.hex_text.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.hex_text.yview)

        self.hex_text.insert("1.0", "Load a save file to view hex data")
        self.hex_text.config(state="disabled")

        # Info panel
        info_panel = ctk.CTkFrame(self.parent, corner_radius=12)
        info_panel.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            info_panel,
            text="Save Structure Info",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        structure_info = """Save File Structure:
• 0x0000-0x0003: Magic bytes (BND4 or SL2\\x00)
• 0x0004-0x02FF: Header data
• 0x0300-0x280FFF: Character slots (10 slots × 0x280000 bytes)
  - Each slot: 0x10 checksum + 0x27FFF0 data
• User data sections contain character stats, inventory, world state"""

        ctk.CTkLabel(
            info_panel,
            text=structure_info,
            font=("Consolas", 10),
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 12))

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

            self.hex_display_at_offset(offset)

        except ValueError:
            CTkMessageBox.showerror(
                "Invalid Offset", "Please enter a valid hex offset (e.g., 0x1000)"
            )

    def hex_display_at_offset(self, offset=0, length=512):
        """Display hex data at offset."""
        save_file = self.get_save_file()
        if not save_file or not hasattr(save_file, "_raw_data"):
            return

        raw_data = save_file._raw_data
        max_offset = len(raw_data)

        if offset >= max_offset:
            CTkMessageBox.showerror(
                "Invalid Offset", f"Offset {offset} exceeds file size {max_offset}"
            )
            return

        end_offset = min(offset + length, max_offset)

        self.hex_text.config(state="normal")
        self.hex_text.delete("1.0", tk.END)

        # Display hex dump
        for i in range(offset, end_offset, 16):
            line_offset = f"{i:08X}: "
            hex_part = ""
            ascii_part = ""

            for j in range(16):
                if i + j < end_offset:
                    byte = raw_data[i + j]
                    hex_part += f"{byte:02X} "
                    ascii_part += chr(byte) if 32 <= byte < 127 else "."
                else:
                    hex_part += "   "
                    ascii_part += " "

                if j == 7:
                    hex_part += " "

            self.hex_text.insert(tk.END, f"{line_offset}{hex_part} {ascii_part}\n")

        self.hex_text.config(state="disabled")

    def hex_refresh(self):
        """Refresh hex view."""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        self.hex_display_at_offset(0)
