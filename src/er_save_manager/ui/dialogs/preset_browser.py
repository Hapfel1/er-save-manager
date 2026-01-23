"""Community preset browser - Full implementation."""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.preset_manager import PresetManager

try:
    from PIL import Image, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not available, screenshots won't display")


class PresetBrowserDialog:
    """Dialog for browsing and applying community presets."""

    def __init__(self, parent, appearance_tab):
        """Initialize preset browser."""
        self.parent = parent
        self.appearance_tab = appearance_tab
        self.manager = PresetManager()
        self.current_preset = None
        self.all_presets = []
        self.filtered_presets = []
        self.preset_widgets = []

    @staticmethod
    def show_coming_soon(parent):
        """Show 'Coming Soon' dialog - for backward compatibility."""
        dialog = tk.Toplevel(parent)
        dialog.title("Community Character Presets")
        dialog.geometry("600x500")
        dialog.transient(parent)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text="Community Character Presets",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(0, 20))

        badge_frame = ttk.Frame(main_frame)
        badge_frame.pack(pady=10)

        ttk.Label(
            badge_frame,
            text="COMING SOON",
            font=("Segoe UI", 12, "bold"),
            foreground="orange",
        ).pack()

        description = """
Share and download character appearance presets!

Features:
  • Browse community character designs
  • Preview with screenshots
  • One-click apply to your character
  • Submit your own creations

Database hosted externally and auto-updates!
        """

        ttk.Label(main_frame, text=description, justify=tk.LEFT).pack(pady=20)
        ttk.Button(main_frame, text="Close", command=dialog.destroy, width=15).pack()

    def show(self):
        """Show full preset browser dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Community Character Presets")
        self.dialog.geometry("1000x700")
        self.dialog.transient(self.parent)

        # Main container
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title and refresh
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            title_frame,
            text="Community Character Presets",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Button(
            title_frame,
            text="Refresh",
            command=self.refresh_presets,
        ).pack(side=tk.RIGHT, padx=5)

        # Search and filter
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.apply_filters())

        ttk.Entry(filter_frame, textvariable=self.search_var, width=30).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))

        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["All", "Male", "Female", "Cosplay", "Original"],
            state="readonly",
            width=15,
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Label(filter_frame, text="Sort:").pack(side=tk.LEFT, padx=(20, 5))

        self.sort_var = tk.StringVar(value="Recent")
        sort_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.sort_var,
            values=["Recent", "Popular", "Name A-Z"],
            state="readonly",
            width=15,
        )
        sort_combo.pack(side=tk.LEFT, padx=5)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        # Split view: Grid + Preview
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: Grid of presets
        grid_frame = ttk.LabelFrame(paned, text="Available Presets", padding=10)
        paned.add(grid_frame, weight=1)

        # Scrollable canvas
        canvas = tk.Canvas(grid_frame, highlightthickness=0, bg="white")
        scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.grid_container = ttk.Frame(canvas)

        self.grid_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window(
            (0, 0), window=self.grid_container, anchor="nw"
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind canvas resize to update window width
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", on_canvas_configure)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Right: Preview
        preview_frame = ttk.LabelFrame(paned, text="Preview", padding=10)
        paned.add(preview_frame, weight=1)

        # Preview screenshot
        self.preview_label = ttk.Label(preview_frame, text="Select a preset to preview")
        self.preview_label.pack(pady=20)

        # Preview details
        self.details_frame = ttk.Frame(preview_frame)
        self.details_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Apply button
        self.apply_button = ttk.Button(
            preview_frame,
            text="Apply to Character",
            command=self.apply_current_preset,
            state=tk.DISABLED,
        )
        self.apply_button.pack(pady=10)

        # Status bar
        self.status_var = tk.StringVar(value="Loading presets...")
        ttk.Label(main_frame, textvariable=self.status_var).pack(pady=5)

        # Load presets
        self.refresh_presets()

    def refresh_presets(self):
        """Fetch and display presets."""
        self.status_var.set("Fetching presets from GitHub...")
        self.dialog.update()

        # Fetch index
        index_data = self.manager.fetch_index(force_refresh=True)
        self.all_presets = index_data.get("presets", [])

        if not self.all_presets:
            self.status_var.set("No presets available yet. Check back later!")
            return

        self.status_var.set(f"Loaded {len(self.all_presets)} presets")
        self.apply_filters()

    def apply_filters(self):
        """Apply search and filter to preset list."""
        search_term = self.search_var.get().lower()
        filter_tag = self.filter_var.get().lower()

        # Filter
        self.filtered_presets = []
        for preset in self.all_presets:
            # Check search
            if search_term:
                name_match = search_term in preset["name"].lower()
                author_match = search_term in preset.get("author", "").lower()
                if not (name_match or author_match):
                    continue

            # Check filter
            if filter_tag != "all":
                tags = [t.lower() for t in preset.get("tags", [])]
                if filter_tag not in tags:
                    continue

            self.filtered_presets.append(preset)

        # Sort
        sort_by = self.sort_var.get()
        if sort_by == "Recent":
            self.filtered_presets.sort(key=lambda p: p.get("created", ""), reverse=True)
        elif sort_by == "Popular":
            self.filtered_presets.sort(
                key=lambda p: p.get("downloads", 0), reverse=True
            )
        elif sort_by == "Name A-Z":
            self.filtered_presets.sort(key=lambda p: p["name"].lower())

        self.display_presets()

    def display_presets(self):
        """Display presets in grid."""
        # Clear existing
        for widget in self.preset_widgets:
            widget.destroy()
        self.preset_widgets = []

        if not self.filtered_presets:
            no_results = ttk.Label(
                self.grid_container,
                text="No presets match your search",
                font=("Segoe UI", 12),
            )
            no_results.grid(row=0, column=0, pady=50)
            self.preset_widgets.append(no_results)
            return

        # Display in grid (3 columns)
        row, col = 0, 0
        for preset in self.filtered_presets:
            card = self.create_preset_card(preset)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self.preset_widgets.append(card)

            col += 1
            if col >= 3:
                col = 0
                row += 1

        # Configure column weights for proper sizing
        for i in range(3):
            self.grid_container.columnconfigure(i, weight=1)

    def create_preset_card(self, preset):
        """Create a preset card widget."""
        frame = ttk.Frame(self.grid_container, relief=tk.RAISED, borderwidth=1)

        # Thumbnail
        thumb_label = ttk.Label(frame, text="[Loading...]", width=20)
        thumb_label.pack(pady=5)

        # Try to load thumbnail
        if HAS_PIL:
            self.load_thumbnail(preset, thumb_label)

        # Name
        name_label = ttk.Label(
            frame,
            text=preset["name"],
            font=("Segoe UI", 9, "bold"),
            wraplength=150,
        )
        name_label.pack(pady=2)

        # Author
        author_label = ttk.Label(
            frame,
            text=f"by {preset.get('author', 'Unknown')}",
            font=("Segoe UI", 8),
            foreground="gray",
        )
        author_label.pack()

        # Downloads
        downloads_label = ttk.Label(
            frame,
            text=f"⬇ {preset.get('downloads', 0)}",
            font=("Segoe UI", 8),
        )
        downloads_label.pack(pady=2)

        # Click to preview
        for widget in [frame, thumb_label, name_label, author_label, downloads_label]:
            widget.bind("<Button-1>", lambda e, p=preset: self.preview_preset(p))
            widget.configure(cursor="hand2")

        return frame

    def load_thumbnail(self, preset, label):
        """Load thumbnail image for preset."""
        preset_id = preset["id"]

        # Check cache first
        cached = self.manager.get_cached_preset(preset_id)
        if cached and "screenshot_path" in cached:
            try:
                self.display_thumbnail(cached["screenshot_path"], label)
                return
            except Exception:
                pass

        # Not cached, show placeholder
        label.configure(text="[No Image]")

    def display_thumbnail(self, image_path, label):
        """Display thumbnail in label."""
        try:
            img = Image.open(image_path)
            img.thumbnail((150, 150))
            photo = ImageTk.PhotoImage(img)
            label.configure(image=photo, text="")
            label.image = photo  # Keep reference
        except Exception as e:
            print(f"Failed to load thumbnail: {e}")
            label.configure(text="[Error]")

    def preview_preset(self, preset):
        """Show preview of selected preset."""
        self.current_preset = preset
        self.status_var.set(f"Loading {preset['name']}...")
        self.dialog.update()

        # Download if not cached
        cached = self.manager.get_cached_preset(preset["id"])
        if not cached:
            cached = self.manager.download_preset(preset["id"], preset)

        if not cached:
            messagebox.showerror("Error", "Failed to download preset")
            self.status_var.set("Error downloading preset")
            return

        # Display large screenshot
        if HAS_PIL and "screenshot_path" in cached:
            try:
                img = Image.open(cached["screenshot_path"])
                img.thumbnail((350, 350))
                photo = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=photo, text="")
                self.preview_label.image = photo
            except Exception as e:
                print(f"Failed to load screenshot: {e}")
                self.preview_label.configure(text="[Screenshot unavailable]")

        # Display details
        for widget in self.details_frame.winfo_children():
            widget.destroy()

        ttk.Label(
            self.details_frame,
            text=preset["name"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=tk.W)

        ttk.Label(
            self.details_frame,
            text=f"Author: {preset.get('author', 'Unknown')}",
        ).pack(anchor=tk.W)

        ttk.Label(
            self.details_frame,
            text=f"Tags: {', '.join(preset.get('tags', []))}",
        ).pack(anchor=tk.W)

        if "description" in preset and preset["description"]:
            ttk.Label(
                self.details_frame,
                text=preset["description"],
                wraplength=300,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=10)

        ttk.Label(
            self.details_frame,
            text=f"Downloads: {preset.get('downloads', 0)}",
            font=("Segoe UI", 8),
            foreground="gray",
        ).pack(anchor=tk.W)

        self.apply_button.configure(state=tk.NORMAL)
        self.status_var.set(f"Previewing: {preset['name']}")

    def apply_current_preset(self):
        """Apply currently selected preset to character."""
        if not self.current_preset:
            return

        # Confirm
        if not messagebox.askyesno(
            "Apply Preset",
            f"Apply '{self.current_preset['name']}' to current character?\n\n"
            f"This will overwrite the character's appearance.\n"
            f"A backup will be created automatically.",
        ):
            return

        try:
            # Get preset data
            preset_data = self.manager.get_cached_preset(self.current_preset["id"])
            if not preset_data:
                preset_data = self.manager.download_preset(
                    self.current_preset["id"], self.current_preset
                )

            if not preset_data or "appearance" not in preset_data:
                messagebox.showerror("Error", "Preset data is invalid or missing")
                return

            # Get save file and character presets from appearance tab
            character_presets = self.appearance_tab.character_presets
            save_file = self.appearance_tab.get_save_file()
            save_path = self.appearance_tab.get_save_path()

            if not character_presets or not save_file:
                messagebox.showerror("Error", "No character loaded")
                return

            # Create backup
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_applying_preset_{self.current_preset['id']}",
                    operation="apply_community_preset",
                    save=save_file,
                )

            # Apply preset using CharacterPresets
            success = self.manager.apply_preset_to_character(
                preset_data, character_presets
            )

            if not success:
                messagebox.showerror("Error", "Failed to apply preset")
                return

            # Save
            save_file.recalculate_checksums()
            save_file.to_file(save_path)

            messagebox.showinfo(
                "Success",
                f"Applied preset '{self.current_preset['name']}'!\n\n"
                f"Reload the save file to see changes in the tool.",
            )

            self.dialog.destroy()
            self.appearance_tab.reload_save()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply preset:\n{str(e)}")
            import traceback

            traceback.print_exc()
