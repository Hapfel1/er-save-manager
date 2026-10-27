"""
Equipment loadout sharing via Supabase.
"""

from __future__ import annotations

from typing import Any

from er_save_manager import supabase_api


def share_loadout(
    payload: dict[str, Any], name: str = "", save_type: str = ""
) -> str | None:
    """Upload a loadout, return its share code (row id), or None on failure."""
    try:
        data = supabase_api.insert(
            "equipment_loadouts",
            {"name": name, "payload": payload, "save_type": save_type},
        )
        if data:
            return data[0]["id"]
        return None
    except Exception as e:
        print(f"[EquipmentSharing] Failed to share loadout: {e}")
        return None


def fetch_loadout(code: str) -> dict[str, Any] | None:
    """Fetch a shared loadout by its share code. Returns the payload dict."""
    try:
        data = supabase_api.select(
            "equipment_loadouts", "payload", eq={"id": code.strip()}
        )
        if data:
            return data[0]["payload"]
        return None
    except Exception as e:
        print(f"[EquipmentSharing] Failed to fetch loadout '{code}': {e}")
        return None
