"""
Browser-based character submission with automatic metadata packaging.

Creates a ZIP file with .erc + metadata.json + images that user can attach to GitHub.
Automation extracts and identifies files automatically.
"""

import json
import tempfile
import traceback
import urllib.parse
import webbrowser
import zipfile
from pathlib import Path

import customtkinter as ctk


def submit_character_via_browser(
    char_name: str,
    author: str,
    description: str,
    tags: str,
    erc_path: str,
    metadata: dict,
    face_image_path: str | None = None,
    body_image_path: str | None = None,
    preview_image_path: str | None = None,
    repo_owner: str = "Hapfel1",
    repo_name: str = "er-character-library",
) -> tuple[bool, str | None]:
    """
    Submit character by opening GitHub with pre-filled data and packaged files.

    Creates a ZIP file with .erc + metadata.json + images that user just drags into GitHub.
    No manual labeling needed!

    Args:
        char_name: Character name
        author: Author name
        description: Character description
        tags: Comma-separated tags
        erc_path: Path to .erc character file
        metadata: Character metadata dict (auto-extracted from .erc)
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
            print(
                "[Character Submission] Error: Both face and body screenshots are required"
            )
            return (False, None)

        # Create ZIP with .erc + metadata + images
        zip_path = _create_character_zip(
            char_name,
            erc_path,
            metadata,
            face_image_path,
            body_image_path,
            preview_image_path,
        )

        # Create issue body
        issue_body = _create_issue_body(
            char_name,
            author,
            description,
            tags,
            metadata,
            zip_path,
        )

        # Create issue title
        issue_title = f"[Character Submission] {char_name}"

        # Build URL with query parameters
        params = {
            "title": issue_title,
            "labels": "character-submission",
            "body": issue_body,
        }

        query_string = urllib.parse.urlencode(params, safe="")
        url = f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"

        # Check URL length
        if len(url) > 8000:
            print("[Character Submission] URL too long, using compact format")
            issue_body = _create_compact_issue_body(
                char_name, author, description, tags, metadata, zip_path
            )
            params["body"] = issue_body
            query_string = urllib.parse.urlencode(params, safe="")
            url = (
                f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"
            )

        # Open browser
        opened = webbrowser.open_new_tab(url)

        # Show success dialog with ZIP info
        show_submission_success_dialog(char_name, zip_path)

        if not opened:
            return (False, url)

        return (True, url)

    except Exception as e:
        print(f"Failed to prepare character submission: {e}")
        print(
            "If you're seeing this, please report this error to the developer with the details below:"
        )
        traceback.print_exc()
        return (False, None)


def _create_character_zip(
    char_name: str,
    erc_path: str,
    metadata: dict,
    face_image_path: str | None,
    body_image_path: str | None,
    preview_image_path: str | None,
) -> str:
    """
    Create ZIP file with .erc + metadata.json + images.

    ZIP structure:
    - character_package.zip
      - character.erc
      - metadata.json
      - face.png (or .jpg)
      - body.png (or .jpg)
      - preview.png (or .jpg, optional)

    Returns:
        Path to created ZIP file
    """
    # Create temp directory for output
    output_dir = Path(tempfile.gettempdir()) / "er_character_submissions"
    output_dir.mkdir(exist_ok=True)

    # Clean character name for filename
    safe_name = "".join(c for c in char_name if c.isalnum() or c in (" ", "-", "_"))
    safe_name = safe_name.strip().replace(" ", "_")

    zip_filename = f"{safe_name}_package.zip"
    zip_path = output_dir / zip_filename

    # Create ZIP file
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add .erc file
        zipf.write(erc_path, "character.erc")

        # Add metadata.json
        metadata_json = json.dumps(metadata, indent=2)
        zipf.writestr("metadata.json", metadata_json)

        # Add images
        if face_image_path:
            ext = Path(face_image_path).suffix or ".jpg"
            zipf.write(face_image_path, f"face{ext}")

        if body_image_path:
            ext = Path(body_image_path).suffix or ".jpg"
            zipf.write(body_image_path, f"body{ext}")

        if preview_image_path:
            ext = Path(preview_image_path).suffix or ".jpg"
            zipf.write(preview_image_path, f"preview{ext}")

    return str(zip_path)


def _create_issue_body(
    char_name: str,
    author: str,
    description: str,
    tags: str,
    metadata: dict,
    zip_path: str | None,
) -> str:
    """Create formatted issue body with ZIP instructions."""

    # Extract key metadata for display
    level = metadata.get("level", "?")
    char_class = metadata.get("class", "Unknown")
    ng_plus = metadata.get("ng_plus", 0)
    ng_text = f" (NG+{ng_plus})" if ng_plus > 0 else ""

    body = f"""**Character Name:** {char_name}
**Author:** {author}
**Tags:** {tags}

**Stats:** Level {level} • {char_class}{ng_text}

**Description:**
{description}

---

### 📦 Character Package

"""

    if zip_path:
        zip_filename = Path(zip_path).name
        body += f"""**Attached File:** `{zip_filename}`

**What's inside:**
- `character.erc` - Full character save data
- `metadata.json` - Auto-extracted character info
- `face.jpg` - Face screenshot
- `body.jpg` - Full body screenshot
- `preview.jpg` - Preview thumbnail (optional)

**📌 TO COMPLETE SUBMISSION:**
1. Drag and drop `{zip_filename}` into this text box
2. Wait for upload to complete
3. Click "Submit new issue"

"""
    else:
        body += """⚠️ **Error:** Failed to create package file.

Please attach your character files manually:
- Character .erc file
- Face screenshot
- Body screenshot
- metadata.json (if available)

"""

    body += "---\n\n"

    # Add metadata preview
    body += """### 📊 Character Metadata Preview

<details>
<summary>Click to expand metadata</summary>

```json
"""
    body += json.dumps(metadata, indent=2)
    body += """
```

</details>

---

**Submitted via ER Save Manager Character Browser**
"""

    return body


def _create_compact_issue_body(
    char_name: str,
    author: str,
    description: str,
    tags: str,
    metadata: dict,
    zip_path: str | None,
) -> str:
    """Create compact issue body to avoid URL length limits."""

    level = metadata.get("level", "?")
    char_class = metadata.get("class", "Unknown")

    body = f"""**Character Name:** {char_name}
**Author:** {author}
**Tags:** {tags}
**Stats:** Level {level} • {char_class}

**Description:**
{description}

---

### 📦 Package
"""

    if zip_path:
        body += f"""Attach: `{Path(zip_path).name}`"""
    else:
        body += """Attach character files manually"""

    body += """

---

**Submitted via ER Save Manager**
"""

    return body


def show_submission_success_dialog(char_name: str, zip_path: str):
    """Show success message with ZIP file location and open file explorer."""
    import os
    import platform

    from er_save_manager.ui.utils import force_render_dialog

    # Create custom dialog
    dialog = ctk.CTkToplevel()
    dialog.title("Submission Ready")
    width, height = 900, 600
    dialog.resizable(False, False)

    # Center on screen
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    # Make it stay on top
    dialog.attributes("-topmost", True)

    # Force rendering on Linux
    force_render_dialog(dialog)

    dialog.grab_set()

    main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    main_frame.pack(fill=ctk.BOTH, expand=True, padx=30, pady=30)

    # Title
    title = ctk.CTkLabel(
        main_frame,
        text="✅ Character Ready to Submit!",
        font=("Segoe UI", 20, "bold"),
    )
    title.pack(pady=(0, 20))

    # ZIP info
    zip_filename = Path(zip_path).name

    info = ctk.CTkLabel(
        main_frame,
        text="📦 Your character package has been created:",
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

    instructions_text = """1. Click 'Open Folder' below to find your package
2. Drag the ZIP file into GitHub's text box
3. Wait for the upload to complete
4. Click the green 'Submit new issue' button
5. Wait for maintainer to test and approve
6. You'll be notified when it's published!"""

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
        """Open the folder containing the ZIP file."""
        folder_path = Path(zip_path).parent
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                os.system(f'open "{folder_path}"')
            else:  # Linux
                os.system(f'xdg-open "{folder_path}"')
        except Exception as e:
            print(f"Failed to open folder: {e}")
            # Fallback: just print the path
            print(f"Package location: {folder_path}")

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
        text="Package Location (for your reference):",
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
