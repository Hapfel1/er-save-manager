"""
Save Inspector Tab (customtkinter version)
Displays character list with quick fix functionality
"""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


class SaveInspectorTab:
    """Tab for viewing save file contents and quick fixes"""

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_details_callback,
        on_slot_selected_callback=None,
    ):
        """
        Initialize save inspector tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
            show_details_callback: Function to show character details dialog (slot_idx)
            on_slot_selected_callback: Function called when slot is selected (slot_idx)
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback
        self.show_details = show_details_callback
        self.on_slot_selected = on_slot_selected_callback

        self.selected_slot = None
        self.rows = []
        self.selection_var = tk.StringVar(value="")

    def setup_ui(self):
        """Setup the save fixer tab UI"""
        # Character selection frame
        char_frame = ctk.CTkFrame(self.parent, corner_radius=12)
        char_frame.pack(fill="both", expand=True, pady=(0, 10))

        header = ctk.CTkFrame(char_frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="Save Fixer",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="View All Issues",
            command=self.show_character_details,
            width=180,
        ).pack(side="right")

        # Instructions
        instructions_frame = ctk.CTkFrame(char_frame, fg_color="transparent")
        instructions_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            instructions_frame,
            text="Select a character and click 'View All Issues' to scan for problems and apply fixes",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(side="left", anchor="w")

        self.list_frame = ctk.CTkScrollableFrame(
            char_frame, width=900, height=320, corner_radius=10
        )
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bind_mousewheel(self.list_frame)

    def populate_character_list(self):
        """Populate character listbox"""
        # Clear existing rows
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.rows.clear()
        self.selected_slot = None

        save_file = self.get_save_file()
        if not save_file:
            return

        try:
            active_slots = save_file.get_active_slots()

            if not active_slots:
                ctk.CTkLabel(self.list_frame, text="No active characters found").pack(
                    anchor="w", padx=6, pady=6
                )
                return

            # Get profiles safely
            profiles = None
            try:
                if save_file.user_data_10_parsed:
                    profiles = save_file.user_data_10_parsed.profile_summary.profiles
            except Exception as e:
                print(f"Warning: Could not load profiles: {e}")

            def select_slot(slot_index: int):
                self.selected_slot = slot_index
                self.selection_var.set(str(slot_index))
                for val, frame, label in self.rows:
                    if val == slot_index:
                        frame.configure(fg_color=("#c9a0dc", "#3b2f5c"))
                        label.configure(text_color=("#1f1f28", "#f0f0f0"))
                    else:
                        frame.configure(fg_color=("#f5f5f5", "#2a2a3e"))
                        label.configure(text_color=("#333333", "#cccccc"))

                # Notify GUI of slot selection
                if self.on_slot_selected:
                    self.on_slot_selected(slot_index)

            for slot_idx in active_slots:
                try:
                    slot = save_file.characters[slot_idx]
                    if not slot:
                        continue

                    # Get character info safely
                    name = "Unknown"
                    level = "?"

                    if profiles and slot_idx < len(profiles):
                        try:
                            profile = profiles[slot_idx]
                            name = profile.character_name or "Unknown"
                            level = str(profile.level) if profile.level else "?"
                        except Exception:
                            pass

                    # Get map location safely
                    map_str = "Unknown"
                    try:
                        if hasattr(slot, "map_id") and slot.map_id:
                            map_str = slot.map_id.to_string_decimal()
                    except Exception:
                        pass

                    display_text = f"Slot {slot_idx + 1:2d} | {name:16s} | Lv.{level:>3s} | Map: {map_str}"

                    row = ctk.CTkFrame(
                        self.list_frame,
                        fg_color=("#f5f5f5", "#2a2a3e"),
                        corner_radius=6,
                    )
                    row.pack(fill="x", padx=4, pady=4)

                    label = ctk.CTkLabel(
                        row,
                        text=display_text,
                        anchor="w",
                        padx=8,
                        pady=8,
                        font=("Courier", 13),  # Large font for readability
                    )
                    label.pack(fill="x")

                    row.bind("<Button-1>", lambda e, v=slot_idx: select_slot(v))
                    label.bind("<Button-1>", lambda e, v=slot_idx: select_slot(v))

                    self.rows.append((slot_idx, row, label))

                except Exception as e:
                    error_row = ctk.CTkLabel(
                        self.list_frame,
                        text=f"Slot {slot_idx + 1:2d} | Error loading data",
                        anchor="w",
                    )
                    error_row.pack(fill="x", padx=4, pady=4)
                    print(f"Error loading slot {slot_idx}: {e}")

            # Select first item by default
            if self.rows:
                select_slot(self.rows[0][0])

        except Exception as e:
            ctk.CTkLabel(self.list_frame, text="Error loading characters").pack(
                anchor="w", padx=6, pady=6
            )
            CTkMessageBox.showerror(
                "Error", f"Failed to load character list:\n{str(e)}"
            )
            import traceback

            traceback.print_exc()

    def on_character_select(self, event):
        """Handle character selection"""
        # Not used in CTk list version
        return

    def on_character_double_click(self, event):
        """Handle double-click to show details"""
        self.show_character_details()

    def show_character_details(self):
        """Show character details dialog"""
        if self.selected_slot is None:
            CTkMessageBox.showwarning(
                "No Selection", "Please select a character first!"
            )
            return

        if self.show_details:
            self.show_details(self.selected_slot)
