"""CustomTkinter Save Selector Dialog with Lavender theme."""

import datetime
import threading
from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.utils import center_window, style_window_frame, transient_to

# Badge colors per save kind (light, dark): background, text. Light mode
# text is darker than GREEN_TEXT and Catppuccin Pink to stay readable on
# the tints.
_BADGES = {
    "Vanilla": (palette.BLUE_TINT, palette.BLUE_TEXT),
    "Seamless Co-op": (palette.PURPLE_TINT, palette.PURPLE_TEXT),
    "Convergence": (("#D6EED2", "#24392B"), ("#2E7D1F", "#A6E3A1")),
    "Custom": (("#F5D6EC", "#47303F"), ("#B4458F", "#F5C2E7")),
}


def _badge(kind: str) -> tuple:
    """Badge colors for a save kind; combined kinds use their first part."""
    for name in ("Custom", "Convergence", "Seamless Co-op"):
        if kind.startswith(name):
            return _BADGES[name]
    return _BADGES["Vanilla"]


def _kind(path: Path, game_key: str | None) -> str | None:
    """Save kind of a file by its extension (Vanilla, Seamless Co-op, ...)."""
    from er_save_manager.games.extension_copy import flavor_of

    flavor = flavor_of(path, game_key or "elden_ring")
    return flavor.label if flavor and flavor.label else None


def _modified(path: Path) -> str:
    try:
        stamp = datetime.datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return ""
    today = datetime.date.today()
    if stamp.date() == today:
        day = "Today"
    elif stamp.date() == today - datetime.timedelta(days=1):
        day = "Yesterday"
    else:
        day = stamp.strftime("%Y-%m-%d")
    return f"{day} {stamp:%H:%M}"


def _save_row(parent, path: Path, kind: str | None, detail: str, on_click):
    """Card row: file name and kind badge, then detail text on a second line.
    Returns (row, detail label)."""
    row = ctk.CTkFrame(parent, fg_color=ds.CARD_ROW, corner_radius=8)
    row.pack(fill="x", padx=4, pady=3)
    top = ctk.CTkFrame(row, fg_color="transparent")
    top.pack(fill="x", padx=12, pady=(7, 0))
    widgets = [row, top]
    name = ctk.CTkLabel(top, text=path.name, font=ds.BOLD, text_color=ds.ROW_TEXT)
    name.pack(side="left")
    widgets.append(name)
    if kind:
        bg, fg = _badge(kind)
        badge = ctk.CTkLabel(
            top,
            text=kind,
            font=ds.SMALL,
            fg_color=bg,
            text_color=fg,
            corner_radius=9,
            height=20,
        )
        badge.pack(side="left", padx=(10, 0))
        widgets.append(badge)
    info = ctk.CTkLabel(
        row,
        text=detail,
        font=ds.SMALL,
        text_color=ds.MUTED,
        anchor="w",
        justify="left",
    )
    info.pack(fill="x", padx=12, pady=(0, 7))
    widgets.append(info)
    for widget in widgets:
        widget.bind("<Button-1>", lambda _e: on_click(), add="+")
    return row, info


# Rows built before the dialog shows (about the list's visible height), then
# per later event loop turn
_FIRST_ROWS = 8
_BATCH_ROWS = 4


class SaveSelectorDialog:
    """Dialog for selecting from multiple save files using customtkinter."""

    @staticmethod
    def show(
        parent,
        saves,
        callback,
        browse_callback=None,
        browse_button_text="Browse Manually",
        game_key=None,
    ):
        """
        Show save selector dialog

        Args:
            parent: Parent window
            saves: List of Path objects for save files
            callback: Function to call with selected save path
            browse_callback: Optional function that opens a manual browse dialog
                and returns a selected save path.
            browse_button_text: Label for the manual browse button.
            game_key: Game of the saves; rows then show the save kind and
                the character names, read in the background.
        """
        dialog = ctk.CTkToplevel(parent)
        dialog.title("Select Save File")
        dialog.resizable(True, True)
        transient_to(dialog, parent)
        # Stay transparent while the rows are built, so the window never
        # shows up empty and fills in afterwards. Position it now: window
        # managers place a window when it is first mapped and may ignore
        # later moves.
        dialog.attributes("-alpha", 0)
        width, height = 950, 520
        dialog.update_idletasks()
        parent.update_idletasks()
        center_window(dialog, width, height, parent=parent)
        style_window_frame(dialog, dialog=False)

        title = ctk.CTkLabel(
            dialog,
            text=f"Found {len(saves)} save files",
            font=("Inter", 14, "bold"),
            pady=6,
        )
        title.pack(padx=15, pady=(12, 0))
        ctk.CTkLabel(
            dialog,
            text="Pick the file of the version you play.",
            font=ds.FONT,
            text_color=palette.PURPLE_TEXT,
        ).pack(padx=15, pady=(0, 4))

        # Scrollable list with click-to-select rows
        selection_var = ctk.StringVar(value=str(saves[0]) if saves else "")
        result = {"value": None}

        from er_save_manager.ui.utils import bind_mousewheel

        list_frame = ctk.CTkScrollableFrame(
            dialog, label_text="Save Files", width=720, height=260
        )
        list_frame.pack(fill="both", expand=True, padx=15, pady=10)

        bind_mousewheel(list_frame)

        row_widgets: list[tuple[str, ctk.CTkFrame]] = []
        show_folders_var = ctk.BooleanVar(value=True)
        # Character summary per path, filled by the worker thread
        summaries: dict[str, str | None] = {}
        info_labels: dict[str, ctk.CTkLabel] = {}

        def detail(path: Path) -> str:
            parts = [_modified(path)]
            summary = summaries.get(str(path))
            if summary:
                parts.append(summary)
            elif game_key and str(path) not in summaries:
                parts.append("Reading characters...")
            text = "  \u00b7  ".join(p for p in parts if p)
            if show_folders_var.get():
                text += f"\n{path.parent}"
            return text

        def apply_selection(value: str):
            selection_var.set(value)
            for val, row in row_widgets:
                ds.select_card_row(row, val == value)

        build_job: dict[str, str | None] = {"id": None}

        def build_rows() -> None:
            if build_job["id"] is not None:
                dialog.after_cancel(build_job["id"])
                build_job["id"] = None
            for _value, row in row_widgets:
                row.destroy()
            row_widgets.clear()
            info_labels.clear()
            add_rows(0, _FIRST_ROWS)

        def add_rows(start: int, count: int) -> None:
            """Rows start..start+count, then the next batch on a later event
            loop turn: the rows in view show at once, the rest fill in."""
            build_job["id"] = None
            if not dialog.winfo_exists():
                return
            for save in saves[start : start + count]:
                # File name as the title, so its extension stays visible when
                # a long folder path is cut off at the right edge
                path = Path(save)
                row, info = _save_row(
                    list_frame,
                    path,
                    _kind(path, game_key) if game_key else None,
                    detail(path),
                    on_click=lambda v=str(save): apply_selection(v),
                )
                info_labels[str(save)] = info
                row_widgets.append((str(save), row))
                ds.select_card_row(row, str(save) == selection_var.get())
            if start + count < len(saves):
                # Tk runs due timers before the idle callbacks that repaint
                # the window, so the timer is armed from an idle callback:
                # the dialog is drawn before each batch
                build_job["id"] = dialog.after_idle(arm, start + count, _BATCH_ROWS)

        def arm(start: int, count: int) -> None:
            build_job["id"] = dialog.after(1, add_rows, start, count)

        build_rows()

        if game_key:
            from er_save_manager.games.save_summary import character_summary

            def read_summaries() -> None:
                # Worker thread: only fills the dict; the UI polls it
                for save in saves:
                    if not dialog_alive["v"]:
                        return
                    summaries[str(save)] = character_summary(save, game_key)

            dialog_alive = {"v": True}
            shown: set[str] = set()

            def poll_summaries() -> None:
                if not dialog.winfo_exists():
                    dialog_alive["v"] = False
                    return
                for key in list(summaries):
                    if key not in shown and key in info_labels:
                        info_labels[key].configure(text=detail(Path(key)))
                        shown.add(key)
                if len(shown) < len(saves):
                    dialog.after(150, poll_summaries)

            threading.Thread(target=read_summaries, daemon=True).start()
            dialog.after(150, poll_summaries)
            dialog.bind(
                "<Destroy>",
                lambda e: dialog_alive.update(v=False) if e.widget is dialog else None,
                add="+",
            )

        def select_save():
            value = selection_var.get()
            if value:
                result["value"] = value
                callback(value)
                dialog.destroy()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 14))

        ctk.CTkCheckBox(
            button_frame,
            text="Show folders",
            variable=show_folders_var,
            command=build_rows,
        ).pack(side="left", padx=15)

        if browse_callback:

            def browse_manually():
                value = browse_callback()
                if value:
                    result["value"] = value
                    callback(value)
                    dialog.destroy()

            browse_button = ctk.CTkButton(
                button_frame,
                text=browse_button_text,
                command=browse_manually,
                width=170,
            )
            browse_button.pack(side="right", padx=(0, 15))

        button = ctk.CTkButton(
            button_frame, text="Select", command=select_save, width=140
        )
        button.pack(side="right", padx=15)

        dialog.attributes("-alpha", 1)
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

        button.focus_set()
        dialog.bind("<Return>", lambda e: select_save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        dialog.wait_window()
        return result["value"]
