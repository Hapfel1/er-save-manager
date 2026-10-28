"""CustomTkinter Save Selector Dialog with Lavender theme."""

from pathlib import Path

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.utils import center_window, style_window_frame, transient_to

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
            text=f"Found {len(saves)} save files:",
            font=("Inter", 14, "bold"),
            pady=10,
        )
        title.pack(padx=15, pady=(12, 6))

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
                row = ds.card_row(
                    list_frame,
                    path.name,
                    str(path.parent) if show_folders_var.get() else "",
                    on_click=lambda v=str(save): apply_selection(v),
                    font=ds.FONT,
                )
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
