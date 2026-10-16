"""Shared list view builder for the DS3 tabs."""

from __future__ import annotations

from er_save_manager.ui import dialog_style as ds


def make_tree(parent, columns: list[tuple[str, str, int, str]], height: int = 8):
    """Treeview plus vertical scrollbar in a frame, packed to fill parent.

    columns: (id, heading, width, anchor). Returns (frame, tree). height is
    the requested row count; pack the frame with expand to fill the rest.
    """
    frame, tree = ds.themed_tree(
        parent,
        columns=[c[0] for c in columns],
        show="tree headings",
        height=height,
        selectmode="extended",
    )
    tree.column("#0", width=18, stretch=False)
    for col, heading, width, anchor in columns:
        tree.heading(col, text=heading)
        tree.column(col, width=width, anchor=anchor, stretch=col == columns[0][0])
    return frame, tree
