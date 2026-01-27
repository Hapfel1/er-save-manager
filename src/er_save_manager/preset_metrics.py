"""
Supabase integration for preset ratings and download tracking.

Handles:
- Anonymous user authentication
- Thumbs up/down voting
- Download tracking
- Metrics caching
"""

import json
import uuid
from pathlib import Path
from typing import Any

from supabase import Client, create_client


class PresetMetrics:
    """Manage preset ratings and downloads via Supabase."""

    SUPABASE_URL = "https://rnsrvcfjzsgrgiwvsbub.supabase.co"
    SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJuc3J2Y2ZqenNncmdpd3ZzYnViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NjM5ODgsImV4cCI6MjA4NTAzOTk4OH0.W54LjC-aJs5RgWSQ0O2-UhY6S2kGco9Ra6AgvgJfXHo"

    def __init__(self, settings_path: Path):
        """
        Initialize metrics manager.

        Args:
            settings_path: Path to settings.json file
        """
        self.settings_path = settings_path

        # Get or create a unique user ID for this client
        self.user_id = self._get_or_create_user_id()

        # Initialize Supabase client with anon key
        # No authentication needed - anon key is sufficient for RLS policies
        try:
            self.supabase: Client = create_client(
                self.SUPABASE_URL, self.SUPABASE_ANON_KEY
            )
        except Exception as e:
            print(f"Failed to initialize Supabase client: {e}")
            self.supabase = None

        # Cache of user actions (preset_id -> list of action_types)
        self.user_actions: dict[str, list[str]] = self._load_user_actions()

    def _get_or_create_user_id(self) -> str:
        """Get or create a unique user ID for this client."""
        settings = self._load_settings()

        if "user_id" not in settings:
            settings["user_id"] = str(uuid.uuid4())
            self._save_settings(settings)

        return settings["user_id"]

    def _authenticate_anonymous(self):
        """Authenticate anonymously with Supabase."""
        try:
            # Sign up anonymously
            self.supabase.auth.sign_up({"email": "anon@local", "password": "anon"})
        except Exception:
            # If signup fails (user already exists), try signing in
            try:
                self.supabase.auth.sign_in_with_password(
                    {"email": "anon@local", "password": "anon"}
                )
            except Exception as e2:
                print(f"Anonymous authentication failed: {e2}")

    def _load_settings(self) -> dict[str, Any]:
        """Load settings from file."""
        if not self.settings_path.exists():
            return {}

        try:
            with open(self.settings_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings(self, settings: dict[str, Any]):
        """Save settings to file."""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    def _load_user_actions(self) -> dict[str, list[str]]:
        """Load cached user actions from settings."""
        settings = self._load_settings()
        actions = settings.get("preset_user_actions", {})

        # Migrate old format (str) to new format (list)
        migrated = {}
        for preset_id, action in actions.items():
            if isinstance(action, str):
                migrated[preset_id] = [action]
            else:
                migrated[preset_id] = action
        return migrated

    def _save_user_action(self, preset_id: str, action_type: str):
        """Cache a user action locally."""
        if preset_id not in self.user_actions:
            self.user_actions[preset_id] = []
        if action_type not in self.user_actions[preset_id]:
            self.user_actions[preset_id].append(action_type)
        settings = self._load_settings()
        settings["preset_user_actions"] = self.user_actions
        self._save_settings(settings)
        print(
            f"Saved action '{action_type}' for {preset_id}. Current actions: {self.user_actions[preset_id]}"
        )

    def has_liked(self, preset_id: str) -> bool:
        """Check if user has already liked this preset."""
        return (
            preset_id in self.user_actions
            and "thumbs_up" in self.user_actions[preset_id]
        )

    def has_downloaded(self, preset_id: str) -> bool:
        """Check if user has already downloaded this preset."""
        return (
            preset_id in self.user_actions
            and "download" in self.user_actions[preset_id]
        )

    def has_user_liked(self, preset_id: str) -> bool:
        """Check if user has liked this preset."""
        actions = self.user_actions.get(preset_id, [])
        return "thumbs_up" in actions

    def fetch_user_likes(self, preset_ids: list[str] | None = None) -> dict[str, bool]:
        """
        Fetch user's likes for presets.

        Uses local cache only - server-side queries blocked by RLS for anonymous users.

        Args:
            preset_ids: Optional list of preset IDs to fetch likes for

        Returns:
            Dict mapping preset_id to True if liked
        """
        # Return locally cached likes (server queries are blocked by RLS)
        likes = {}
        if not preset_ids:
            for pid, actions in self.user_actions.items():
                if "thumbs_up" in actions:
                    likes[pid] = True
        else:
            for pid in preset_ids:
                actions = self.user_actions.get(pid, [])
                if "thumbs_up" in actions:
                    likes[pid] = True
        return likes

    def fetch_metrics(self, preset_ids: list[str] | None = None) -> dict[str, dict]:
        """
        Fetch metrics for presets from Supabase.

        Args:
            preset_ids: Optional list of preset IDs to fetch. If None, fetches all.

        Returns:
            Dict mapping preset_id to metrics dict with keys:
            - thumbs_up: int
            - thumbs_down: int
            - downloads: int
        """
        if not self.supabase:
            return {}

        try:
            query = self.supabase.table("preset_metrics").select("*")

            # Add filter if specific presets requested
            if preset_ids:
                query = query.in_("preset_id", preset_ids)

            response = query.execute()

            # Convert list to dict keyed by preset_id
            metrics_list = response.data if hasattr(response, "data") else response
            return {
                item["preset_id"]: {
                    "thumbs_up": item.get("thumbs_up", 0),
                    "thumbs_down": item.get("thumbs_down", 0),
                    "downloads": item.get("downloads", 0),
                }
                for item in metrics_list
            }

        except Exception as e:
            print(f"Failed to fetch metrics: {e}")
            return {}

    def record_action(self, preset_id: str, action_type: str) -> dict[str, Any] | None:
        """
        Record a user action (like or download).

        Args:
            preset_id: ID of the preset
            action_type: One of 'thumbs_up', 'download'

        Returns:
            Updated metrics dict or None if failed
        """
        if not self.supabase:
            return None

        # For likes: check if already liked
        if action_type == "thumbs_up" and self.has_liked(preset_id):
            print(f"Already liked preset {preset_id}")
            return None

        # For downloads: check if already downloaded
        if action_type == "download" and self.has_downloaded(preset_id):
            print(f"Already downloaded preset {preset_id}")
            return None

        try:
            # Call Supabase RPC function with user_id parameter
            response = self.supabase.rpc(
                "record_action",
                {
                    "p_preset_id": preset_id,
                    "p_action_type": action_type,
                    "p_user_id": self.user_id,
                },
            ).execute()

            result = response.data if hasattr(response, "data") else response

            # Cache the action locally
            self._save_user_action(preset_id, action_type)

            return result

        except Exception as e:
            error_str = str(e).lower()
            # Check if it's a duplicate constraint error
            if "duplicate" in error_str or "unique" in error_str:
                print("Action already recorded (duplicate)")
                self._save_user_action(preset_id, action_type)
                return None
            print(f"Failed to record action: {e}")
            return None

    def like(self, preset_id: str) -> dict[str, Any] | None:
        """Record a like."""
        return self.record_action(preset_id, "thumbs_up")

    def record_download(self, preset_id: str) -> dict[str, Any] | None:
        """Record a preset download/application."""
        return self.record_action(preset_id, "download")
