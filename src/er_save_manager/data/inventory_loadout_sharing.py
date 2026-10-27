"""
Inventory loadout sharing via Supabase.

Uses supabase_api (anon key, no authentication). A share code is the row id returned on upload:
copy the code, paste it elsewhere to import.
"""

from __future__ import annotations

from typing import Any

from er_save_manager import supabase_api


def share_loadout(payload: list[dict[str, Any]], name: str = "") -> str | None:
    """Upload an inventory loadout, return the share code (row id), or None on failure."""
    try:
        data = supabase_api.insert(
            "inventory_loadouts", {"name": name, "payload": payload}
        )
        if data:
            return data[0]["id"]
        return None
    except Exception as e:
        print(f"[InventoryLoadoutSharing] Failed to share loadout: {e}")
        return None


def fetch_loadout(code: str) -> list[dict[str, Any]] | None:
    """Fetch a shared inventory loadout payload by its share code."""
    try:
        data = supabase_api.select(
            "inventory_loadouts", "payload", eq={"id": code.strip()}
        )
        if data:
            return data[0]["payload"]
        return None
    except Exception as e:
        print(f"[InventoryLoadoutSharing] Failed to fetch loadout '{code}': {e}")
        return None
