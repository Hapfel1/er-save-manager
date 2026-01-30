"""
Event Flags Tab (customtkinter version)
Comprehensive event flag viewer and editor with 948 documented flags
"""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.boss_data import (
    BOSS_CATEGORIES,
    get_boss_flags,
    get_bosses_by_category,
)
from er_save_manager.data.event_flags_db import (
    CATEGORIES,
    get_category_flags,
    get_flag_name,
    get_subcategories,
)
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class EventFlagsTab:
    """Tab for event flag viewing and management (customtkinter version)"""

    class _EventFlagAccessor:
        """Adapter that wraps slot.event_flags bytes with get/set helpers."""

        def __init__(self, slot):
            self.slot = slot
            # Keep a mutable buffer for repeated writes
            self.buffer = (
                bytearray(slot.event_flags)
                if not isinstance(slot.event_flags, bytearray)
                else slot.event_flags
            )

        def get_flag(self, flag_id: int) -> bool:
            return EventFlags.get_flag(bytes(self.buffer), flag_id)

        def set_flag(self, flag_id: int, state: bool) -> None:
            EventFlags.set_flag(self.buffer, flag_id, state)
            # Persist back onto the slot so saves use updated bytes
            self.slot.event_flags = bytes(self.buffer)

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
        # Main scrollable container
        main_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(main_frame)

        # Header
        ctk.CTkLabel(
            main_frame,
            text="Event Flags",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(15, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            main_frame,
            text="View and edit event flags and respawn bosses",
            font=("Segoe UI", 11),
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 12), padx=15, anchor="w")

        # Slot selector
        slot_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        slot_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        ctk.CTkLabel(slot_frame, text="Character Slot:", font=("Segoe UI", 11)).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        self.eventflag_slot_var = tk.IntVar(value=1)
        slot_combo = ctk.CTkComboBox(
            slot_frame,
            variable=self.eventflag_slot_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=80,
        )
        slot_combo.pack(side=tk.LEFT, padx=(0, 12))

        ctk.CTkButton(
            slot_frame,
            text="Load Flags",
            command=self.load_event_flags,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 12))

        ctk.CTkButton(
            slot_frame,
            text="Advanced...",
            command=self.open_advanced_editor,
            width=110,
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            slot_frame,
            text="Apply Changes",
            command=self.apply_changes,
            width=130,
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            slot_frame,
            text="Unlock All in Category",
            command=self.unlock_all_in_category,
            width=160,
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            slot_frame,
            text="Boss Respawn...",
            command=self.open_boss_respawn,
            width=140,
        ).pack(side=tk.LEFT, padx=2)

        # Category selector
        filter_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        filter_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            filter_frame,
            text="Browse by Category",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(10, 8), padx=12, anchor="w")

        cat_inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        cat_inner.pack(fill=tk.X, padx=12, pady=(0, 12))

        ctk.CTkLabel(cat_inner, text="Category:").pack(side=tk.LEFT, padx=(0, 8))
        self.category_var = tk.StringVar(value="")
        cat_combo = ctk.CTkComboBox(
            cat_inner,
            variable=self.category_var,
            values=[""] + CATEGORIES,
            state="readonly",
            width=260,
            command=self.on_category_changed,
        )
        cat_combo.pack(side=tk.LEFT, padx=(0, 20))

        ctk.CTkLabel(cat_inner, text="Subcategory:").pack(side=tk.LEFT, padx=(0, 8))
        self.subcategory_var = tk.StringVar(value="")
        self.subcat_combo = ctk.CTkComboBox(
            cat_inner,
            variable=self.subcategory_var,
            state="readonly",
            width=260,
            command=self.on_subcategory_changed,
        )
        self.subcat_combo.pack(side=tk.LEFT)

        # Search bar
        search_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        search_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            search_frame,
            text="Search Flags",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(10, 8), padx=12, anchor="w")

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(fill=tk.X, padx=12, pady=(0, 12))

        ctk.CTkLabel(search_inner, text="Search:").pack(side=tk.LEFT, padx=(0, 8))
        self.search_var = tk.StringVar(value="")
        self.search_var.trace_add("write", self.on_search_changed)
        search_entry = ctk.CTkEntry(
            search_inner, textvariable=self.search_var, width=320
        )
        search_entry.pack(side=tk.LEFT, padx=(0, 12))

        ctk.CTkLabel(
            search_inner,
            text="(Search by flag ID or name)",
            text_color=("gray50", "gray70"),
        ).pack(side=tk.LEFT, padx=(0, 12))

        ctk.CTkButton(
            search_inner, text="Clear", command=self.clear_search, width=90
        ).pack(side=tk.LEFT)

        # Flags viewer
        flags_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        flags_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        ctk.CTkLabel(
            flags_frame,
            text="Event Flags",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(10, 8), padx=12, anchor="w")

        # Scrollable flags list
        self.flags_inner_frame = ctk.CTkScrollableFrame(
            flags_frame, corner_radius=8, fg_color=("#f5f5f5", "#2a2a3e")
        )
        self.flags_inner_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        bind_mousewheel(self.flags_inner_frame)

        # Action buttons area
        action_frame = ctk.CTkFrame(flags_frame, fg_color="transparent")
        action_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            action_frame,
            text="Select a category or search for flags",
            text_color=("gray50", "gray70"),
        )
        self.status_label.pack(side=tk.LEFT)

    def load_event_flags(self):
        """Load event flags for selected character"""
        save_file = self.get_save_file()
        if not save_file:
            CTkMessageBox.showwarning("No Save", "Please load a save file first!")
            return

        slot_idx = int(self.eventflag_slot_var.get()) - 1
        slot = save_file.characters[slot_idx]

        if slot.is_empty():
            CTkMessageBox.showwarning("Empty Slot", f"Slot {slot_idx + 1} is empty!")
            return

        self.current_slot = slot_idx

        if not hasattr(slot, "event_flags") or not slot.event_flags:
            CTkMessageBox.showerror("Error", "Event flags not available")
            return

        self.current_event_flags = self._EventFlagAccessor(slot)
        self.flag_states.clear()
        self.flag_widgets.clear()
        for widget in self.flags_inner_frame.winfo_children():
            widget.destroy()

        self.status_label.configure(
            text=f"Loaded Slot {slot_idx + 1}. Select category or search."
        )

        CTkMessageBox.showinfo(
            "Loaded",
            f"Loaded event flags for Slot {slot_idx + 1}.\n\n"
            f"Use Category dropdown or Search to view flags.",
        )

    def on_category_changed(self, choice=None):
        """Handle category selection"""
        if self.current_event_flags is None:
            CTkMessageBox.showwarning(
                "Not Loaded", "Please load event flags for a character first!"
            )
            return

        category = self.category_var.get()
        if not category:
            return

        # Update subcategories
        subcats = get_subcategories(category)
        if subcats:
            self.subcat_combo.configure(values=subcats, state="readonly")
            self.subcategory_var.set(subcats[0])
            self.on_subcategory_changed()
        else:
            self.subcat_combo.configure(values=[], state="disabled")
            self.subcategory_var.set("")
            # Show all flags in category
            self.display_flags(category, None)

    def on_subcategory_changed(self, choice=None):
        """Handle subcategory selection"""
        if self.current_event_flags is None:
            return

        category = self.category_var.get()
        subcategory = self.subcategory_var.get()

        if category and subcategory:
            self.display_flags(category, subcategory)

    def display_flags(self, category, subcategory):
        """Display flags for category/subcategory"""
        # Clear current flags
        for widget in self.flags_inner_frame.winfo_children():
            widget.destroy()
        self.flag_widgets.clear()

        flags = get_category_flags(category, subcategory)
        count = 0

        for flag_id in flags:
            flag_name = get_flag_name(flag_id)
            is_set = self.current_event_flags.get_flag(flag_id)

            # Store initial state
            if flag_id not in self.flag_states:
                self.flag_states[flag_id] = is_set

            # Create checkbox
            var = tk.BooleanVar(value=is_set)

            flag_frame = ctk.CTkFrame(
                self.flags_inner_frame,
                corner_radius=6,
                fg_color=("#ffffff", "#1f1f28"),
            )
            flag_frame.pack(fill=tk.X, pady=2, padx=4)

            checkbox = ctk.CTkCheckBox(
                flag_frame,
                text=f"{flag_id}: {flag_name}",
                variable=var,
                command=lambda fid=flag_id, v=var: self.on_flag_toggled(fid, v),
            )
            checkbox.pack(side=tk.LEFT, padx=8, pady=6)

            self.flag_widgets[flag_id] = (checkbox, var)
            count += 1

        if subcategory:
            self.status_label.configure(
                text=f"Showing {count} flags in {category} > {subcategory}"
            )
        else:
            self.status_label.configure(text=f"Showing {count} flags in {category}")

    def on_flag_toggled(self, flag_id, var):
        """Handle flag checkbox toggle"""
        self.flag_states[flag_id] = var.get()

    def on_search_changed(self, *args):
        """Handle search text change"""
        if self.current_event_flags is None:
            return

        query = self.search_var.get().strip().lower()
        if not query:
            return

        # Clear current display
        for widget in self.flags_inner_frame.winfo_children():
            widget.destroy()
        self.flag_widgets.clear()

        # Search through all categories
        results = []
        for category in CATEGORIES:
            subcats = get_subcategories(category)
            if subcats:
                for subcat in subcats:
                    flags = get_category_flags(category, subcat)
                    for flag_id in flags:
                        flag_name = get_flag_name(flag_id)
                        if query in str(flag_id).lower() or query in flag_name.lower():
                            results.append((flag_id, flag_name, category, subcat))
            else:
                flags = get_category_flags(category, None)
                for flag_id in flags:
                    flag_name = get_flag_name(flag_id)
                    if query in str(flag_id).lower() or query in flag_name.lower():
                        results.append((flag_id, flag_name, category, None))

        # Display results
        for flag_id, flag_name, category, subcategory in results:
            is_set = self.current_event_flags.get_flag(flag_id)

            if flag_id not in self.flag_states:
                self.flag_states[flag_id] = is_set

            var = tk.BooleanVar(value=is_set)

            flag_frame = ctk.CTkFrame(
                self.flags_inner_frame,
                corner_radius=6,
                fg_color=("#ffffff", "#1f1f28"),
            )
            flag_frame.pack(fill=tk.X, pady=2, padx=4)

            location = f"{category} > {subcategory}" if subcategory else category

            checkbox = ctk.CTkCheckBox(
                flag_frame,
                text=f"{flag_id}: {flag_name} ({location})",
                variable=var,
                command=lambda fid=flag_id, v=var: self.on_flag_toggled(fid, v),
            )
            checkbox.pack(side=tk.LEFT, padx=8, pady=6)

            self.flag_widgets[flag_id] = (checkbox, var)

        self.status_label.configure(text=f"Found {len(results)} matching flags")

    def clear_search(self):
        """Clear search field"""
        self.search_var.set("")
        for widget in self.flags_inner_frame.winfo_children():
            widget.destroy()
        self.flag_widgets.clear()
        self.status_label.configure(text="Select a category or search for flags")

    def unlock_all_in_category(self):
        """Unlock all flags in current category"""
        if not self.flag_widgets:
            CTkMessageBox.showwarning("No Flags", "No flags are currently displayed!")
            return

        result = CTkMessageBox.askyesno(
            "Confirm",
            f"Set all {len(self.flag_widgets)} displayed flags to ON?\n\n"
            f"This will affect only the flags currently visible.",
        )

        if result:
            for flag_id, (checkbox, var) in self.flag_widgets.items():
                var.set(True)
                self.flag_states[flag_id] = True
                checkbox.select()

            CTkMessageBox.showinfo(
                "Success",
                f"Enabled all {len(self.flag_widgets)} displayed flags.\n\nClick 'Apply Changes' to save.",
            )

    def apply_changes(self):
        """Apply flag changes to save file"""
        if self.current_event_flags is None:
            CTkMessageBox.showwarning("Not Loaded", "No event flags loaded!")
            return

        if not self.flag_states:
            CTkMessageBox.showwarning("No Changes", "No flags have been modified!")
            return

        # Count changes
        changes = 0
        for flag_id, new_state in self.flag_states.items():
            current_state = self.current_event_flags.get_flag(flag_id)
            if current_state != new_state:
                changes += 1

        if changes == 0:
            CTkMessageBox.showinfo("No Changes", "No flags were modified!")
            return

        result = CTkMessageBox.askyesno(
            "Confirm Changes",
            f"Apply {changes} flag changes to Slot {self.current_slot + 1}?\n\n"
            f"A backup will be created automatically.",
        )

        if not result:
            return

        # Create backup
        save_path = self.get_save_path()
        if save_path:
            backup_mgr = BackupManager(save_path.parent)
            backup_mgr.create_backup(
                save_path.name,
                f"Before event flag changes (Slot {self.current_slot + 1})",
            )

        # Apply changes
        for flag_id, new_state in self.flag_states.items():
            self.current_event_flags.set_flag(flag_id, new_state)

        # Save
        save_file = self.get_save_file()
        save_file.save(self.get_save_path())
        self.reload_save()

        CTkMessageBox.showinfo(
            "Success",
            f"Applied {changes} flag changes to Slot {self.current_slot + 1}!\n\n"
            f"Backup created and save file reloaded.",
        )

        # Clear states
        self.flag_states.clear()

    def open_advanced_editor(self):
        """Open advanced flag editor dialog"""
        if self.current_event_flags is None:
            CTkMessageBox.showwarning(
                "Not Loaded", "Please load event flags for a character first!"
            )
            return

        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Advanced Event Flag Editor")
        dialog.geometry("600x500")
        dialog.transient(self.parent)

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (500 // 2)
        dialog.geometry(f"+{x}+{y}")

        # Force rendering on Linux before grab_set
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Advanced Event Flag Editor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(15, 10), padx=15)

        # Input frame
        input_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        input_frame.pack(fill=tk.X, padx=15, pady=10)

        ctk.CTkLabel(input_frame, text="Flag ID:").pack(side=tk.LEFT, padx=(0, 8))

        flag_id_var = tk.StringVar(value="")
        flag_entry = ctk.CTkEntry(input_frame, textvariable=flag_id_var, width=150)
        flag_entry.pack(side=tk.LEFT, padx=(0, 12))

        def toggle_flag():
            try:
                flag_id = int(flag_id_var.get())
                current = self.current_event_flags.get_flag(flag_id)
                new_state = not current
                self.current_event_flags.set_flag(flag_id, new_state)

                # Save
                save_file = self.get_save_file()
                save_file.save(self.get_save_path())
                self.reload_save()

                CTkMessageBox.showinfo(
                    "Success",
                    f"Flag {flag_id} set to {'ON' if new_state else 'OFF'}",
                )
            except ValueError:
                CTkMessageBox.showerror("Error", "Invalid flag ID!")
            except Exception as e:
                CTkMessageBox.showerror("Error", f"Failed to toggle flag: {e}")

        def check_flag():
            try:
                flag_id = int(flag_id_var.get())
                state = self.current_event_flags.get_flag(flag_id)
                flag_name = get_flag_name(flag_id)
                CTkMessageBox.showinfo(
                    "Flag Status",
                    f"Flag {flag_id}: {flag_name}\n\nState: {'ON' if state else 'OFF'}",
                )
            except ValueError:
                CTkMessageBox.showerror("Error", "Invalid flag ID!")
            except Exception as e:
                CTkMessageBox.showerror("Error", f"Failed to check flag: {e}")

        ctk.CTkButton(input_frame, text="Toggle", command=toggle_flag, width=100).pack(
            side=tk.LEFT, padx=2
        )

        ctk.CTkButton(input_frame, text="Check", command=check_flag, width=100).pack(
            side=tk.LEFT, padx=2
        )

        # Help text
        help_frame = ctk.CTkFrame(dialog, corner_radius=10)
        help_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        help_text = tk.Text(
            help_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=12,
            pady=12,
            bg="#1f1f28",
            fg="#e5e5f5",
            relief=tk.FLAT,
            highlightthickness=0,
        )
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        help_text.insert(
            "1.0",
            "Advanced Flag Editor\n\n"
            "Use this to directly toggle or check individual flags by ID.\n\n"
            "How to use:\n"
            "1. Enter a flag ID (e.g., 1035, 10000800)\n"
            "2. Click 'Check' to see current state\n"
            "3. Click 'Toggle' to flip the flag on/off\n\n"
            "Warning:\n"
            "- Changing unknown flags may break your save\n"
            "- Always backup before experimenting\n"
            "- Use the category browser for documented flags\n\n"
            "Tip: You can find flag IDs in the event_flags_db.py file in the source code.",
        )
        help_text.configure(state="disabled")

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy, width=120).pack(
            pady=(0, 15)
        )

    def open_boss_respawn(self):
        """Open boss respawn dialog"""
        if self.current_event_flags is None:
            CTkMessageBox.showwarning(
                "Not Loaded", "Please load event flags for a character first!"
            )
            return

        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Boss Respawn")
        width, height = 700, 600
        dialog.transient(self.parent)
        dialog.update_idletasks()
        # Center over parent window
        self.parent.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        # Force rendering on Linux before grab_set
        force_render_dialog(dialog)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Boss Respawn",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(15, 5), padx=15)

        ctk.CTkLabel(
            dialog,
            text="Reset boss defeat flags to respawn bosses",
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 12), padx=15)

        # Category selector
        cat_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        cat_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        ctk.CTkLabel(cat_frame, text="Boss Category:").pack(side=tk.LEFT, padx=(0, 8))

        boss_category_var = tk.StringVar(value=BOSS_CATEGORIES[0])
        cat_combo = ctk.CTkComboBox(
            cat_frame,
            variable=boss_category_var,
            values=BOSS_CATEGORIES,
            state="readonly",
            width=300,
        )
        cat_combo.pack(side=tk.LEFT)

        # Boss list
        boss_frame = ctk.CTkScrollableFrame(dialog, corner_radius=10)
        boss_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        bind_mousewheel(boss_frame)

        boss_vars = {}

        def populate_bosses(*_args):
            # Clear current bosses
            for widget in boss_frame.winfo_children():
                widget.destroy()
            boss_vars.clear()

            category = boss_category_var.get()
            bosses_in_cat = get_bosses_by_category(category)

            for boss_name in bosses_in_cat:
                flags = get_boss_flags(boss_name)
                if not flags:
                    continue

                is_defeated = any(
                    self.current_event_flags.get_flag(fid) for fid in flags
                )
                var = tk.BooleanVar(value=False)
                boss_vars[boss_name] = (flags, var)

                item_frame = ctk.CTkFrame(
                    boss_frame,
                    corner_radius=6,
                    fg_color=("#ffffff", "#1f1f28"),
                )
                item_frame.pack(fill=tk.X, pady=3, padx=4)

                status = "Defeated" if is_defeated else "Alive"
                checkbox = ctk.CTkCheckBox(
                    item_frame,
                    text=f"{boss_name} ({status})",
                    variable=var,
                )
                checkbox.pack(side=tk.LEFT, padx=8, pady=6)

        cat_combo.configure(command=populate_bosses)
        populate_bosses()

        # Action buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        def respawn_selected():
            """Respawn selected bosses"""
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path",
                    "Could not locate the save file to back up. Load a valid save (.sl2) first.",
                )
                return

            count = 0
            for _boss_name, (flags, var) in boss_vars.items():
                if var.get():  # user explicitly selected this boss
                    is_defeated_now = any(
                        self.current_event_flags.get_flag(fid) for fid in flags
                    )
                    if is_defeated_now:
                        for flag_id in flags:
                            self.current_event_flags.set_flag(flag_id, False)
                        count += 1

            if count == 0:
                CTkMessageBox.showinfo(
                    "No Selection",
                    "No valid selections. Select defeated bosses to respawn.",
                )
                return

            if save_path and save_path.is_file():
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        save_path.name,
                        f"Before boss respawn (Slot {self.current_slot + 1})",
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied)."
                        " Continuing without backup.",
                    )
            else:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup because the save path is not a file."
                    " Proceeding without backup.",
                )

            # Save
            save_file = self.get_save_file()
            save_file.save(self.get_save_path())
            self.reload_save()

            # Teleport to Roundtable Hold
            try:
                from er_save_manager.fixes.teleport import TeleportFix

                teleport = TeleportFix("roundtable")
                result = teleport.apply(save_file, self.current_slot)
                if result.applied:
                    save_file.save(self.get_save_path())
                    self.reload_save()
            except Exception as e:
                CTkMessageBox.showwarning(
                    "Teleport Failed",
                    f"Could not teleport to Roundtable Hold: {e}",
                )

            CTkMessageBox.showinfo(
                "Success", f"Respawned {count} boss(es)!\n\nSave file updated."
            )
            dialog.destroy()

        def respawn_all():
            """Respawn all bosses in category"""
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path",
                    "Could not locate the save file to back up. Load a valid save (.sl2) first.",
                )
                return

            result = CTkMessageBox.askyesno(
                "Confirm",
                f"Respawn ALL bosses in {boss_category_var.get()}?\n\n"
                f"This will reset {len(boss_vars)} boss(es).",
            )

            if not result:
                return

            count = 0
            for _boss_name, (flags, _var) in boss_vars.items():
                for flag_id in flags:
                    self.current_event_flags.set_flag(flag_id, False)
                count += 1

            # Create backup
            save_path = self.get_save_path()
            if save_path and save_path.is_file():
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        save_path.name,
                        f"Before respawn all ({boss_category_var.get()}, Slot {self.current_slot + 1})",
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied)."
                        " Continuing without backup.",
                    )
            else:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup because the save path is not a file."
                    " Proceeding without backup.",
                )

            # Save
            save_file = self.get_save_file()
            save_file.save(self.get_save_path())
            self.reload_save()

            # Teleport to Roundtable Hold
            try:
                from er_save_manager.fixes.teleport import TeleportFix

                teleport = TeleportFix("roundtable")
                result = teleport.apply(save_file, self.current_slot)
                if result.applied:
                    save_file.save(self.get_save_path())
                    self.reload_save()
            except Exception as e:
                CTkMessageBox.showwarning(
                    "Teleport Failed",
                    f"Could not teleport to Roundtable Hold: {e}",
                )

            CTkMessageBox.showinfo(
                "Success",
                f"Respawned all {count} bosses in {boss_category_var.get()}!\n\n"
                f"Save file updated.",
            )
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy, width=120).pack(
            side=tk.LEFT
        )

        ctk.CTkButton(
            btn_frame, text="Respawn Selected", command=respawn_selected, width=150
        ).pack(side=tk.RIGHT, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Respawn All in Category", command=respawn_all, width=180
        ).pack(side=tk.RIGHT)
