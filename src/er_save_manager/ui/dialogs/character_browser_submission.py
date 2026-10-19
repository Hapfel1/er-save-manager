"""
Browser-based character submission with automatic metadata packaging.

Creates a ZIP file with .erc + metadata.json + images that user can attach to GitHub.
Automation extracts and identifies files automatically.
"""

import json
import tempfile
import traceback
import urllib.parse
import zipfile
from pathlib import Path

from er_save_manager.ui.utils import open_folder as utils_open_folder
from er_save_manager.ui.utils import open_url


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

        issue_body = _create_issue_body(
            char_name,
            author,
            description,
            tags,
            metadata,
            zip_path,
        )

        issue_title = f"[Character Submission] {char_name}"

        params = {
            "title": issue_title,
            "labels": "character-submission",
            "body": issue_body,
        }

        query_string = urllib.parse.urlencode(params, safe="")
        url = f"https://github.com/{repo_owner}/{repo_name}/issues/new?{query_string}"

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

        opened = open_url(url)

        show_submission_success_dialog(char_name, zip_path)

        if not opened:
            return (False, url)

        return (True, url)

    except Exception as e:
        print(f"Failed to prepare character submission: {e}")
        print(
            "If you're seeing this, report this error to the developer with the details below:"
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
    output_dir = Path(tempfile.gettempdir()) / "er_character_submissions"
    output_dir.mkdir(exist_ok=True)

    safe_name = "".join(c for c in char_name if c.isalnum() or c in (" ", "-", "_"))
    safe_name = safe_name.strip().replace(" ", "_")

    zip_filename = f"{safe_name}_package.zip"
    zip_path = output_dir / zip_filename

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(erc_path, "character.erc")

        metadata_json = json.dumps(metadata, indent=2)
        zipf.writestr("metadata.json", metadata_json)

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

    level = metadata.get("level", "?")
    char_class = metadata.get("class", "Unknown")
    ng_plus = metadata.get("ng_plus", 0)
    ng_text = f" (NG+{ng_plus})" if ng_plus > 0 else ""

    max_hp = metadata.get("max_hp")
    max_fp = metadata.get("max_fp")
    max_stamina = metadata.get("max_stamina")

    resources_text = ""
    if max_hp or max_fp or max_stamina:
        resources_parts = []
        if max_hp:
            resources_parts.append(f"HP: {max_hp}")
        if max_fp:
            resources_parts.append(f"FP: {max_fp}")
        if max_stamina:
            resources_parts.append(f"Stamina: {max_stamina}")
        resources_text = f"\n**Resources:** {' • '.join(resources_parts)}"

    body = f"""**Character Name:** {char_name}
**Author:** {author}
**Tags:** {tags}

**Stats:** Level {level} • {char_class}{ng_text}{resources_text}

**Description:**
{description}

---

### Character Package

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

**To complete the submission:**
1. Drag and drop `{zip_filename}` into this text box
2. Wait for upload to complete
3. Click "Submit new issue"

"""
    else:
        body += """**Error:** Failed to create package file.

Attach your character files manually:
- Character .erc file
- Face screenshot
- Body screenshot
- metadata.json (if available)

"""

    body += "---\n\n"

    body += """### Character Metadata Preview

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

### Package
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
    from er_save_manager.ui.dialogs.community_dialogs import show_submission_ready

    def open_folder():
        if not utils_open_folder(zip_path):
            print(f"Failed to open folder. Package location: {zip_path}")

    show_submission_ready(
        "Character Ready to Submit",
        "Your character package has been created.",
        zip_path,
        [
            "Click 'Open Folder' below to find your package",
            "Drag the ZIP file into GitHub's text box",
            "Wait for the upload to complete",
            "Click the green 'Submit new issue' button",
            "Wait for maintainer to test and approve",
            "You'll be notified when it's published.",
        ],
        open_folder,
    )
