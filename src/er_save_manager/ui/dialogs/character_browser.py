"""CustomTkinter character browser dialog.

Browse and contribute community character builds with 10-slot support.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from er_save_manager.character_manager import CharacterManager
from er_save_manager.character_metrics import CharacterMetrics
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.progress_dialog import ProgressDialog
from er_save_manager.ui.utils import bind_mousewheel, open_url, trace_variable

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

    def _get_slot_display_names(self):
        """Get display names for all slots"""
        if not self.save_file:
            return [str(i) for i in range(1, 11)]

        slot_names = []
        profiles = None

        try:
            if self.save_file.user_data_10_parsed:
                profiles = self.save_file.user_data_10_parsed.profile_summary.profiles
        except Exception:
            pass

        for i in range(10):
            slot_num = i + 1
            char = self.save_file.characters[i]

            if char.is_empty():
                slot_names.append(f"{slot_num} - Empty")
                continue

            char_name = "Unknown"
            if profiles and i < len(profiles):
                try:
                    char_name = profiles[i].character_name or "Unknown"
                except Exception:
                    pass

            slot_names.append(f"{slot_num} - {char_name}")

        return slot_names

    def refresh_slot_names(self):
        """Refresh slot names in both tabs"""
        slot_names = self._get_slot_display_names()

        # Update browse tab target slot
        if hasattr(self, "target_slot_combo"):
            self.target_slot_combo.configure(values=slot_names)
            self.target_slot_combo.set(slot_names[0])

        # Update contribute tab slot
        if hasattr(self, "contrib_slot_combo"):
            self.contrib_slot_combo.configure(values=slot_names)
            self.contrib_slot_combo.set(slot_names[0])

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
        content.columnconfigure(0, weight=1, minsize=300)
        content.columnconfigure(1, weight=1, minsize=300)
        content.rowconfigure(0, weight=1)

        self.grid_container = ctk.CTkScrollableFrame(
            content,
            fg_color=("gray95", "gray20"),
            corner_radius=8,
            border_width=1,
        )
        self.grid_container.grid(row=0, column=0, sticky="nsew", padx=(0, 0))
        bind_mousewheel(self.grid_container)

        preview_panel = ctk.CTkFrame(content)
        preview_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

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
        self.target_slot_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        self.target_slot_combo = ctk.CTkComboBox(
            slot_frame,
            values=slot_names,
            width=200,
            state="readonly",
            command=lambda v: self.target_slot_var.set(int(v.split(" - ")[0])),
        )
        self.target_slot_combo.set(slot_names[0])
        self.target_slot_combo.pack(side=tk.LEFT)

        import_button = ctk.CTkButton(
            slot_frame,
            text="Download & Import",
            command=self.import_to_slot,
            width=180,
        )
        import_button.pack(side=ctk.LEFT, padx=10)

    # ---------------------- Contribute tab ----------------------
    def setup_contribute_tab(self):
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

        form_frame = ctk.CTkFrame(
            scroll_frame,
            fg_color="transparent",
        )
        form_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=(0, 20))

        slot_section = ctk.CTkFrame(form_frame, fg_color="transparent")
        slot_section.pack(fill=ctk.X, pady=(0, 15))

        ctk.CTkLabel(
            slot_section,
            text="Character Slot:",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 5))

        self.contrib_slot_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        self.contrib_slot_combo = ctk.CTkComboBox(
            slot_section,
            values=slot_names,
            width=200,
            state="readonly",
            command=lambda v: self.contrib_slot_var.set(int(v.split(" - ")[0])),
        )
        self.contrib_slot_combo.set(slot_names[0])
        self.contrib_slot_combo.pack(anchor=ctk.W)

        self.char_name_var = ctk.StringVar()
        self._labeled_entry(form_frame, "Character Name:", self.char_name_var)

        self.char_author_var = ctk.StringVar()
        self._labeled_entry(form_frame, "Author (your name):", self.char_author_var)

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

        self.char_tags_var = ctk.StringVar()
        self._labeled_entry(form_frame, "Tags (comma-separated):", self.char_tags_var)

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
        link.bind("<Button-1>", lambda e: open_url("https://github.com/login"))

        submit_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        submit_frame.pack(fill=ctk.X, padx=0, pady=(0, 10))

        ctk.CTkButton(
            submit_frame,
            text="Submit to GitHub",
            command=self.submit_contribution,
            width=200,
            height=40,
        ).pack(side=ctk.RIGHT)

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

    def _requires_convergence(self, convergence: dict | None) -> bool:
        return bool(convergence and convergence.get("convergence_detected"))

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
        char_name = self.char_name_var.get().strip()
        author = self.char_author_var.get().strip()
        description = self.char_desc_text.get("1.0", "end").strip()
        tags = self.char_tags_var.get().strip()

        missing_fields = []
        if not char_name:
            missing_fields.append("Name")
        if not author:
            missing_fields.append("Author")
        if not description:
            missing_fields.append("Description")

        missing_images = []
        if not self.face_image_path:
            missing_images.append("Face screenshot")
        if not self.body_image_path:
            missing_images.append("Body screenshot")

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

        slot_index = self.contrib_slot_var.get() - 1

        char = self.save_file.character_slots[slot_index]
        if char.is_empty():
            CTkMessageBox.showerror(
                "Empty Slot",
                f"Slot {slot_index + 1} is empty. Please select a slot with a character.",
                parent=self.dialog,
            )
            return

        try:
            import tempfile

            from er_save_manager.transfer.character_ops import CharacterOperations
            from er_save_manager.ui.dialogs.character_browser_submission import (
                submit_character_via_browser,
            )

            metadata = CharacterOperations.extract_character_metadata(
                self.save_file, slot_index
            )

            from er_save_manager.data.convergence_items import (
                get_convergence_items_for_submission,
            )

            save_path = getattr(self.save_file, "_original_filepath", None) or getattr(
                self.save_file, "file_path", None
            )
            print(f"[Character Submit] Checking save file path: {save_path}")

            convergence_data = get_convergence_items_for_submission(
                self.save_file,
                save_path,
            )
            if convergence_data:
                print(
                    f"[Character Submit] Convergence data detected: {convergence_data}"
                )
                metadata["convergence"] = convergence_data
            else:
                print("[Character Submit] No Convergence data detected")

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

            temp_dir = Path(tempfile.gettempdir()) / "er_character_export"
            temp_dir.mkdir(exist_ok=True)

            safe_name = "".join(
                c for c in char_name if c.isalnum() or c in (" ", "-", "_")
            )
            safe_name = safe_name.strip().replace(" ", "_")
            erc_path = temp_dir / f"{safe_name}.erc"

            CharacterOperations.export_character(
                self.save_file, slot_index, str(erc_path)
            )

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

        for widget in self.grid_container.winfo_children():
            widget.destroy()

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

                character_ids = [c["id"] for c in self.all_characters]
                if character_ids:
                    self.character_metrics_cache = self.metrics.fetch_metrics(
                        character_ids
                    )

                def finalize():
                    progress.close()
                    self.apply_filters()

                self.dialog.after(0, finalize)

            except Exception as e:
                print(f"[Character Browser] Failed to refresh: {e}")

                def show_error(error_msg=e):
                    progress.close()
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

        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def apply_filters(self):
        """Apply search and filter criteria."""
        search = self.search_var.get().lower()
        filter_type = self.filter_var.get()
        sort_by = self.sort_var.get()

        self.filtered_characters = []
        for char in self.all_characters:
            if search:
                searchable = (
                    char.get("name", "").lower()
                    + char.get("author", "").lower()
                    + " ".join(char.get("tags", [])).lower()
                )
                if search not in searchable:
                    continue

            if filter_type == "Overhaul Mod":
                mod_info = char.get("overhaul_mod") or char.get("mod_info")
                if not (mod_info and mod_info.get("name")):
                    continue
            elif filter_type == "No Overhaul":
                mod_info = char.get("overhaul_mod") or char.get("mod_info")
                if mod_info and mod_info.get("name"):
                    continue

            self.filtered_characters.append(char)

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

        card.bind("<Button-1>", lambda e: self.preview_character(character))
        card.configure(cursor="hand2")

        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill=ctk.BOTH, expand=True, padx=12, pady=10)

        thumbnail_label = ctk.CTkLabel(
            content_frame,
            text="",
            width=80,
            height=80,
        )
        thumbnail_label.pack(side=ctk.LEFT, padx=(0, 12))
        thumbnail_label.bind("<Button-1>", lambda e: self.preview_character(character))

        self.load_thumbnail(character, thumbnail_label)

        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True)
        info_frame.bind("<Button-1>", lambda e: self.preview_character(character))

        name_label = ctk.CTkLabel(
            info_frame,
            text=character.get("name", "Unnamed"),
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        )
        name_label.pack(anchor=ctk.W)
        name_label.bind("<Button-1>", lambda e: self.preview_character(character))

        level = character.get("level", "?")
        char_class = character.get("class", "Unknown")
        ng_level = character.get("ng_level")
        if ng_level and ng_level != "NG":
            ng_text = f" ({ng_level})"
        else:
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

        tags = []
        if character.get("has_dlc"):
            tags.append("DLC")

        convergence = character.get("convergence")
        if self._requires_convergence(convergence):
            mod_name = "Convergence"
            version = convergence.get("version", "")
            tag_text = f"{mod_name} {version}" if version else mod_name
            tags.append((tag_text, "convergence"))
        elif character.get("overhaul_mod") or character.get("mod_info"):
            mod_info = character.get("overhaul_mod") or character.get("mod_info")
            if mod_info and mod_info.get("name"):
                mod_name = mod_info.get("name", "Mod")
                version = mod_info.get("version", "")
                tag_text = f"{mod_name} {version}" if version else mod_name
                tags.append((tag_text, "mod"))

        if tags:
            tags_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            tags_frame.pack(side=ctk.RIGHT, padx=(8, 0), anchor=ctk.N, pady=8)
            tags_frame.bind("<Button-1>", lambda e: self.preview_character(character))

            for tag_data in tags:
                if isinstance(tag_data, tuple):
                    tag_text, tag_type = tag_data
                else:
                    tag_text = tag_data
                    tag_type = tag_data

                if tag_type == "DLC" or tag_text == "DLC":
                    tag_color = ("#dbeafe", "#1e3a5f")
                    text_color = ("#1e40af", "#93c5fd")
                elif tag_type == "convergence" or "Convergence" in tag_text:
                    tag_color = ("#fef3c7", "#3f2f1e")
                    text_color = ("#92400e", "#fbbf24")
                else:
                    tag_color = ("#fef3c7", "#78350f")
                    text_color = ("#92400e", "#fbbf24")

                tag_label = ctk.CTkLabel(
                    tags_frame,
                    text=tag_text,
                    font=("Segoe UI", 9, "bold"),
                    fg_color=tag_color,
                    text_color=text_color,
                    corner_radius=4,
                    padx=6,
                    pady=2,
                )
                tag_label.pack(pady=2, anchor=ctk.E)
                tag_label.bind(
                    "<Button-1>", lambda e: self.preview_character(character)
                )

        return card

    def load_thumbnail(self, character: dict[str, Any], label: ctk.CTkLabel):
        """Load thumbnail for a character card.

        Downloads and decodes the image in a background thread, then
        updates the label on the main thread to avoid blocking the UI.
        """
        if not HAS_PIL:
            return

        import threading

        char_id = character["id"]

        screenshots = character.get("screenshots", {})
        if isinstance(screenshots, dict):
            thumbnail_url = screenshots.get("thumbnail_url")
            face_url = screenshots.get("face_url")
        else:
            thumbnail_url = character.get("thumbnail_url")
            face_url = None

        if not thumbnail_url and not face_url:
            return

        def _download_and_set():
            path = None
            if thumbnail_url:
                path = self.manager.download_thumbnail(char_id, thumbnail_url)
            if (not path or not path.exists()) and face_url:
                path = self.manager.download_thumbnail(char_id, face_url)
            if not path or not path.exists():
                return
            try:
                img = Image.open(path)
                ctk_img = ctk.CTkImage(img, size=(80, 80))

                def _apply():
                    try:
                        label.configure(image=ctk_img)
                        label.image = ctk_img
                    except Exception:
                        pass

                self.dialog.after(0, _apply)
            except Exception:
                pass

        threading.Thread(target=_download_and_set, daemon=True).start()

    def preview_character(self, character: dict[str, Any]):
        """Show character preview in right panel.

        Metadata is fetched in a background thread when not already cached.
        If cached it is merged synchronously before rendering.
        """
        import threading

        char_id = character.get("id")
        metadata_url = character.get("metadata_url")

        # Use cached metadata immediately if available
        if char_id and metadata_url:
            cached = self.manager.get_cached_metadata(char_id)
            if cached:
                character = {**character, **cached}

        self.current_character = character

        # If metadata isn't cached yet, fetch it in the background and re-render
        if char_id and metadata_url and not self.manager.get_cached_metadata(char_id):

            def _fetch_and_rerender():
                metadata = self.manager.download_metadata(char_id, metadata_url)
                if metadata and self.current_character.get("id") == char_id:
                    self.dialog.after(
                        0,
                        lambda: self.preview_character(
                            {**self.current_character, **metadata}
                        ),
                    )

            threading.Thread(target=_fetch_and_rerender, daemon=True).start()

        # Clear preview area
        for widget in self.preview_area.winfo_children():
            widget.destroy()

        # Clear details frame
        for widget in self.details_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.preview_area,
            text=character.get("name", "Unnamed"),
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(5, 5))

        author = character.get("author", "Unknown")
        ctk.CTkLabel(
            self.preview_area,
            text=f"by {author}",
            font=("Segoe UI", 11),
            text_color=("gray40", "gray70"),
        ).pack(pady=(0, 15))

        if HAS_PIL:
            screenshots_frame = ctk.CTkFrame(self.preview_area, fg_color="transparent")
            screenshots_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))

            char_id = character["id"]

            face_url = None
            body_url = None

            screenshots_obj = character.get("screenshots")

            if screenshots_obj:
                face_url = screenshots_obj.get("face_url")
                body_url = screenshots_obj.get("body_url")

            if not (face_url or body_url):
                metadata_url = character.get("metadata_url")

                if metadata_url:
                    metadata = self.manager.get_cached_metadata(char_id)

                    if not metadata:
                        metadata = self.manager.download_metadata(char_id, metadata_url)

                    if metadata:
                        screenshots = metadata.get("screenshots", {})
                        face_url = screenshots.get("face_url")
                        body_url = screenshots.get("body_url")

            if face_url or body_url:
                screenshot_container = ctk.CTkFrame(screenshots_frame)
                screenshot_container.pack(fill=ctk.BOTH, expand=True)

                if face_url:
                    face_label = ctk.CTkLabel(
                        screenshot_container, text="Loading face..."
                    )
                    face_label.pack(side=ctk.LEFT, padx=5, expand=True)
                    self._load_screenshot(
                        char_id, face_url, face_label, "_face", (220, 220)
                    )

                if body_url:
                    body_label = ctk.CTkLabel(
                        screenshot_container, text="Loading body..."
                    )
                    body_label.pack(side=ctk.LEFT, padx=5, expand=True)
                    self._load_screenshot(
                        char_id, body_url, body_label, "_body", (220, 220)
                    )

        level = character.get("level", "?")
        char_class = character.get("class", "Unknown")
        ng_level = character.get("ng_level")
        if ng_level:
            ng_text = f" ({ng_level})"
        else:
            ng_plus = character.get("ng_plus", 0)
            ng_text = f" (NG+{ng_plus})" if ng_plus > 0 else ""

        stats_header = ctk.CTkLabel(
            self.details_frame,
            text=f"Level {level} {char_class}{ng_text}",
            font=("Segoe UI", 14, "bold"),
        )
        stats_header.pack(anchor=ctk.W, pady=(0, 10))

        playtime = character.get("playtime")
        if playtime:
            playtime_label = ctk.CTkLabel(
                self.details_frame,
                text=f"Playtime: {playtime}",
                font=("Segoe UI", 11),
                text_color=("gray40", "gray70"),
            )
            playtime_label.pack(anchor=ctk.W, pady=(0, 10))

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

        max_hp = character.get("max_hp")
        max_fp = character.get("max_fp")
        max_stamina = character.get("max_stamina")

        if max_hp or max_fp or max_stamina:
            resources_frame = ctk.CTkFrame(
                self.details_frame,
                fg_color=("#e0f2fe", "#1e3a5f"),
                corner_radius=6,
            )
            resources_frame.pack(fill=ctk.X, pady=(0, 10))

            ctk.CTkLabel(
                resources_frame,
                text="Max Resources:",
                font=("Segoe UI", 11, "bold"),
                text_color=("#0369a1", "#7dd3fc"),
            ).pack(anchor=ctk.W, padx=10, pady=(8, 4))

            resources_grid = ctk.CTkFrame(resources_frame, fg_color="transparent")
            resources_grid.pack(fill=ctk.X, padx=10, pady=(0, 8))

            resource_items = []
            if max_hp:
                resource_items.append((f"❤️ HP: {max_hp}", 0))
            if max_fp:
                resource_items.append((f"🔮 FP: {max_fp}", 1))
            if max_stamina:
                resource_items.append((f"⚡ Stamina: {max_stamina}", 2))

            for text, idx in resource_items:
                ctk.CTkLabel(
                    resources_grid,
                    text=text,
                    font=("Segoe UI", 10),
                    text_color=("#0369a1", "#7dd3fc"),
                ).grid(row=0, column=idx, sticky=ctk.W, padx=(0, 15), pady=1)

        bosses_defeated = character.get("bosses_defeated")
        graces_unlocked = character.get("graces_unlocked")
        ng_level = character.get("ng_level")

        if bosses_defeated is not None or graces_unlocked is not None or ng_level:
            prog_frame = ctk.CTkFrame(
                self.details_frame,
                fg_color=("#f0f9ff", "#1e3a5f"),
                corner_radius=6,
            )
            prog_frame.pack(fill=ctk.X, pady=(5, 10))

            ctk.CTkLabel(
                prog_frame,
                text="Progression:",
                font=("Segoe UI", 11, "bold"),
                text_color=("#1e40af", "#93c5fd"),
            ).pack(anchor=ctk.W, padx=10, pady=(8, 2))

            prog_stats = ctk.CTkFrame(prog_frame, fg_color="transparent")
            prog_stats.pack(fill=ctk.X, padx=10, pady=(0, 8))

            if ng_level:
                ctk.CTkLabel(
                    prog_stats,
                    text=f"🔄 Playthrough: {ng_level}",
                    font=("Segoe UI", 10),
                    text_color=("#1e40af", "#93c5fd"),
                ).pack(anchor=ctk.W, pady=1)

            if bosses_defeated is not None:
                ctk.CTkLabel(
                    prog_stats,
                    text=f"⚔️ Bosses Defeated: {bosses_defeated}",
                    font=("Segoe UI", 10),
                    text_color=("#1e40af", "#93c5fd"),
                ).pack(anchor=ctk.W, pady=1)

            if graces_unlocked is not None:
                ctk.CTkLabel(
                    prog_stats,
                    text=f"🔥 Graces Unlocked: {graces_unlocked}",
                    font=("Segoe UI", 10),
                    text_color=("#1e40af", "#93c5fd"),
                ).pack(anchor=ctk.W, pady=1)

        convergence = character.get("convergence")
        if convergence and convergence.get("custom_items"):
            conv_frame = ctk.CTkFrame(
                self.details_frame,
                fg_color=("#fef3c7", "#3f2f1e"),
                corner_radius=6,
            )
            conv_frame.pack(fill=ctk.X, pady=(0, 10))

            ctk.CTkLabel(
                conv_frame,
                text="⚡ Convergence Mod Items:",
                font=("Segoe UI", 11, "bold"),
                text_color=("#92400e", "#fbbf24"),
            ).pack(anchor=ctk.W, padx=10, pady=(8, 4))

            custom_items = convergence.get("custom_items", {})
            for category, items in custom_items.items():
                if items:
                    category_display = category.capitalize()
                    items_text = ", ".join(items[:5])
                    if len(items) > 5:
                        items_text += f" (+{len(items) - 5} more)"

                    ctk.CTkLabel(
                        conv_frame,
                        text=f"• {category_display}: {items_text}",
                        font=("Segoe UI", 10),
                        text_color=("#78350f", "#fbbf24"),
                        wraplength=580,
                    ).pack(anchor=ctk.W, padx=20, pady=1)

            ctk.CTkLabel(
                conv_frame,
                text="",
                font=("Segoe UI", 4),
            ).pack()

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

        tags = character.get("tags", [])
        if tags:
            tags_label = ctk.CTkLabel(
                self.details_frame,
                text=f"Tags: {', '.join(tags)}",
                font=("Segoe UI", 11),
                text_color=("gray40", "gray70"),
            )
            tags_label.pack(anchor=ctk.W, pady=(10, 0))

        warnings = []
        if character.get("has_dlc"):
            warnings.append("ℹ️ Character has Shadow of the Erdtree DLC")

        convergence = character.get("convergence")
        if convergence and convergence.get("convergence_detected") is True:
            mod_version = convergence.get("version", "")
            version_text = f" v{mod_version}" if mod_version else ""
            warnings.append(f"⚡ Requires Convergence mod{version_text}")
        else:
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

        has_liked = self.metrics.has_user_liked(char_id)

        def vote_like():
            self.metrics.like(char_id)
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
        """Download and display a screenshot in a background thread.

        The download and decode run off the main thread; only the widget
        update is posted back via dialog.after().
        """
        if not HAS_PIL:
            return

        import threading

        def _download_and_set():
            path = self.manager.download_screenshot(char_id, screenshot_url, suffix)
            if not path or not path.exists():
                self.dialog.after(0, lambda: label.configure(text="No image"))
                return
            try:
                img = Image.open(path)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(img, size=img.size)

                def _apply():
                    try:
                        label.configure(image=ctk_img, text="")
                        label.image = ctk_img
                    except Exception:
                        pass

                self.dialog.after(0, _apply)
            except Exception:
                self.dialog.after(0, lambda: label.configure(text="Failed to load"))

        threading.Thread(target=_download_and_set, daemon=True).start()

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

        target_slot = self.target_slot_var.get() - 1

        warnings = []

        if character.get("has_dlc"):
            warnings.append("ℹ️ Character has Shadow of the Erdtree DLC")

        convergence = character.get("convergence")
        if convergence and convergence.get("convergence_detected") is True:
            mod_version = convergence.get("version", "")
            version_text = f" v{mod_version}" if mod_version else ""
            warnings.append(f"⚡ Requires Convergence mod{version_text}")
        else:
            mod_info = character.get("overhaul_mod") or character.get("mod_info")
            if mod_info and mod_info.get("name"):
                mod_name = mod_info.get("name", "Unknown mod")
                mod_version = mod_info.get("version", "")
                version_text = f" v{mod_version}" if mod_version else ""
                warnings.append(f"⚠ Uses overhaul mod: {mod_name}{version_text}")

        char_ng = character.get("ng_plus", 0)
        if char_ng > 0:
            warnings.append(
                f"⚠ Character is from NG+{char_ng} (may have issues on lower NG cycles)"
            )

        target_char = self.save_file.character_slots[target_slot]
        slot_warning = ""
        if not target_char.is_empty():
            existing_name = target_char.get_character_name()
            slot_warning = f"\n\n⚠ WARNING: Slot {target_slot + 1} is occupied by '{existing_name}'.\nThis will DELETE that character!"

        message = f"Import '{char_name}' to Slot {target_slot + 1}?"
        if warnings:
            message += "\n\n" + "\n".join(warnings)
        message += slot_warning
        message += "\n\nThe character's SteamID will be automatically synced to match your save file."

        if not CTkMessageBox.askyesno(
            "Confirm Import",
            message,
            parent=self.dialog,
            font_size=12,
        ):
            return

        import threading

        progress = ProgressDialog(
            self.dialog, "Importing Character", f"Importing '{char_name}'..."
        )

        def import_in_background():
            try:
                import tempfile

                from er_save_manager.transfer.character_ops import CharacterOperations

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

                success = self.manager.stream_character_download(
                    char_id, erc_url, temp_erc
                )
                if not success:
                    raise RuntimeError("Failed to download character file")

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
                        description=f"Before importing '{char_name}' to Slot {target_slot + 1}",
                        operation="character_import",
                        save=self.save_file,
                    )

                except Exception:
                    pass

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Importing character...", "Processing character data"
                    ),
                )
                imported_name = CharacterOperations.import_character(
                    self.save_file, target_slot, str(temp_erc)
                )

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Saving changes...", "Writing to save file"
                    ),
                )
                self.save_file.save()

                self.dialog.after(
                    0,
                    lambda: progress.update_status("Finalizing...", "Updating metrics"),
                )
                self.metrics.record_download(char_id)

                if char_id in self.character_metrics_cache:
                    self.character_metrics_cache[char_id]["downloads"] = (
                        self.character_metrics_cache[char_id].get("downloads", 0) + 1
                    )

                try:
                    temp_erc.unlink()
                except Exception:
                    pass

                if self.character_tab and hasattr(self.character_tab, "reload_save"):
                    self.character_tab.reload_save()

                try:
                    fresh_metrics = self.metrics.fetch_metrics([char_id])
                    if fresh_metrics and char_id in fresh_metrics:
                        self.current_character["downloads"] = fresh_metrics[
                            char_id
                        ].get("downloads", 0)
                        self.current_character["likes"] = fresh_metrics[char_id].get(
                            "likes", 0
                        )
                        self.character_metrics_cache[char_id] = fresh_metrics[char_id]
                        self.preview_character(self.current_character)
                except Exception:
                    pass

                def show_success():
                    progress.close()
                    self.dialog.update_idletasks()
                    slot_str = f"Slot {target_slot + 1}"
                    self.refresh_slot_names()
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

        thread = threading.Thread(target=import_in_background, daemon=True)
        thread.start()

    def _show_report_dialog(self, character: dict[str, Any]):
        """Show dialog for reporting a character."""
        from er_save_manager.ui.utils import force_render_dialog

        report_dialog = ctk.CTkToplevel(self.dialog)
        report_dialog.title("Report Character")
        report_dialog.geometry("600x600")
        report_dialog.transient(self.dialog)

        force_render_dialog(report_dialog)
        report_dialog.grab_set()

        main_frame = ctk.CTkFrame(report_dialog)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

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

        ctk.CTkLabel(
            main_frame,
            text="Reason for report:",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 8))

        report_text = ctk.CTkTextbox(main_frame, height=150)
        report_text.pack(fill=ctk.BOTH, expand=True, pady=(0, 20))
        report_text.focus()

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

        char_name = character.get("name", "Unknown Character")
        char_author = character.get("author", "Unknown")
        char_id = character.get("id", "unknown")

        issue_title = f"[Report] {char_name}"

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
        open_url(url)

        # Show confirmation
        CTkMessageBox.showinfo(
            "Report Submitted",
            "Your browser has opened to GitHub.\n\nClick 'Submit new issue' to complete the report.",
            parent=self.dialog,
        )
