"""CustomTkinter character browser dialog.

Browse and contribute community character builds with 10-slot support.
"""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from typing import Any

import customtkinter as ctk

from er_save_manager.character_manager import CharacterManager
from er_save_manager.character_metrics import CharacterMetrics
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
from er_save_manager.ui.toast import notify
from er_save_manager.ui.utils import (
    bind_mousewheel,
    open_url,
    pick_file,
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
        # Grid thumbnails by character id; None once a download found no image
        self._thumbs: dict[str, Any] = {}
        self._thumb_jobs: set[str] = set()
        self._thumb_done: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._by_id: dict[str, dict[str, Any]] = {}

        from pathlib import Path

        settings_path = Path.home() / ".er-save-manager" / "data" / "settings.json"
        self.metrics = CharacterMetrics(settings_path)
        self.character_metrics_cache: dict[str, dict] = {}  # character_id -> metrics

        self.face_image_path: str | None = None
        self.body_image_path: str | None = None
        self.preview_image_path: str | None = None

    def show(self):
        """Show character browser with tabs."""
        self.dialog = ds.create(self.parent, "Community Character Library")
        self.dialog.resizable(True, True)

        def on_close():
            self.dialog.grab_release()
            self.dialog.destroy()

        self.dialog.protocol("WM_DELETE_WINDOW", on_close)

        self.tabview = ctk.CTkTabview(self.dialog)
        self.tabview.pack(fill=ctk.BOTH, expand=True, padx=12, pady=(4, 12))

        self.browse_tab = self.tabview.add("Browse Characters")
        self.contribute_tab = self.tabview.add("Contribute Character")

        self.setup_browse_tab()
        self.setup_contribute_tab()
        ds.finish(self.dialog, self.parent, width=1240, height=860)

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
        # Deleted characters keep their slot data until the slot is reused;
        # the profile summary active flag tells them apart.
        active = set(self.save_file.get_active_slots())

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

            if i not in active:
                char_name += " (deleted)"
            slot_names.append(f"{slot_num} - {char_name}")

        return slot_names

    def refresh_slot_names(self):
        """Refresh slot names in both tabs"""
        slot_names = self._get_slot_display_names()

        if hasattr(self, "target_slot_combo"):
            self.target_slot_combo.configure(values=slot_names)
            self.target_slot_combo.set(slot_names[0])

        if hasattr(self, "contrib_slot_combo"):
            self.contrib_slot_combo.configure(values=slot_names)
            self.contrib_slot_combo.set(slot_names[0])

    # ---------------------- Browse tab ----------------------
    def setup_browse_tab(self):
        main_frame = ctk.CTkFrame(self.browse_tab, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=8, pady=4)

        top_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_frame.pack(fill=ctk.X)
        ctk.CTkLabel(
            top_frame, text="Browse Community Characters", font=ds.TITLE_LARGE
        ).pack(side=ctk.LEFT)
        ds.button(top_frame, "Refresh", self.refresh_characters, primary=False).pack(
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
            values=["All", "Overhaul Mod", "No Overhaul"],
            width=150,
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
            values=["Recent", "Likes", "Downloads", "Name", "Level"],
            width=140,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            state="readonly",
            command=lambda _value=None: self.apply_filters(),
        ).pack(side=ctk.LEFT)

        self.status_label = ctk.CTkLabel(
            filter_frame, text="", font=ds.SMALL, text_color=ds.MUTED
        )
        self.status_label.pack(side=ctk.RIGHT)

        content = ctk.CTkFrame(main_frame, fg_color="transparent")
        content.pack(fill=ctk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=0)
        content.rowconfigure(0, weight=1)

        self.grid = VirtualIconGrid(
            content,
            self._on_grid_select,
            cell_w=170,
            cell_h=214,
            icon_size=128,
            fg_color=ds.LIST_BG,
            corner_radius=8,
        )
        self.grid.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._poll_thumbnails()

        preview_panel = ctk.CTkFrame(
            content, width=500, fg_color=ds.BOX, corner_radius=8
        )
        preview_panel.grid(row=0, column=1, sticky="nsew")
        preview_panel.pack_propagate(False)

        slot_frame = ctk.CTkFrame(preview_panel, fg_color="transparent")
        slot_frame.pack(side=ctk.BOTTOM, fill=ctk.X, padx=12, pady=12)
        ctk.CTkLabel(slot_frame, text="Target slot:", font=ds.FONT).pack(
            side=ctk.LEFT, padx=(0, 8)
        )
        self.target_slot_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        self.target_slot_combo = ctk.CTkComboBox(
            slot_frame,
            values=slot_names,
            width=190,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            state="readonly",
            command=lambda v: self.target_slot_var.set(int(v.split(" - ")[0])),
        )
        self.target_slot_combo.set(slot_names[0])
        self.target_slot_combo.pack(side=tk.LEFT)
        ds.button(slot_frame, "Download & Import", self.import_to_slot, width=150).pack(
            side=ctk.RIGHT
        )

        preview_scroll = ctk.CTkScrollableFrame(preview_panel, fg_color="transparent")
        preview_scroll.pack(fill=ctk.BOTH, expand=True, padx=4, pady=(6, 0))
        bind_mousewheel(preview_scroll)

        self.preview_area = ctk.CTkFrame(preview_scroll, fg_color="transparent")
        self.preview_area.pack(fill=ctk.X, padx=6)
        ctk.CTkLabel(
            self.preview_area,
            text="Select a character to preview it.",
            font=ds.FONT,
            text_color=ds.MUTED,
        ).pack(pady=40)

        self.details_frame = ctk.CTkFrame(preview_scroll, fg_color="transparent")
        self.details_frame.pack(fill=ctk.X, padx=6, pady=(0, 6))

    # ---------------------- Contribute tab ----------------------
    def setup_contribute_tab(self):
        scroll_frame = ctk.CTkScrollableFrame(
            self.contribute_tab, fg_color="transparent"
        )
        scroll_frame.pack(fill=ctk.BOTH, expand=True, padx=8, pady=4)
        bind_mousewheel(scroll_frame)

        main_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=(0, 8))

        ctk.CTkLabel(
            main_frame,
            text="Contribute Your Character",
            font=ds.TITLE_LARGE,
            anchor="w",
        ).pack(fill=ctk.X)
        ctk.CTkLabel(
            main_frame,
            text="Share your character build with the community. Provide screenshots and details.",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=ctk.X, pady=(2, 10))
        github_notice(
            main_frame,
            "submitting",
            retry="\nIf the GitHub home page opens, log in first then submit again.",
            pady=(0, 16),
        )

        form = ctk.CTkFrame(main_frame, fg_color="transparent")
        form.pack(fill=ctk.BOTH, expand=True)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        left = ctk.CTkFrame(form, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        right = ctk.CTkFrame(form, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(left, text="Character slot:", font=ds.FONT).pack(
            anchor=ctk.W, pady=(0, 4)
        )
        self.contrib_slot_var = tk.IntVar(value=1)
        slot_names = self._get_slot_display_names()
        self.contrib_slot_combo = ctk.CTkComboBox(
            left,
            values=slot_names,
            width=220,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            state="readonly",
            command=lambda v: self.contrib_slot_var.set(int(v.split(" - ")[0])),
        )
        self.contrib_slot_combo.set(slot_names[0])
        self.contrib_slot_combo.pack(anchor=ctk.W, pady=(0, 12))

        self.char_name_var = ctk.StringVar()
        self._labeled_entry(left, "Character name:", self.char_name_var)
        self.char_author_var = ctk.StringVar()
        self._labeled_entry(left, "Author (your name):", self.char_author_var)

        ctk.CTkLabel(left, text="Description:", font=ds.FONT).pack(
            anchor=ctk.W, pady=(0, 4)
        )
        self.char_desc_text = ctk.CTkTextbox(left, height=100, font=ds.FONT)
        self.char_desc_text.pack(fill=ctk.X, pady=(0, 12))

        self.char_tags_var = ctk.StringVar()
        self._labeled_entry(left, "Tags (comma-separated):", self.char_tags_var)

        ctk.CTkLabel(right, text="Screenshots (required):", font=ds.TITLE).pack(
            anchor=ctk.W, pady=(0, 6)
        )
        self.face_image_label = self._file_selector(
            right, "Face screenshot:", self.select_face_image
        )
        self.body_image_label = self._file_selector(
            right, "Body screenshot:", self.select_body_image
        )
        self.preview_image_label = self._file_selector(
            right,
            "Preview screenshot:",
            self.select_preview_image,
            placeholder="Optional",
        )

        ctk.CTkLabel(right, text="Overhaul mod:", font=ds.TITLE).pack(
            anchor=ctk.W, pady=(16, 6)
        )
        self.overhaul_used_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            right,
            text="Uses an overhaul mod",
            font=ds.FONT,
            variable=self.overhaul_used_var,
            command=self._toggle_overhaul_details,
        ).pack(anchor=ctk.W, pady=(0, 8))

        self.overhaul_details_frame = ctk.CTkFrame(
            right, fg_color=ds.BOX, corner_radius=8
        )
        details = ctk.CTkFrame(self.overhaul_details_frame, fg_color="transparent")
        details.pack(fill=ctk.X, padx=12, pady=(10, 0))
        overhaul_name_frame = ctk.CTkFrame(details, fg_color="transparent")
        overhaul_name_frame.pack(fill=ctk.X, pady=(0, 12))
        ctk.CTkLabel(overhaul_name_frame, text="Overhaul:", font=ds.FONT).pack(
            side=ctk.LEFT, padx=(0, 8)
        )
        self.overhaul_name_var = ctk.StringVar(value="Convergence")
        ctk.CTkComboBox(
            overhaul_name_frame,
            variable=self.overhaul_name_var,
            values=["Convergence", "Elden Ring Reforged", "Other"],
            width=200,
            font=ds.FONT,
            dropdown_font=ds.FONT,
            state="readonly",
        ).pack(side=ctk.LEFT)

        self.overhaul_custom_var = ctk.StringVar()
        self._labeled_entry(
            details, "Custom mod name (optional):", self.overhaul_custom_var
        )
        self.overhaul_version_var = ctk.StringVar()
        self._labeled_entry(details, "Mod version:", self.overhaul_version_var)

        self._toggle_overhaul_details()

        self.submit_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.submit_frame.pack(fill=ctk.X, pady=(16, 4))
        ds.button(
            self.submit_frame, "Submit to GitHub", self.submit_contribution, width=150
        ).pack(side=ctk.RIGHT)

        self.dialog.after(100, self._auto_detect_convergence)

    # ---------------------- Helpers ----------------------
    def _auto_detect_convergence(self):
        """Auto-detect Convergence mod from save file extension."""
        if self.save_file and hasattr(self.save_file, "_original_filepath"):
            filepath = self.save_file._original_filepath.lower()
            if ".cnv" in filepath:
                self.overhaul_used_var.set(True)
                self.overhaul_name_var.set("Convergence")
                self._toggle_overhaul_details()

    def _file_selector(
        self, parent, label: str, command, placeholder: str = "No file selected"
    ):
        """Create file selector with label and button."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill=ctk.X, pady=4)
        ds.button(frame, "Browse...", command, primary=False, width=90).pack(
            side=ctk.RIGHT, padx=(12, 0)
        )
        ctk.CTkLabel(frame, text=label, font=ds.FONT, width=150, anchor=ctk.W).pack(
            side=ctk.LEFT
        )
        file_label = ctk.CTkLabel(
            frame, text=placeholder, font=ds.SMALL, text_color=ds.MUTED, anchor=ctk.W
        )
        file_label.pack(side=ctk.LEFT, fill=ctk.X, expand=True)
        return file_label

    def _labeled_entry(self, parent, label: str, var: ctk.StringVar):
        """Create labeled entry field."""
        ctk.CTkLabel(parent, text=label, font=ds.FONT).pack(anchor=ctk.W, pady=(0, 4))
        ctk.CTkEntry(parent, textvariable=var, height=32, font=ds.FONT).pack(
            fill=ctk.X, pady=(0, 12)
        )

    def _toggle_overhaul_details(self):
        """Show or hide overhaul details based on checkbox state."""
        if self.overhaul_used_var.get():
            self.overhaul_details_frame.pack(
                fill=ctk.X, pady=(0, 10), before=self.submit_frame
            )
        else:
            self.overhaul_details_frame.pack_forget()

    def _requires_convergence(self, convergence: dict | None) -> bool:
        return bool(convergence and convergence.get("convergence_detected"))

    # ---------------------- Image selection ----------------------
    def select_face_image(self):
        path = pick_file(
            title="Select Face Screenshot",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
        )
        if path:
            self.face_image_path = path
            self.face_image_label.configure(
                text=Path(path).name,
                text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"],
            )

    def select_body_image(self):
        path = pick_file(
            title="Select Body Screenshot",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
        )
        if path:
            self.body_image_path = path
            self.body_image_label.configure(
                text=Path(path).name,
                text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"],
            )

    def select_preview_image(self):
        path = pick_file(
            title="Select Preview Screenshot",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
        )
        if path:
            self.preview_image_path = path
            self.preview_image_label.configure(
                text=Path(path).name,
                text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"],
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
                "Provide the following:\n\n• " + "\n• ".join(all_missing),
                parent=self.dialog,
            )
            return

        if not self.save_file:
            notify(
                self.dialog, "No save file loaded. Load a save file first.", "warning"
            )
            return

        slot_index = self.contrib_slot_var.get() - 1

        char = self.save_file.character_slots[slot_index]
        if char.is_empty():
            notify(
                self.dialog,
                f"Slot {slot_index + 1} is empty. Select a slot with a character.",
                "warning",
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
        show_submission_link(self.dialog, submission_url)

    # ---------------------- Browse logic ----------------------
    def refresh_characters(self):
        """Refresh character list from remote."""
        import threading

        self.status_label.configure(text="", text_color=ds.MUTED)
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
                    self.status_label.configure(
                        text=f"Failed to load characters: {error_msg}",
                        text_color=ds.ERROR,
                    )

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
        # The window may have closed while the index was loading
        if not self.grid.winfo_exists():
            return
        self._by_id = {c["id"]: c for c in self.filtered_characters}
        entries = [
            GridEntry(c["id"], self._card_text(c), "", lambda c=c: self._thumbnail(c))
            for c in self.filtered_characters
        ]
        self.grid.set_entries(entries, keep_selection=True)
        self.status_label.configure(
            text="" if entries else "No characters found", text_color=ds.MUTED
        )

    def _card_text(self, character: dict[str, Any]) -> str:
        level = character.get("level", "?")
        char_class = character.get("class", "Unknown")
        ng_level = character.get("ng_level")
        if ng_level and ng_level != "NG":
            ng_text = f" ({ng_level})"
        else:
            ng_plus = character.get("ng_plus", 0)
            ng_text = f" (NG+{ng_plus})" if ng_plus > 0 else ""
        lines = [
            character.get("name", "Unnamed"),
            f"Level {level} • {char_class}{ng_text}",
        ]

        tags = []
        if character.get("has_dlc"):
            tags.append("DLC")
        convergence = character.get("convergence")
        if self._requires_convergence(convergence):
            version = convergence.get("version", "")
            tags.append(f"Convergence {version}" if version else "Convergence")
        else:
            mod_info = character.get("overhaul_mod") or character.get("mod_info")
            if mod_info and mod_info.get("name"):
                version = mod_info.get("version", "")
                name = mod_info.get("name", "Mod")
                tags.append(f"{name} {version}" if version else name)
        if tags:
            lines.append(" • ".join(tags))

        metrics = self.character_metrics_cache.get(character["id"], {})
        lines.append(metrics_text(metrics.get("likes", 0), metrics.get("downloads", 0)))
        return "\n".join(lines)

    def _on_grid_select(self, keys: list) -> None:
        if keys and keys[0] in self._by_id:
            self.preview_character(self._by_id[keys[0]])

    def _thumbnail(self, character: dict[str, Any]):
        """Cached grid thumbnail, or None while it downloads in the background."""
        char_id = character["id"]
        if char_id in self._thumbs or not HAS_PIL:
            return self._thumbs.get(char_id)
        if char_id not in self._thumb_jobs:
            self._thumb_jobs.add(char_id)
            self.load_thumbnail(character)
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

    def load_thumbnail(self, character: dict[str, Any]):
        """Download and decode a grid thumbnail in a background thread."""
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
            self._thumbs[char_id] = no_image_icon()
            self._thumb_done.put(char_id)
            return

        def _download_and_set():
            img = None
            try:
                path = None
                if thumbnail_url:
                    path = self.manager.download_thumbnail(char_id, thumbnail_url)
                if (not path or not path.exists()) and face_url:
                    path = self.manager.download_thumbnail(char_id, face_url)
                if path and path.exists():
                    img = Image.open(path)
                    img.load()
            except Exception:
                img = None
            self._thumbs[char_id] = img or no_image_icon()
            # Tk is only touched from the main thread (_poll_thumbnails)
            self._thumb_done.put(char_id)

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

        for widget in self.preview_area.winfo_children():
            widget.destroy()

        for widget in self.details_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.preview_area,
            text=character.get("name", "Unnamed"),
            font=ds.TITLE_LARGE,
            anchor="w",
        ).pack(fill=ctk.X, pady=(4, 0))

        author = character.get("author", "Unknown")
        ctk.CTkLabel(
            self.preview_area,
            text=f"by {author}",
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=ctk.X, pady=(0, 10))

        if HAS_PIL:
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
                screenshot_container = ctk.CTkFrame(
                    self.preview_area, fg_color="transparent"
                )
                screenshot_container.pack(pady=(0, 10))

                for url, suffix, text in (
                    (face_url, "_face", "Loading face..."),
                    (body_url, "_body", "Loading body..."),
                ):
                    if not url:
                        continue
                    label = ctk.CTkLabel(
                        screenshot_container,
                        text=text,
                        font=ds.SMALL,
                        text_color=ds.MUTED,
                    )
                    label.pack(side=ctk.LEFT, padx=4)
                    self._load_screenshot(char_id, url, label, suffix, (220, 220))

        level = character.get("level", "?")
        char_class = character.get("class", "Unknown")
        ng_level = character.get("ng_level")
        if ng_level:
            ng_text = f" ({ng_level})"
        else:
            ng_plus = character.get("ng_plus", 0)
            ng_text = f" (NG+{ng_plus})" if ng_plus > 0 else ""

        ctk.CTkLabel(
            self.details_frame,
            text=f"Level {level} {char_class}{ng_text}",
            font=ds.TITLE,
            anchor="w",
        ).pack(fill=ctk.X)

        playtime = character.get("playtime")
        if playtime:
            ctk.CTkLabel(
                self.details_frame,
                text=f"Playtime: {playtime}",
                font=ds.SMALL,
                text_color=ds.MUTED,
                anchor="w",
            ).pack(fill=ctk.X)

        def section(title: str) -> ctk.CTkFrame:
            ctk.CTkLabel(self.details_frame, text=title, font=ds.BOLD, anchor="w").pack(
                fill=ctk.X, pady=(10, 0)
            )
            return ds.box(self.details_frame, pady=(4, 0))

        def value_grid(box, pairs, cols) -> None:
            rows = (len(pairs) + cols - 1) // cols
            for i, (name, value) in enumerate(pairs):
                row, col = divmod(i, cols)
                pady = (8 if row == 0 else 1, 8 if row == rows - 1 else 1)
                ctk.CTkLabel(
                    box, text=name, font=ds.FONT, text_color=ds.MUTED, anchor="w"
                ).grid(row=row, column=col * 2, sticky="w", padx=(12, 6), pady=pady)
                ctk.CTkLabel(box, text=str(value), font=ds.BOLD, anchor="w").grid(
                    row=row, column=col * 2 + 1, sticky="w", padx=(0, 12), pady=pady
                )

        stats = character.get("stats", {})
        if stats:
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
            value_grid(
                section("Attributes"),
                [
                    (f"{stat.capitalize()[:3]}:", stats.get(stat, 0))
                    for stat in stat_names
                ],
                4,
            )

        resources = [
            (name, value)
            for name, value in (
                ("HP:", character.get("max_hp")),
                ("FP:", character.get("max_fp")),
                ("Stamina:", character.get("max_stamina")),
            )
            if value
        ]
        if resources:
            value_grid(section("Max Resources:"), resources, 3)

        bosses_defeated = character.get("bosses_defeated")
        graces_unlocked = character.get("graces_unlocked")
        ng_level = character.get("ng_level")
        progression = []
        if ng_level:
            progression.append(("Playthrough:", ng_level))
        if bosses_defeated is not None:
            progression.append(("Bosses Defeated:", bosses_defeated))
        if graces_unlocked is not None:
            progression.append(("Graces Unlocked:", graces_unlocked))
        if progression:
            value_grid(section("Progression:"), progression, 1)

        def bullets(box, lines, color=None) -> None:
            for i, text in enumerate(lines):
                ctk.CTkLabel(
                    box,
                    text=text,
                    font=ds.FONT,
                    text_color=color,
                    anchor="w",
                    justify=ctk.LEFT,
                    wraplength=420,
                ).pack(
                    fill=ctk.X,
                    padx=12,
                    pady=(8 if i == 0 else 1, 8 if i == len(lines) - 1 else 1),
                )

        convergence = character.get("convergence")
        if convergence and convergence.get("custom_items"):
            lines = []
            for category, items in convergence.get("custom_items", {}).items():
                if items:
                    items_text = ", ".join(items[:5])
                    if len(items) > 5:
                        items_text += f" (+{len(items) - 5} more)"
                    lines.append(f"• {category.capitalize()}: {items_text}")
            if lines:
                bullets(section("Convergence Mod Items:"), lines)

        equipment = character.get("equipment", {})
        if equipment and isinstance(equipment, dict):
            lines = [
                f"• {slot_name.replace('_', ' ').title()}: {item.get('name', 'Unknown')}"
                for slot_name, item in equipment.items()
                if isinstance(item, dict) and item.get("name")
            ]
            if lines:
                bullets(section("Equipment:"), lines)

        description = character.get("description", "")
        if description:
            ctk.CTkLabel(
                self.details_frame, text="Description:", font=ds.BOLD, anchor="w"
            ).pack(fill=ctk.X, pady=(10, 2))
            ctk.CTkLabel(
                self.details_frame,
                text=description,
                font=ds.FONT,
                wraplength=440,
                justify=ctk.LEFT,
                anchor="w",
            ).pack(fill=ctk.X)

        tags = character.get("tags", [])
        if tags:
            ctk.CTkLabel(
                self.details_frame,
                text=f"Tags: {', '.join(tags)}",
                font=ds.SMALL,
                text_color=ds.MUTED,
                anchor="w",
                wraplength=440,
                justify=ctk.LEFT,
            ).pack(fill=ctk.X, pady=(10, 0))

        notes = []
        if character.get("has_dlc"):
            notes.append(("Character has Shadow of the Erdtree DLC", ds.INFO))
        convergence = character.get("convergence")
        if convergence and convergence.get("convergence_detected") is True:
            mod_version = convergence.get("version", "")
            version_text = f" v{mod_version}" if mod_version else ""
            notes.append((f"Requires Convergence mod{version_text}", ds.WARNING))
        else:
            mod_info = character.get("overhaul_mod") or character.get("mod_info")
            if mod_info and mod_info.get("name"):
                mod_name = mod_info.get("name", "Unknown mod")
                mod_version = mod_info.get("version", "")
                version_text = f" v{mod_version}" if mod_version else ""
                notes.append(
                    (f"Uses overhaul mod: {mod_name}{version_text}", ds.WARNING)
                )
        if notes:
            box = ds.box(self.details_frame, pady=(12, 0))
            for i, (text, color) in enumerate(notes):
                ctk.CTkLabel(
                    box, text=text, font=ds.FONT, text_color=color, anchor="w"
                ).pack(
                    fill=ctk.X,
                    padx=12,
                    pady=(8 if i == 0 else 1, 8 if i == len(notes) - 1 else 1),
                )

        char_id = character.get("id", "")
        metrics = self.character_metrics_cache.get(char_id, {})
        ctk.CTkLabel(
            self.details_frame,
            text=metrics_text(metrics.get("likes", 0), metrics.get("downloads", 0)),
            font=ds.SMALL,
            text_color=ds.MUTED,
            anchor="w",
        ).pack(fill=ctk.X, pady=(12, 6))

        has_liked = self.metrics.has_user_liked(char_id)

        def vote_like():
            self.metrics.like(char_id)
            self.preview_character(character)

        def report():
            message = ask_report(
                self.dialog,
                "Character",
                character.get("name", "Unnamed"),
                character.get("author", "Unknown"),
            )
            if message:
                self._submit_character_report(character, message)

        like_report_row(self.details_frame, has_liked, vote_like, report).pack(
            anchor=ctk.W
        )

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
            notify(self.dialog, "Select a character to import", "warning")
            return

        if not self.save_file:
            notify(
                self.dialog, "No save file loaded. Load a save file first.", "warning"
            )
            return

        character = self.current_character
        char_name = character.get("name", "Unnamed")
        char_id = character["id"]

        target_slot = self.target_slot_var.get() - 1

        warnings = []

        if character.get("has_dlc"):
            warnings.append("Character has Shadow of the Erdtree DLC")

        convergence = character.get("convergence")
        if convergence and convergence.get("convergence_detected") is True:
            mod_version = convergence.get("version", "")
            version_text = f" v{mod_version}" if mod_version else ""
            warnings.append(f"Requires Convergence mod{version_text}")
        else:
            mod_info = character.get("overhaul_mod") or character.get("mod_info")
            if mod_info and mod_info.get("name"):
                mod_name = mod_info.get("name", "Unknown mod")
                mod_version = mod_info.get("version", "")
                version_text = f" v{mod_version}" if mod_version else ""
                warnings.append(f"Uses overhaul mod: {mod_name}{version_text}")

        char_ng = character.get("ng_plus", 0)
        if char_ng > 0:
            warnings.append(
                f"Character is from NG+{char_ng} (may have issues on lower NG cycles)"
            )

        target_char = self.save_file.character_slots[target_slot]
        slot_warning = ""
        if not target_char.is_empty():
            existing_name = target_char.get_character_name()
            slot_warning = f"\n\nWARNING: Slot {target_slot + 1} is occupied by '{existing_name}'.\nThis will DELETE that character."

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
                    notify(
                        self.dialog,
                        f"'{imported_name}' has been imported to {slot_str}.",
                        "success",
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

        repo_owner = "Hapfel1"
        repo_name = "er-character-library"
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
