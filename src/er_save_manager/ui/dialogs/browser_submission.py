"""
Browser-based preset submission with automatic image packaging.

Creates a ZIP file with properly named images that user can attach to GitHub.
Automation extracts and identifies images automatically.
"""

import json
import tempfile
import urllib.parse
import webbrowser
import zipfile
from pathlib import Path
from tkinter import messagebox


def submit_preset_via_browser(
    preset_name: str,
    author: str,
    description: str,
    tags: str,
    appearance_data: dict,
    face_image_path: str | None = None,
    body_image_path: str | None = None,
    preview_image_path: str | None = None,
    repo_owner: str = "Hapfel1",
    repo_name: str = "er-character-presets",
) -> tuple[bool, str | None]:
    """
    Submit preset by opening GitHub with pre-filled data and packaged images.

    Creates a ZIP file with properly named images that user just drags into GitHub.
    No manual labeling needed!

    Args:
        preset_name: Name of preset
        author: Author name
        description: Preset description
        tags: Comma-separated tags
        appearance_data: Appearance JSON dict
        face_image_path: Path to face screenshot (REQUIRED)
        body_image_path: Path to body screenshot (REQUIRED)
        preview_image_path: Optional preview image path
        repo_owner: Repository owner
        repo_name: Repository name

    Returns:
        (success: bool, submission_url: str | None) - Returns the submission URL as fallback
    """
    try:
        # Validate images - both face AND body required
        if not face_image_path or not body_image_path:
            messagebox.showerror(
                "Images Required",
                "Both face AND body screenshots are required!\n\n"
                "Please select both images before submitting.",
            )
            return False, None

        # Create ZIP with images
        zip_path = _create_image_zip(
            preset_name,
            face_image_path,
            body_image_path,
            preview_image_path,
        )

        # Create issue body
        issue_body = _create_issue_body(
            preset_name,
            author,
            description,
            tags,
            appearance_data,
            zip_path,
        )

        # Create issue title
        issue_title = f"[Preset Submission] {preset_name}"

        # Build URL with query parameters
        params = {
            "title": issue_title,
            "labels": "preset-submission",
            "body": issue_body,
        }

        query_string = urllib.parse.urlencode(params, safe="")
        url = f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"

        # Check URL length
        if len(url) > 8000:
            # Use compact JSON
            issue_body = _create_compact_issue_body(
                preset_name, author, description, tags, appearance_data, zip_path
            )
            params["body"] = issue_body
            query_string = urllib.parse.urlencode(params, safe="")
            url = (
                f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"
            )

        # Open browser
        webbrowser.open(url)

        # Show success dialog with ZIP info
        show_submission_success_dialog(preset_name, zip_path)

        return True, url

    except Exception as e:
        print(f"Failed to prepare submission: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def _create_image_zip(
    preset_name: str,
    face_image_path: str | None,
    body_image_path: str | None,
    preview_image_path: str | None,
) -> str:
    """
    Create ZIP file with properly named images.

    ZIP structure:
    - preset_images.zip
      - face.png (or .jpg)
      - body.png (or .jpg)
      - preview.png (or .jpg, optional)

    Returns:
        Path to created ZIP file
    """
    # Create temp directory for output
    output_dir = Path(tempfile.gettempdir()) / "er_preset_submissions"
    output_dir.mkdir(exist_ok=True)

    # Clean preset name for filename
    safe_name = "".join(c for c in preset_name if c.isalnum() or c in (" ", "-", "_"))
    safe_name = safe_name.strip().replace(" ", "_")

    zip_filename = f"{safe_name}_images.zip"
    zip_path = output_dir / zip_filename

    # Create ZIP file
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        if face_image_path:
            src_path = Path(face_image_path)
            ext = src_path.suffix  # Keep original extension
            zipf.write(src_path, f"face{ext}")

        if body_image_path:
            src_path = Path(body_image_path)
            ext = src_path.suffix
            zipf.write(src_path, f"body{ext}")

        if preview_image_path:
            src_path = Path(preview_image_path)
            ext = src_path.suffix
            zipf.write(src_path, f"preview{ext}")

    return str(zip_path)


def _create_issue_body(
    preset_name: str,
    author: str,
    description: str,
    tags: str,
    appearance_data: dict,
    zip_path: str | None,
) -> str:
    """Create formatted issue body with ZIP instructions."""

    # Use formatted JSON for readability
    appearance_json = json.dumps(appearance_data, indent=2)

    body = f"""**Preset Name:** {preset_name}
**Author:** {author}
**Tags:** {tags}

**Description:**
{description}

---

### 📸 Images

"""

    if zip_path:
        zip_filename = Path(zip_path).name
        body += f"""**Image package ready!**

Your images have been packaged into: `{zip_filename}`

**To attach:**
1. Drag the ZIP file into the text box below
2. GitHub will upload it automatically
3. That's it!

The automation will extract and use the images automatically.

"""
    else:
        body += """No images selected.

You can still attach images manually if you have them:
- Name them: `face.png`, `body.png`, `preview.png`
- Put them in a ZIP file
- Drag the ZIP into the text box

"""

    body += "---\n\n"

    # Add appearance JSON
    body += """### Appearance Data

<details>
<summary>Click to expand appearance JSON</summary>

```json
"""
    body += appearance_json
    body += """
```

</details>

---

**Submitted via ER Save Manager Preset Browser**
"""

    return body


def _create_compact_issue_body(
    preset_name: str,
    author: str,
    description: str,
    tags: str,
    appearance_data: dict,
    zip_path: str | None,
) -> str:
    """Create compact issue body to avoid URL length limits."""

    # Compact JSON
    appearance_json = json.dumps(appearance_data, separators=(",", ":"))

    body = f"""**Preset Name:** {preset_name}
**Author:** {author}
**Tags:** {tags}

**Description:**
{description}

---

### 📸 Images
"""

    if zip_path:
        zip_filename = Path(zip_path).name
        body += f"""
Drag `{zip_filename}` into this text box.
"""
    else:
        body += "No images provided."

    body += f"""

---

### Appearance Data

```json
{appearance_json}
```

---

**Submitted via ER Save Manager**
"""

    return body


def show_submission_success_dialog(preset_name: str, zip_path: str):
    """Show success message with ZIP file location and open file explorer."""
    import platform
    import subprocess

    import customtkinter as ctk

    from er_save_manager.ui.utils import force_render_dialog

    # Create custom dialog
    dialog = ctk.CTkToplevel()
    dialog.title("Submission Ready")
    dialog.geometry("900x700")
    dialog.resizable(False, False)

    # Center on screen
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    # Make it stay on top
    dialog.attributes("-topmost", True)

    # Force rendering on Linux
    force_render_dialog(dialog)

    dialog.grab_set()  # ensure this dialog owns the grab so buttons remain clickable

    main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    main_frame.pack(fill=ctk.BOTH, expand=True, padx=30, pady=30)

    # Title
    title = ctk.CTkLabel(
        main_frame,
        text="✅ Preset Ready to Submit!",
        font=("Segoe UI", 20, "bold"),
    )
    title.pack(pady=(0, 20))

    # ZIP info
    zip_filename = Path(zip_path).name

    info = ctk.CTkLabel(
        main_frame,
        text="📦 Your images have been packaged:",
        font=("Segoe UI", 14),
        justify=ctk.CENTER,
    )
    info.pack(pady=(0, 8))

    zip_label = ctk.CTkLabel(
        main_frame,
        text=zip_filename,
        font=("Segoe UI", 13, "bold"),
        text_color=("#2563eb", "#60a5fa"),
    )
    zip_label.pack(pady=(0, 25))

    # Info box
    info_box = ctk.CTkFrame(
        main_frame, fg_color=("#f0f4f8", "#1e2839"), corner_radius=10
    )
    info_box.pack(fill=ctk.BOTH, expand=True, padx=0, pady=(0, 20))

    ctk.CTkLabel(
        info_box,
        text="Your browser has opened to GitHub.",
        font=("Segoe UI", 13),
        justify=ctk.LEFT,
    ).pack(anchor=ctk.W, padx=20, pady=(15, 12))

    ctk.CTkLabel(
        info_box,
        text="Next steps:",
        font=("Segoe UI", 12, "bold"),
        justify=ctk.LEFT,
    ).pack(anchor=ctk.W, padx=20, pady=(0, 10))

    instructions_text = """1. Click 'Open Folder' below
2. Drag the ZIP file into GitHub's text box
3. Click the green 'Create new issue' button
4. Wait for maintainer to review and approve
5. You'll be notified when it's added!"""

    ctk.CTkLabel(
        info_box,
        text=instructions_text,
        justify=ctk.LEFT,
        font=("Segoe UI", 12),
        text_color=("#4b5563", "#d0d8e0"),
    ).pack(anchor=ctk.W, padx=20, pady=(0, 15))

    # Buttons frame
    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(fill=ctk.X, pady=(0, 0))

    def open_folder():
        """Open file explorer to ZIP location and select file."""
        system = platform.system()

        try:
            if system == "Windows":
                # Open explorer and select the file - use absolute path
                abs_path = str(Path(zip_path).resolve())
                subprocess.run(["explorer", f"/select,{abs_path}"], shell=False)
            elif system == "Darwin":  # macOS
                # Open Finder and select the file
                subprocess.run(["open", "-R", str(zip_path)])
            else:  # Linux
                # Open file manager to directory
                zip_dir = str(Path(zip_path).parent)
                subprocess.run(["xdg-open", zip_dir])
        except Exception as e:
            print(f"Failed to open file explorer: {e}")

    # Large "Open Folder" button
    open_btn = ctk.CTkButton(
        button_frame,
        text="📁 Open Folder",
        command=open_folder,
        width=200,
        height=40,
        font=("Segoe UI", 13),
    )
    open_btn.pack(side=ctk.LEFT, padx=(0, 12))

    # Close button
    close_btn = ctk.CTkButton(
        button_frame,
        text="Close",
        command=dialog.destroy,
        width=150,
        height=40,
        font=("Segoe UI", 13),
    )
    close_btn.pack(side=ctk.LEFT)

    # Show path at bottom (for user reference)
    path_label = ctk.CTkLabel(
        main_frame,
        text="ZIP Location (for your reference):",
        font=("Segoe UI", 12, "bold"),
    )
    path_label.pack(anchor=ctk.W, pady=(20, 8))

    path_display = ctk.CTkLabel(
        main_frame,
        text=str(zip_path),
        font=("Segoe UI", 12),
        text_color=("#666666", "#999999"),
        wraplength=800,
        justify=ctk.LEFT,
    )
    path_display.pack(anchor=ctk.W)
