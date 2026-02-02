"""CustomTkinter preset browser dialog.

Browse and contribute community appearance presets with 15-slot support.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.preset_manager import PresetManager
from er_save_manager.preset_metrics import PresetMetrics
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class EnhancedPresetBrowser:
    """Enhanced preset browser with Browse and Contribute tabs."""

    NUM_SLOTS = 15

    def __init__(self, parent, appearance_tab):
        self.parent = parent
        self.appearance_tab = appearance_tab
        self.manager = PresetManager()
        self.current_preset: dict[str, Any] | None = None
        self.all_presets: list[dict[str, Any]] = []
        self.filtered_presets: list[dict[str, Any]] = []
        self.preset_widgets: list[ctk.CTkFrame] = []

        # Metrics integration
        from pathlib import Path

        settings_path = Path.home() / ".er-save-manager" / "data" / "settings.json"
        self.metrics = PresetMetrics(settings_path)
        self.preset_metrics_cache: dict[str, dict] = {}  # preset_id -> metrics

        # Contribution data
        self.face_image_path: str | None = None
        self.body_image_path: str | None = None
        self.preview_image_path: str | None = None

    def show(self):
        """Show enhanced preset browser with tabs."""
        from er_save_manager.ui.utils import force_render_dialog

        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Community Appearance Presets")
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

        self.browse_tab = self.tabview.add("Browse Presets")
        self.contribute_tab = self.tabview.add("Contribute Preset")

        self.setup_browse_tab()
        self.setup_contribute_tab()

        # Force update and rendering on Linux
        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()

        # Load presets asynchronously after dialog is displayed
        self.dialog.after(50, self.refresh_presets)

    # ---------------------- Browse tab ----------------------
    def setup_browse_tab(self):
        main_frame = ctk.CTkFrame(self.browse_tab)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill=ctk.X, pady=(6, 10))

        ctk.CTkLabel(
            top_frame,
            text="Browse Community Presets",
            font=("Segoe UI", 18, "bold"),
        ).pack(side=ctk.LEFT)

        ctk.CTkButton(
            top_frame, text="Refresh", command=self.refresh_presets, width=90
        ).pack(side=ctk.RIGHT)

        filter_frame = ctk.CTkFrame(main_frame)
        filter_frame.pack(fill=ctk.X, pady=(0, 14))

        ctk.CTkLabel(filter_frame, text="Search:").pack(side=ctk.LEFT, padx=(0, 8))
        self.search_var = ctk.StringVar(value="")
        self.search_var.trace("w", lambda *args: self.apply_filters())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var, width=240).pack(
            side=ctk.LEFT
        )

        ctk.CTkLabel(filter_frame, text="Filter:").pack(side=ctk.LEFT, padx=(18, 8))
        self.filter_var = ctk.StringVar(value="All")
        filter_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.filter_var,
            values=["All", "Male", "Female", "Cosplay", "Original"],
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
            values=["Recent", "Likes", "Downloads", "Name"],
            width=150,
            state="readonly",
            command=lambda _value=None: self.apply_filters(),
        )
        sort_combo.pack(side=ctk.LEFT)
        sort_combo.bind("<<ComboboxSelected>>", lambda _e=None: self.apply_filters())

        content = ctk.CTkFrame(main_frame)
        content.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))
        # Fixed widths to prevent shifting when preview loads
        content.columnconfigure(0, weight=1, minsize=750)
        content.columnconfigure(1, weight=0, minsize=520)
        content.rowconfigure(0, weight=1)

        self.grid_container = ctk.CTkScrollableFrame(
            content,
            fg_color=("gray95", "gray20"),
            corner_radius=8,
            border_width=1,
            width=750,
        )
        self.grid_container.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        bind_mousewheel(self.grid_container)

        preview_panel = ctk.CTkFrame(content, width=520)
        preview_panel.grid(row=0, column=1, sticky="nsew")
        preview_panel.grid_propagate(False)  # Prevent resizing based on content
        preview_panel.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            preview_panel,
            text="Preview",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=ctk.W, padx=10, pady=(10, 2))

        self.preview_area = ctk.CTkFrame(preview_panel)
        self.preview_area.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        self.details_frame = ctk.CTkFrame(preview_panel)
        self.details_frame.pack(fill=ctk.X, padx=10, pady=(0, 12))

        slot_frame = ctk.CTkFrame(preview_panel)
        slot_frame.pack(fill=ctk.X, padx=10, pady=(0, 10))

        ctk.CTkLabel(slot_frame, text="Preset Slot:").pack(side=ctk.LEFT, padx=(0, 8))
        self.target_slot_var = ctk.StringVar(value="Slot 1")
        ctk.CTkComboBox(
            slot_frame,
            variable=self.target_slot_var,
            values=[f"Slot {i + 1}" for i in range(self.NUM_SLOTS)],
            width=120,
            state="readonly",
        ).pack(side=ctk.LEFT)

        self.apply_button = ctk.CTkButton(
            slot_frame,
            text="Apply to Slot",
            command=self.apply_to_slot,
            state="disabled",
            width=170,
        )
        self.apply_button.pack(side=ctk.RIGHT)

        self.status_var = ctk.StringVar(value="Loading presets...")
        ctk.CTkLabel(
            main_frame, textvariable=self.status_var, font=("Segoe UI", 11)
        ).pack(pady=(4, 0))

    # ---------------------- Contribute tab ----------------------
    def setup_contribute_tab(self):
        # Make the contribute tab scrollable for smaller screens
        scrollable_frame = ctk.CTkScrollableFrame(self.contribute_tab)
        scrollable_frame.pack(fill=ctk.BOTH, expand=True, padx=12, pady=12)
        bind_mousewheel(scrollable_frame)

        main_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True)
        main_frame.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            main_frame,
            text="Contribute Your Character Preset",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 12), sticky="w")

        notice = ctk.CTkFrame(
            main_frame, fg_color=("#fff7ed", "#3b2f1b"), corner_radius=8
        )
        notice.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 20), padx=0)
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

        content = ctk.CTkFrame(main_frame)
        content.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=0, pady=0)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=0, minsize=400)

        left_col = ctk.CTkFrame(content, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        slot_section = ctk.CTkFrame(left_col, fg_color="transparent")
        slot_section.pack(fill=ctk.X, pady=(0, 20))
        ctk.CTkLabel(
            slot_section,
            text="1) Select Appearance Preset Slot",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 8), padx=0)
        ctk.CTkLabel(
            slot_section,
            text="Slots from the in-game 'Detailed Appearance' menu",
            justify=ctk.LEFT,
            font=("Segoe UI", 11),
            text_color=("#666666", "#999999"),
        ).pack(anchor=ctk.W, padx=0, pady=(0, 12))

        self.contrib_slot_var = ctk.StringVar(value="Slot 1")
        slot_grid_frame = ctk.CTkFrame(slot_section, fg_color="transparent")
        slot_grid_frame.pack(anchor=ctk.W)

        for row in range(3):
            row_frame = ctk.CTkFrame(slot_grid_frame, fg_color="transparent")
            row_frame.pack(anchor=ctk.W, pady=4)
            for col in range(5):
                slot_num = row * 5 + col + 1
                if slot_num <= self.NUM_SLOTS:
                    ctk.CTkRadioButton(
                        row_frame,
                        text=f"{slot_num}",
                        variable=self.contrib_slot_var,
                        value=f"Slot {slot_num}",
                        font=("Segoe UI", 11),
                    ).pack(side=ctk.LEFT, padx=6, pady=2)

        images_section = ctk.CTkFrame(left_col, fg_color="transparent")
        images_section.pack(fill=ctk.X, pady=(0, 0))
        ctk.CTkLabel(
            images_section,
            text="2) Add Images (Face & Body required)",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=ctk.W, padx=0, pady=(0, 12))

        self.face_image_label = self._file_selector(
            images_section, "Face Screenshot", self.select_face_image
        )
        self.body_image_label = self._file_selector(
            images_section, "Full Body Screenshot", self.select_body_image
        )
        self.preview_image_label = self._file_selector(
            images_section,
            "Preview Thumbnail (optional)",
            self.select_preview_image,
            placeholder="Uses face if not set",
        )

        right_col = ctk.CTkFrame(content, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(0, 0))

        meta_section = ctk.CTkFrame(right_col, fg_color="transparent")
        meta_section.pack(fill=ctk.BOTH, expand=True, padx=0, pady=0)
        ctk.CTkLabel(
            meta_section, text="3) Preset Information", font=("Segoe UI", 14, "bold")
        ).pack(anchor=ctk.W, padx=0, pady=(0, 12))

        self.preset_name_var = ctk.StringVar(value="")
        self.author_var = ctk.StringVar(value="")
        self.custom_tags_var = ctk.StringVar(value="")

        self._labeled_entry(meta_section, "Preset Name", self.preset_name_var)
        self._labeled_entry(meta_section, "Your Name", self.author_var)

        desc_frame = ctk.CTkFrame(meta_section, fg_color="transparent")
        desc_frame.pack(fill=ctk.BOTH, expand=True, padx=0, pady=(0, 12))
        ctk.CTkLabel(desc_frame, text="Description", font=("Segoe UI", 11)).pack(
            anchor=ctk.W, pady=(0, 4)
        )
        self.description_text = ctk.CTkTextbox(desc_frame, height=100)
        self.description_text.pack(fill=ctk.BOTH, expand=True, pady=0)

        tags_section = ctk.CTkFrame(meta_section, fg_color="transparent")
        tags_section.pack(fill=ctk.X, padx=0, pady=(0, 12))
        ctk.CTkLabel(
            tags_section, text="Tags (select all that apply)", font=("Segoe UI", 11)
        ).pack(anchor=ctk.W, pady=(0, 6))

        tags_container = ctk.CTkFrame(tags_section, fg_color="transparent")
        tags_container.pack(fill=ctk.X, pady=0)
        left_tags = ctk.CTkFrame(tags_container, fg_color="transparent")
        left_tags.pack(side=ctk.LEFT, fill=ctk.X, expand=True)
        right_tags = ctk.CTkFrame(tags_container, fg_color="transparent")
        right_tags.pack(side=ctk.LEFT, fill=ctk.X, expand=True)

        self.tag_vars: dict[str, ctk.BooleanVar] = {}
        available_tags = [
            "male",
            "female",
            "cosplay",
            "original",
            "fantasy",
            "realistic",
            "anime",
            "meme",
            "elder",
            "young",
        ]
        for i, tag in enumerate(available_tags):
            var = ctk.BooleanVar(value=False)
            self.tag_vars[tag] = var
            container = left_tags if i < len(available_tags) // 2 else right_tags
            ctk.CTkCheckBox(container, text=tag, variable=var).pack(
                anchor=ctk.W, pady=2
            )

        custom_tags_frame = ctk.CTkFrame(meta_section, fg_color="transparent")
        custom_tags_frame.pack(fill=ctk.X, padx=0, pady=(0, 12))
        ctk.CTkLabel(
            custom_tags_frame,
            text="Custom Tags (comma-separated)",
            font=("Segoe UI", 11),
        ).pack(anchor=ctk.W, pady=(0, 4))
        ctk.CTkEntry(custom_tags_frame, textvariable=self.custom_tags_var).pack(
            fill=ctk.X, pady=0
        )

        login_notice = ctk.CTkFrame(
            meta_section, fg_color=("#eef2ff", "#1f2937"), corner_radius=8
        )
        login_notice.pack(fill=ctk.X, padx=0, pady=(0, 12))
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
        link.bind("<Button-1>", lambda e: self._open_github_login())

        # Submit button at bottom of right column
        submit_frame = ctk.CTkFrame(meta_section, fg_color="transparent")
        submit_frame.pack(fill=ctk.X, pady=(12, 0))
        self.submit_button = ctk.CTkButton(
            submit_frame,
            text="Submit Preset",
            command=self.submit_contribution,
            width=150,
            height=38,
            font=("Segoe UI", 12),
        )
        self.submit_button.pack(side=ctk.LEFT)

    # ---------------------- Helpers ----------------------
    def _file_selector(
        self, parent, label: str, command, placeholder: str = "No file selected"
    ):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=ctk.X, pady=8, padx=0)
        ctk.CTkLabel(
            row, text=f"{label}:", font=("Segoe UI", 11), width=180, anchor=ctk.W
        ).pack(side=ctk.LEFT, padx=(0, 12))
        value_label = ctk.CTkLabel(
            row,
            text=placeholder,
            font=("Segoe UI", 10),
            text_color=("#808080", "#a0a0a0"),
        )
        value_label.pack(side=ctk.LEFT, padx=0, expand=True, fill=ctk.X)
        ctk.CTkButton(row, text="Browse...", width=90, command=command).pack(
            side=ctk.LEFT, padx=(12, 0)
        )
        return value_label

    def _labeled_entry(self, parent, label: str, var: ctk.StringVar):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=ctk.X, padx=0, pady=(0, 12))
        ctk.CTkLabel(row, text=f"{label}:", font=("Segoe UI", 11)).pack(
            anchor=ctk.W, pady=(0, 4)
        )
        ctk.CTkEntry(row, textvariable=var).pack(fill=ctk.X, pady=0)

    def _open_github_login(self):
        import webbrowser

        webbrowser.open("https://github.com/login")

    def _make_ctk_image(self, img: Image.Image, size: tuple[int, int]) -> ctk.CTkImage:
        try:
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except Exception as e:
            # Handle PIL/Tkinter integration issues (common in AppImage packaging)
            print(f"[Image] Failed to create CTkImage: {e}")
            return None

    # ---------------------- Image selection ----------------------
    def select_face_image(self):
        path = filedialog.askopenfilename(
            title="Select Face Screenshot",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.face_image_path = path
            self.face_image_label.configure(text=Path(path).name)

    def select_body_image(self):
        path = filedialog.askopenfilename(
            title="Select Full Body Screenshot",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.body_image_path = path
            self.body_image_label.configure(text=Path(path).name)

    def select_preview_image(self):
        path = filedialog.askopenfilename(
            title="Select Preview Thumbnail",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.preview_image_path = path
            self.preview_image_label.configure(text=Path(path).name)

    # ---------------------- Contribution submit ----------------------
    def submit_contribution(self):
        preset_name = self.preset_name_var.get().strip()
        if not preset_name:
            CTkMessageBox.showerror(
                "Error", "Preset name is required", parent=self.dialog
            )
            return

        author = self.author_var.get().strip()
        if not author:
            CTkMessageBox.showerror(
                "Error", "Author name is required", parent=self.dialog
            )
            return

        description = self.description_text.get("1.0", tk.END).strip()
        if not description:
            CTkMessageBox.showerror(
                "Error", "Description is required", parent=self.dialog
            )
            return

        selected_tags = [tag for tag, var in self.tag_vars.items() if var.get()]
        custom_tags = [
            t.strip() for t in self.custom_tags_var.get().split(",") if t.strip()
        ]
        selected_tags.extend(custom_tags)
        if not selected_tags:
            CTkMessageBox.showerror(
                "Error", "At least one tag is required", parent=self.dialog
            )
            return

        tags = ", ".join(selected_tags)
        slot_index = int(self.contrib_slot_var.get().split()[1]) - 1

        try:
            save_file = self.appearance_tab.get_save_file()
            if not save_file:
                CTkMessageBox.showerror(
                    "Error", "No save file loaded", parent=self.dialog
                )
                return

            if slot_index >= self.NUM_SLOTS:
                CTkMessageBox.showerror(
                    "Error",
                    f"Preset slot {slot_index + 1} is invalid (max {self.NUM_SLOTS})",
                    parent=self.dialog,
                )
                return

            presets_data = save_file.get_character_presets()
            if not presets_data or slot_index >= len(presets_data.presets):
                CTkMessageBox.showerror(
                    "Error",
                    f"Character slot {slot_index + 1} preset doesn't exist",
                    parent=self.dialog,
                )
                return

            face_preset = presets_data.presets[slot_index]
            appearance_data = face_preset.to_dict()

            from .browser_submission import submit_preset_via_browser

            success, submission_url = submit_preset_via_browser(
                preset_name=preset_name,
                author=author,
                description=description,
                tags=tags,
                appearance_data=appearance_data,
                face_image_path=self.face_image_path,
                body_image_path=self.body_image_path,
                preview_image_path=self.preview_image_path,
            )

            if not success:
                self._show_submission_error_dialog(submission_url)
        except Exception as exc:  # pragma: no cover - UI path
            CTkMessageBox.showerror(
                "Error", f"Failed to create submission:\n{exc}", parent=self.dialog
            )

    def _show_submission_error_dialog(self, submission_url: str | None):
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(self.dialog)
        dialog.title("Use This Link to Submit")
        dialog.geometry("720x360")
        dialog.transient(self.dialog)

        # Force rendering on Linux before grab_set
        force_render_dialog(dialog)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill=ctk.BOTH, expand=True, padx=14, pady=14)

        ctk.CTkLabel(
            frame,
            text="GitHub not logged in",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text=(
                "Log in to GitHub, then copy and paste this link in your browser to finish the submission."
            ),
            justify=ctk.LEFT,
        ).pack(anchor=ctk.W)

        if submission_url:
            url_box = ctk.CTkTextbox(frame, height=120)
            url_box.pack(fill=ctk.BOTH, expand=True, pady=10)
            url_box.insert("1.0", submission_url)
            url_box.configure(state="disabled")

            def copy_url():
                dialog.clipboard_clear()
                dialog.clipboard_append(submission_url)
                CTkMessageBox.showinfo(
                    "Copied", "URL copied to clipboard.", parent=dialog
                )

            ctk.CTkButton(frame, text="Copy URL", command=copy_url, width=140).pack(
                pady=6
            )
        else:
            ctk.CTkLabel(
                frame,
                text="Could not generate a submission URL. Please log in to GitHub and try again.",
                text_color=("#dc2626", "#fca5a5"),
            ).pack(anchor=ctk.W, pady=10)

        ctk.CTkButton(frame, text="Close", command=dialog.destroy, width=120).pack(
            pady=(6, 0)
        )

    # ---------------------- Browse logic ----------------------
    def refresh_presets(self):
        self.status_var.set("Fetching presets from GitHub...")
        self.dialog.update_idletasks()

        try:
            index_data = self.manager.fetch_index(force_refresh=True)
            self.all_presets = index_data.get("presets", [])

            if not self.all_presets:
                self.status_var.set("No presets available yet")
                return

            # Validate cache entries in case index changed
            invalidated_count = 0
            for preset in self.all_presets:
                is_valid, _ = self.manager.validate_preset_in_index(
                    preset["id"], preset
                )
                if not is_valid:
                    invalidated_count += 1
                    cache_dir = self.manager.cache_dir / preset["id"]
                    if cache_dir.exists():
                        import shutil

                        try:
                            shutil.rmtree(cache_dir)
                        except Exception:
                            pass
                    preset_path = self.manager.cache_dir / f"{preset['id']}.json"
                    if preset_path.exists():
                        try:
                            preset_path.unlink()
                        except Exception:
                            pass

            if invalidated_count:
                print(
                    f"Invalidated {invalidated_count} cached presets due to index changes"
                )

            # Load presets first so UI opens quickly
            self.status_var.set(f"Loaded {len(self.all_presets)} presets")
            self.apply_filters()

            # Fetch metrics from Supabase asynchronously after UI loads
            def load_metrics_async():
                try:
                    preset_ids = [p.get("id") for p in self.all_presets if p.get("id")]
                    self.preset_metrics_cache = self.metrics.fetch_metrics(preset_ids)
                    print(
                        f"Fetched metrics for {len(self.preset_metrics_cache)} presets"
                    )

                    # Load user's likes from local settings (persisted across sessions)
                    user_likes = self.metrics.fetch_user_likes(preset_ids)
                    like_count = len([k for k, v in user_likes.items() if v])
                    if like_count > 0:
                        print(f"Loaded {like_count} user likes from local cache")

                    # Refresh display with metrics and respect sort order
                    self.apply_filters()
                except Exception as e:
                    print(f"Failed to fetch metrics: {e}")
                    self.preset_metrics_cache = {}

            # Schedule async load after 10ms to allow UI to render first
            self.dialog.after(10, load_metrics_async)

        except Exception as exc:  # pragma: no cover - UI path
            self.status_var.set(f"Error loading presets: {exc}")

    def apply_filters(self):
        search_term = self.search_var.get().lower()
        filter_tag = self.filter_var.get().lower()
        self.filtered_presets = []

        for preset in self.all_presets:
            if search_term:
                name_match = search_term in preset.get("name", "").lower()
                author_match = search_term in preset.get("author", "").lower()
                if not (name_match or author_match):
                    continue

            if filter_tag != "all":
                raw_tags = preset.get("tags", [])
                if isinstance(raw_tags, str):
                    tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
                else:
                    tags = [t.lower() for t in raw_tags]
                if filter_tag not in tags:
                    continue

            self.filtered_presets.append(preset)

        sort_mode = self.sort_var.get()
        if sort_mode == "Recent":
            self.filtered_presets.sort(key=lambda p: p.get("created", ""), reverse=True)
        elif sort_mode == "Likes":
            self.filtered_presets.sort(
                key=lambda p: (
                    self.preset_metrics_cache.get(p.get("id", ""), {}).get(
                        "thumbs_up", 0
                    ),
                    p.get("created", ""),
                ),
                reverse=True,
            )
        elif sort_mode == "Downloads":
            self.filtered_presets.sort(
                key=lambda p: (
                    self.preset_metrics_cache.get(p.get("id", ""), {}).get(
                        "downloads", 0
                    ),
                    p.get("created", ""),
                ),
                reverse=True,
            )
        else:
            self.filtered_presets.sort(key=lambda p: p.get("name", "").lower())

        self.display_presets()

    def display_presets(self):
        for widget in self.preset_widgets:
            widget.destroy()
        self.preset_widgets.clear()

        if not self.filtered_presets:
            empty = ctk.CTkLabel(
                self.grid_container, text="No presets match your search"
            )
            empty.grid(row=0, column=0, pady=30, padx=10)
            self.preset_widgets.append(empty)
            return

        row = col = 0
        for preset in self.filtered_presets:
            card = self.create_preset_card(preset)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self.preset_widgets.append(card)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        for i in range(3):
            self.grid_container.grid_columnconfigure(i, weight=1)

    def create_preset_card(self, preset: dict[str, Any]):
        frame = ctk.CTkFrame(self.grid_container, corner_radius=6, border_width=1)
        frame.preset = preset

        thumb = ctk.CTkLabel(frame, text="[Loading...]")
        thumb.pack(pady=(8, 4))
        frame.thumb_label = thumb

        if HAS_PIL:
            self.load_thumbnail(preset, thumb)
        else:
            thumb.configure(text="[No image]")

        ctk.CTkLabel(
            frame,
            text=preset.get("name", "Unknown"),
            font=("Segoe UI", 11, "bold"),
            wraplength=150,
        ).pack(pady=(0, 2))
        ctk.CTkLabel(
            frame,
            text=f"by {preset.get('author', 'Unknown')}",
            font=("Segoe UI", 10),
            text_color=("#6b7280", "#d1d5db"),
        ).pack()

        # Metrics display
        preset_id = preset.get("id", "")
        metrics = self.preset_metrics_cache.get(preset_id, {})
        likes = metrics.get("thumbs_up", 0)
        downloads = metrics.get("downloads", 0)

        metrics_frame = ctk.CTkFrame(frame, fg_color="transparent")
        metrics_frame.pack(pady=(4, 6))

        # Likes
        ctk.CTkLabel(
            metrics_frame,
            text=f"👍 {likes}",
            font=("Segoe UI", 9),
            text_color=("#6b7280", "#9ca3af"),
        ).pack(side=ctk.LEFT, padx=4)

        # Downloads
        ctk.CTkLabel(
            metrics_frame,
            text=f"⬇ {downloads}",
            font=("Segoe UI", 9),
            text_color=("#6b7280", "#9ca3af"),
        ).pack(side=ctk.LEFT, padx=4)

        for widget in frame.winfo_children():
            widget.bind("<Button-1>", lambda _e, p=preset: self.preview_preset(p))
            widget.configure(cursor="hand2")
        frame.bind("<Button-1>", lambda _e, p=preset: self.preview_preset(p))
        frame.configure(cursor="hand2")
        return frame

    def load_thumbnail(self, preset: dict[str, Any], label: ctk.CTkLabel):
        preset_id = preset["id"]
        cached = self.manager.get_cached_preset(preset_id)
        if cached and "screenshot_path" in cached:
            try:
                img = Image.open(cached["screenshot_path"])
                img.thumbnail((150, 150))
                actual_size = img.size
                label.configure(
                    image=self._make_ctk_image(img, actual_size),
                    text="",
                    width=actual_size[0],
                    height=actual_size[1],
                    anchor="center",
                )
                return
            except Exception:
                pass

        label.configure(text="[Downloading...]")
        self.dialog.after(
            0, lambda: self._download_and_display_thumbnail(preset, label)
        )

    def _download_and_display_thumbnail(
        self, preset: dict[str, Any], label: ctk.CTkLabel
    ):
        try:
            preset_id = preset["id"]
            downloaded = self.manager.download_preset(preset_id, preset)
            if downloaded and "screenshot_path" in downloaded:
                img = Image.open(downloaded["screenshot_path"])
                img.thumbnail((150, 150))
                actual_size = img.size
                label.configure(
                    image=self._make_ctk_image(img, actual_size),
                    text="",
                    width=actual_size[0],
                    height=actual_size[1],
                    anchor="center",
                )
                return
        except Exception:
            pass
        label.configure(text="[No Image]")

    def preview_preset(self, preset: dict[str, Any]):
        self.current_preset = preset
        self.status_var.set(f"Loading {preset.get('name', 'Preset')}...")
        self.dialog.update_idletasks()

        cached = self.manager.get_cached_preset(preset["id"])
        if not cached:
            cached = self.manager.download_preset(preset["id"], preset)

        if not cached:
            CTkMessageBox.showerror(
                "Error", "Failed to download preset", parent=self.dialog
            )
            return

        self._refresh_all_thumbnails()

        for widget in self.preview_area.winfo_children():
            widget.destroy()

        if HAS_PIL:
            try:
                face_img = self._load_cached_image(
                    preset, cached, suffix="_face", key="face_url", size=(260, 260)
                )
                body_img = self._load_cached_image(
                    preset, cached, suffix="_body", key="body_url", size=(260, 260)
                )

                if face_img or body_img:
                    img_row = ctk.CTkFrame(self.preview_area)
                    img_row.pack(pady=10)
                    if face_img:
                        face_col = ctk.CTkFrame(img_row)
                        face_col.pack(side=ctk.LEFT, padx=8)
                        ctk.CTkLabel(face_col, image=face_img, text="").pack()
                        ctk.CTkLabel(face_col, text="Face").pack()
                    if body_img:
                        body_col = ctk.CTkFrame(img_row)
                        body_col.pack(side=ctk.LEFT, padx=8)
                        ctk.CTkLabel(body_col, image=body_img, text="").pack()
                        ctk.CTkLabel(body_col, text="Body").pack()
                elif "screenshot_path" in cached:
                    try:
                        img = Image.open(cached["screenshot_path"])
                        img.thumbnail((320, 320))
                        ctk_img = self._make_ctk_image(img, (320, 320))
                        if ctk_img:
                            ctk.CTkLabel(
                                self.preview_area,
                                image=ctk_img,
                                text="",
                            ).pack(pady=10)
                        else:
                            ctk.CTkLabel(
                                self.preview_area, text="[Preview not available]"
                            ).pack(pady=10)
                    except Exception:
                        ctk.CTkLabel(
                            self.preview_area, text="[Preview not available]"
                        ).pack(pady=10)
                else:
                    ctk.CTkLabel(self.preview_area, text="[No preview available]").pack(
                        pady=10
                    )
            except Exception as e:
                # Handle any PIL/Tkinter integration errors
                print(f"[Preview] Image display error: {e}")
                ctk.CTkLabel(self.preview_area, text="[Preview not available]").pack(
                    pady=10
                )
        else:
            ctk.CTkLabel(self.preview_area, text="[Install Pillow for previews]").pack(
                pady=10
            )

        for widget in self.details_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.details_frame,
            text=preset.get("name", "Preset"),
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor=ctk.W)
        ctk.CTkLabel(
            self.details_frame, text=f"Author: {preset.get('author', 'Unknown')}"
        ).pack(anchor=ctk.W, pady=(2, 0))
        ctk.CTkLabel(
            self.details_frame, text=f"Tags: {', '.join(preset.get('tags', []))}"
        ).pack(anchor=ctk.W, pady=(2, 0))

        if "description" in preset:
            ctk.CTkLabel(
                self.details_frame,
                text=preset["description"],
                wraplength=360,
                justify=ctk.LEFT,
            ).pack(anchor=ctk.W, pady=(6, 0))

        # Metrics and voting section
        preset_id = preset.get("id", "")
        metrics = self.preset_metrics_cache.get(preset_id, {})
        likes = metrics.get("thumbs_up", 0)
        downloads = metrics.get("downloads", 0)

        metrics_section = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        metrics_section.pack(anchor=ctk.W, pady=(12, 0), fill=ctk.X)

        # Display current metrics
        stats_label = ctk.CTkLabel(
            metrics_section,
            text=f"👍 {likes} likes  |  ⬇ {downloads} downloads",
            font=("Segoe UI", 11),
            text_color=("#6b7280", "#9ca3af"),
        )
        stats_label.pack(anchor=ctk.W, pady=(0, 8))

        # Like button - check if user has already liked
        has_liked = self.metrics.has_user_liked(preset_id)

        vote_frame = ctk.CTkFrame(metrics_section, fg_color="transparent")
        vote_frame.pack(anchor=ctk.W)

        def vote_like():
            if has_liked:
                # Already liked - just return (button should be disabled anyway)
                return

            self.metrics.like(preset_id)
            # Update metrics from server
            updated_metrics = self.metrics.fetch_metrics([preset_id])
            if updated_metrics:
                self.preset_metrics_cache.update(updated_metrics)
            # Refresh preview to show updated state
            self.preview_preset(preset)

        like_btn = ctk.CTkButton(
            vote_frame,
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
            vote_frame,
            text="🚩 Report",
            command=lambda: self._show_report_dialog(preset),
            width=90,
            height=32,
            fg_color=("#dc2626", "#b91c1c"),
            hover_color=("#b91c1c", "#991b1b"),
        )
        report_btn.pack(side=ctk.LEFT, padx=(0, 8))

        self.apply_button.configure(state="normal")
        self.status_var.set(f"Previewing: {preset.get('name', 'Preset')}")

    def _load_cached_image(
        self,
        preset: dict[str, Any],
        cached: dict[str, Any],
        suffix: str,
        key: str,
        size: tuple[int, int],
    ) -> ctk.CTkImage | None:
        cache_dir = self.manager.cache_dir / preset["id"]
        if cache_dir.exists():
            for img_file in cache_dir.glob(f"*{suffix}.*"):
                try:
                    img = Image.open(img_file)
                    img = img.copy()
                    img.thumbnail(size, Image.LANCZOS)
                    return self._make_ctk_image(img, img.size)
                except Exception:
                    continue

        if key in preset:
            try:
                path = self.manager.download_image(preset["id"], preset[key], suffix)
                if path and path.exists():
                    img = Image.open(path)
                    img = img.copy()
                    img.thumbnail(size, Image.LANCZOS)
                    return self._make_ctk_image(img, img.size)
            except Exception:
                return None
        return None

    def _refresh_all_thumbnails(self):
        for card in self.preset_widgets:
            if hasattr(card, "preset") and hasattr(card, "thumb_label"):
                preset = card.preset
                label = card.thumb_label
                cached = self.manager.get_cached_preset(preset["id"])
                if cached and "screenshot_path" in cached and HAS_PIL:
                    try:
                        img = Image.open(cached["screenshot_path"])
                        img.thumbnail((150, 150))
                        actual_size = img.size
                        label.configure(
                            image=self._make_ctk_image(img, actual_size),
                            text="",
                            width=actual_size[0],
                            height=actual_size[1],
                            anchor="center",
                        )
                    except Exception:
                        pass

    def apply_to_slot(self):
        if not self.current_preset:
            return

        slot_str = self.target_slot_var.get()
        target_slot = int(slot_str.split()[1]) - 1

        try:
            current_char = self.appearance_tab.get_current_character_slot()
            char_name = f"Character {current_char + 1}"
        except Exception:
            char_name = "the current character"

        if not CTkMessageBox.askyesno(
            "Apply Preset",
            (
                f"Apply '{self.current_preset.get('name', 'preset')}' to {char_name}'s {slot_str}?\n\n"
                "This will add the preset to that character's appearance menu."
            ),
            parent=self.dialog,
        ):
            return
        try:
            preset_data = self.manager.get_cached_preset(self.current_preset["id"])
            if not preset_data:
                preset_data = self.manager.download_preset()

            if not preset_data or "appearance" not in preset_data:
                CTkMessageBox.showerror(
                    "Error", "Invalid preset data", parent=self.dialog
                )
                return

            save_file = self.appearance_tab.get_save_file()
            save_path = self.appearance_tab.get_save_path()

            if not save_file or not save_path:
                CTkMessageBox.showerror(
                    "Error", "No save file loaded", parent=self.dialog
                )
                return

            if target_slot >= self.NUM_SLOTS:
                CTkMessageBox.showerror(
                    "Error",
                    f"Preset slot {target_slot + 1} is invalid (max {self.NUM_SLOTS})",
                    parent=self.dialog,
                )
                return

            manager = BackupManager(Path(save_path))
            manager.create_backup(
                description=f"before_applying_preset_to_slot_{target_slot + 1}",
                operation="apply_community_preset",
                save=save_file,
            )

            save_file.import_preset(preset_data["appearance"], target_slot)
            save_file.recalculate_checksums()
            save_file.to_file(Path(save_path))

            # Track download in Supabase
            preset_id = self.current_preset.get("id", "")
            if preset_id:
                self.metrics.record_download(preset_id)
                # Update local cache
                updated_metrics = self.metrics.fetch_metrics([preset_id])
                if updated_metrics:
                    self.preset_metrics_cache.update(updated_metrics)
                # Refresh preview to show updated download count
                self.preview_preset(self.current_preset)

            CTkMessageBox.showinfo(
                "Success",
                f"Applied '{self.current_preset.get('name', 'preset')}' to Preset Slot {target_slot + 1}.",
                parent=self.dialog,
            )

            # Keep browser open - don't close the dialog
            # self.dialog.destroy()
            if (
                hasattr(self.appearance_tab, "reload_save")
                and self.appearance_tab.reload_save
            ):
                self.appearance_tab.reload_save()

        except Exception as exc:  # pragma: no cover - UI path
            CTkMessageBox.showerror(
                "Error", f"Failed to apply preset:\n{exc}", parent=self.dialog
            )

    def _show_report_dialog(self, preset: dict[str, Any]):
        """Show dialog for reporting a preset."""
        from er_save_manager.ui.utils import force_render_dialog

        report_dialog = ctk.CTkToplevel(self.dialog)
        report_dialog.title("Report Preset")
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
            text=f"Report: {preset.get('name', 'Preset')}",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=ctk.W, pady=(0, 5))

        ctk.CTkLabel(
            main_frame,
            text=f"by {preset.get('author', 'Unknown')}",
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
            self._submit_preset_report(preset, message)
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

    def _submit_preset_report(self, preset: dict[str, Any], message: str):
        """Submit a preset report by opening GitHub with pre-filled issue."""
        import urllib.parse
        import webbrowser

        preset_name = preset.get("name", "Unknown Preset")
        preset_author = preset.get("author", "Unknown")
        preset_id = preset.get("id", "unknown")

        # Create issue title
        issue_title = f"[Report] {preset_name}"

        # Create issue body
        issue_body = f"""**Reported Preset:** {preset_name}
**Author:** {preset_author}
**Preset ID:** {preset_id}

---

**Reason for Report:**
{message}

---

*Submitted via ER Save Manager Preset Browser*
"""

        # Build GitHub issue URL
        repo_owner = "Hapfel1"
        repo_name = "er-character-presets"
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


class PresetBrowserDialog:
    """Backward compatibility wrapper."""

    @staticmethod
    def show_coming_soon(parent):
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(parent)
        dialog.title("Community Character Presets")
        dialog.geometry("600x480")
        dialog.transient(parent)

        # Force rendering on Linux before grab_set
        force_render_dialog(dialog)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame, text="Community Character Presets", font=("Segoe UI", 16, "bold")
        ).pack(pady=(0, 12))
        ctk.CTkLabel(
            frame,
            text="Community Character Presets",
            font=("Segoe UI", 16, "bold"),
            text_color=("#f59e0b", "#fcd34d"),
        ).pack(pady=6)

        desc = (
            "Share and download character appearance presets!\n\n"
            "Features:\n"
            "  • Browse community character designs\n"
            "  • Preview with screenshots\n"
            "  • Apply to any character slot (1-15)\n"
            "  • Submit your own creations\n\n"
            "Database hosted externally and auto-updates!"
        )
        ctk.CTkLabel(frame, text=desc, justify=ctk.LEFT).pack(pady=8)
        ctk.CTkButton(frame, text="Close", command=dialog.destroy, width=120).pack(
            pady=8
        )
