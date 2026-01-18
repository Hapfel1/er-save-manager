"""
Hex Editor Tab
View raw save file data in hexadecimal format
"""

import tkinter as tk
from tkinter import messagebox, ttk


class HexEditorTab:
    """Tab for viewing hex data of save files"""
    
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
        """Setup the hex editor tab UI"""
        ttk.Label(
            self.parent,
            text="Hex Editor",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)
        
        info_text = ttk.Label(
            self.parent,
            text="Advanced: View and edit raw save file data in hexadecimal format",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)
        
        # Warning
        warning_frame = ttk.Frame(self.parent, padding=10)
        warning_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(
            warning_frame,
            text="⚠️  Warning: Direct hex editing can corrupt your save file. Use with caution!",
            font=("Segoe UI", 10, "bold"),
            foreground="red",
        ).pack()
        
        # Controls
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(control_frame, text="Offset:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )
        
        self.hex_offset_var = tk.StringVar(value="0x0000")
        offset_entry = ttk.Entry(
            control_frame,
            textvariable=self.hex_offset_var,
            font=("Consolas", 10),
            width=12,
        )
        offset_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Go to Offset",
            command=self.hex_goto_offset,
            width=15,
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Refresh",
            command=self.hex_refresh,
            width=12,
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Save Changes",
            command=self.hex_save,
            width=15,
        ).pack(side=tk.LEFT, padx=5)
        
        # Hex viewer
        hex_frame = ttk.LabelFrame(self.parent, text="Hex Data", padding=10)
        hex_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create a frame for hex display
        display_frame = ttk.Frame(hex_frame)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        # Hex display
        hex_text_frame = ttk.Frame(display_frame)
        hex_text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        hex_scrollbar = ttk.Scrollbar(hex_text_frame)
        hex_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.hex_text = tk.Text(
            hex_text_frame,
            height=20,
            width=60,
            font=("Consolas", 9),
            yscrollcommand=hex_scrollbar.set,
            wrap=tk.NONE,
        )
        self.hex_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hex_scrollbar.config(command=self.hex_text.yview)
        
        self.hex_text.insert("1.0", "Load a save file to view hex data")
        self.hex_text.config(state="disabled")
        
        # Info panel
        info_panel = ttk.LabelFrame(
            self.parent, text="Save Structure Info", padding=10
        )
        info_panel.pack(fill=tk.X, padx=20, pady=5)
        
        structure_info = """Save File Structure:
• 0x0000-0x0003: Magic bytes (BND4 or SL2\\x00)
• 0x0004-0x02FF: Header data
• 0x0300-0x280FFF: Character slots (10 slots × 0x280000 bytes)
  - Each slot: 0x10 checksum + 0x27FFF0 data
• User data sections contain character stats, inventory, world state"""
        
        ttk.Label(
            info_panel,
            text=structure_info,
            font=("Consolas", 8),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)
    
    def hex_goto_offset(self):
        """Jump to specific offset in hex view"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        offset_str = self.hex_offset_var.get().strip()
        try:
            if offset_str.startswith("0x"):
                offset = int(offset_str, 16)
            else:
                offset = int(offset_str)
            
            self.hex_display_at_offset(offset)
        
        except ValueError:
            messagebox.showerror(
                "Invalid Offset", "Please enter a valid hex offset (e.g., 0x1000)"
            )
    
    def hex_display_at_offset(self, offset=0, length=512):
        """Display hex data at offset"""
        save_file = self.get_save_file()
        if not save_file or not hasattr(save_file, "_raw_data"):
            return
        
        raw_data = save_file._raw_data
        max_offset = len(raw_data)
        
        if offset >= max_offset:
            messagebox.showerror(
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
        """Refresh hex view"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        self.hex_display_at_offset(0)
    
    def hex_save(self):
        """Save hex changes"""
        messagebox.showinfo(
            "Not Implemented",
            "Direct hex editing is not yet implemented.\n\n"
            "This is a read-only hex viewer for now.",
        )
