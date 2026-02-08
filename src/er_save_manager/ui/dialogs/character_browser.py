"""CustomTkinter character browser dialog.

Browse and contribute community character builds with 10-slot support.
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from er_save_manager.character_manager import CharacterManager
from er_save_manager.character_metrics import CharacterMetrics
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.progress_dialog import ProgressDialog
from er_save_manager.ui.utils import bind_mousewheel, trace_variable

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class CharacterBrowser:
    """Character browser with Browse and Contribute tabs."""

    NUM_SLOTS = 10

    def __init__(self, parent, character_tab=None, save_file=None):
        self.parent = parent
        self.character_tab = character_tab
        self.save_file = save_file
        self.manager = CharacterManager()
        self.current_character: dict[str, Any] | None = None
        self.all_characters: list[dict[str, Any]] = []
        self.filtered_characters: list[dict[str, Any]] = []
        self.character_widgets: list[ctk.CTkFrame] = []

        # Metrics integration
        from pathlib import Path

        settings_path = Path.home() / ".er-save-manager" / "data" / "settings.json"
        self.metrics = CharacterMetrics(settings_path)
        self.character_metrics_cache: dict[str, dict] = {}  # character_id -> metrics

        # Contribution data
        self.face_image_path: str | None = None
        self.body_image_path: str | None = None
        self.preview_image_path: str | None = None

    def show(self):
        """Show character browser with tabs."""
        from er_save_manager.ui.utils import force_render_dialog

        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Community Character Library")
        self.dialog.geometry("1400x1000")
        self.dialog.transient(self.parent)

        # Force rendering before grab_set to avoid "window not viewable" errors
        force_render_dialog(self.dialog)
        self.dialog.grab_set()

        def on_close():
            self.dialog.grab_release()
            self.dialog.destroy()

        self.dialog.protocol("WM_DELETE_WINDOW", on_close)

        self.tabview = ctk.CTkTabview(self.dialog, width=1150, height=820)
        self.tabview.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        self.browse_tab = self.tabview.add("Browse Characters")
        self.contribute_tab = self.tabview.add("Contribute Character")

        self.setup_browse_tab()
        self.setup_contribute_tab()

        # Force update and rendering on Linux
        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()

        # Load characters asynchronously after dialog is displayed
        self.dialog.after(50, self.refresh_characters)

    # ---------------------- Browse tab ----------------------
    def setup_browse_tab(self):
        main_frame = ctk.CTkFrame(self.browse_tab)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill=ctk.X, pady=(6, 10))

        ctk.CTkLabel(
            top_frame,
            text="Browse Community Characters",
            font=("Segoe UI", 18, "bold"),
        ).pack(side=ctk.LEFT)

        ctk.CTkButton(
            top_frame, text="Refresh", command=self.refresh_characters, width=90
        ).pack(side=ctk.RIGHT)

        filter_frame = ctk.CTkFrame(main_frame)
        filter_frame.pack(fill=ctk.X, pady=(0, 14))

        ctk.CTkLabel(filter_frame, text="Search:").pack(side=ctk.LEFT, padx=(0, 8))
        self.search_var = ctk.StringVar(value="")
        trace_variable(self.search_var, "w", lambda *args: self.apply_filters())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var, width=240).pack(
            side=ctk.LEFT
        )

        ctk.CTkLabel(filter_frame, text="Filter:").pack(side=ctk.LEFT, padx=(18, 8))
        self.filter_var = ctk.StringVar(value="All")
        filter_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.filter_var,
            values=[
                "All",
                "Overhaul Mod",
                "No Overhaul",
            ],
            width=150,
            state="readonly",
            command=lambda _value=None: self.apply_filters(),
        )
        filter_combo.pack(side=ctk.LEFT)
        filter_combo.bind("<<ComboboxSelected>>", lambda _e=None: self.apply_filters())

        ctk.CTkLabel(filter_frame, text="Sort:").pack(side=ctk.LEFT, padx=(18, 8))
        self.sort_var = ctk.StringVar(value="Recent")
        sort_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.sort_var,
            values=["Recent", "Likes", "Downloads", "Name", "Level"],
            width=150,
            state="readonly",
            command=lambda _value=None: self.apply_filters(),
        )
        sort_combo.pack(side=ctk.LEFT)
        sort_combo.bind("<<ComboboxSelected>>", lambda _e=None: self.apply_filters())

        content = ctk.CTkFrame(main_frame)
        content.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))
        # Fixed widths to prevent shifting when preview loads
        content.columnconfigure(0, weight=1, minsize=620)
        content.columnconfigure(1, weight=0, minsize=650)
        content.rowconfigure(0, weight=1)

        self.grid_container = ctk.CTkScrollableFrame(
            content,
            fg_color=("gray95", "gray20"),
            corner_radius=8,
            border_width=1,
            width=620,
        )
        self.grid_container.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        bind_mousewheel(self.grid_container)

        preview_panel = ctk.CTkFrame(content, width=650)
        preview_panel.grid(row=0, column=1, sticky="nsew")
        preview_panel.grid_propagate(False)  # Prevent resizing based on content

        # Create scrollable container for preview content
        preview_scroll = ctk.CTkScrollableFrame(preview_panel, fg_color="transparent")
        preview_scroll.pack(fill=ctk.BOTH, expand=True)
        bind_mousewheel(preview_scroll)

        ctk.CTkLabel(
            preview_scroll,
            text="Preview",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=ctk.W, padx=10, pady=(10, 2))

        self.preview_area = ctk.CTkFrame(preview_scroll)
        self.preview_area.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(10, 60))

        self.details_frame = ctk.CTkScrollableFrame(
            preview_scroll, fg_color="transparent"
        )
        self.details_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 0))
        bind_mousewheel(self.details_frame)

        slot_frame = ctk.CTkFrame(preview_scroll)
        slot_frame.pack(fill=ctk.X, padx=10, pady=(60, 10))

        ctk.CTkLabel(slot_frame, text="Target Slot:").pack(side=ctk.LEFT, padx=(0, 8))
        self.target_slot_var = ctk.StringVar(value="Slot 1")
        ctk.CTkComboBox(
            slot_frame,
            variable=self.target_slot_var,
            values=[f"Slot {i + 1}" for i in range(self.NUM_SLOTS)],
            width=120,
            state="readonly",
        ).pack(side=ctk.LEFT)

        import_button = ctk.CTkButton(
            slot_frame,
            text="Download & Import",
            command=self.import_to_slot,
            width=180,
        )
        import_button.pack(side=ctk.LEFT, padx=10)

    # ---------------------- Contribute tab ----------------------
    def setup_contribute_tab(self):
        # Create main scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(
            self.contribute_tab, fg_color="transparent"
        )
        scroll_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)
        bind_mousewheel(scroll_frame)

        title_label = ctk.CTkLabel(
            scroll_frame,
            text="Contribute Your Character",
            font=("Segoe UI", 18, "bold"),
        )
        title_label.pack(pady=(10, 5))

        desc_label = ctk.CTkLabel(
            scroll_frame,
            text="Share your character build with the community! Provide screenshots and details.",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        )
        desc_label.pack(pady=(0, 10))

        # GitHub Account Required notice
        notice = ctk.CTkFrame(
            scroll_frame, fg_color=("#fff7ed", "#3b2f1b"), corner_radius=8
        )
        notice.pack(fill=ctk.X, pady=(0, 20), padx=20)
        ctk.CTkLabel(
            notice,
            text="⚠ GitHub Account Required",
            font=("Segoe UI", 14, "bold"),
            text_color=("#b45309", "#fbbf24"),
        ).pack(pady=(12, 4))
        ctk.CTkLabel(
            notice,
            text="Log into GitHub in your browser before submitting",
            font=("Segoe UI", 12),
            text_color=("#6b7280", "#d1d5db"),
        ).pack(pady=(0, 12))

        # Form content frame
        form_frame = ctk.CTkFrame(
            scroll_frame,
            fg_color="transparent",
        )
        form_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Character slot selector
        slot_section = ctk.CTkFrame(form_frame, fg_color="transparent")
        slot_section.pack(fill=ctk.X, pady=(0, 15))

        ctk.CTkLabel(
            slot_section,
            text="Character Slot:",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 5))

        self.contrib_slot_var = ctk.StringVar(value="Slot 1")
        ctk.CTkComboBox(
            slot_section,
            variable=self.contrib_slot_var,
            values=[f"Slot {i + 1}" for i in range(self.NUM_SLOTS)],
            width=150,
            state="readonly",
        ).pack(anchor=ctk.W)

        # Character name
        self.char_name_var = ctk.StringVar()
        self._labeled_entry(form_frame, "Character Name:", self.char_name_var)

        # Author
        self.char_author_var = ctk.StringVar()
        self._labeled_entry(form_frame, "Author (your name):", self.char_author_var)

        # Description
        desc_section = ctk.CTkFrame(form_frame, fg_color="transparent")
        desc_section.pack(fill=ctk.X, pady=(0, 15))

        ctk.CTkLabel(
            desc_section,
            text="Description:",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 5))

        self.char_desc_text = ctk.CTkTextbox(
            desc_section,
            height=100,
            font=("Segoe UI", 11),
        )
        self.char_desc_text.pack(fill=ctk.X)

        # Tags
        self.char_tags_var = ctk.StringVar()
        self._labeled_entry(form_frame, "Tags (comma-separated):", self.char_tags_var)

        # Screenshots section
        screenshots_section = ctk.CTkFrame(form_frame, fg_color="transparent")
        screenshots_section.pack(fill=ctk.X, pady=(10, 15))

        ctk.CTkLabel(
            screenshots_section,
            text="Screenshots (Required):",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 8))

        self.face_image_label = self._file_selector(
            screenshots_section,
            "Face Screenshot:",
            self.select_face_image,
        )

        self.body_image_label = self._file_selector(
            screenshots_section,
            "Body Screenshot:",
            self.select_body_image,
        )

        self.preview_image_label = self._file_selector(
            screenshots_section,
            "Preview Screenshot:",
            self.select_preview_image,
            placeholder="Optional",
        )

        # Overhaul mod section
        mod_section = ctk.CTkFrame(form_frame, fg_color="transparent")
        mod_section.pack(fill=ctk.X, pady=(10, 15))

        ctk.CTkLabel(
            mod_section,
            text="Overhaul Mod:",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 8))

        self.overhaul_used_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            mod_section,
            text="Uses an overhaul mod",
            variable=self.overhaul_used_var,
            command=self._toggle_overhaul_details,
        ).pack(anchor=ctk.W, pady=(0, 8))

        self.overhaul_details_frame = ctk.CTkFrame(
            mod_section, fg_color=("gray90", "gray25")
        )

        overhaul_name_frame = ctk.CTkFrame(
            self.overhaul_details_frame, fg_color="transparent"
        )
        overhaul_name_frame.pack(fill=ctk.X, pady=(10, 0), padx=10)
        ctk.CTkLabel(overhaul_name_frame, text="Overhaul:").pack(
            side=ctk.LEFT, padx=(0, 8)
        )
        self.overhaul_name_var = ctk.StringVar(value="Convergence")
        ctk.CTkComboBox(
            overhaul_name_frame,
            variable=self.overhaul_name_var,
            values=[
                "Convergence",
                "Elden Ring Reforged",
                "Other",
            ],
            width=200,
            state="readonly",
        ).pack(side=ctk.LEFT)

        self.overhaul_custom_var = ctk.StringVar()
        self._labeled_entry(
            self.overhaul_details_frame,
            "Custom Mod Name (optional):",
            self.overhaul_custom_var,
        )

        self.overhaul_version_var = ctk.StringVar()
        self._labeled_entry(
            self.overhaul_details_frame,
            "Mod Version:",
            self.overhaul_version_var,
        )

        self._toggle_overhaul_details()

        # Login notice
        login_notice = ctk.CTkFrame(
            form_frame, fg_color=("#eef2ff", "#1f2937"), corner_radius=8
        )
        login_notice.pack(fill=ctk.X, padx=0, pady=(20, 15))
        ctk.CTkLabel(
            login_notice,
            text=(
                "Make sure you're logged into GitHub in your browser before submitting.\n"
                "If the GitHub home page opens, log in first then submit again."
            ),
            justify=ctk.LEFT,
            font=("Segoe UI", 11),
        ).pack(anchor=ctk.W, padx=12, pady=(10, 8))

        link = ctk.CTkLabel(
            login_notice,
            text="https://github.com/login",
            text_color=("#2563eb", "#60a5fa"),
            cursor="hand2",
            font=("Segoe UI", 11),
        )
        link.pack(anchor=ctk.W, padx=12, pady=(0, 10))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/login"))

        # Submit button
        submit_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        submit_frame.pack(fill=ctk.X, padx=0, pady=(0, 10))

        ctk.CTkButton(
            submit_frame,
            text="Submit to GitHub",
            command=self.submit_contribution,
            width=200,
            height=40,
        ).pack(side=ctk.RIGHT)

        # Auto-detect Convergence mod from save file extension (delayed to ensure widgets are ready)
        self.dialog.after(100, self._auto_detect_convergence)

    # ---------------------- Helpers ----------------------
    def _auto_detect_convergence(self):
        """Auto-detect Convergence mod from save file extension."""
        if self.save_file and hasattr(self.save_file, "_original_filepath"):
            filepath = self.save_file._original_filepath.lower()
            if filepath.endswith(".cnv") or filepath.endswith(".cnv.co2"):
                self.overhaul_used_var.set(True)
                self.overhaul_name_var.set("Convergence")
                self._toggle_overhaul_details()

    def _file_selector(
        self, parent, label: str, command, placeholder: str = "No file selected"
    ):
        """Create file selector with label and button."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill=ctk.X, pady=5)

        ctk.CTkLabel(frame, text=label).pack(side=ctk.LEFT, padx=(0, 10))

        file_label = ctk.CTkLabel(
            frame,
            text=placeholder,
            text_color=("gray50", "gray60"),
        )
        file_label.pack(side=ctk.LEFT, fill=ctk.X, expand=True)

        ctk.CTkButton(frame, text="Browse...", command=command, width=100).pack(
            side=ctk.RIGHT
        )

        return file_label

    def _labeled_entry(self, parent, label: str, var: ctk.StringVar):
        """Create labeled entry field."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill=ctk.X, pady=(0, 15))

        ctk.CTkLabel(frame, text=label, font=("Segoe UI", 12, "bold")).pack(
            anchor=ctk.W, pady=(0, 5)
        )
        ctk.CTkEntry(frame, textvariable=var, font=("Segoe UI", 11)).pack(fill=ctk.X)

    def _toggle_overhaul_details(self):
        """Show or hide overhaul details based on checkbox state."""
        if self.overhaul_used_var.get():
            self.overhaul_details_frame.pack(fill=ctk.X, padx=0, pady=(0, 10))
        else:
            self.overhaul_details_frame.pack_forget()

    # ---------------------- Image selection ----------------------
    def select_face_image(self):
        path = filedialog.askopenfilename(
            title="Select Face Screenshot",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
        )
        if path:
            self.face_image_path = path
            self.face_image_label.configure(
                text=Path(path).name, text_color=("black", "white")
            )

    def select_body_image(self):
        path = filedialog.askopenfilename(
            title="Select Body Screenshot",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
        )
        if path:
            self.body_image_path = path
            self.body_image_label.configure(
                text=Path(path).name, text_color=("black", "white")
            )

    def select_preview_image(self):
        path = filedialog.askopenfilename(
            title="Select Preview Screenshot",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
        )
        if path:
            self.preview_image_path = path
            self.preview_image_label.configure(
                text=Path(path).name, text_color=("black", "white")
            )

    # ---------------------- Contribution submit ----------------------
    def submit_contribution(self):
        """Submit character contribution via browser."""
        # Validate inputs
        char_name = self.char_name_var.get().strip()
        author = self.char_author_var.get().strip()
        description = self.char_desc_text.get("1.0", "end").strip()
        tags = self.char_tags_var.get().strip()

        # Build list of missing required fields
        missing_fields = []
        if not char_name:
            missing_fields.append("Name")
        if not author:
            missing_fields.append("Author")
        if not description:
            missing_fields.append("Description")

        # Build list of missing screenshots
        missing_images = []
        if not self.face_image_path:
            missing_images.append("Face screenshot")
        if not self.body_image_path:
            missing_images.append("Body screenshot")

        # Combine all missing items
        all_missing = missing_fields + missing_images

        if all_missing:
            CTkMessageBox.showwarning(
                "Missing Information",
                "Please provide the following:\n\n• " + "\n• ".join(all_missing),
                parent=self.dialog,
            )
            return

        if not self.save_file:
            CTkMessageBox.showerror(
                "No Save File",
                "No save file loaded. Please load a save file first.",
                parent=self.dialog,
            )
            return

        # Get selected slot
        slot_str = self.contrib_slot_var.get()
        slot_index = int(slot_str.split()[1]) - 1

        # Verify slot is not empty
        char = self.save_file.character_slots[slot_index]
        if char.is_empty():
            CTkMessageBox.showerror(
                "Empty Slot",
                f"{slot_str} is empty. Please select a slot with a character.",
                parent=self.dialog,
            )
            return

        try:
            import tempfile

            from er_save_manager.transfer.character_ops import CharacterOperations
            from er_save_manager.ui.dialogs.character_browser_submission import (
                submit_character_via_browser,
            )

            # Extract character metadata
            metadata = CharacterOperations.extract_character_metadata(
                self.save_file, slot_index
            )

            # Attach overhaul mod info
            if hasattr(self, "overhaul_used_var") and self.overhaul_used_var.get():
                selected_name = self.overhaul_name_var.get().strip()
                custom_name = self.overhaul_custom_var.get().strip()
                version = self.overhaul_version_var.get().strip()
                mod_name = custom_name if custom_name else selected_name
                metadata["overhaul_mod"] = {
                    "name": mod_name,
                    "version": version,
                }
                metadata["requires_mod"] = True
                metadata["mod_info"] = {
                    "name": mod_name,
                    "version": version,
                    "required": True,
                }

            # Export character to temp .erc file
            temp_dir = Path(tempfile.gettempdir()) / "er_character_export"
            temp_dir.mkdir(exist_ok=True)

            # Clean name for filename
            safe_name = "".join(
                c for c in char_name if c.isalnum() or c in (" ", "-", "_")
            )
            safe_name = safe_name.strip().replace(" ", "_")
            erc_path = temp_dir / f"{safe_name}.erc"

            CharacterOperations.export_character(
                self.save_file, slot_index, str(erc_path)
            )

            # Submit via browser
            success, url = submit_character_via_browser(
                char_name=char_name,
                author=author,
                description=description,
                tags=tags,
                erc_path=str(erc_path),
                metadata=metadata,
                face_image_path=self.face_image_path,
                body_image_path=self.body_image_path,
                preview_image_path=self.preview_image_path,
            )

            if not success:
                # Show fallback dialog with URL
                self._show_submission_error_dialog(url)

        except Exception as e:
            print(f"[Character Submission] Failed: {e}")
            import traceback

            traceback.print_exc()
            CTkMessageBox.showerror(
                "Submission Failed",
                f"Failed to prepare character submission:\n\n{str(e)}",
                parent=self.dialog,
            )

    def _show_submission_error_dialog(self, submission_url: str | None):
        """Show error dialog with manual submission URL."""
        from er_save_manager.ui.utils import force_render_dialog

        error_dialog = ctk.CTkToplevel(self.dialog)
        error_dialog.title("Use This Link to Submit")
        error_dialog.geometry("720x360")
        error_dialog.transient(self.dialog)

        force_render_dialog(error_dialog)
        error_dialog.grab_set()

        frame = ctk.CTkFrame(error_dialog)
        frame.pack(fill=ctk.BOTH, expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            frame,
            text="GitHub not logged in",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text="Log in to GitHub, then copy and paste this link in your browser to finish the submission.",
            justify=ctk.LEFT,
        ).pack(anchor=ctk.W)

        if submission_url:
            url_text = ctk.CTkTextbox(frame, height=80, wrap="word")
            url_text.pack(fill=ctk.X, pady=10)
            url_text.insert("1.0", submission_url)
            url_text.configure(state="disabled")

            def copy_url():
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(submission_url)
                copy_btn.configure(text="✓ Copied!")
                self.dialog.after(2000, lambda: copy_btn.configure(text="Copy Link"))

            copy_btn = ctk.CTkButton(
                frame, text="Copy Link", command=copy_url, width=120
            )
            copy_btn.pack(pady=6)
        else:
            ctk.CTkLabel(
                frame,
                text="Failed to generate submission URL. Please try again.",
                text_color=("red", "lightcoral"),
            ).pack(pady=10)

        ctk.CTkButton(
            frame, text="Close", command=error_dialog.destroy, width=120
        ).pack(pady=(6, 0))

    # ---------------------- Browse logic ----------------------
    def refresh_characters(self):
        """Refresh character list from remote."""
        import threading

        # Show loading state
        for widget in self.grid_container.winfo_children():
            widget.destroy()

        # Show progress dialog
        progress = ProgressDialog(
            self.dialog, "Loading Characters", "Fetching characters from GitHub..."
        )

        def load_in_background():
            try:
                index_data = self.manager.fetch_index(force_refresh=True)
                self.all_characters = index_data.get("characters", [])

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Loading metrics...",
                        f"Fetched {len(self.all_characters)} characters",
                    ),
                )

                # Fetch metrics for all characters
                character_ids = [c["id"] for c in self.all_characters]
                if character_ids:
                    self.character_metrics_cache = self.metrics.fetch_metrics(
                        character_ids
                    )

                # Update UI on main thread
                def finalize():
                    progress.close()
                    self.apply_filters()

                self.dialog.after(0, finalize)

            except Exception as e:
                print(f"[Character Browser] Failed to refresh: {e}")

                def show_error(error_msg=e):
                    progress.close()
                    # Show error in grid
                    for widget in self.grid_container.winfo_children():
                        widget.destroy()
                    error_label = ctk.CTkLabel(
                        self.grid_container,
                        text=f"Failed to load characters:\n{error_msg}",
                        font=("Segoe UI", 12),
                        text_color=("red", "red"),
                    )
                    error_label.pack(pady=50)

                self.dialog.after(0, show_error)

        # Start loading in background thread
        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def apply_filters(self):
        """Apply search and filter criteria."""
        search = self.search_var.get().lower()
        filter_type = self.filter_var.get()
        sort_by = self.sort_var.get()

        # Filter characters
        self.filtered_characters = []
        for char in self.all_characters:
            # Search filter
            if search:
                searchable = (
                    char.get("name", "").lower()
                    + char.get("author", "").lower()
                    + " ".join(char.get("tags", [])).lower()
                )
                if search not in searchable:
                    continue

            # Overhaul mod filter
            if filter_type == "Overhaul Mod":
                mod_info = char.get("overhaul_mod") or char.get("mod_info")
                if not (mod_info and mod_info.get("name")):
                    continue
            elif filter_type == "No Overhaul":
                mod_info = char.get("overhaul_mod") or char.get("mod_info")
                if mod_info and mod_info.get("name"):
                    continue

            self.filtered_characters.append(char)

        # Sort characters
        if sort_by == "Recent":
            self.filtered_characters.sort(
                key=lambda c: c.get("created_at", ""), reverse=True
            )
        elif sort_by == "Likes":
            self.filtered_characters.sort(
                key=lambda c: self.character_metrics_cache.get(c["id"], {}).get(
                    "likes", 0
                ),
                reverse=True,
            )
        elif sort_by == "Downloads":
            self.filtered_characters.sort(
                key=lambda c: self.character_metrics_cache.get(c["id"], {}).get(
                    "downloads", 0
                ),
                reverse=True,
            )
        elif sort_by == "Name":
            self.filtered_characters.sort(key=lambda c: c.get("name", "").lower())
        elif sort_by == "Level":
            self.filtered_characters.sort(key=lambda c: c.get("level", 0), reverse=True)

        self.display_characters()

    def display_characters(self):
        """Display filtered characters in grid."""
        # Clear existing widgets
        for widget in self.grid_container.winfo_children():
            widget.destroy()

        if not self.filtered_characters:
            no_results = ctk.CTkLabel(
                self.grid_container,
                text="No characters found",
                font=("Segoe UI", 14),
                text_color=("gray50", "gray60"),
            )
            no_results.pack(pady=50)
            return

        # Display character cards
        for character in self.filtered_characters:
            card = self.create_character_card(character)
            card.pack(fill=ctk.X, padx=10, pady=8)

    def create_character_card(self, character: dict[str, Any]):
        """Create character card widget."""
        card = ctk.CTkFrame(
            self.grid_container,
            fg_color=("white", "gray30"),
            corner_radius=8,
            border_width=1,
            border_color=("gray80", "gray50"),
        )

        # Make card clickable
        card.bind("<Button-1>", lambda e: self.preview_character(character))
        card.configure(cursor="hand2")

        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill=ctk.BOTH, expand=True, padx=12, pady=10)

        # Thumbnail (left side)
        thumbnail_label = ctk.CTkLabel(
            content_frame,
            text="",
            width=80,
            height=80,
        )
        thumbnail_label.pack(side=ctk.LEFT, padx=(0, 12))
        thumbnail_label.bind("<Button-1>", lambda e: self.preview_character(character))

        # Load thumbnail asynchronously
        self.dialog.after(10, lambda: self.load_thumbnail(character, thumbnail_label))

        # Info (middle)
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True)
        info_frame.bind("<Button-1>", lambda e: self.preview_character(character))

        # Name
        name_label = ctk.CTkLabel(
            info_frame,
            text=character.get("name", "Unnamed"),
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        )
        name_label.pack(anchor=ctk.W)
        name_label.bind("<Button-1>", lambda e: self.preview_character(character))

        # Stats line
        level = character.get("level", "?")
        char_class = character.get("class", "Unknown")
        ng_plus = character.get("ng_plus", 0)
        ng_text = f" (NG+{ng_plus})" if ng_plus > 0 else ""

        stats_text = f"Level {level} • {char_class}{ng_text}"
        stats_label = ctk.CTkLabel(
            info_frame,
            text=stats_text,
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
            anchor="w",
        )
        stats_label.pack(anchor=ctk.W, pady=(2, 0))
        stats_label.bind("<Button-1>", lambda e: self.preview_character(character))

        # Metrics
        char_id = character["id"]
        metrics = self.character_metrics_cache.get(char_id, {})
        likes = metrics.get("likes", 0)
        downloads = metrics.get("downloads", 0)

        metrics_text = f"👍 {likes}  •  ⬇ {downloads}"
        metrics_label = ctk.CTkLabel(
            info_frame,
            text=metrics_text,
            font=("Segoe UI", 10),
            text_color=("gray50", "gray60"),
            anchor="w",
        )
        metrics_label.pack(anchor=ctk.W, pady=(4, 0))
        metrics_label.bind("<Button-1>", lambda e: self.preview_character(character))

        # Tags for DLC and mod (right side)
        tags = []
        if character.get("has_dlc"):
            tags.append("DLC")
        mod_info = character.get("overhaul_mod") or character.get("mod_info")
        if mod_info and mod_info.get("name"):
            mod_name = mod_info.get("name", "Mod")
            tags.append(mod_name)

        if tags:
            tags_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            tags_frame.pack(side=ctk.RIGHT, padx=(8, 0))
            tags_frame.bind("<Button-1>", lambda e: self.preview_character(character))

            for tag in tags:
                tag_color = (
                    ("#dbeafe", "#1e3a5f") if tag == "DLC" else ("#fef3c7", "#78350f")
                )
                text_color = (
                    ("#1e40af", "#93c5fd") if tag == "DLC" else ("#92400e", "#fbbf24")
                )

                tag_label = ctk.CTkLabel(
                    tags_frame,
                    text=tag,
                    font=("Segoe UI", 9, "bold"),
                    fg_color=tag_color,
                    text_color=text_color,
                    corner_radius=4,
                    padx=6,
                    pady=2,
                )
                tag_label.pack(pady=2)
                tag_label.bind(
                    "<Button-1>", lambda e: self.preview_character(character)
                )

        return card

    def load_thumbnail(self, character: dict[str, Any], label: ctk.CTkLabel):
        """Load thumbnail for character card."""
        if not HAS_PIL:
            return

        char_id = character["id"]

        # Get URLs from screenshots object
        screenshots = character.get("screenshots", {})
        if isinstance(screenshots, dict):
            thumbnail_url = screenshots.get("thumbnail_url")
            face_url = screenshots.get("face_url")
        else:
            thumbnail_url = character.get("thumbnail_url")
            face_url = None

        if not thumbnail_url and not face_url:
            return

        # Try thumbnail first, fall back to face if it fails
        thumbnail_path = None
        if thumbnail_url:
            thumbnail_path = self.manager.download_thumbnail(char_id, thumbnail_url)

        # If thumbnail failed or doesn't exist, try face
        if (not thumbnail_path or not thumbnail_path.exists()) and face_url:
            thumbnail_path = self.manager.download_thumbnail(char_id, face_url)

        if thumbnail_path and thumbnail_path.exists():
            try:
                img = Image.open(thumbnail_path)
                ctk_img = ctk.CTkImage(img, size=(80, 80))
                label.configure(image=ctk_img)
                label.image = ctk_img  # Keep reference
            except Exception:
                pass

    def preview_character(self, character: dict[str, Any]):
        """Show character preview in right panel."""
        self.current_character = character

        # Clear preview area
        for widget in self.preview_area.winfo_children():
            widget.destroy()

        # Clear details frame
        for widget in self.details_frame.winfo_children():
            widget.destroy()

        # Character name and basic info
        ctk.CTkLabel(
            self.preview_area,
            text=character.get("name", "Unnamed"),
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(5, 5))

        # Author
        author = character.get("author", "Unknown")
        ctk.CTkLabel(
            self.preview_area,
            text=f"by {author}",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(pady=(0, 15))

        # Screenshots section
        if HAS_PIL:
            screenshots_frame = ctk.CTkFrame(self.preview_area, fg_color="transparent")
            screenshots_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))

            # Try to load screenshots
            char_id = character["id"]

            # First, try to get screenshot URLs from index.json character entry
            face_url = None
            body_url = None

            screenshots_obj = character.get("screenshots")

            if screenshots_obj:
                face_url = screenshots_obj.get("face_url")
                body_url = screenshots_obj.get("body_url")
            # Fallback: try to get from metadata if not in index
            if not (face_url or body_url):
                metadata_url = character.get("metadata_url")

                if metadata_url:
                    # Download metadata to get screenshot URLs
                    metadata = self.manager.get_cached_metadata(char_id)

                    if not metadata:
                        metadata = self.manager.download_metadata(char_id, metadata_url)

                    if metadata:
                        screenshots = metadata.get("screenshots", {})

                        # Load face and body screenshots
                        face_url = screenshots.get("face_url")
                        body_url = screenshots.get("body_url")

            # Display screenshots (from index.json or fallback metadata)
            if face_url or body_url:
                screenshot_container = ctk.CTkFrame(screenshots_frame)
                screenshot_container.pack(fill=ctk.BOTH, expand=True)

                if face_url:
                    face_label = ctk.CTkLabel(
                        screenshot_container, text="Loading face..."
                    )
                    face_label.pack(side=ctk.LEFT, padx=5, expand=True)
                    self.dialog.after(
                        10,
                        lambda url=face_url: self._load_screenshot(
                            char_id, url, face_label, "_face", (220, 220)
                        ),
                    )

                if body_url:
                    body_label = ctk.CTkLabel(
                        screenshot_container, text="Loading body..."
                    )
                    body_label.pack(side=ctk.LEFT, padx=5, expand=True)
                    self.dialog.after(
                        10,
                        lambda url=body_url: self._load_screenshot(
                            char_id, url, body_label, "_body", (220, 220)
                        ),
                    )

        # Details frame - show stats and equipment
        # Character level and class
        level = character.get("level", "?")
        char_class = character.get("class", "Unknown")
        ng_plus = character.get("ng_plus", 0)
        ng_text = f" (NG+{ng_plus})" if ng_plus > 0 else ""

        stats_header = ctk.CTkLabel(
            self.details_frame,
            text=f"Level {level} {char_class}{ng_text}",
            font=("Segoe UI", 14, "bold"),
        )
        stats_header.pack(anchor=ctk.W, pady=(0, 10))

        # Stats
        stats = character.get("stats", {})
        if stats:
            stats_grid = ctk.CTkFrame(self.details_frame, fg_color="transparent")
            stats_grid.pack(fill=ctk.X, pady=(0, 10))

            stat_names = [
                "vigor",
                "mind",
                "endurance",
                "strength",
                "dexterity",
                "intelligence",
                "faith",
                "arcane",
            ]
            for i, stat in enumerate(stat_names):
                value = stats.get(stat, 0)
                row = i // 4
                col = i % 4

                stat_frame = ctk.CTkFrame(stats_grid, fg_color="transparent")
                stat_frame.grid(row=row, column=col, sticky="w", padx=5, pady=2)

                ctk.CTkLabel(
                    stat_frame,
                    text=f"{stat.capitalize()[:3]}:",
                    font=("Segoe UI", 11),
                    width=35,
                ).pack(side=ctk.LEFT)

                ctk.CTkLabel(
                    stat_frame,
                    text=str(value),
                    font=("Segoe UI", 11, "bold"),
                ).pack(side=ctk.LEFT)

        # Equipment
        equipment = character.get("equipment", {})
        if equipment and isinstance(equipment, dict):
            equip_label = ctk.CTkLabel(
                self.details_frame,
                text="Equipment:",
                font=("Segoe UI", 12, "bold"),
            )
            equip_label.pack(anchor=ctk.W, pady=(10, 5))

            equip_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
            equip_frame.pack(fill=ctk.X, pady=(0, 10))

            for slot_name, item in equipment.items():
                if isinstance(item, dict) and item.get("name"):
                    item_name = item.get("name", "Unknown")
                    slot_display = slot_name.replace("_", " ").title()
                    ctk.CTkLabel(
                        equip_frame,
                        text=f"• {slot_display}: {item_name}",
                        font=("Segoe UI", 11),
                        anchor="w",
                    ).pack(anchor=ctk.W, pady=1)

        # Description
        description = character.get("description", "")
        if description:
            desc_label = ctk.CTkLabel(
                self.details_frame,
                text="Description:",
                font=("Segoe UI", 12, "bold"),
            )
            desc_label.pack(anchor=ctk.W, pady=(10, 5))

            desc_text = ctk.CTkLabel(
                self.details_frame,
                text=description,
                font=("Segoe UI", 11),
                wraplength=600,
                justify=ctk.LEFT,
            )
            desc_text.pack(anchor=ctk.W, fill=ctk.X)

        # Tags
        tags = character.get("tags", [])
        if tags:
            tags_label = ctk.CTkLabel(
                self.details_frame,
                text=f"Tags: {', '.join(tags)}",
                font=("Segoe UI", 11),
                text_color=("gray40", "gray70"),
            )
            tags_label.pack(anchor=ctk.W, pady=(10, 0))

        # Warnings
        warnings = []
        if character.get("has_dlc"):
            warnings.append("ℹ️ Character has Shadow of the Erdtree DLC")
        mod_info = character.get("overhaul_mod") or character.get("mod_info")
        if mod_info and mod_info.get("name"):
            mod_name = mod_info.get("name", "Unknown mod")
            mod_version = mod_info.get("version", "")
            version_text = f" v{mod_version}" if mod_version else ""
            warnings.append(f"⚠ Uses overhaul mod: {mod_name}{version_text}")

        if warnings:
            warning_frame = ctk.CTkFrame(
                self.details_frame, fg_color=("#fff7ed", "#3b2f1b"), corner_radius=6
            )
            warning_frame.pack(fill=ctk.X, pady=(15, 0))

            for warning in warnings:
                ctk.CTkLabel(
                    warning_frame,
                    text=warning,
                    font=("Segoe UI", 11),
                    text_color=("#b45309", "#fbbf24"),
                ).pack(anchor=ctk.W, padx=10, pady=5)

        # Metrics and voting
        char_id = character.get("id", "")
        metrics = self.character_metrics_cache.get(char_id, {})
        likes = metrics.get("likes", 0)
        downloads = metrics.get("downloads", 0)

        metrics_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        metrics_frame.pack(anchor=ctk.W, pady=(15, 0), fill=ctk.X)

        stats_label = ctk.CTkLabel(
            metrics_frame,
            text=f"👍 {likes} likes  |  ⬇ {downloads} downloads",
            font=("Segoe UI", 12),
            text_color=("gray40", "gray70"),
        )
        stats_label.pack(anchor=ctk.W, pady=(0, 8))

        # Like button
        has_liked = self.metrics.has_user_liked(char_id)

        def vote_like():
            self.metrics.like(char_id)
            # Update UI regardless of server response (action was cached locally)
            # Refresh preview to show updated like state
            self.preview_character(character)

        like_btn = ctk.CTkButton(
            metrics_frame,
            text="👍 Like" if not has_liked else "👍 Liked",
            command=vote_like,
            width=90,
            height=32,
            state="disabled" if has_liked else "normal",
            fg_color=("#10b981", "#059669") if has_liked else None,
        )
        like_btn.pack(side=ctk.LEFT, padx=(0, 8))

        # Report button
        report_btn = ctk.CTkButton(
            metrics_frame,
            text="🚩 Report",
            command=lambda: self._show_report_dialog(character),
            width=90,
            height=32,
            fg_color=("#dc2626", "#b91c1c"),
            hover_color=("#b91c1c", "#991b1b"),
        )
        report_btn.pack(side=ctk.LEFT, padx=(0, 0))

    def _load_screenshot(
        self,
        char_id: str,
        screenshot_url: str,
        label: ctk.CTkLabel,
        suffix: str,
        size: tuple[int, int],
    ):
        """Load screenshot image asynchronously."""
        if not HAS_PIL:
            return

        screenshot_path = self.manager.download_screenshot(
            char_id, screenshot_url, suffix
        )

        if screenshot_path and screenshot_path.exists():
            try:
                img = Image.open(screenshot_path)
                # Use thumbnail to maintain aspect ratio while fitting within size
                img.thumbnail(size, Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(img, size=img.size)
                label.configure(image=ctk_img, text="")
                label.image = ctk_img  # Keep reference
            except Exception:
                label.configure(text="Failed to load")
        else:
            label.configure(text="No image")

    def import_to_slot(self):
        """Import selected character to chosen slot."""
        if not self.current_character:
            CTkMessageBox.showwarning(
                "No Character Selected",
                "Please select a character to import",
                parent=self.dialog,
            )
            return

        if not self.save_file:
            CTkMessageBox.showerror(
                "No Save File",
                "No save file loaded. Please load a save file first.",
                parent=self.dialog,
            )
            return

        character = self.current_character
        char_name = character.get("name", "Unnamed")
        char_id = character["id"]

        # Get target slot
        slot_str = self.target_slot_var.get()
        target_slot = int(slot_str.split()[1]) - 1

        # Build warning message
        warnings = []

        # Check DLC requirement
        if character.get("has_dlc"):
            warnings.append("ℹ️ Character has Shadow of the Erdtree DLC")

        # Check mod requirement
        mod_info = character.get("overhaul_mod") or character.get("mod_info")
        if mod_info and mod_info.get("name"):
            mod_name = mod_info.get("name", "Unknown mod")
            mod_version = mod_info.get("version", "")
            version_text = f" v{mod_version}" if mod_version else ""
            warnings.append(f"⚠ Uses overhaul mod: {mod_name}{version_text}")

        # Check NG+ compatibility
        char_ng = character.get("ng_plus", 0)
        if char_ng > 0:
            warnings.append(
                f"⚠ Character is from NG+{char_ng} (may have issues on lower NG cycles)"
            )

        # Check if slot is occupied
        target_char = self.save_file.character_slots[target_slot]
        slot_warning = ""
        if not target_char.is_empty():
            existing_name = target_char.get_character_name()
            slot_warning = f"\n\n⚠ WARNING: {slot_str} is occupied by '{existing_name}'.\nThis will DELETE that character!"

        # Build confirmation message
        message = f"Import '{char_name}' to {slot_str}?"
        if warnings:
            message += "\n\n" + "\n".join(warnings)
        message += slot_warning
        message += "\n\nThe character's SteamID will be automatically synced to match your save file."

        # Confirm with user
        if not CTkMessageBox.askyesno(
            "Confirm Import",
            message,
            parent=self.dialog,
            font_size=12,
        ):
            return

        import threading

        # Show progress dialog
        progress = ProgressDialog(
            self.dialog, "Importing Character", f"Importing '{char_name}'..."
        )

        def import_in_background():
            try:
                import tempfile

                from er_save_manager.transfer.character_ops import CharacterOperations

                # Download .erc file to temp location

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Downloading character file...", "This may take a moment"
                    ),
                )

                erc_url = character.get("erc_url")
                if not erc_url:
                    raise ValueError("Character does not have an .erc download URL")

                temp_dir = Path(tempfile.gettempdir()) / "er_character_downloads"
                temp_dir.mkdir(exist_ok=True)

                temp_erc = temp_dir / f"{char_id}.erc"

                # Stream download
                success = self.manager.stream_character_download(
                    char_id, erc_url, temp_erc
                )
                if not success:
                    raise RuntimeError("Failed to download character file")

                # Create backup before importing

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Creating backup...", "Saving current slot data"
                    ),
                )
                try:
                    from er_save_manager.backup.manager import BackupManager

                    backup_manager = BackupManager(self.save_file._original_filepath)
                    backup_path, _ = backup_manager.create_backup(
                        description=f"Before importing '{char_name}' to {slot_str}",
                        operation="character_import",
                        save=self.save_file,
                    )

                except Exception:
                    # Continue with import even if backup fails
                    pass

                # Import character

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Importing character...", "Processing character data"
                    ),
                )
                imported_name = CharacterOperations.import_character(
                    self.save_file, target_slot, str(temp_erc)
                )

                # Save the modified save file to disk

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Saving changes...", "Writing to save file"
                    ),
                )
                self.save_file.save()

                # Record download metric

                self.dialog.after(
                    0,
                    lambda: progress.update_status("Finalizing...", "Updating metrics"),
                )
                self.metrics.record_download(char_id)

                # Update metrics cache
                if char_id in self.character_metrics_cache:
                    self.character_metrics_cache[char_id]["downloads"] = (
                        self.character_metrics_cache[char_id].get("downloads", 0) + 1
                    )

                # Clean up temp file
                try:
                    temp_erc.unlink()
                except Exception:
                    pass

                # Reload save file if there's a callback
                if self.character_tab and hasattr(self.character_tab, "reload_save"):
                    self.character_tab.reload_save()

                # Refresh metrics for this character from Supabase

                try:
                    fresh_metrics = self.metrics.fetch_metrics([char_id])
                    if fresh_metrics and char_id in fresh_metrics:
                        # Update the character data with fresh metrics
                        self.current_character["downloads"] = fresh_metrics[
                            char_id
                        ].get("downloads", 0)
                        self.current_character["likes"] = fresh_metrics[char_id].get(
                            "likes", 0
                        )
                        # Update metrics cache so preview displays new counts
                        self.character_metrics_cache[char_id] = fresh_metrics[char_id]
                        # Re-display with updated metrics
                        self.preview_character(self.current_character)
                except Exception:
                    pass

                # Show success dialog on main thread
                def show_success():
                    progress.close()
                    CTkMessageBox.showinfo(
                        "Import Successful",
                        f"'{imported_name}' has been imported to {slot_str}!\n\nThe character's SteamID has been synced to your save file.",
                        parent=self.dialog,
                    )

                self.dialog.after(0, show_success)

            except Exception as e:
                print(f"[Character Browser] Import failed: {e}")

                def show_error(error_msg=e):
                    progress.close()
                    CTkMessageBox.showerror(
                        "Import Failed",
                        f"Failed to import character:\n{error_msg}",
                        parent=self.dialog,
                    )

                self.dialog.after(0, show_error)

        # Start import in background thread
        thread = threading.Thread(target=import_in_background, daemon=True)
        thread.start()

    def _show_report_dialog(self, character: dict[str, Any]):
        """Show dialog for reporting a character."""
        from er_save_manager.ui.utils import force_render_dialog

        report_dialog = ctk.CTkToplevel(self.dialog)
        report_dialog.title("Report Character")
        report_dialog.geometry("600x600")
        report_dialog.transient(self.dialog)

        # Force rendering on Linux before grab_set
        force_render_dialog(report_dialog)
        report_dialog.grab_set()

        main_frame = ctk.CTkFrame(report_dialog)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        # GitHub Account Required notice
        notice_frame = ctk.CTkFrame(
            main_frame, fg_color=("#fff7ed", "#3b2f1b"), corner_radius=8
        )
        notice_frame.pack(fill=ctk.X, pady=(0, 15))
        ctk.CTkLabel(
            notice_frame,
            text="⚠ GitHub Account Required",
            font=("Segoe UI", 13, "bold"),
            text_color=("#b45309", "#fbbf24"),
        ).pack(pady=(10, 4))
        ctk.CTkLabel(
            notice_frame,
            text="Log into GitHub in your browser before reporting",
            font=("Segoe UI", 11),
            text_color=("#6b7280", "#d1d5db"),
        ).pack(pady=(0, 10))

        # Title
        ctk.CTkLabel(
            main_frame,
            text=f"Report: {character.get('name', 'Character')}",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 5))

        ctk.CTkLabel(
            main_frame,
            text=f"by {character.get('author', 'Unknown')}",
            font=("Segoe UI", 11),
            text_color=("#6b7280", "#9ca3af"),
        ).pack(anchor=ctk.W, pady=(0, 15))

        # Info box
        info_frame = ctk.CTkFrame(
            main_frame, fg_color=("#fef3c7", "#3f2f1e"), corner_radius=8
        )
        info_frame.pack(fill=ctk.X, pady=(0, 20))
        ctk.CTkLabel(
            info_frame,
            text="⚠️ Please report only genuine issues (inappropriate content, etc.)",
            font=("Segoe UI", 11),
            text_color=("#92400e", "#fbbf24"),
            wraplength=550,
        ).pack(padx=15, pady=12)

        # Reason label
        ctk.CTkLabel(
            main_frame,
            text="Reason for report:",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 8))

        # Text box for report message
        report_text = ctk.CTkTextbox(main_frame, height=150)
        report_text.pack(fill=ctk.BOTH, expand=True, pady=(0, 20))
        report_text.focus()

        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=ctk.X)

        def submit_report():
            message = report_text.get("1.0", tk.END).strip()
            if not message:
                CTkMessageBox.showerror(
                    "Error",
                    "Please enter a reason for the report.",
                    parent=report_dialog,
                )
                return

            # Submit report
            self._submit_character_report(character, message)
            report_dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="Submit Report",
            command=submit_report,
            width=150,
            height=35,
            fg_color=("#dc2626", "#b91c1c"),
            hover_color=("#b91c1c", "#991b1b"),
        ).pack(side=ctk.LEFT, padx=(0, 10))

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=report_dialog.destroy,
            width=120,
            height=35,
        ).pack(side=ctk.LEFT)

    def _submit_character_report(self, character: dict[str, Any], message: str):
        """Submit a character report by opening GitHub with pre-filled issue."""
        import urllib.parse
        import webbrowser

        char_name = character.get("name", "Unknown Character")
        char_author = character.get("author", "Unknown")
        char_id = character.get("id", "unknown")

        # Create issue title
        issue_title = f"[Report] {char_name}"

        # Create issue body
        issue_body = f"""**Reported Character:** {char_name}
**Author:** {char_author}
**Character ID:** {char_id}

---

**Reason for Report:**
```
{message}
```

*Submitted via ER Save Manager Character Browser*
"""

        # Build GitHub issue URL
        repo_owner = "Hapfel1"
        repo_name = "er-character-library"
        params = {
            "title": issue_title,
            "labels": "report",
            "body": issue_body,
        }

        query_string = urllib.parse.urlencode(params, safe="")
        url = f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"

        # Open browser
        webbrowser.open(url)

        # Show confirmation
        CTkMessageBox.showinfo(
            "Report Submitted",
            "Your browser has opened to GitHub.\n\nClick 'Submit new issue' to complete the report.",
            parent=self.dialog,
        )
