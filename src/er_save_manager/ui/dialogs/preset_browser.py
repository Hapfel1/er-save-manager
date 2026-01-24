"""Enhanced preset browser with 15 slots and improved contribution."""

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.preset_manager import PresetManager

try:
    from PIL import Image, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class EnhancedPresetBrowser:
    """Enhanced preset browser with Browse and Contribute tabs."""

    # Constants
    NUM_SLOTS = 15  # Elden Ring has 15 character slots

    def __init__(self, parent, appearance_tab):
        """Initialize enhanced preset browser."""
        self.parent = parent
        self.appearance_tab = appearance_tab
        self.manager = PresetManager()
        self.current_preset = None
        self.all_presets = []
        self.filtered_presets = []
        self.preset_widgets = []

        # Contribution data
        self.face_image_path = None
        self.body_image_path = None
        self.preview_image_path = None

    def show(self):
        """Show enhanced preset browser with tabs."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Community Character Presets")
        self.dialog.geometry("1200x850")
        self.dialog.transient(self.parent)

        # Cleanup on close
        def on_close():
            # Unbind mousewheel
            if hasattr(self, '_mousewheel_unbind'):
                try:
                    self._mousewheel_unbind(None)
                except Exception:
                    pass
            self.dialog.destroy()

        self.dialog.protocol("WM_DELETE_WINDOW", on_close)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self.browse_tab = ttk.Frame(self.notebook)
        self.contribute_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.browse_tab, text="Browse Presets")
        self.notebook.add(self.contribute_tab, text="Contribute Preset")

        # Setup both tabs
        self.setup_browse_tab()
        self.setup_contribute_tab()

        # Load presets
        self.refresh_presets()

    def setup_browse_tab(self):
        """Setup the browse presets tab."""
        main_frame = ttk.Frame(self.browse_tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title and controls
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            top_frame,
            text="Browse Community Presets",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Button(top_frame, text="Refresh", command=self.refresh_presets).pack(
            side=tk.RIGHT, padx=5
        )

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
            values=["Recent", "Name A-Z"],
            state="readonly",
            width=15,
        )
        sort_combo.pack(side=tk.LEFT, padx=5)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        # Split view: Grid + Preview
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: Grid
        grid_frame = ttk.LabelFrame(paned, text="Available Presets", padding=10)
        paned.add(grid_frame, weight=1)

        canvas = tk.Canvas(grid_frame, highlightthickness=0, bg="white")
        scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.grid_container = ttk.Frame(canvas)

        self.grid_container.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window(
            (0, 0), window=self.grid_container, anchor="nw"
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", on_canvas_configure)

        # Enable mousewheel scrolling ONLY when mouse is over canvas
        def on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Store canvas reference for resetting scroll position
        self.preset_canvas = canvas

        # Store mousewheel unbind function for cleanup
        self._mousewheel_unbind = unbind_mousewheel

        # Right: Preview + Slot Selection
        preview_frame = ttk.LabelFrame(paned, text="Preview", padding=10)
        paned.add(preview_frame, weight=1)

        self.preview_label = ttk.Label(preview_frame, text="Select a preset")
        self.preview_label.pack(pady=10)

        self.details_frame = ttk.Frame(preview_frame)
        self.details_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Slot selection for applying preset
        slot_frame = ttk.LabelFrame(preview_frame, text="Apply To", padding=10)
        slot_frame.pack(fill=tk.X, pady=10)

        ttk.Label(slot_frame, text="Preset Slot:").pack(side=tk.LEFT, padx=5)
        self.target_slot_var = tk.StringVar(value="Slot 1")
        slot_combo = ttk.Combobox(
            slot_frame,
            textvariable=self.target_slot_var,
            values=[f"Slot {i + 1}" for i in range(5)],  # Only 5 preset slots
            state="readonly",
            width=10,
        )
        slot_combo.pack(side=tk.LEFT, padx=5)

        self.apply_button = ttk.Button(
            slot_frame,
            text="Apply to Selected Slot",
            command=self.apply_to_slot,
            state=tk.DISABLED,
        )
        self.apply_button.pack(side=tk.LEFT, padx=10)

        # Add info label
        info_label = ttk.Label(
            slot_frame,
            text="⚠ Applies to currently selected character",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        info_label.pack(side=tk.LEFT, padx=5)

        # Status
        self.status_var = tk.StringVar(value="Loading presets...")
        ttk.Label(main_frame, textvariable=self.status_var).pack(pady=5)

    def setup_contribute_tab(self):
        """Setup the contribute preset tab with 2-column layout."""
        main_frame = ttk.Frame(self.contribute_tab, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(
            main_frame,
            text="Contribute Your Character Preset",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 10))

        # Instructions
        instructions = """Submit your character appearance to the community database!

✅ Submission creates an issue automatically
✅ Maintainer will review and merge your preset
✅ You'll be notified when it's approved

Just fill the form and click Submit!"""

        ttk.Label(main_frame, text=instructions, justify=tk.CENTER, font=("Segoe UI", 9)).pack(pady=(0, 15))

        # Create 2-column layout
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # LEFT COLUMN
        left_column = ttk.Frame(content_frame)
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Character slot selection
        slot_section = ttk.LabelFrame(
            left_column, text="1. Select Character", padding=10
        )
        slot_section.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(slot_section, text="Choose which character slot to export:").pack(
            anchor=tk.W, pady=(0, 5)
        )

        # Create 3 rows of 5 slots each
        self.contrib_slot_var = tk.StringVar(value="Slot 1")
        for row in range(3):
            slot_row = ttk.Frame(slot_section)
            slot_row.pack(fill=tk.X, pady=2)
            for col in range(5):
                slot_num = row * 5 + col + 1
                if slot_num <= self.NUM_SLOTS:
                    ttk.Radiobutton(
                        slot_row,
                        text=f"Slot {slot_num}",
                        variable=self.contrib_slot_var,
                        value=f"Slot {slot_num}",
                    ).pack(side=tk.LEFT, padx=5)

        # Images section - REQUIRED
        images_section = ttk.LabelFrame(
            left_column, text="2. Add Images (Required)", padding=10
        )
        images_section.pack(fill=tk.X, pady=(0, 10))

        # Helper text
        ttk.Label(
            images_section,
            text="Both face AND body screenshots are required!",
            font=("Segoe UI", 8, "bold"),
            foreground="red",
        ).pack(anchor=tk.W, pady=(0, 10))

        # Face image
        face_frame = ttk.Frame(images_section)
        face_frame.pack(fill=tk.X, pady=5)
        ttk.Label(face_frame, text="Face Screenshot:", width=20).pack(
            side=tk.LEFT, padx=5
        )
        self.face_image_label = ttk.Label(face_frame, text="No file selected", width=25)
        self.face_image_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(face_frame, text="Browse...", command=self.select_face_image).pack(
            side=tk.LEFT
        )

        # Body image
        body_frame = ttk.Frame(images_section)
        body_frame.pack(fill=tk.X, pady=5)
        ttk.Label(body_frame, text="Full Body Screenshot:", width=20).pack(
            side=tk.LEFT, padx=5
        )
        self.body_image_label = ttk.Label(body_frame, text="No file selected", width=25)
        self.body_image_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(body_frame, text="Browse...", command=self.select_body_image).pack(
            side=tk.LEFT
        )

        # Preview image (optional - uses face if not provided)
        preview_frame = ttk.Frame(images_section)
        preview_frame.pack(fill=tk.X, pady=5)
        ttk.Label(preview_frame, text="Preview Thumbnail:", width=20).pack(
            side=tk.LEFT, padx=5
        )
        self.preview_image_label = ttk.Label(preview_frame, text="Optional (uses face)", width=25, foreground="gray")
        self.preview_image_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(
            preview_frame, text="Browse...", command=self.select_preview_image
        ).pack(side=tk.LEFT)

        # RIGHT COLUMN
        right_column = ttk.Frame(content_frame)
        right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Metadata section
        meta_section = ttk.LabelFrame(
            right_column, text="3. Preset Information", padding=10
        )
        meta_section.pack(fill=tk.BOTH, expand=True)

        # Name
        name_frame = ttk.Frame(meta_section)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Preset Name:", width=15).pack(side=tk.LEFT, padx=5)
        self.preset_name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.preset_name_var, width=30).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )

        # Author
        author_frame = ttk.Frame(meta_section)
        author_frame.pack(fill=tk.X, pady=5)
        ttk.Label(author_frame, text="Your Name:", width=15).pack(
            side=tk.LEFT, padx=5
        )
        self.author_var = tk.StringVar()
        ttk.Entry(author_frame, textvariable=self.author_var, width=30).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )

        # Description
        desc_frame = ttk.Frame(meta_section)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(desc_frame, text="Description:", width=15).pack(
            side=tk.LEFT, padx=5, anchor=tk.N
        )
        self.description_text = tk.Text(desc_frame, width=30, height=5, wrap=tk.WORD)
        self.description_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Tags - CHECKBOXES
        tags_section = ttk.LabelFrame(meta_section, text="Tags (select all that apply)", padding=5)
        tags_section.pack(fill=tk.X, pady=(10, 5))

        # Predefined tags
        self.tag_vars = {}
        available_tags = [
            "male", "female", "cosplay", "original",
            "fantasy", "realistic", "anime", "meme",
            "elder", "young"
        ]

        # Create 2 columns of checkboxes
        tags_container = ttk.Frame(tags_section)
        tags_container.pack(fill=tk.X)

        left_tags = ttk.Frame(tags_container)
        left_tags.pack(side=tk.LEFT, fill=tk.X, expand=True)

        right_tags = ttk.Frame(tags_container)
        right_tags.pack(side=tk.LEFT, fill=tk.X, expand=True)

        for i, tag in enumerate(available_tags):
            var = tk.BooleanVar()
            self.tag_vars[tag] = var
            container = left_tags if i < 6 else right_tags
            ttk.Checkbutton(container, text=tag, variable=var).pack(anchor=tk.W, pady=1)

        # Custom tags entry (optional)
        custom_tags_frame = ttk.Frame(meta_section)
        custom_tags_frame.pack(fill=tk.X, pady=5)
        ttk.Label(custom_tags_frame, text="Custom Tags:", width=15, foreground="gray").pack(side=tk.LEFT, padx=5)
        self.custom_tags_var = tk.StringVar()
        ttk.Entry(custom_tags_frame, textvariable=self.custom_tags_var, width=30).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )
        ttk.Label(custom_tags_frame, text="(comma-separated)", font=("Segoe UI", 7), foreground="gray").pack(
            side=tk.LEFT
        )

        # Submit section
        submit_frame = ttk.Frame(main_frame)
        submit_frame.pack(fill=tk.X, pady=(15, 0))

        self.submit_button = ttk.Button(
            submit_frame,
            text="Submit Preset",
            command=self.submit_contribution,
        )
        self.submit_button.pack()

        ttk.Label(
            submit_frame,
            text="After submission, wait for maintainer approval. You'll be notified via the GitHub issue!",
            font=("Segoe UI", 8),
            foreground="gray",
        ).pack(pady=5)

    def select_face_image(self):
        """Select face image."""
        path = filedialog.askopenfilename(
            title="Select Face Screenshot",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.face_image_path = path
            self.face_image_label.configure(text=Path(path).name)

    def select_body_image(self):
        """Select body image."""
        path = filedialog.askopenfilename(
            title="Select Full Body Screenshot",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.body_image_path = path
            self.body_image_label.configure(text=Path(path).name)

    def select_preview_image(self):
        """Select preview image."""
        path = filedialog.askopenfilename(
            title="Select Preview Thumbnail",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.preview_image_path = path
            self.preview_image_label.configure(text=Path(path).name)

    def submit_contribution(self):
        """Submit contribution by opening pre-filled GitHub issue."""
        # Validate inputs
        preset_name = self.preset_name_var.get().strip()
        if not preset_name:
            messagebox.showerror("Error", "Preset name is required")
            return

        author = self.author_var.get().strip()
        if not author:
            messagebox.showerror("Error", "Author name is required")
            return

        description = self.description_text.get("1.0", tk.END).strip()
        if not description:
            messagebox.showerror("Error", "Description is required")
            return

        # Collect tags from checkboxes
        selected_tags = [tag for tag, var in self.tag_vars.items() if var.get()]

        # Add custom tags if provided
        custom_tags = self.custom_tags_var.get().strip()
        if custom_tags:
            selected_tags.extend([t.strip() for t in custom_tags.split(",") if t.strip()])

        if not selected_tags:
            messagebox.showerror("Error", "At least one tag is required")
            return

        tags = ", ".join(selected_tags)

        # Get slot index
        slot_str = self.contrib_slot_var.get()
        slot_index = int(slot_str.split()[1]) - 1

        try:
            # Export character appearance
            save_file = self.appearance_tab.get_save_file()
            if not save_file:
                messagebox.showerror("Error", "No save file loaded")
                return

            if slot_index >= self.NUM_SLOTS or slot_index >= len(save_file.characters):
                messagebox.showerror(
                    "Error", f"Character slot {slot_index + 1} doesn't exist"
                )
                return

            # Get character presets for this slot

            presets_data = save_file.get_character_presets()
            if not presets_data or slot_index >= len(presets_data.presets):
                messagebox.showerror(
                    "Error", f"Character slot {slot_index + 1} preset doesn't exist"
                )
                return

            face_preset = presets_data.presets[slot_index]
            appearance_data = face_preset.to_dict()

            # Submit via browser
            from .browser_submission import submit_preset_via_browser

            success = submit_preset_via_browser(
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
                messagebox.showerror(
                    "Error",
                    "Failed to open browser.\n\nPlease check your default browser settings.",
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create submission:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def create_github_issue_body(
        self, preset_name, author, description, tags, appearance_data
    ):
        """Create GitHub issue body with all data."""
        # Include image paths in the issue body for maintainer
        image_paths = f"""
        ### Image Paths (for maintainer)
        Face: `{self.face_image_path if self.face_image_path else "Not provided"}`
        Body: `{self.body_image_path if self.body_image_path else "Not provided"}`
        Preview: `{self.preview_image_path if self.preview_image_path else "Not provided"}`
        """

        issue_body = f"""**Preset Name:** {preset_name}
**Author:** {author}
**Tags:** {tags}

**Description:**
{description}

---

{image_paths}

---

### Appearance Data
<details>
<summary>Click to expand appearance JSON</summary>

```json
{json.dumps(appearance_data, indent=2)}
```
</details>

---

**Submitted via ER Save Manager Preset Browser**
**User does not need GitHub account - automated submission**
"""
        return issue_body

    def create_github_issue_automatic(
        self, preset_name, author, description, tags, appearance_data
    ):
        """
        Create GitHub issue automatically without user interaction.

        Returns:
            (success: bool, message: str)
        """
        import urllib.error
        import urllib.request

        try:
            # Create issue body
            issue_body = self.create_github_issue_body(
                preset_name, author, description, tags, appearance_data
            )

            # GitHub API endpoint
            repo_owner = "Hapfel1"
            repo_name = "er-character-presets"
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

            # Create issue data
            issue_data = {
                "title": f"[Preset Submission] {preset_name}",
                "body": issue_body,
                "labels": ["preset-submission"],
            }

            # Make API request
            req = urllib.request.Request(
                url,
                data=json.dumps(issue_data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ER-Save-Manager-Preset-Browser/1.0",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                issue_url = result.get("html_url")
                issue_number = result.get("number")

                return (
                    True,
                    f"Success!\n\nIssue URL: {issue_url}\nIssue Number: #{issue_number}",
                )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else "Unknown error"
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get("message", error_body)
            except Exception:
                error_msg = error_body

            return False, f"GitHub API Error ({e.code}): {error_msg}"

        except Exception as e:
            return False, f"Failed to create issue: {str(e)}"

    def clear_contribution_form(self):
        """Clear the contribution form."""
        self.face_image_path = None
        self.body_image_path = None
        self.preview_image_path = None
        self.face_image_label.configure(text="No file selected")
        self.body_image_label.configure(text="No file selected")
        self.preview_image_label.configure(text="Uses face if not set")
        self.preset_name_var.set("")
        self.author_var.set("")
        self.description_text.delete("1.0", tk.END)
        self.tags_var.set("")

    # Browse tab methods
    def refresh_presets(self):
        """Fetch and display presets."""
        self.status_var.set("Fetching presets from GitHub...")
        self.dialog.update()

        try:
            index_data = self.manager.fetch_index(force_refresh=True)
            self.all_presets = index_data.get("presets", [])

            if not self.all_presets:
                self.status_var.set("No presets available yet")
                return

            self.status_var.set(f"Loaded {len(self.all_presets)} presets")
            self.apply_filters()
        except Exception as e:
            self.status_var.set(f"Error loading presets: {str(e)}")
            import traceback
            traceback.print_exc()

    def apply_filters(self):
        """Apply search and filter."""
        search_term = self.search_var.get().lower()
        filter_tag = self.filter_var.get().lower()

        self.filtered_presets = []
        for preset in self.all_presets:
            if search_term:
                name_match = search_term in preset["name"].lower()
                author_match = search_term in preset.get("author", "").lower()
                if not (name_match or author_match):
                    continue

            if filter_tag != "all":
                tags = [t.lower() for t in preset.get("tags", [])]
                if filter_tag not in tags:
                    continue

            self.filtered_presets.append(preset)

        # Sort
        sort_by = self.sort_var.get()
        if sort_by == "Recent":
            self.filtered_presets.sort(key=lambda p: p.get("created", ""), reverse=True)
        elif sort_by == "Name A-Z":
            self.filtered_presets.sort(key=lambda p: p["name"].lower())

        self.display_presets()

    def display_presets(self):
        """Display presets in grid."""
        for widget in self.preset_widgets:
            widget.destroy()
        self.preset_widgets = []

        # Reset scroll to top
        if hasattr(self, 'preset_canvas'):
            self.preset_canvas.yview_moveto(0)

        if not self.filtered_presets:
            no_results = ttk.Label(
                self.grid_container, text="No presets match your search"
            )
            no_results.grid(row=0, column=0, pady=50)
            self.preset_widgets.append(no_results)
            return

        row, col = 0, 0
        for preset in self.filtered_presets:
            card = self.create_preset_card(preset)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self.preset_widgets.append(card)

            col += 1
            if col >= 3:
                col = 0
                row += 1

        for i in range(3):
            self.grid_container.columnconfigure(i, weight=1)

    def create_preset_card(self, preset):
        """Create preset card widget."""
        frame = ttk.Frame(self.grid_container, relief=tk.RAISED, borderwidth=1)

        thumb_label = ttk.Label(frame, text="[Loading...]", width=20)
        thumb_label.pack(pady=5)

        if HAS_PIL:
            self.load_thumbnail(preset, thumb_label)

        name_label = ttk.Label(
            frame, text=preset["name"], font=("Segoe UI", 9, "bold"), wraplength=150
        )
        name_label.pack(pady=2)

        author_label = ttk.Label(
            frame,
            text=f"by {preset.get('author', 'Unknown')}",
            font=("Segoe UI", 8),
            foreground="gray",
        )
        author_label.pack()

        for widget in [frame, thumb_label, name_label, author_label]:
            widget.bind("<Button-1>", lambda e, p=preset: self.preview_preset(p))
            widget.configure(cursor="hand2")

        return frame

    def load_thumbnail(self, preset, label):
        """Load thumbnail image."""
        preset_id = preset["id"]
        cached = self.manager.get_cached_preset(preset_id)

        if cached and "screenshot_path" in cached:
            try:
                img = Image.open(cached["screenshot_path"])
                img.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(img)
                label.configure(image=photo, text="")
                label.image = photo
                return
            except Exception:
                pass

        label.configure(text="[No Image]")

    def preview_preset(self, preset):
        """Show preview of selected preset with face and body screenshots."""
        self.current_preset = preset
        self.status_var.set(f"Loading {preset['name']}...")
        self.dialog.update()

        cached = self.manager.get_cached_preset(preset["id"])
        if not cached:
            cached = self.manager.download_preset(preset["id"], preset)

        if not cached:
            messagebox.showerror("Error", "Failed to download preset")
            return

        # Clear all previous preview content
        for widget in self.preview_label.winfo_children():
            widget.destroy()
        self.preview_label.configure(image="", text="")

        # Display face and body screenshots side by side
        if HAS_PIL:
            # Try to load face and body images
            face_img = None
            body_img = None

            # Check cache first
            cache_dir = self.manager.cache_dir / preset["id"]

            if cache_dir.exists():
                list(cache_dir.glob("*"))

                for img_file in cache_dir.glob("*_face.*"):
                    try:
                        face_img = Image.open(img_file)
                        face_img.thumbnail((250, 250))
                        break
                    except Exception:
                        pass

                for img_file in cache_dir.glob("*_body.*"):
                    try:
                        body_img = Image.open(img_file)
                        body_img.thumbnail((250, 250))
                        break
                    except Exception:
                        pass

            # If not in cache, try to download from URLs in preset metadata
            if not face_img and "face_url" in preset:
                try:
                    face_path = self.manager.download_image(preset["id"], preset["face_url"], "_face")
                    if face_path and face_path.exists():
                        face_img = Image.open(face_path)
                        face_img.thumbnail((250, 250))
                except Exception:
                    pass

            if not body_img and "body_url" in preset:
                try:
                    body_path = self.manager.download_image(preset["id"], preset["body_url"], "_body")
                    if body_path and body_path.exists():
                        body_img = Image.open(body_path)
                        body_img.thumbnail((250, 250))
                except Exception:
                    pass


            # If we have separate face/body images, show them side by side
            if face_img or body_img:
                img_frame = ttk.Frame(self.preview_label)
                img_frame.pack(pady=10)

                if face_img:
                    face_col = ttk.Frame(img_frame)
                    face_col.pack(side=tk.LEFT, padx=10)

                    face_photo = ImageTk.PhotoImage(face_img)
                    face_label = ttk.Label(face_col, image=face_photo)
                    face_label.image = face_photo  # Keep reference
                    face_label.pack()

                    ttk.Label(face_col, text="Face", font=("Segoe UI", 9, "bold")).pack(pady=5)

                if body_img:
                    body_col = ttk.Frame(img_frame)
                    body_col.pack(side=tk.LEFT, padx=10)

                    body_photo = ImageTk.PhotoImage(body_img)
                    body_label = ttk.Label(body_col, image=body_photo)
                    body_label.image = body_photo  # Keep reference
                    body_label.pack()

                    ttk.Label(body_col, text="Body", font=("Segoe UI", 9, "bold")).pack(pady=5)

            # If no separate images, use main screenshot
            elif "screenshot_path" in cached:
                try:
                    img = Image.open(cached["screenshot_path"])
                    img.thumbnail((300, 300))
                    photo = ImageTk.PhotoImage(img)
                    img_label = ttk.Label(self.preview_label, image=photo)
                    img_label.image = photo  # Keep reference
                    img_label.pack(pady=10)
                except Exception as e:
                    print(f"Error loading screenshot: {e}")
                    ttk.Label(self.preview_label, text="[Preview not available]").pack(pady=10)
            else:
                ttk.Label(self.preview_label, text="[No preview available]").pack(pady=10)

        # Display details
        for widget in self.details_frame.winfo_children():
            widget.destroy()

        ttk.Label(
            self.details_frame, text=preset["name"], font=("Segoe UI", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(
            self.details_frame, text=f"Author: {preset.get('author', 'Unknown')}"
        ).pack(anchor=tk.W, pady=2)

        ttk.Label(
            self.details_frame, text=f"Tags: {', '.join(preset.get('tags', []))}"
        ).pack(anchor=tk.W, pady=2)

        if "description" in preset:
            ttk.Label(
                self.details_frame,
                text=preset["description"],
                wraplength=300,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(10, 5))

        # Enable apply button
        self.apply_button.configure(state=tk.NORMAL)
        self.status_var.set(f"Viewing {preset['name']}")

        self.apply_button.configure(state=tk.NORMAL)
        self.status_var.set(f"Previewing: {preset['name']}")

    def apply_to_slot(self):
        """Apply current preset to selected slot."""
        if not self.current_preset:
            return

        # Get target slot (convert from 1-based to 0-based)
        slot_str = self.target_slot_var.get()
        target_slot = int(slot_str.split()[1]) - 1

        # Get current character from appearance tab
        try:
            current_char = self.appearance_tab.get_current_character_slot()
            char_name = f"Character {current_char + 1}"
        except Exception:
            char_name = "the current character"

        if not messagebox.askyesno(
            "Apply Preset",
            f"Apply '{self.current_preset['name']}' to {char_name}'s {slot_str}?\n\n"
            f"This will add the preset to that character's appearance menu.\n"
            f"A backup will be created automatically.",
        ):
            return

        try:
            preset_data = self.manager.get_cached_preset(self.current_preset["id"])
            if not preset_data:
                preset_data = self.manager.download_preset(
                    self.current_preset["id"], self.current_preset
                )

            if not preset_data or "appearance" not in preset_data:
                messagebox.showerror("Error", "Invalid preset data")
                return

            save_file = self.appearance_tab.get_save_file()
            save_path = self.appearance_tab.get_save_path()

            if not save_file:
                messagebox.showerror("Error", "No save file loaded")
                return

            if target_slot >= len(save_file.characters):
                messagebox.showerror(
                    "Error", f"Character slot {target_slot + 1} doesn't exist in save"
                )
                return

            # Backup
            if save_path:
                manager = BackupManager(Path(save_path))
                manager.create_backup(
                    description=f"before_applying_preset_to_slot_{target_slot + 1}",
                    operation="apply_community_preset",
                    save=save_file,
                )

            # Import using the SAME method as appearance_tab
            # Pass the appearance data dict directly
            save_file.import_preset(preset_data["appearance"], target_slot)

            # Save
            save_file.recalculate_checksums()
            save_file.to_file(Path(save_path))

            messagebox.showinfo(
                "Success",
                f"Applied '{self.current_preset['name']}' to Preset Slot {target_slot + 1}!\n\n"
                f"The preset is now available in the appearance menu.",
            )

            self.dialog.destroy()

            # Force reload
            if hasattr(self.appearance_tab, 'reload_save') and self.appearance_tab.reload_save:
                self.appearance_tab.reload_save()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply preset:\n{str(e)}")
            import traceback

            traceback.print_exc()


# Backward compatibility
class PresetBrowserDialog:
    """Backward compatibility wrapper."""

    @staticmethod
    def show_coming_soon(parent):
        """Show coming soon dialog."""
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

        ttk.Label(
            main_frame,
            text="COMING SOON",
            font=("Segoe UI", 12, "bold"),
            foreground="orange",
        ).pack(pady=10)

        description = """
Share and download character appearance presets!

Features:
  • Browse community character designs
  • Preview with screenshots
  • Apply to any character slot (1-15)
  • Submit your own creations

Database hosted externally and auto-updates!
        """

        ttk.Label(main_frame, text=description, justify=tk.LEFT).pack(pady=20)
        ttk.Button(main_frame, text="Close", command=dialog.destroy, width=15).pack()
