"""
Character loadout sharing via Supabase.
"""

from __future__ import annotations

from typing import Any

from supabase import Client, create_client

SUPABASE_URL = "https://rnsrvcfjzsgrgiwvsbub.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "InJuc3J2Y2ZqenNncmdpd3ZzYnViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NjM5"
    "ODgsImV4cCI6MjA4NTAzOTk4OH0.W54LjC-aJs5RgWSQ0O2-UhY6S2kGco9Ra6AgvgJfXHo"
)

_client: Client | None = None
_client_failed = False


def _get_client() -> Client | None:
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed:
        return None
    try:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return _client
    except Exception:
        _client_failed = True
        return None


def share_loadout(payload: dict[str, Any], name: str = "") -> str | None:
    """Upload a character loadout, return the share code (row id), or None on failure."""
    client = _get_client()
    if client is None:
        return None
    try:
        response = (
            client.table("character_loadouts")
            .insert({"name": name, "payload": payload})
            .execute()
        )
        data = response.data if hasattr(response, "data") else response
        if data:
            return data[0]["id"]
        return None
    except Exception as e:
        print(f"[CharacterLoadoutSharing] Failed to share loadout: {e}")
        return None


def fetch_loadout(code: str) -> dict[str, Any] | None:
    """Fetch a shared character loadout payload by its share code."""
    client = _get_client()
    if client is None:
        return None
    try:
        response = (
            client.table("character_loadouts")
            .select("payload")
            .eq("id", code.strip())
            .execute()
        )
        data = response.data if hasattr(response, "data") else response
        if data:
            return data[0]["payload"]
        return None
    except Exception as e:
        print(f"[CharacterLoadoutSharing] Failed to fetch loadout '{code}': {e}")
        return None
