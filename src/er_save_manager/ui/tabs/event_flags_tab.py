"""
Event Flags Tab
Comprehensive event flag viewer and editor with 948 documented flags
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from er_save_manager.backup.manager import BackupManager
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
        except Exception:
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
                except Exception:
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
            except Exception:
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
            except Exception:
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
