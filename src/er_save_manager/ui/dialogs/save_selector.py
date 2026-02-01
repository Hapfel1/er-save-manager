"""CustomTkinter Save Selector Dialog with Lavender theme."""

from importlib import resources

import customtkinter as ctk


class SaveSelectorDialog:
    """Dialog for selecting from multiple save files using customtkinter."""

    @staticmethod
    def _load_lavender_theme():
        """Load the lavender theme from customtkinterthemes if available."""
        try:
            import customtkinterthemes as ctt

            theme_path = resources.files(ctt).joinpath("themes", "lavender.json")
            ctk.set_default_color_theme(theme_path)
        except Exception:
            # Fallback to built-in dark-blue if theme package missing
            ctk.set_default_color_theme("dark-blue")

    @staticmethod
    def show(parent, saves, callback):
        """
        Show save selector dialog

        Args:
            parent: Parent window
            saves: List of Path objects for save files
            callback: Function to call with selected save path
        """
        # Load lavender theme (appearance mode already set in main GUI)
        SaveSelectorDialog._load_lavender_theme()

        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(parent)
        dialog.title("Select Save File")
        dialog.resizable(True, True)

        width, height = 780, 520
        dialog.update_idletasks()
        # Center over parent window
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Force rendering on Linux before grab_set
        force_render_dialog(dialog)
        dialog.grab_set()

        title = ctk.CTkLabel(
            dialog,
            text=f"Found {len(saves)} save files:",
            font=("Segoe UI", 14, "bold"),
            pady=10,
        )
        title.pack(padx=15, pady=(12, 6))

        # Scrollable list with click-to-select rows
        selection_var = ctk.StringVar(value=str(saves[0]) if saves else "")

        from er_save_manager.ui.utils import bind_mousewheel

        list_frame = ctk.CTkScrollableFrame(
            dialog, label_text="Save Files", width=720, height=260
        )
        list_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Bind mousewheel for scrolling on Linux and other platforms
        bind_mousewheel(list_frame)

        row_widgets: list[tuple[str, ctk.CTkFrame, ctk.CTkLabel]] = []

        def apply_selection(value: str):
            selection_var.set(value)
            # Update row highlight with mode-aware colors
            for val, row, label in row_widgets:
                if val == value:
                    # Selected: lavender highlight
                    row.configure(fg_color=("#c9a0dc", "#3b2f5c"))
                    label.configure(text_color=("#1f1f28", "#f0f0f0"))
                else:
                    # Unselected: subtle background
                    row.configure(fg_color=("#f5f5f5", "#2a2a3e"))
                    label.configure(text_color=("#333333", "#cccccc"))

        for save in saves:
            row = ctk.CTkFrame(
                list_frame, fg_color=("#f5f5f5", "#2a2a3e"), corner_radius=6
            )
            row.pack(fill="x", pady=4, padx=4)

            label = ctk.CTkLabel(row, text=str(save), anchor="w", padx=8, pady=6)
            label.pack(fill="x")

            row.bind("<Button-1>", lambda e, v=str(save): apply_selection(v))
            label.bind("<Button-1>", lambda e, v=str(save): apply_selection(v))

            row_widgets.append((str(save), row, label))

        if saves:
            apply_selection(str(saves[0]))

        def select_save():
            value = selection_var.get()
            if value:
                callback(value)
                dialog.destroy()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 14))

        button = ctk.CTkButton(
            button_frame, text="Select", command=select_save, width=140
        )
        button.pack(side="right", padx=15)

        # Default selection and keyboard activation
        button.focus_set()
        dialog.bind("<Return>", lambda e: select_save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
