"""
Supabase integration for character ratings and download tracking.

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


class CharacterMetrics:
    """Manage character ratings and downloads via Supabase."""

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

        # Cache of user actions (character_id -> list of action_types)
        self.user_actions: dict[str, list[str]] = self._load_user_actions()

    def _get_or_create_user_id(self) -> str:
        """Get or create a unique user ID for this client."""
        settings = self._load_settings()

        if "user_id" not in settings:
            settings["user_id"] = str(uuid.uuid4())
            self._save_settings(settings)

        return settings["user_id"]

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
        actions = settings.get("character_user_actions", {})

        # Ensure list format
        migrated = {}
        for character_id, action in actions.items():
            if isinstance(action, str):
                migrated[character_id] = [action]
            else:
                migrated[character_id] = action
        return migrated

    def _save_user_action(self, character_id: str, action_type: str):
        """Cache a user action locally."""
        if character_id not in self.user_actions:
            self.user_actions[character_id] = []
        if action_type not in self.user_actions[character_id]:
            self.user_actions[character_id].append(action_type)
        settings = self._load_settings()
        settings["character_user_actions"] = self.user_actions
        self._save_settings(settings)
        print(
            f"Saved action '{action_type}' for {character_id}. Current actions: {self.user_actions[character_id]}"
        )

    def has_liked(self, character_id: str) -> bool:
        """Check if user has already liked this character."""
        return character_id in self.user_actions and (
            "like" in self.user_actions[character_id]
            or "thumbs_up" in self.user_actions[character_id]
        )

    def has_downloaded(self, character_id: str) -> bool:
        """Check if user has already downloaded this character."""
        return (
            character_id in self.user_actions
            and "download" in self.user_actions[character_id]
        )

    def has_user_liked(self, character_id: str) -> bool:
        """Check if user has liked this character."""
        actions = self.user_actions.get(character_id, [])
        return "like" in actions or "thumbs_up" in actions

    def fetch_user_likes(
        self, character_ids: list[str] | None = None
    ) -> dict[str, bool]:
        """
        Fetch user's likes for characters.

        Uses local cache only - server-side queries blocked by RLS for anonymous users.

        Args:
            character_ids: Optional list of character IDs to fetch likes for

        Returns:
            Dict mapping character_id to True if liked
        """
        # Return locally cached likes (server queries are blocked by RLS)
        likes = {}
        if not character_ids:
            for cid, actions in self.user_actions.items():
                if "like" in actions or "thumbs_up" in actions:
                    likes[cid] = True
        else:
            for cid in character_ids:
                actions = self.user_actions.get(cid, [])
                if "like" in actions or "thumbs_up" in actions:
                    likes[cid] = True
        return likes

    def fetch_metrics(self, character_ids: list[str] | None = None) -> dict[str, dict]:
        """
        Fetch metrics for characters from Supabase.

        Args:
            character_ids: Optional list of character IDs to fetch. If None, fetches all.

        Returns:
            Dict mapping character_id to metrics dict with keys:
            - likes: int
            - downloads: int
        """
        if not self.supabase:
            return {}

        try:
            metrics = {}

            # Get base metrics from character_metrics table
            query = self.supabase.table("character_metrics").select("*")

            # Add filter if specific characters requested
            if character_ids:
                query = query.in_("character_id", character_ids)

            response = query.execute()
            metrics_list = response.data if hasattr(response, "data") else response

            # Initialize metrics from table
            for item in metrics_list:
                metrics[item["character_id"]] = {
                    "likes": 0,  # Will be overwritten by action counts
                    "downloads": item.get("downloads", 0),
                }

            # Count likes and downloads from character_actions table
            # (since character_metrics.likes is not being updated by triggers)
            actions_query = self.supabase.table("character_actions").select(
                "character_id, action_type"
            )

            if character_ids:
                actions_query = actions_query.in_("character_id", character_ids)

            actions_response = actions_query.execute()
            actions_list = (
                actions_response.data
                if hasattr(actions_response, "data")
                else actions_response
            )

            # Count actions by type
            action_counts: dict[str, dict[str, int]] = {}
            for action in actions_list:
                char_id = action["character_id"]
                action_type = action["action_type"]

                if char_id not in action_counts:
                    action_counts[char_id] = {"like": 0, "download": 0}

                if action_type in action_counts[char_id]:
                    action_counts[char_id][action_type] += 1

            # Update metrics with actual action counts
            for char_id, counts in action_counts.items():
                if char_id not in metrics:
                    metrics[char_id] = {"likes": 0, "downloads": 0}

                metrics[char_id]["likes"] = counts["like"]
                metrics[char_id]["downloads"] = max(
                    metrics[char_id]["downloads"], counts["download"]
                )

            return metrics

        except Exception as e:
            print(f"Failed to fetch character metrics: {e}")
            return {}

    def record_action(
        self, character_id: str, action_type: str
    ) -> dict[str, Any] | None:
        """
        Record a user action (like or download).

        Args:
            character_id: ID of the character
            action_type: One of 'like', 'download'

        Returns:
            Updated metrics dict or None if failed
        """
        if not self.supabase:
            print("[Metrics] Supabase not initialized")
            return None

        # For likes: check if already liked (can only like once)
        if action_type == "like" and self.has_liked(character_id):
            print(f"Already liked character {character_id}")
            return None

        # For downloads: allow multiple downloads to be recorded
        # (don't check has_downloaded - users can import the same character multiple times)

        try:
            print(
                f"[Metrics] Recording action: character_id={character_id}, action_type={action_type}"
            )

            # Call Supabase RPC function with user_id parameter
            response = self.supabase.rpc(
                "record_character_action",
                {
                    "p_character_id": character_id,
                    "p_action_type": action_type,
                    "p_user_id": self.user_id,
                },
            ).execute()

            result = response.data if hasattr(response, "data") else response

            # Cache the action locally
            self._save_user_action(character_id, action_type)

            return result

        except Exception as e:
            error_str = str(e).lower()
            error_full = str(e)

            # Check for constraint errors
            if "check constraint" in error_str:
                print(
                    f"[Metrics] Check constraint error - the database may not accept '{action_type}' as an action type"
                )
                print(f"[Metrics] Full error: {error_full}")
                # Still cache it locally
                self._save_user_action(character_id, action_type)
                return None

            # Check if it's a duplicate constraint error
            if "duplicate" in error_str or "unique" in error_str:
                print("Action already recorded (duplicate)")
                self._save_user_action(character_id, action_type)
                return None

            print(f"[Metrics] Failed to record character action: {error_full}")
            return None

    def like(self, character_id: str) -> dict[str, Any] | None:
        """Record a like."""
        return self.record_action(character_id, "like")

    def record_download(self, character_id: str) -> dict[str, Any] | None:
        """Record a character download/import."""
        return self.record_action(character_id, "download")
