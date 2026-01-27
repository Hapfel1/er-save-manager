"""
Custom message dialogs for customtkinter with lavender theme
Replacement for tkinter.messagebox with styled CTk dialogs
"""

import tkinter as tk

import customtkinter as ctk


class CTkMessageBox:
    """Custom message box dialogs matching the lavender theme"""

    @staticmethod
    def _create_dialog(parent, title, message, icon_type="info", buttons=None):
        """Create base dialog"""
        from er_save_manager.ui.utils import force_render_dialog

        dialog = ctk.CTkToplevel(parent if parent else None)
        dialog.title(title)

        # Calculate dialog size based on message length
        # Estimate: ~80 characters per line at wraplength 280
        line_count = max(3, len(message) // 80 + 1)
        dialog_height = 180 + (line_count * 20)  # Base height + extra for more lines
        dialog_width = 550  # Wider to accommodate longer messages

        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.resizable(False, False)

        # Force rendering on Linux before grab_set
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

        # Main container
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Icon + Message row
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Icon
        icon_label = ctk.CTkLabel(
            content_frame,
            text=icon_symbols.get(icon_type, "ℹ"),
            font=("Segoe UI", 32, "bold"),
            text_color=icon_color,
            width=60,
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))

        # Message
        message_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=("Segoe UI", 11),
            wraplength=380,
            justify=tk.LEFT,
        )
        message_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Buttons
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
            ).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()
        return result["value"]

    @staticmethod
    def showinfo(title, message, parent=None):
        """Show info message"""
        CTkMessageBox._create_dialog(
            parent, title, message, icon_type="info", buttons=[("OK", None)]
        )

    @staticmethod
    def showwarning(title, message, parent=None):
        """Show warning message"""
        CTkMessageBox._create_dialog(
            parent, title, message, icon_type="warning", buttons=[("OK", None)]
        )

    @staticmethod
    def showerror(title, message, parent=None):
        """Show error message"""
        CTkMessageBox._create_dialog(
            parent, title, message, icon_type="error", buttons=[("OK", None)]
        )

    @staticmethod
    def askyesno(title, message, parent=None):
        """Ask yes/no question"""
        result = CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="question",
            buttons=[("Yes", True), ("No", False)],
        )
        return result if result is not None else False

    @staticmethod
    def askokcancel(title, message, parent=None):
        """Ask OK/Cancel question"""
        result = CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="question",
            buttons=[("OK", True), ("Cancel", False)],
        )
        return result if result is not None else False

    @staticmethod
    def askyesnocancel(title, message, parent=None):
        """Ask yes/no/cancel question"""
        result = CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="question",
            buttons=[("Yes", True), ("No", False), ("Cancel", None)],
        )
        return result
