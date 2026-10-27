"""
Appearance preset sharing via Supabase.

Uses supabase_api (anon key, no authentication). A share code is the row id returned on upload,
copy the code, paste it elsewhere to import.
"""

from __future__ import annotations

from typing import Any

from er_save_manager import supabase_api


def share_preset(payload: dict[str, Any], name: str = "") -> str | None:
    """Upload one or more appearance presets, return the share code (row id), or None on failure."""
    try:
        data = supabase_api.insert(
            "appearance_presets", {"name": name, "payload": payload}
        )
        if data:
            return data[0]["id"]
        return None
    except Exception as e:
        print(f"[AppearanceSharing] Failed to share preset: {e}")
        return None


def fetch_preset(code: str) -> dict[str, Any] | None:
    """Fetch a shared appearance preset payload by its share code."""
    try:
        data = supabase_api.select(
            "appearance_presets", "payload", eq={"id": code.strip()}
        )
        if data:
            return data[0]["payload"]
        return None
    except Exception as e:
        print(f"[AppearanceSharing] Failed to fetch preset '{code}': {e}")
        return None
