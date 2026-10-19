"""
Browser-based preset submission with automatic image packaging.

Creates a ZIP file with properly named images that user can attach to GitHub.
Automation extracts and identifies images automatically.
"""

import json
import tempfile
import urllib.parse
import zipfile
from pathlib import Path
from tkinter import messagebox

from er_save_manager.ui.utils import open_folder as utils_open_folder
from er_save_manager.ui.utils import open_url


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
                "Both face AND body screenshots are required.\n\n"
                "Select both images before submitting.",
            )
            return False, None

        zip_path = _create_image_zip(
            preset_name,
            face_image_path,
            body_image_path,
            preview_image_path,
        )

        issue_body = _create_issue_body(
            preset_name,
            author,
            description,
            tags,
            appearance_data,
            zip_path,
        )

        issue_title = f"[Preset Submission] {preset_name}"

        params = {
            "title": issue_title,
            "labels": "preset-submission",
            "body": issue_body,
        }

        query_string = urllib.parse.urlencode(params, safe="")
        url = f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"

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

        open_url(url)

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
    output_dir = Path(tempfile.gettempdir()) / "er_preset_submissions"
    output_dir.mkdir(exist_ok=True)

    safe_name = "".join(c for c in preset_name if c.isalnum() or c in (" ", "-", "_"))
    safe_name = safe_name.strip().replace(" ", "_")

    zip_filename = f"{safe_name}_images.zip"
    zip_path = output_dir / zip_filename

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        if face_image_path:
            src_path = Path(face_image_path)
            ext = src_path.suffix
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

    appearance_json = json.dumps(appearance_data, indent=2)

    body = f"""**Preset Name:** {preset_name}
**Author:** {author}
**Tags:** {tags}

**Description:**
{description}

---

### Images

"""

    if zip_path:
        zip_filename = Path(zip_path).name
        body += f"""**Image package ready**

Your images have been packaged into: `{zip_filename}`

**To attach:**
1. Drag the ZIP file into the text box below
2. GitHub will upload it automatically
3. That's it.

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

    appearance_json = json.dumps(appearance_data, separators=(",", ":"))

    body = f"""**Preset Name:** {preset_name}
**Author:** {author}
**Tags:** {tags}

**Description:**
{description}

---

### Images
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
    from er_save_manager.ui.dialogs.community_dialogs import show_submission_ready

    def open_folder():
        if not utils_open_folder(zip_path):
            print(f"Failed to open file explorer for {zip_path}")

    show_submission_ready(
        "Preset Ready to Submit",
        "Your images have been packaged.",
        zip_path,
        [
            "Click 'Open Folder' below",
            "Drag the ZIP file into GitHub's text box",
            "Click the green 'Create new issue' button",
            "Wait for maintainer to review and approve",
            "You'll be notified when it's added.",
        ],
        open_folder,
    )
