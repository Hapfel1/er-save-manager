"""
Event Flags Tab
Comprehensive event flag viewer and editor with 948 documented flags
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.boss_data import BOSS_CATEGORIES, BOSSES
from er_save_manager.data.event_flags_db import (
    CATEGORIES,
    get_category_flags,
    get_flag_name,
    get_subcategories,
)
from er_save_manager.parser.event_flags import EventFlags


class EventFlagsTab:
    """Tab for event flag viewing and management"""

    def __init__(
        self, parent, get_save_file_callback, get_save_path_callback, reload_callback
    ):
        """
        Initialize event flags tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback

        self.eventflag_slot_var = None
        self.current_slot = None
        self.category_var = None
        self.subcategory_var = None
        self.search_var = None
        self.flag_states = {}  # Track checkbox states
        self.flag_widgets = {}  # Track checkbox widgets
        self.current_event_flags = None

    def setup_ui(self):
        """Setup the event flags tab UI"""
        ttk.Label(
            self.parent,
            text="Event Flags",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=10)

        info_text = ttk.Label(
            self.parent,
            text="View and edit event flags - 1,295 documented flags across 8 categories",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        info_text.pack(pady=5)

        # Slot selector
        slot_frame = ttk.Frame(self.parent)
        slot_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(slot_frame, text="Character Slot:", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, padx=5
        )

        self.eventflag_slot_var = tk.IntVar(value=1)
        slot_combo = ttk.Combobox(
            slot_frame,
            textvariable=self.eventflag_slot_var,
            values=list(range(1, 11)),
            state="readonly",
            width=5,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            slot_frame,
            text="Load Flags",
            command=self.load_event_flags,
            width=15,
        ).pack(side=tk.LEFT, padx=10)

        # Category selector
        filter_frame = ttk.LabelFrame(
            self.parent, text="Browse by Category", padding=10
        )
        filter_frame.pack(fill=tk.X, padx=20, pady=5)

        cat_frame = ttk.Frame(filter_frame)
        cat_frame.pack(fill=tk.X)

        ttk.Label(cat_frame, text="Category:").pack(side=tk.LEFT, padx=5)
        self.category_var = tk.StringVar()
        cat_combo = ttk.Combobox(
            cat_frame,
            textvariable=self.category_var,
            values=[""] + CATEGORIES,
            state="readonly",
            width=30,
        )
        cat_combo.pack(side=tk.LEFT, padx=5)
        cat_combo.bind("<<ComboboxSelected>>", self.on_category_changed)

        ttk.Label(cat_frame, text="Subcategory:").pack(side=tk.LEFT, padx=(20, 5))
        self.subcategory_var = tk.StringVar()
        self.subcat_combo = ttk.Combobox(
            cat_frame,
            textvariable=self.subcategory_var,
            state="readonly",
            width=30,
        )
        self.subcat_combo.pack(side=tk.LEFT, padx=5)
        self.subcat_combo.bind("<<ComboboxSelected>>", self.on_subcategory_changed)

        # Search bar
        search_frame = ttk.LabelFrame(self.parent, text="Search Flags", padding=10)
        search_frame.pack(fill=tk.X, padx=20, pady=5)

        search_inner = ttk.Frame(search_frame)
        search_inner.pack(fill=tk.X)

        ttk.Label(search_inner, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search_changed)
        search_entry = ttk.Entry(search_inner, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(
            search_inner, text="(Search by flag ID or name)", foreground="gray"
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            search_inner, text="Clear", command=self.clear_search, width=10
        ).pack(side=tk.LEFT, padx=5)

        # Flags viewer
        flags_frame = ttk.LabelFrame(self.parent, text="Event Flags", padding=10)
        flags_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # Canvas for scrollable flags
        flags_canvas = tk.Canvas(flags_frame, highlightthickness=0)
        flags_scrollbar = ttk.Scrollbar(
            flags_frame, orient="vertical", command=flags_canvas.yview
        )
        self.flags_inner_frame = ttk.Frame(flags_canvas)

        self.flags_inner_frame.bind(
            "<Configure>",
            lambda e: flags_canvas.configure(scrollregion=flags_canvas.bbox("all")),
        )

        flags_canvas.create_window((0, 0), window=self.flags_inner_frame, anchor="nw")
        flags_canvas.configure(yscrollcommand=flags_scrollbar.set)

        flags_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        flags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel
        def on_mousewheel(event):
            flags_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        flags_canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Action buttons
        action_frame = ttk.Frame(flags_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            action_frame,
            text="Boss Respawn...",
            command=self.open_boss_respawn,
            width=18,
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            action_frame,
            text="Unlock All in Category",
            command=self.unlock_all_in_category,
            width=20,
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            action_frame,
            text="Apply Changes",
            command=self.apply_changes,
            width=18,
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            action_frame,
            text="Advanced...",
            command=self.open_advanced_editor,
            width=15,
        ).pack(side=tk.RIGHT, padx=5)

        self.status_label = ttk.Label(
            action_frame,
            text="Select a category or search for flags",
            foreground="gray",
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

    def load_event_flags(self):
        """Load event flags for selected character"""
        save_file = self.get_save_file()
        if not save_file:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = self.eventflag_slot_var.get() - 1
        slot = save_file.characters[slot_idx]

        if slot.is_empty():
            messagebox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return

        self.current_slot = slot_idx

        if not hasattr(slot, "event_flags") or not slot.event_flags:
            messagebox.showerror("Error", "Event flags not available")
            return

        self.current_event_flags = slot.event_flags
        self.flag_states.clear()
        self.flag_widgets.clear()
        for widget in self.flags_inner_frame.winfo_children():
            widget.destroy()

        self.status_label.config(
            text=f"Loaded Slot {slot_idx + 1}. Select category or search."
        )

        messagebox.showinfo(
            "Loaded",
            f"Loaded event flags for Slot {slot_idx + 1}.\n\n"
            f"Use Category dropdown or Search to view flags.",
        )

    def on_category_changed(self, event=None):
        """Handle category selection"""
        if self.current_event_flags is None:
            messagebox.showwarning("No Flags", "Load event flags first!")
            self.category_var.set("")
            return

        category = self.category_var.get()
        if not category:
            self.clear_flags_display()
            return

        subcats = get_subcategories(category)
        if subcats:
            self.subcat_combo.config(values=["All"] + subcats)
            self.subcategory_var.set("All")
        else:
            self.subcat_combo.config(values=[])
            self.subcategory_var.set("")

        self.load_category_flags(category, None)

    def on_subcategory_changed(self, event=None):
        """Handle subcategory selection"""
        if self.current_event_flags is None:
            return

        category = self.category_var.get()
        subcategory = self.subcategory_var.get()

        if not category:
            return

        if subcategory == "All" or not subcategory:
            self.load_category_flags(category, None)
        else:
            self.load_category_flags(category, subcategory)

    def load_category_flags(self, category: str, subcategory: str = None):
        """Load flags for category/subcategory"""
        flag_ids = get_category_flags(category, subcategory)

        if not flag_ids:
            self.clear_flags_display()
            self.status_label.config(text="No flags in this category")
            return

        self.clear_flags_display()

        for flag_id in flag_ids:
            self.create_flag_checkbox(flag_id)

        subcat_text = f" > {subcategory}" if subcategory else ""
        self.status_label.config(
            text=f"Showing {len(flag_ids)} flags from {category}{subcat_text}"
        )

    def on_search_changed(self, *args):
        """Handle search"""
        if self.current_event_flags is None:
            return

        search_term = self.search_var.get().strip().lower()

        if not search_term:
            if not self.category_var.get():
                self.clear_flags_display()
            return

        self.category_var.set("")
        self.subcategory_var.set("")

        matching_flags = []

        try:
            flag_id = int(search_term)
            matching_flags = [flag_id]
        except ValueError:
            from er_save_manager.data.event_flags_db import EVENT_FLAGS

            for fid, info in EVENT_FLAGS.items():
                if search_term in info["name"].lower() or search_term in str(fid):
                    matching_flags.append(fid)

        if matching_flags:
            self.clear_flags_display()
            for flag_id in sorted(matching_flags)[:100]:
                self.create_flag_checkbox(flag_id)

            count_text = (
                f"{len(matching_flags)} (showing 100)"
                if len(matching_flags) > 100
                else str(len(matching_flags))
            )
            self.status_label.config(text=f"Found {count_text} matching flags")
        else:
            self.clear_flags_display()
            self.status_label.config(text="No matching flags")

    def create_flag_checkbox(self, flag_id: int):
        """Create checkbox for flag"""
        if flag_id in self.flag_widgets:
            return

        name = get_flag_name(flag_id)

        try:
            flag_value = EventFlags.get_flag(self.current_event_flags, flag_id)
        except (ValueError, IndexError):
            flag_value = False

        var = tk.BooleanVar(value=flag_value)
        self.flag_states[flag_id] = var

        cb = ttk.Checkbutton(
            self.flags_inner_frame,
            text=f"{flag_id}: {name}",
            variable=var,
        )
        cb.pack(anchor=tk.W, pady=1, padx=5)
        self.flag_widgets[flag_id] = cb

    def clear_flags_display(self):
        """Clear all checkboxes"""
        for widget in self.flag_widgets.values():
            widget.pack_forget()
        self.flag_widgets.clear()
        self.flag_states.clear()

    def clear_search(self):
        """Clear search"""
        self.search_var.set("")
        self.clear_flags_display()
        self.status_label.config(text="Search cleared")

    def unlock_all_in_category(self):
        """Unlock all flags in current category/subcategory"""
        if not self.flag_states:
            messagebox.showwarning(
                "No Category", "Please select a category first to unlock all flags."
            )
            return

        category = self.category_var.get()
        subcategory = self.subcategory_var.get()

        if not category:
            messagebox.showwarning("No Category", "Please select a category first.")
            return

        subcat_text = (
            f" > {subcategory}" if subcategory and subcategory != "All" else ""
        )
        count = len(self.flag_states)

        if not messagebox.askyesno(
            "Unlock All",
            f"Set ALL {count} flags in {category}{subcat_text} to ON?\n\n"
            f"Click Apply Changes after to save.",
        ):
            return

        # Set all to True
        for var in self.flag_states.values():
            var.set(True)

        messagebox.showinfo(
            "Flags Selected", f"Set {count} flags to ON. Click Apply Changes to save."
        )

    def open_advanced_editor(self):
        """Open advanced custom flag editor dialog"""
        if self.current_event_flags is None:
            messagebox.showwarning("No Flags", "Please load event flags first!")
            return

        # Create dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Advanced Flag Editor")
        dialog.geometry("600x400")
        dialog.transient(self.parent)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Advanced Custom Flag Editor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        ttk.Label(
            dialog,
            text="Enter custom flag IDs to read/modify (one per line or comma-separated)",
            font=("Segoe UI", 10),
        ).pack(pady=5)

        # Input frame
        input_frame = ttk.LabelFrame(dialog, text="Enter Flag IDs", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Text widget for flag IDs
        text_frame = ttk.Frame(input_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        flag_ids_text = tk.Text(
            text_frame,
            height=10,
            width=50,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
        )
        flag_ids_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=flag_ids_text.yview)

        ttk.Label(
            input_frame,
            text="Example: 71190, 9100, 20\nor one per line",
            foreground="gray",
            font=("Segoe UI", 8),
        ).pack(pady=5)

        # Results frame
        results_frame = ttk.LabelFrame(dialog, text="Flag States", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        results_text = tk.Text(
            results_frame,
            height=8,
            width=50,
            font=("Consolas", 9),
            state="disabled",
        )
        results_text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        def read_flags():
            """Read entered flag IDs"""
            text_content = flag_ids_text.get("1.0", tk.END).strip()
            if not text_content:
                messagebox.showwarning("No IDs", "Please enter flag IDs first.")
                return

            # Parse IDs (comma or newline separated)
            import re

            flag_ids = []
            for match in re.finditer(r"\d+", text_content):
                try:
                    flag_ids.append(int(match.group()))
                except (ValueError, AttributeError):
                    pass

            if not flag_ids:
                messagebox.showwarning("No Valid IDs", "No valid flag IDs found.")
                return

            # Read flags
            results_text.config(state="normal")
            results_text.delete("1.0", tk.END)

            for flag_id in sorted(set(flag_ids)):
                try:
                    value = EventFlags.get_flag(self.current_event_flags, flag_id)
                    name = get_flag_name(flag_id)
                    state = "ON" if value else "OFF"
                    results_text.insert(tk.END, f"{flag_id}: [{state}] {name}\n")
                except Exception as e:
                    results_text.insert(tk.END, f"{flag_id}: ERROR - {str(e)}\n")

            results_text.config(state="disabled")

        def set_flags_on():
            """Set entered flags to ON"""
            self._apply_advanced_flags(flag_ids_text, True)
            dialog.destroy()

        def set_flags_off():
            """Set entered flags to OFF"""
            self._apply_advanced_flags(flag_ids_text, False)
            dialog.destroy()

        ttk.Button(button_frame, text="Read Flags", command=read_flags, width=15).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            button_frame, text="Set All ON", command=set_flags_on, width=15
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            button_frame, text="Set All OFF", command=set_flags_off, width=15
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy, width=10).pack(
            side=tk.RIGHT, padx=5
        )

    def _apply_advanced_flags(self, text_widget, state: bool):
        """Apply advanced flag changes"""
        text_content = text_widget.get("1.0", tk.END).strip()
        if not text_content:
            messagebox.showwarning("No IDs", "Please enter flag IDs first.")
            return

        # Parse IDs
        import re

        flag_ids = []
        for match in re.finditer(r"\d+", text_content):
            try:
                flag_ids.append(int(match.group()))
            except (ValueError, AttributeError):
                pass

        if not flag_ids:
            messagebox.showwarning("No Valid IDs", "No valid flag IDs found.")
            return

        save_file = self.get_save_file()
        if not save_file or self.current_slot is None:
            messagebox.showwarning("Error", "No save file loaded!")
            return

        slot = save_file.characters[self.current_slot]

        state_text = "ON" if state else "OFF"
        if not messagebox.askyesno(
            "Apply Advanced Changes",
            f"Set {len(flag_ids)} flags to {state_text} in Slot {self.current_slot + 1}?\n\n"
            f"Backup will be created.",
        ):
            return

        try:
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            if isinstance(self.current_event_flags, bytes):
                self.current_event_flags = bytearray(self.current_event_flags)
                slot.event_flags = self.current_event_flags

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_advanced_flags_slot_{self.current_slot + 1}",
                    operation=f"advanced_flags_slot_{self.current_slot + 1}",
                    save=save_file,
                )

            # Apply changes
            success_count = 0
            for flag_id in sorted(set(flag_ids)):
                try:
                    EventFlags.set_flag(self.current_event_flags, flag_id, state)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to set flag {flag_id}: {e}")

            # Write back
            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset >= 0:
                slot_offset = save_file._slot_offsets[self.current_slot]
                abs_offset = slot_offset + 0x10 + slot.event_flags_offset
                save_file._raw_data[
                    abs_offset : abs_offset + len(self.current_event_flags)
                ] = self.current_event_flags

            save_file.recalculate_checksums()
            save_file.to_file(save_path)

            messagebox.showinfo(
                "Success",
                f"Set {success_count}/{len(flag_ids)} flags to {state_text}!",
            )

            self.reload_save()

        except Exception as e:
            messagebox.showerror("Error", f"Failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def apply_changes(self):
        """Apply flag changes"""
        if not self.flag_states:
            messagebox.showinfo("No Changes", "No flags to apply")
            return

        save_file = self.get_save_file()
        if not save_file or self.current_slot is None:
            messagebox.showwarning("Error", "No save file loaded!")
            return

        slot = save_file.characters[self.current_slot]

        changes = []
        for flag_id, var in self.flag_states.items():
            try:
                current = EventFlags.get_flag(self.current_event_flags, flag_id)
                new_value = var.get()
                if current != new_value:
                    changes.append((flag_id, new_value))
            except (ValueError, IndexError):
                pass

        if not changes:
            messagebox.showinfo("No Changes", "No flags modified")
            return

        if not messagebox.askyesno(
            "Apply Changes",
            f"Apply {len(changes)} changes to Slot {self.current_slot + 1}?\n\n"
            f"Backup will be created.",
        ):
            return

        try:
            if isinstance(save_file._raw_data, bytes):
                save_file._raw_data = bytearray(save_file._raw_data)

            if isinstance(self.current_event_flags, bytes):
                self.current_event_flags = bytearray(self.current_event_flags)
                slot.event_flags = self.current_event_flags

            save_path = self.get_save_path()
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_event_flags_slot_{self.current_slot + 1}",
                    operation=f"event_flags_slot_{self.current_slot + 1}",
                    save=save_file,
                )

            for flag_id, new_value in changes:
                EventFlags.set_flag(self.current_event_flags, flag_id, new_value)

            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset >= 0:
                slot_offset = save_file._slot_offsets[self.current_slot]
                abs_offset = slot_offset + 0x10 + slot.event_flags_offset
                save_file._raw_data[
                    abs_offset : abs_offset + len(self.current_event_flags)
                ] = self.current_event_flags

            save_file.recalculate_checksums()
            save_file.to_file(save_path)

            messagebox.showinfo(
                "Success",
                f"Applied {len(changes)} changes to Slot {self.current_slot + 1}!",
            )

            self.reload_save()
            self.load_event_flags()

        except Exception as e:
            messagebox.showerror("Error", f"Failed:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def open_boss_respawn(self):
        """Open boss respawn dialog"""
        if self.current_event_flags is None:
            messagebox.showwarning("No Flags", "Please load event flags first!")
            return

        # Create dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Boss Respawn")
        dialog.geometry("700x500")
        dialog.transient(self.parent)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Boss Respawn",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        ttk.Label(
            dialog,
            text="Respawn bosses by clearing their defeat flags",
            font=("Segoe UI", 10),
        ).pack(pady=5)

        # Warning
        warning_frame = ttk.Frame(dialog)
        warning_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(
            warning_frame,
            text="IMPORTANT: After loading the game, REST AT A GRACE IMMEDIATELY!\n"
            "This forces the game to reload world state from event flags.\n"
            "If you don't rest immediately, the game will undo the changes.",
            foreground="red",
            font=("Segoe UI", 9, "bold"),
            wraplength=660,
            justify=tk.CENTER,
        ).pack()

        # Boss selection frame
        boss_frame = ttk.LabelFrame(dialog, text="Select Boss", padding=10)
        boss_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Important instructions
        instruction_frame = ttk.LabelFrame(
            boss_frame, text="CRITICAL: Read Before Respawning", padding=10
        )
        instruction_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            instruction_frame,
            text="After respawning bosses, you MUST:\n"
            "1. Load the game and your character\n"
            "2. IMMEDIATELY rest at ANY grace (before doing anything else)\n"
            "3. The boss will spawn after you rest\n\n"
            "If you don't rest immediately, the game will revert the changes!",
            foreground="red",
            font=("Segoe UI", 9, "bold"),
            justify=tk.LEFT,
        ).pack()

        # Category filter
        filter_frame = ttk.Frame(boss_frame)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        filter_var = tk.StringVar(value="All")

        # Use actual boss categories from data
        filter_values = ["All"] + sorted(BOSS_CATEGORIES)

        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=filter_var,
            values=filter_values,
            state="readonly",
            width=30,
        )
        filter_combo.pack(side=tk.LEFT, padx=5)

        # Boss list
        boss_list_frame = ttk.Frame(boss_frame)
        boss_list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(boss_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        boss_listbox = tk.Listbox(
            boss_list_frame,
            selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 9),
        )
        boss_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=boss_listbox.yview)

        # Boss data imported from boss_data.py (157 bosses total)

        def populate_boss_list(filter_text="All"):
            """Populate boss list based on filter"""
            boss_listbox.delete(0, tk.END)
            for boss_name, boss_data in sorted(BOSSES.items()):
                if filter_text == "All" or boss_data["category"] == filter_text:
                    # Check if boss is alive
                    try:
                        main_flag = boss_data["flags"][0]
                        is_defeated = EventFlags.get_flag(
                            self.current_event_flags, main_flag
                        )
                        status = "[DEFEATED]" if is_defeated else "[ALIVE]"
                    except (ValueError, IndexError, KeyError):
                        status = "[?]"

                    boss_listbox.insert(tk.END, f"{status} | {boss_name}")

        filter_combo.bind(
            "<<ComboboxSelected>>", lambda e: populate_boss_list(filter_var.get())
        )
        populate_boss_list()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        def respawn_selected():
            """Respawn selected bosses"""
            selection = boss_listbox.curselection()
            if not selection:
                messagebox.showwarning(
                    "No Selection", "Please select bosses to respawn."
                )
                return

            selected_bosses = []
            for idx in selection:
                text = boss_listbox.get(idx)
                boss_name = text.split(" | ", 1)[1]
                if boss_name in BOSSES:
                    selected_bosses.append(boss_name)

            if not messagebox.askyesno(
                "Respawn Bosses",
                f"Respawn {len(selected_bosses)} boss(es)?\n\n"
                f"This will clear all defeat flags for selected bosses.\n\n"
                f"CRITICAL STEP AFTER LOADING GAME:\n"
                f"You MUST rest at a grace IMMEDIATELY after loading!\n\n"
                f"Backup will be created.",
            ):
                return

            try:
                save_file = self.get_save_file()
                if isinstance(save_file._raw_data, bytes):
                    save_file._raw_data = bytearray(save_file._raw_data)

                if isinstance(self.current_event_flags, bytes):
                    self.current_event_flags = bytearray(self.current_event_flags)
                    slot = save_file.characters[self.current_slot]
                    slot.event_flags = self.current_event_flags

                save_path = self.get_save_path()
                if save_path:
                    manager = BackupManager(Path(save_path))
                    manager.create_backup(
                        description=f"before_boss_respawn_slot_{self.current_slot + 1}",
                        operation=f"boss_respawn_slot_{self.current_slot + 1}",
                        save=save_file,
                    )

                # Respawn bosses - clear all flags
                for boss_name in selected_bosses:
                    boss_flags = BOSSES[boss_name]["flags"]
                    for flag_id in boss_flags:
                        try:
                            EventFlags.set_flag(
                                self.current_event_flags, flag_id, False
                            )
                        except Exception as e:
                            print(
                                f"Failed to clear flag {flag_id} for {boss_name}: {e}"
                            )

                # Write back
                slot = save_file.characters[self.current_slot]
                if hasattr(slot, "event_flags_offset") and slot.event_flags_offset >= 0:
                    slot_offset = save_file._slot_offsets[self.current_slot]
                    abs_offset = slot_offset + 0x10 + slot.event_flags_offset
                    save_file._raw_data[
                        abs_offset : abs_offset + len(self.current_event_flags)
                    ] = self.current_event_flags

                save_file.recalculate_checksums()
                save_file.to_file(save_path)

                # Verify the write by reloading and checking
                try:
                    from er_save_manager.parser.save import Save

                    verify_save = Save.from_file(save_path)
                    verify_slot = verify_save.characters[self.current_slot]
                    verify_event_flags = verify_slot.event_flags

                    # Check if first boss flag is still OFF
                    test_boss = selected_bosses[0]
                    test_flag = BOSSES[test_boss]["flags"][0]
                    verify_state = EventFlags.get_flag(verify_event_flags, test_flag)

                    if verify_state:
                        messagebox.showwarning(
                            "Verification Failed",
                            f"WARNING: Verified save file still shows boss flag as ON!\n"
                            f"Test flag {test_flag} for {test_boss} is still TRUE.\n\n"
                            f"This suggests:\n"
                            f"1. Steam Cloud may be syncing old save\n"
                            f"2. Another process is modifying the file\n"
                            f"3. File write permissions issue\n\n"
                            f"Try: Disable Steam Cloud sync for Elden Ring",
                        )
                except Exception as e:
                    print(f"Verification check failed: {e}")

                messagebox.showinfo(
                    "Success",
                    f"Respawned {len(selected_bosses)} boss(es)!\n\n"
                    f"CRITICAL: Follow these steps EXACTLY:\n"
                    f"1. Close this tool\n"
                    f"2. Start Elden Ring\n"
                    f"3. Load your character\n"
                    f"4. IMMEDIATELY rest at ANY grace\n"
                    f"5. Boss will spawn after resting\n\n"
                    f"If you don't rest immediately, changes will be reverted!",
                )

                dialog.destroy()
                self.reload_save()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to respawn bosses:\n{str(e)}")
                import traceback

                traceback.print_exc()

        ttk.Button(
            button_frame,
            text="Check World Area Data",
            command=lambda: self.check_world_area(boss_listbox),
            width=25,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Check Selected Boss Flags",
            command=lambda: self.check_boss_flags(boss_listbox),
            width=25,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame, text="Respawn Selected", command=respawn_selected, width=20
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Select All",
            command=lambda: boss_listbox.select_set(0, tk.END),
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Deselect All",
            command=lambda: boss_listbox.selection_clear(0, tk.END),
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Close", command=dialog.destroy, width=10).pack(
            side=tk.RIGHT, padx=5
        )

    def check_boss_flags(self, boss_listbox):
        """Check and display current state of boss flags"""
        if self.current_event_flags is None:
            messagebox.showwarning("No Flags", "Please load event flags first!")
            return

        selection = boss_listbox.curselection()
        if not selection or len(selection) != 1:
            messagebox.showwarning(
                "Selection", "Please select exactly ONE boss to check."
            )
            return

        # Get boss name
        text = boss_listbox.get(selection[0])
        boss_name = text.split(" | ", 1)[1]

        if boss_name not in BOSSES:
            messagebox.showerror("Error", f"Boss '{boss_name}' not found in database.")
            return

        boss_flags = BOSSES[boss_name]["flags"]

        # Check all flags
        flag_states = []
        for flag_id in boss_flags:
            try:
                state = EventFlags.get_flag(self.current_event_flags, flag_id)
                flag_states.append((flag_id, state))
            except Exception as e:
                flag_states.append((flag_id, f"ERROR: {e}"))

        # Create display dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"Flag States: {boss_name}")
        dialog.geometry("600x400")
        dialog.transient(self.parent)

        ttk.Label(
            dialog,
            text=f"Current Flag States for {boss_name}",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=10)

        # Text widget to show flags
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(
            text_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            wrap=tk.WORD,
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # Add flag information
        flag_descriptions = {
            0: "isDefeated - Main defeat flag",
            1: "isEncountered - Boss has been seen",
            2: "Defeat flag (Loot, common funcs)",
            3: "Loot already given (should be FALSE to get loot)",
            4: "Defeat flag (Non-resetting, ALWAYS_TRUE in CEA)",
            5: "Event status after defeat",
            6: "Door/Arena flag",
            7: "Grace menu icon (ALWAYS_FALSE in CEA)",
            8: "Defeat flag (Resetting, clears on NG+)",
        }

        text_widget.insert(tk.END, f"Boss: {boss_name}\n")
        text_widget.insert(tk.END, f"Category: {BOSSES[boss_name]['category']}\n")
        text_widget.insert(tk.END, f"Total flags: {len(boss_flags)}\n\n")
        text_widget.insert(tk.END, "Flag States:\n")
        text_widget.insert(tk.END, "=" * 60 + "\n\n")

        for idx, (flag_id, state) in enumerate(flag_states):
            desc = flag_descriptions.get(idx, "Unknown")
            state_str = (
                "ON" if state is True else "OFF" if state is False else str(state)
            )

            text_widget.insert(tk.END, f"Flag #{idx}: {flag_id}\n")
            text_widget.insert(tk.END, f"  Description: {desc}\n")
            text_widget.insert(tk.END, f"  Current State: {state_str}\n")

            # Add hint about what this means
            if idx == 0:
                if state:
                    text_widget.insert(
                        tk.END,
                        "  -> Boss is DEFEATED (this should be OFF for respawn)\n",
                    )
                else:
                    text_widget.insert(tk.END, "  -> Boss is ALIVE\n")
            elif idx == 4:
                text_widget.insert(
                    tk.END, "  -> CEA keeps this ON even when respawning\n"
                )

            text_widget.insert(tk.END, "\n")

        text_widget.insert(tk.END, "\n" + "=" * 60 + "\n")
        text_widget.insert(tk.END, "DIAGNOSIS:\n")

        main_flag_state = flag_states[0][1]
        if main_flag_state is True:
            text_widget.insert(tk.END, "Boss appears DEFEATED (flag #0 is ON)\n")
            text_widget.insert(tk.END, "To respawn: Set flag #0 to OFF\n")
        elif main_flag_state is False:
            text_widget.insert(tk.END, "Boss appears ALIVE (flag #0 is OFF)\n")
            text_widget.insert(tk.END, "If boss is still dead in-game:\n")
            text_widget.insert(tk.END, "  1. Game may be checking a different flag\n")
            text_widget.insert(tk.END, "  2. Boss entity may need area reload\n")
            text_widget.insert(tk.END, "  3. Try clearing flag #4 as well (risky)\n")

        text_widget.config(state="disabled")

        ttk.Button(dialog, text="Close", command=dialog.destroy, width=15).pack(pady=10)

    def check_world_area(self, boss_listbox):
        """Check world area data to see if boss entities are stored there"""
        save_file = self.get_save_file()
        if not save_file or self.current_slot is None:
            messagebox.showwarning("No Save", "Please load a save file first!")
            return

        slot = save_file.characters[self.current_slot]

        # Create display dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"World Area Data - Slot {self.current_slot + 1}")
        dialog.geometry("700x500")
        dialog.transient(self.parent)

        ttk.Label(
            dialog,
            text="World Area Data Analysis",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=10)

        # Text widget to show data
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(
            text_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            wrap=tk.WORD,
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # Analyze world area
        if not hasattr(slot, "world_area") or slot.world_area is None:
            text_widget.insert(tk.END, "No world_area data found in slot!\n")
        else:
            world_area = slot.world_area
            text_widget.insert(tk.END, "World Area Data Structure:\n")
            text_widget.insert(tk.END, "=" * 60 + "\n\n")

            text_widget.insert(tk.END, f"Size: {world_area.size} bytes\n\n")

            if hasattr(world_area, "data") and world_area.data:
                chr_data = world_area.data
                text_widget.insert(tk.END, "WorldAreaChrData:\n")
                text_widget.insert(tk.END, f"  Magic: {chr_data.magic.hex()}\n")
                text_widget.insert(
                    tk.END, f"  unk_0x21042700: {chr_data.unk_0x21042700}\n"
                )
                text_widget.insert(tk.END, f"  unk0x8: {chr_data.unk0x8}\n")
                text_widget.insert(tk.END, f"  unk0xc: {chr_data.unk0xc}\n\n")

                if hasattr(chr_data, "blocks") and chr_data.blocks:
                    text_widget.insert(
                        tk.END, f"Character/Entity Blocks: {len(chr_data.blocks)}\n"
                    )
                    text_widget.insert(tk.END, "=" * 60 + "\n\n")

                    for idx, block in enumerate(chr_data.blocks):
                        if block.size < 1:
                            text_widget.insert(
                                tk.END, f"Block {idx}: TERMINATOR (size={block.size})\n"
                            )
                            break

                        text_widget.insert(tk.END, f"Block {idx}:\n")
                        text_widget.insert(tk.END, f"  Magic: {block.magic.hex()}\n")
                        text_widget.insert(tk.END, f"  Map ID: {block.map_id}\n")
                        text_widget.insert(tk.END, f"  Size: {block.size} bytes\n")
                        text_widget.insert(tk.END, f"  unk0xc: {block.unk0xc}\n")
                        text_widget.insert(
                            tk.END, f"  Data length: {len(block.data)} bytes\n"
                        )

                        # Show first 64 bytes of data as hex
                        if block.data:
                            preview = block.data[:64].hex()
                            text_widget.insert(
                                tk.END, f"  Data preview: {preview}...\n"
                            )

                        text_widget.insert(tk.END, "\n")
                else:
                    text_widget.insert(tk.END, "No blocks found\n")
            else:
                text_widget.insert(tk.END, "No WorldAreaChrData found\n")

            text_widget.insert(tk.END, "\n" + "=" * 60 + "\n")
            text_widget.insert(tk.END, "NOTES:\n")
            text_widget.insert(
                tk.END, "These blocks likely contain entity/character state data.\n"
            )
            text_widget.insert(tk.END, "Boss entities may be stored here.\n")
            text_widget.insert(tk.END, "Each block corresponds to a map area.\n")
            text_widget.insert(
                tk.END, "Data format is unknown - needs reverse engineering.\n"
            )

        text_widget.config(state="disabled")

        ttk.Button(
            dialog,
            text="Export Raw Data",
            command=lambda: self.export_world_area(slot),
            width=20,
        ).pack(side=tk.LEFT, padx=20, pady=10)
        ttk.Button(dialog, text="Close", command=dialog.destroy, width=15).pack(
            side=tk.RIGHT, padx=20, pady=10
        )

    def export_world_area(self, slot):
        """Export world area data to file for analysis"""
        try:
            if not hasattr(slot, "world_area") or slot.world_area is None:
                messagebox.showwarning("No Data", "No world area data to export")
                return

            from io import BytesIO

            buffer = BytesIO()
            slot.world_area.write(buffer)
            raw_data = buffer.getvalue()

            output_path = Path(
                "/mnt/user-data/outputs/world_area_slot_"
                + str(self.current_slot + 1)
                + ".bin"
            )
            output_path.write_bytes(raw_data)

            messagebox.showinfo(
                "Exported",
                f"World area data exported to:\n{output_path}\n\nSize: {len(raw_data)} bytes",
            )
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export:\n{str(e)}")
