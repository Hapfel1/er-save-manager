"""
Custom message dialogs for customtkinter with lavender theme
Replacement for tkinter.messagebox with styled CTk dialogs
"""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import palette
from er_save_manager.ui.utils import center_window


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
        # Keep invisible until fully built to prevent white flash on Windows.
        dialog.attributes("-alpha", 0)
        dialog.title(title)

        line_height = font_size + 10  # px per line at given font size

        def estimate_lines(wrap: int) -> int:
            # Split on explicit newlines, then wrap each segment at ~wrap px
            chars_per_line = max(1, int(wrap / (font_size * 0.6)))
            return sum(
                max(1, (len(segment) + chars_per_line - 1) // chars_per_line)
                for segment in message.split("\n")
            )

        dialog_width, wraplength = 550, 380
        if estimate_lines(wraplength) > 14:
            dialog_width, wraplength = 760, 590
        text_height = estimate_lines(wraplength) * line_height

        button_area = 80  # button row + padding
        icon_padding = 40  # top/bottom padding
        max_height = int(dialog.winfo_screenheight() * 0.8)
        dialog_height = max(
            180, min(text_height + button_area + icon_padding, max_height)
        )
        # Text taller than the dialog scrolls instead of pushing the buttons out
        # Long messages scroll: the line estimate is approximate, and a clipped
        # label would hide text without any way to reach it
        scroll_text = (
            text_height + button_area + icon_padding > max_height
            or estimate_lines(wraplength) > 14
        )

        if position is None:
            center_window(
                dialog, dialog_width, dialog_height, parent=parent if parent else None
            )
        else:
            px, py = position
            dialog.geometry(f"{dialog_width}x{dialog_height}+{px}+{py}")
        dialog.resizable(False, False)

        force_render_dialog(dialog)
        dialog.attributes("-alpha", 1)
        dialog.grab_set()

        icon_symbols = {
            "info": "ℹ",
            "warning": "⚠",
            "error": "✕",
            "question": "?",
        }

        icon_colors = {
            "info": palette.BLUE_TEXT,
            "warning": ("#ea580c", "#fb923c"),
            "error": ("#dc2626", "#fca5a5"),
            "question": palette.PURPLE_TEXT,
        }

        icon_color = icon_colors.get(icon_type, icon_colors["info"])

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Packed first so the buttons keep their place at the bottom
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(side=tk.BOTTOM, pady=(15, 0))

        if scroll_text:
            from er_save_manager.ui.utils import bind_mousewheel

            content_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
            bind_mousewheel(content_frame)
        else:
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
