"""
Custom message dialogs for customtkinter with lavender theme
Replacement for tkinter.messagebox with styled CTk dialogs
"""

import tkinter as tk

import customtkinter as ctk


class CTkMessageBox:
    """Custom message box dialogs matching the lavender theme"""

    @staticmethod
    def _create_dialog(
        parent,
        title,
        message,
        icon_type="info",
        buttons=None,
        font_size=16,
        position=None,
    ):
        """Create base dialog"""
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(parent if parent else None)
        dialog.title(title)

        dialog_width = 550
        wraplength = 380

        # Estimate lines: split on explicit newlines first, then wrap long lines
        line_height = font_size + 10  # px per line at given font size
        lines = 0
        for segment in message.split("\n"):
            # Each segment wraps at ~wraplength / (font_size * 0.6) chars
            chars_per_line = max(1, int(wraplength / (font_size * 0.6)))
            lines += max(1, (len(segment) + chars_per_line - 1) // chars_per_line)

        text_height = lines * line_height
        button_area = 80  # button row + padding
        icon_padding = 40  # top/bottom padding
        dialog_height = text_height + button_area + icon_padding

        # Clamp to reasonable bounds
        dialog_height = max(180, min(dialog_height, 600))

        if position is None:
            if parent:
                parent.update_idletasks()
                px = (
                    parent.winfo_rootx()
                    + (parent.winfo_width() // 2)
                    - (dialog_width // 2)
                )
                py = (
                    parent.winfo_rooty()
                    + (parent.winfo_height() // 2)
                    - (dialog_height // 2)
                )
            else:
                screen = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
                px = (screen[0] // 2) - (dialog_width // 2)
                py = (screen[1] // 2) - (dialog_height // 2)
        else:
            px, py = position

        dialog.geometry(f"{dialog_width}x{dialog_height}+{px}+{py}")
        dialog.resizable(False, False)

        force_render_dialog(dialog)
        dialog.grab_set()

        icon_symbols = {
            "info": "ℹ",
            "warning": "⚠",
            "error": "✕",
            "question": "?",
        }

        icon_colors = {
            "info": ("#2563eb", "#60a5fa"),
            "warning": ("#ea580c", "#fb923c"),
            "error": ("#dc2626", "#fca5a5"),
            "question": ("#7c3aed", "#c084fc"),
        }

        icon_color = icon_colors.get(icon_type, icon_colors["info"])

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill=tk.BOTH, expand=True)

        ctk.CTkLabel(
            content_frame,
            text=icon_symbols.get(icon_type, "ℹ"),
            font=("Segoe UI Semibold", 32, "bold"),
            text_color=icon_color,
            width=60,
        ).pack(side=tk.LEFT, anchor="n", padx=(0, 15))

        ctk.CTkLabel(
            content_frame,
            text=message,
            font=("Segoe UI Semibold", font_size),
            wraplength=wraplength,
            justify=tk.LEFT,
        ).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(15, 0))

        if buttons is None:
            buttons = [("OK", True)]

        result = {}

        for btn_text, btn_value in buttons:
            ctk.CTkButton(
                button_frame,
                text=btn_text,
                command=lambda v=btn_value: (
                    result.update({"value": v}),
                    dialog.destroy(),
                ),
                width=120,
                font=("Segoe UI Semibold", 18),
            ).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()
        return result["value"] if "value" in result else None

    @staticmethod
    def showinfo(title, message, parent=None, font_size=16, position=None):
        CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="info",
            buttons=[("OK", None)],
            font_size=font_size,
            position=position,
        )

    @staticmethod
    def showwarning(title, message, parent=None, font_size=16, position=None):
        CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="warning",
            buttons=[("OK", None)],
            font_size=font_size,
            position=position,
        )

    @staticmethod
    def showerror(title, message, parent=None, font_size=16, position=None):
        CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="error",
            buttons=[("OK", None)],
            font_size=font_size,
            position=position,
        )

    @staticmethod
    def askyesno(title, message, parent=None, font_size=16, position=None):
        result = CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="question",
            buttons=[("Yes", True), ("No", False)],
            font_size=font_size,
            position=position,
        )
        return result if result is not None else False

    @staticmethod
    def askokcancel(title, message, parent=None, font_size=16, position=None):
        result = CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="question",
            buttons=[("OK", True), ("Cancel", False)],
            font_size=font_size,
            position=position,
        )
        return result if result is not None else False

    @staticmethod
    def askyesnocancel(title, message, parent=None, font_size=16, position=None):
        return CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="question",
            buttons=[("Yes", True), ("No", False), ("Cancel", None)],
            font_size=font_size,
            position=position,
        )
