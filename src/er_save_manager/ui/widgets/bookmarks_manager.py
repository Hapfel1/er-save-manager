"""Bookmarks Manager - Manages hex editor bookmarks and annotations."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Bookmark:
    """A bookmark with offset and optional annotation."""

    offset: int
    name: str
    annotation: str = ""
    color: str = "#FFD700"  # Gold by default

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Create bookmark from dictionary."""
        return cls(**data)


class BookmarksManager:
    """Manages bookmarks for hex editor."""

    def __init__(self):
        self.bookmarks: list[Bookmark] = []
        self.bookmarks_file = Path("data/hex_bookmarks.json")

    def add_bookmark(
        self, offset: int, name: str, annotation: str = "", color: str = "#FFD700"
    ):
        """Add a new bookmark."""
        # Check if bookmark at this offset already exists
        existing = self.get_bookmark_at_offset(offset)
        if existing:
            # Update existing bookmark
            existing.name = name
            existing.annotation = annotation
            existing.color = color
        else:
            # Add new bookmark
            bookmark = Bookmark(offset, name, annotation, color)
            self.bookmarks.append(bookmark)
            self.bookmarks.sort(key=lambda b: b.offset)

    def remove_bookmark(self, offset: int):
        """Remove bookmark at offset."""
        self.bookmarks = [b for b in self.bookmarks if b.offset != offset]

    def get_bookmark_at_offset(self, offset: int) -> Bookmark | None:
        """Get bookmark at specific offset."""
        for bookmark in self.bookmarks:
            if bookmark.offset == offset:
                return bookmark
        return None

    def get_all_bookmarks(self) -> list[Bookmark]:
        """Get all bookmarks sorted by offset."""
        return sorted(self.bookmarks, key=lambda b: b.offset)

    def clear_bookmarks(self):
        """Clear all bookmarks."""
        self.bookmarks.clear()

    def save_bookmarks(self):
        """Save bookmarks to file."""
        try:
            self.bookmarks_file.parent.mkdir(parents=True, exist_ok=True)
            data = [b.to_dict() for b in self.bookmarks]
            with open(self.bookmarks_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save bookmarks: {e}")

    def load_bookmarks(self):
        """Load bookmarks from file."""
        try:
            if self.bookmarks_file.exists():
                with open(self.bookmarks_file) as f:
                    data = json.load(f)
                    self.bookmarks = [Bookmark.from_dict(b) for b in data]
                    self.bookmarks.sort(key=lambda b: b.offset)
        except Exception as e:
            print(f"Failed to load bookmarks: {e}")
            self.bookmarks = []
