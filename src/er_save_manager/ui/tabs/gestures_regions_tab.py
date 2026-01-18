"""
Gestures & Regions Tab
View unlocked gestures and discovered regions
"""

import tkinter as tk
from tkinter import messagebox, ttk


class GesturesRegionsTab:
    """Tab for viewing gestures and discovered regions"""
    
    def __init__(self, parent, get_save_file_callback):
        """
        Initialize gestures & regions tab
        
        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        
        self.gesture_slot_var = None
        self.gestures_text = None
        self.regions_text = None
    
    def setup_ui(self):
        """Setup the gestures & regions tab UI"""
        ttk.Label(
            self.parent,
            text="Gestures & Regions",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)
        
        info_text = ttk.Label(
            self.parent,
            text="View and manage unlocked gestures and discovered regions",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)
        
        # Slot selector
        slot_frame = ttk.Frame(self.parent)
        slot_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(slot_frame, text="Character Slot:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )
        
        self.gesture_slot_var = tk.IntVar(value=1)
        slot_combo = ttk.Combobox(
            slot_frame,
            textvariable=self.gesture_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            slot_frame,
            text="Load Character",
            command=self.load_gestures_regions,
            width=20,
        ).pack(side=tk.LEFT, padx=10)
        
        # Notebook for gestures and regions
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Gestures tab
        gestures_frame = ttk.Frame(notebook, padding=10)
        notebook.add(gestures_frame, text="Gestures")
        
        gestures_text_frame = ttk.Frame(gestures_frame)
        gestures_text_frame.pack(fill=tk.BOTH, expand=True)
        
        gestures_scrollbar = ttk.Scrollbar(gestures_text_frame)
        gestures_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.gestures_text = tk.Text(
            gestures_text_frame,
            height=15,
            font=("Consolas", 9),
            yscrollcommand=gestures_scrollbar.set,
            wrap=tk.WORD,
        )
        self.gestures_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        gestures_scrollbar.config(command=self.gestures_text.yview)
        
        self.gestures_text.insert("1.0", "Load a character to view unlocked gestures")
        self.gestures_text.config(state="disabled")
        
        # Regions tab
        regions_frame = ttk.Frame(notebook, padding=10)
        notebook.add(regions_frame, text="Regions")
        
        regions_text_frame = ttk.Frame(regions_frame)
        regions_text_frame.pack(fill=tk.BOTH, expand=True)
        
        regions_scrollbar = ttk.Scrollbar(regions_text_frame)
        regions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.regions_text = tk.Text(
            regions_text_frame,
            height=15,
            font=("Consolas", 9),
            yscrollcommand=regions_scrollbar.set,
            wrap=tk.WORD,
        )
        self.regions_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        regions_scrollbar.config(command=self.regions_text.yview)
        
        self.regions_text.insert("1.0", "Load a character to view discovered regions")
        self.regions_text.config(state="disabled")
    
    def load_gestures_regions(self):
        """Load gestures and regions for selected character"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return
        
        slot_idx = self.gesture_slot_var.get() - 1
        slot = save_file.characters[slot_idx]
        
        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return
        
        try:
            char_name = slot.get_character_name()
            
            # Load Gestures
            self.gestures_text.config(state="normal")
            self.gestures_text.delete("1.0", tk.END)
            self.gestures_text.insert("1.0", f"Gestures for {char_name}\n\n")
            
            if hasattr(slot, "gestures") and slot.gestures:
                unlocked = [g for g in slot.gestures.gesture_ids if g > 0]
                self.gestures_text.insert(
                    tk.END,
                    f"Total gestures unlocked: {len(unlocked)}\n\n",
                )
                self.gestures_text.insert(tk.END, "Gesture IDs:\n")
                for i, gesture_id in enumerate(slot.gestures.gesture_ids):
                    if gesture_id > 0:
                        self.gestures_text.insert(tk.END, f"  Slot {i}: {gesture_id}\n")
            else:
                self.gestures_text.insert(tk.END, "No gesture data available")
            
            self.gestures_text.config(state="disabled")
            
            # Load Regions
            self.regions_text.config(state="normal")
            self.regions_text.delete("1.0", tk.END)
            self.regions_text.insert("1.0", f"Regions for {char_name}\n\n")
            
            if hasattr(slot, "regions") and slot.regions:
                discovered = [r for r in slot.regions.region_ids if r > 0]
                self.regions_text.insert(
                    tk.END, f"Total regions discovered: {len(discovered)}\n\n"
                )
                self.regions_text.insert(tk.END, "Region IDs:\n")
                for i, region_id in enumerate(slot.regions.region_ids):
                    if region_id > 0:
                        self.regions_text.insert(tk.END, f"  Slot {i}: {region_id}\n")
            else:
                self.regions_text.insert(tk.END, "No region data available")
            
            self.regions_text.config(state="disabled")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
            import traceback
            traceback.print_exc()
