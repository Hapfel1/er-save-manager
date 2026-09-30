"""Shared ttk styling for the DS3 tabs' list views."""

from __future__ import annotations

from tkinter import ttk

TREE_STYLE = "DS3.Treeview"


def apply_treeview_style() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        TREE_STYLE,
        background="#2b2b2b",
        foreground="white",
        fieldbackground="#2b2b2b",
        rowheight=22,
        borderwidth=0,
    )
    style.configure(f"{TREE_STYLE}.Heading", background="#3b3b3b", foreground="white")
    style.map(TREE_STYLE, background=[("selected", "#5a4a7a")])


def make_tree(parent, columns: list[tuple[str, str, int, str]], height: int = 18):
    """Treeview plus vertical scrollbar in a frame, packed to fill parent.

    columns: (id, heading, width, anchor). Returns (frame, tree).
    """
    apply_treeview_style()
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(
        frame,
        columns=[c[0] for c in columns],
        show="tree headings",
        style=TREE_STYLE,
        height=height,
        selectmode="extended",
    )
    tree.column("#0", width=18, stretch=False)
    for col, heading, width, anchor in columns:
        tree.heading(col, text=heading)
        tree.column(col, width=width, anchor=anchor, stretch=col == columns[0][0])
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return frame, tree
