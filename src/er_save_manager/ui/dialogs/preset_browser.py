"""CustomTkinter preset browser dialog.

Browse and contribute community appearance presets with 15-slot support.
"""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.preset_manager import PresetManager
from er_save_manager.preset_metrics import PresetMetrics
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.dialogs.community_dialogs import (
    ask_report,
    github_notice,
    like_report_row,
    metrics_text,
    show_submission_link,
)
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.progress_dialog import ProgressDialog
from er_save_manager.ui.utils import (
    bind_mousewheel,
    open_url,
    patch_combo_scroll,
    trace_variable,
)
from er_save_manager.ui.virtual_grid import (
    GridEntry,
    VirtualIconGrid,
    no_image_icon,
)

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class EnhancedPresetBrowser:
    """Preset browser with Browse and Contribute tabs."""

    NUM_SLOTS = 15

    def __init__(self, parent, appearance_tab):
        self.parent = parent
        self.appearance_tab = appearance_tab
        self.manager = PresetManager()
        self.current_preset: dict[str, Any] | None = None
        self.all_presets: list[dict[str, Any]] = []
        self.filtered_presets: list[dict[str, Any]] = []
        # Grid thumbnails by preset id; None once a download found no image
        self._thumbs: dict[str, Any] = {}
        self._thumb_jobs: set[str] = set()
        self._thumb_done: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._by_id: dict[str, dict[str, Any]] = {}

        from pathlib import Path

        settings_path = Path.home() / ".er-save-manager" / "data" / "settings.json"
        self.metrics = PresetMetrics(settings_path)
        self.preset_metrics_cache: dict[str, dict] = {}  # preset_id -> metrics

        self.face_image_path: str | None = None
        self.body_image_path: str | None = None
        self.preview_image_path: str | None = None

    def show(self):
        """Show the preset browser with tabs."""
        self.dialog = ds.create(self.parent, "Community Appearance Presets")
        self.dialog.resizable(True, True)

        def on_close():
            self.dialog.grab_release()
            self.dialog.destroy()

        self.dialog.protocol("WM_DELETE_WINDOW", on_close)

        self.tabview = ctk.CTkTabview(self.dialog)
        self.tabview.pack(fill=ctk.BOTH, expand=True, padx=12, pady=(4, 12))

        self.browse_tab = self.tabview.add("Browse Presets")
        self.contribute_tab = self.tabview.add("Contribute Preset")

        self.setup_browse_tab()
        self.setup_contribute_tab()
        ds.finish(self.dialog, self.parent, width=1240, height=860)

        # Load presets asynchronously after dialog is displayed
        self.dialog.after(50, self.refresh_presets)

    # ---------------------- Browse tab ----------------------
    def setup_browse_tab(self):
        main_frame = ctk.CTkFrame(self.browse_tab, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=8, pady=4)

        top_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_frame.pack(fill=ctk.X)
        ctk.CTkLabel(
            top_frame, text="Browse Community Presets", font=ds.TITLE_LARGE
        ).pack(side=ctk.LEFT)
        ds.button(top_frame, "Refresh", self.refresh_presets, primary=False).pack(
            side=ctk.RIGHT
        )

        filter_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        filter_frame.pack(fill=ctk.X, pady=(10, 12))

        ctk.CTkLabel(filter_frame, text="Search:", font=ds.FONT).pack(
            side=ctk.LEFT, padx=(0, 8)
        )
        self.search_var = ctk.StringVar(value="")
        trace_variable(self.search_var, "w", lambda *args: self.apply_filters())
        ctk.CTkEntry(
            filter_frame,
            textvariable=self.search_var,
            width=240,
            height=32,
            font=ds.FONT,
        ).pack(side=ctk.LEFT)

        ctk.CTkLabel(filter_frame, text="Filter:", font=ds.FONT).pack(
            side=ctk.LEFT, padx=(18, 8)
        )
        self.filter_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            filter_frame,
            variable=self.filter_var,
            values=["All", "Male", "Female", "Cosplay", "Original"],
            width=140,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            state="readonly",
            command=lambda _value=None: self.apply_filters(),
        ).pack(side=ctk.LEFT)

        ctk.CTkLabel(filter_frame, text="Sort:", font=ds.FONT).pack(
            side=ctk.LEFT, padx=(18, 8)
        )
        self.sort_var = ctk.StringVar(value="Recent")
        ctk.CTkComboBox(
            filter_frame,
            variable=self.sort_var,
            values=["Recent", "Likes", "Downloads", "Name"],
            width=140,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            state="readonly",
            command=lambda _value=None: self.apply_filters(),
        ).pack(side=ctk.LEFT)

        self.status_var = ctk.StringVar(value="Loading presets...")
        ctk.CTkLabel(
            filter_frame,
            textvariable=self.status_var,
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(side=ctk.RIGHT)

        content = ctk.CTkFrame(main_frame, fg_color="transparent")
        content.pack(fill=ctk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=0)
        content.rowconfigure(0, weight=1)

        self.grid = VirtualIconGrid(
            content,
            self._on_grid_select,
            cell_w=170,
            cell_h=232,
            icon_size=150,
            fg_color=ds.LIST_BG,
            corner_radius=8,
        )
        self.grid.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._poll_thumbnails()

        preview_panel = ctk.CTkFrame(
            content, width=460, fg_color=ds.BOX, corner_radius=8
        )
        preview_panel.grid(row=0, column=1, sticky="nsew")
        preview_panel.pack_propagate(False)

        slot_frame = ctk.CTkFrame(preview_panel, fg_color="transparent")
        slot_frame.pack(side=ctk.BOTTOM, fill=ctk.X, padx=12, pady=12)
        ctk.CTkLabel(slot_frame, text="Preset slot:", font=ds.FONT).pack(
            side=ctk.LEFT, padx=(0, 8)
        )
        self.target_slot_var = ctk.StringVar(value="Slot 1")
        patch_combo_scroll(
            ctk.CTkComboBox(
                slot_frame,
                variable=self.target_slot_var,
                values=[f"Slot {i + 1}" for i in range(self.NUM_SLOTS)],
                width=110,
                font=ds.FONT,
                dropdown_font=ds.FONT,
                state="readonly",
            )
        ).pack(side=ctk.LEFT)
        self.apply_button = ds.button(
            slot_frame,
            "Apply to Slot",
            self.apply_to_slot,
            width=130,
            state="disabled",
        )
        self.apply_button.pack(side=ctk.RIGHT)

        ctk.CTkLabel(preview_panel, text="Preview", font=ds.TITLE).pack(
            anchor=ctk.W, padx=12, pady=(10, 0)
        )
        self.preview_area = ctk.CTkFrame(preview_panel, fg_color="transparent")
        self.preview_area.pack(fill=ctk.BOTH, expand=True, padx=12, pady=(6, 0))
        ctk.CTkLabel(
            self.preview_area,
            text="Select a preset to preview it.",
            font=ds.FONT,
            text_color=ds.MUTED,
        ).pack(pady=40)

        self.details_frame = ctk.CTkFrame(preview_panel, fg_color="transparent")
        self.details_frame.pack(fill=ctk.X, padx=12, pady=(0, 4))

    # ---------------------- Contribute tab ----------------------
    def setup_contribute_tab(self):
        # Make the contribute tab scrollable for smaller screens
        scrollable_frame = ctk.CTkScrollableFrame(
            self.contribute_tab, fg_color="transparent"
        )
        scrollable_frame.pack(fill=ctk.BOTH, expand=True, padx=8, pady=4)
        bind_mousewheel(scrollable_frame)

        main_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=(0, 8))

        ctk.CTkLabel(
            main_frame,
            text="Contribute Your Character Preset",
            font=ds.TITLE_LARGE,
            anchor="w",
        ).pack(fill=ctk.X, pady=(0, 10))
        github_notice(
            main_frame,
            "submitting",
            retry="\nIf the GitHub home page opens, log in first then submit again.",
            pady=(0, 16),
        )

        content = ctk.CTkFrame(main_frame, fg_color="transparent")
        content.pack(fill=ctk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        left_col = ctk.CTkFrame(content, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 24))

        ctk.CTkLabel(
            left_col, text="1) Select appearance preset slot", font=ds.TITLE
        ).pack(anchor=ctk.W)
        ctk.CTkLabel(
            left_col,
            text="Slots from the in-game 'Detailed Appearance' menu",
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(anchor=ctk.W, pady=(0, 8))

        self.contrib_slot_var = ctk.StringVar(value="Slot 1")
        slot_grid = ds.box(left_col, pady=(0, 20))
        for slot_num in range(1, self.NUM_SLOTS + 1):
            row, col = divmod(slot_num - 1, 5)
            ctk.CTkRadioButton(
                slot_grid,
                text=f"{slot_num}",
                variable=self.contrib_slot_var,
                value=f"Slot {slot_num}",
                font=ds.FONT,
                width=60,
            ).grid(
                row=row,
                column=col,
                sticky="w",
                padx=(12, 0),
                pady=(10 if row == 0 else 4, 10 if row == 2 else 4),
            )

        ctk.CTkLabel(
            left_col, text="2) Add images (face & body required)", font=ds.TITLE
        ).pack(anchor=ctk.W, pady=(0, 6))
        self.face_image_label = self._file_selector(
            left_col, "Face screenshot", self.select_face_image
        )
        self.body_image_label = self._file_selector(
            left_col, "Full body screenshot", self.select_body_image
        )
        self.preview_image_label = self._file_selector(
            left_col,
            "Preview thumbnail (optional)",
            self.select_preview_image,
            placeholder="Uses face if not set",
        )

        meta_section = ctk.CTkFrame(content, fg_color="transparent")
        meta_section.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(meta_section, text="3) Preset information", font=ds.TITLE).pack(
            anchor=ctk.W, pady=(0, 8)
        )

        self.preset_name_var = ctk.StringVar(value="")
        self.author_var = ctk.StringVar(value="")
        self.custom_tags_var = ctk.StringVar(value="")

        self._labeled_entry(meta_section, "Preset name", self.preset_name_var)
        self._labeled_entry(meta_section, "Your name", self.author_var)

        ctk.CTkLabel(meta_section, text="Description:", font=ds.FONT).pack(
            anchor=ctk.W, pady=(0, 4)
        )
        self.description_text = ctk.CTkTextbox(meta_section, height=100, font=ds.FONT)
        self.description_text.pack(fill=ctk.X, pady=(0, 12))

        ctk.CTkLabel(
            meta_section, text="Tags (select all that apply)", font=ds.FONT
        ).pack(anchor=ctk.W, pady=(0, 4))
        tags_box = ds.box(meta_section, pady=(0, 12))
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
            row, col = divmod(i, 2)
            ctk.CTkCheckBox(tags_box, text=tag, variable=var, font=ds.FONT).grid(
                row=row,
                column=col,
                sticky="w",
                padx=12,
                pady=(10 if row == 0 else 3, 10 if row == 4 else 3),
            )

        ctk.CTkLabel(
            meta_section, text="Custom tags (comma-separated)", font=ds.FONT
        ).pack(anchor=ctk.W, pady=(0, 4))
        ctk.CTkEntry(
            meta_section, textvariable=self.custom_tags_var, height=32, font=ds.FONT
        ).pack(fill=ctk.X)

        self.submit_button = ds.button(
            meta_section, "Submit Preset", self.submit_contribution, width=140
        )
        self.submit_button.pack(anchor=ctk.E, pady=(16, 4))

    # ---------------------- Helpers ----------------------
    def _file_selector(
        self, parent, label: str, command, placeholder: str = "No file selected"
    ):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=ctk.X, pady=4)
        ds.button(row, "Browse...", command, primary=False, width=90).pack(
            side=ctk.RIGHT, padx=(12, 0)
        )
        ctk.CTkLabel(row, text=f"{label}:", font=ds.FONT, width=200, anchor=ctk.W).pack(
            side=ctk.LEFT
        )
        value_label = ctk.CTkLabel(
            row, text=placeholder, font=ds.SMALL, text_color=ds.MUTED, anchor=ctk.W
        )
        value_label.pack(side=ctk.LEFT, expand=True, fill=ctk.X)
        return value_label

    def _labeled_entry(self, parent, label: str, var: ctk.StringVar):
        ctk.CTkLabel(parent, text=f"{label}:", font=ds.FONT).pack(
            anchor=ctk.W, pady=(0, 4)
        )
        ctk.CTkEntry(parent, textvariable=var, height=32, font=ds.FONT).pack(
            fill=ctk.X, pady=(0, 12)
        )

    def _open_github_login(self):
        open_url("https://github.com/login")

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
                "Missing Information", "Preset name is required", parent=self.dialog
            )
            return

        author = self.author_var.get().strip()
        if not author:
            CTkMessageBox.showerror(
                "Missing Information", "Author name is required", parent=self.dialog
            )
            return

        description = self.description_text.get("1.0", tk.END).strip()
        if not description:
            CTkMessageBox.showerror(
                "Missing Information", "Description is required", parent=self.dialog
            )
            return

        selected_tags = [tag for tag, var in self.tag_vars.items() if var.get()]
        custom_tags = [
            t.strip() for t in self.custom_tags_var.get().split(",") if t.strip()
        ]
        selected_tags.extend(custom_tags)
        if not selected_tags:
            CTkMessageBox.showerror(
                "Missing Information",
                "At least one tag is required",
                parent=self.dialog,
            )
            return

        tags = ", ".join(selected_tags)
        slot_index = int(self.contrib_slot_var.get().split()[1]) - 1

        try:
            save_file = self.appearance_tab.get_save_file()
            if not save_file:
                CTkMessageBox.showerror(
                    "No Save Loaded", "No save file loaded", parent=self.dialog
                )
                return

            if slot_index >= self.NUM_SLOTS:
                CTkMessageBox.showerror(
                    "Invalid Slot",
                    f"Preset slot {slot_index + 1} is invalid (max {self.NUM_SLOTS})",
                    parent=self.dialog,
                )
                return

            presets_data = save_file.get_character_presets()
            if not presets_data or slot_index >= len(presets_data.presets):
                CTkMessageBox.showerror(
                    "Preset Not Found",
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
                "Submission Failed",
                f"Failed to create submission:\n{exc}",
                parent=self.dialog,
            )

    def _show_submission_error_dialog(self, submission_url: str | None):
        show_submission_link(self.dialog, submission_url)

    # ---------------------- Browse logic ----------------------
    def refresh_presets(self):
        import threading

        progress = ProgressDialog(
            self.dialog, "Loading Presets", "Fetching presets from GitHub..."
        )

        def load_in_background():
            try:
                index_data = self.manager.fetch_index(force_refresh=True)
                self.all_presets = index_data.get("presets", [])

                if not self.all_presets:
                    self.dialog.after(0, progress.close)
                    self.dialog.after(
                        0, lambda: self.status_var.set("No presets available yet")
                    )
                    return

                self.dialog.after(
                    0,
                    lambda: progress.update_status(
                        "Loading presets...", f"Loaded {len(self.all_presets)} presets"
                    ),
                )

                # Load presets first so UI opens quickly
                self.dialog.after(
                    0,
                    lambda: (
                        self.status_var.set(f"Loaded {len(self.all_presets)} presets"),
                        self.apply_filters(),
                    ),
                )

                # Fetch metrics from Supabase asynchronously after UI loads
                def load_metrics_async():
                    try:
                        preset_ids = [
                            p.get("id") for p in self.all_presets if p.get("id")
                        ]
                        self.preset_metrics_cache = self.metrics.fetch_metrics(
                            preset_ids
                        )
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
                # Close progress after metrics load
                self.dialog.after(100, progress.close)

            except Exception as exc:  # pragma: no cover - UI path
                self.dialog.after(0, progress.close)
                self.dialog.after(
                    0,
                    lambda err=exc: self.status_var.set(
                        f"Error loading presets: {err}"
                    ),
                )

        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

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
        # The window may have closed while the index was loading
        if not self.grid.winfo_exists():
            return
        self._by_id = {p["id"]: p for p in self.filtered_presets if p.get("id")}
        entries = []
        for preset in self.filtered_presets:
            preset_id = preset.get("id")
            if not preset_id:
                continue
            metrics = self.preset_metrics_cache.get(preset_id, {})
            text = (
                f"{preset.get('name', 'Unknown')}\n"
                f"by {preset.get('author', 'Unknown')}\n"
                + metrics_text(metrics.get("thumbs_up", 0), metrics.get("downloads", 0))
            )
            entries.append(
                GridEntry(preset_id, text, "", lambda p=preset: self._thumbnail(p))
            )
        self.grid.set_entries(entries, keep_selection=True)
        if not entries and self.all_presets:
            self.status_var.set("No presets match your search")

    def _on_grid_select(self, keys: list) -> None:
        if keys and keys[0] in self._by_id:
            self.preview_preset(self._by_id[keys[0]])

    def _thumbnail(self, preset: dict[str, Any]):
        """Cached grid thumbnail, or None while it downloads in the background."""
        preset_id = preset["id"]
        if preset_id in self._thumbs or not HAS_PIL:
            return self._thumbs.get(preset_id)
        if preset_id not in self._thumb_jobs:
            self._thumb_jobs.add(preset_id)
            self.load_thumbnail(preset)
        return None

    def _poll_thumbnails(self) -> None:
        """Show thumbnails the download threads finished."""
        if not self.grid.winfo_exists():
            return
        while True:
            try:
                key = self._thumb_done.get_nowait()
            except queue.Empty:
                break
            self.grid.refresh_icon(key)
        self.grid.after(100, self._poll_thumbnails)

    def load_thumbnail(self, preset: dict[str, Any]):
        import threading

        preset_id = preset["id"]

        def _work():
            img = None
            try:
                cached = self.manager.get_cached_preset(preset_id)
                if not (cached and "screenshot_path" in cached):
                    cached = self.manager.download_preset(preset_id, preset)
                if cached and "screenshot_path" in cached:
                    img = Image.open(cached["screenshot_path"])
                    img.thumbnail((150, 150))
            except Exception:
                img = None
            self._thumbs[preset_id] = img or no_image_icon()
            # Tk is only touched from the main thread (_poll_thumbnails)
            self._thumb_done.put(preset_id)

        threading.Thread(target=_work, daemon=True).start()

    def preview_preset(self, preset: dict[str, Any]):
        self.current_preset = preset
        self.status_var.set(f"Loading {preset.get('name', 'Preset')}...")
        self.dialog.update_idletasks()

        cached = self.manager.get_cached_preset(preset["id"])
        if not cached:
            cached = self.manager.download_preset(preset["id"], preset)

        if not cached:
            CTkMessageBox.showerror(
                "Download Failed", "Failed to download preset", parent=self.dialog
            )
            return

        # The preview download may have brought a thumbnail the grid lacked
        thumb = self._thumbs.get(preset["id"])
        if thumb is None or thumb is no_image_icon():
            self._thumbs.pop(preset["id"], None)
            self._thumb_jobs.discard(preset["id"])
            self.grid.refresh_icon(preset["id"])

        for widget in self.preview_area.winfo_children():
            widget.destroy()

        def placeholder(text: str) -> None:
            ctk.CTkLabel(
                self.preview_area, text=text, font=ds.FONT, text_color=ds.MUTED
            ).pack(pady=10)

        if HAS_PIL:
            try:
                face_img = self._load_cached_image(
                    preset, cached, suffix="_face", key="face_url", size=(210, 260)
                )
                body_img = self._load_cached_image(
                    preset, cached, suffix="_body", key="body_url", size=(210, 260)
                )

                if face_img or body_img:
                    img_row = ctk.CTkFrame(self.preview_area, fg_color="transparent")
                    img_row.pack(pady=(4, 0))
                    for image, caption in ((face_img, "Face"), (body_img, "Body")):
                        if not image:
                            continue
                        col = ctk.CTkFrame(img_row, fg_color="transparent")
                        col.pack(side=ctk.LEFT, padx=4)
                        ctk.CTkLabel(col, image=image, text="").pack()
                        ctk.CTkLabel(
                            col, text=caption, font=ds.SMALL, text_color=ds.MUTED
                        ).pack()
                elif "screenshot_path" in cached:
                    try:
                        img = Image.open(cached["screenshot_path"])
                        img.thumbnail((320, 320))
                        ctk_img = self._make_ctk_image(img, img.size)
                        if ctk_img:
                            ctk.CTkLabel(
                                self.preview_area, image=ctk_img, text=""
                            ).pack(pady=(4, 0))
                        else:
                            placeholder("Preview not available")
                    except Exception:
                        placeholder("Preview not available")
                else:
                    placeholder("No preview available")
            except Exception as e:
                print(f"[Preview] Image display error: {e}")
                placeholder("Preview not available")
        else:
            placeholder("Install Pillow for previews")

        for widget in self.details_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.details_frame,
            text=preset.get("name", "Preset"),
            font=ds.TITLE,
            anchor="w",
        ).pack(fill=ctk.X)
        ctk.CTkLabel(
            self.details_frame,
            text=f"Author: {preset.get('author', 'Unknown')}",
            font=ds.FONT,
            anchor="w",
        ).pack(fill=ctk.X, pady=(2, 0))
        ctk.CTkLabel(
            self.details_frame,
            text=f"Tags: {', '.join(preset.get('tags', []))}",
            font=ds.FONT,
            anchor="w",
            wraplength=420,
            justify=ctk.LEFT,
        ).pack(fill=ctk.X, pady=(2, 0))

        if "description" in preset:
            ctk.CTkLabel(
                self.details_frame,
                text=preset["description"],
                font=ds.FONT,
                wraplength=420,
                justify=ctk.LEFT,
                anchor="w",
            ).pack(fill=ctk.X, pady=(6, 0))

        preset_id = preset.get("id", "")
        metrics = self.preset_metrics_cache.get(preset_id, {})
        ctk.CTkLabel(
            self.details_frame,
            text=metrics_text(metrics.get("thumbs_up", 0), metrics.get("downloads", 0)),
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=ctk.X, pady=(10, 6))

        has_liked = self.metrics.has_user_liked(preset_id)

        def vote_like():
            if has_liked:
                return
            self.metrics.like(preset_id)
            updated_metrics = self.metrics.fetch_metrics([preset_id])
            if updated_metrics:
                self.preset_metrics_cache.update(updated_metrics)
            self.preview_preset(preset)

        def report():
            message = ask_report(
                self.dialog,
                "Preset",
                preset.get("name", "Preset"),
                preset.get("author", "Unknown"),
            )
            if message:
                self._submit_preset_report(preset, message)

        like_report_row(self.details_frame, has_liked, vote_like, report).pack(
            anchor=ctk.W
        )

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
                    "Preset Unavailable", "Invalid preset data", parent=self.dialog
                )
                return

            save_file = self.appearance_tab.get_save_file()
            save_path = self.appearance_tab.get_save_path()

            if not save_file or not save_path:
                CTkMessageBox.showerror(
                    "No Save Loaded", "No save file loaded", parent=self.dialog
                )
                return

            if target_slot >= self.NUM_SLOTS:
                CTkMessageBox.showerror(
                    "Invalid Slot",
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

            preset_id = self.current_preset.get("id", "")
            if preset_id:
                self.metrics.record_download(preset_id)
                updated_metrics = self.metrics.fetch_metrics([preset_id])
                if updated_metrics:
                    self.preset_metrics_cache.update(updated_metrics)
                self.preview_preset(self.current_preset)

            CTkMessageBox.showinfo(
                "Preset Applied",
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
                "Apply Failed", f"Failed to apply preset:\n{exc}", parent=self.dialog
            )

    def _submit_preset_report(self, preset: dict[str, Any], message: str):
        """Submit a preset report by opening GitHub with pre-filled issue."""
        import urllib.parse

        preset_name = preset.get("name", "Unknown Preset")
        preset_author = preset.get("author", "Unknown")
        preset_id = preset.get("id", "unknown")

        issue_title = f"[Report] {preset_name}"

        issue_body = f"""**Reported Preset:** {preset_name}
**Author:** {preset_author}
**Preset ID:** {preset_id}

---

**Reason for Report:**
{message}

---

*Submitted via ER Save Manager Preset Browser*
"""

        repo_owner = "Hapfel1"
        repo_name = "er-character-presets"
        params = {
            "title": issue_title,
            "labels": "report",
            "body": issue_body,
        }

        query_string = urllib.parse.urlencode(params, safe="")
        url = f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"

        open_url(url)

        CTkMessageBox.showinfo(
            "Report Submitted",
            "Your browser has opened to GitHub.\n\nClick 'Submit new issue' to complete the report.",
            parent=self.dialog,
        )
