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
        font_size=13,
        position=None,
    ):
        """Create base dialog, sized to its content.

        The first button is the primary action (Enter); Escape and the window
        close button pick the value of the last button.
        """
        import tkinter.font as tkfont

        from er_save_manager.ui.utils import bind_mousewheel, force_render_dialog

        dialog = ctk.CTkToplevel(parent if parent else None)
        # Withdrawn until fully built and placed, so it never shows at the
        # default position or as a white flash on Windows.
        dialog.withdraw()
        dialog.attributes("-alpha", 0)
        dialog.title(title)
        dialog.resizable(False, False)

        font = ("Segoe UI", font_size)
        # Wide layout once the text would run past ~12 lines at the normal wrap
        text_px = tkfont.Font(family=font[0], size=-font_size).measure(message)
        wraplength = 560 if text_px > 400 * 12 else 400

        icon_symbols = {
            "info": "ℹ",
            "warning": "⚠",
            "error": "✕",
            "question": "?",
        }

        icon_colors = {
            "info": palette.PURPLE_TEXT,
            "warning": palette.WARNING_TEXT,
            "error": palette.RED_TEXT,
            "question": palette.PURPLE_TEXT,
        }

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        # Packed first so the buttons keep their place at the bottom
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(16, 0))

        def build_content(container):
            ctk.CTkLabel(
                container,
                text=icon_symbols.get(icon_type, "ℹ"),
                font=("Segoe UI Semibold", 24),
                text_color=icon_colors.get(icon_type, icon_colors["info"]),
            ).pack(side=tk.LEFT, anchor="n", padx=(0, 12))
            ctk.CTkLabel(
                container,
                text=message,
                font=font,
                wraplength=wraplength,
                justify=tk.LEFT,
                anchor="w",
            ).pack(side=tk.LEFT, anchor="n", fill=tk.X, expand=True)

        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill=tk.BOTH, expand=True)
        build_content(content_frame)

        if buttons is None:
            buttons = [("OK", True)]

        result = {}

        def choose(value):
            result["value"] = value
            dialog.grab_release()
            dialog.destroy()

        # Packed right to left so the buttons keep their order, right aligned
        for i, (btn_text, btn_value) in reversed(list(enumerate(buttons))):
            extra = {} if i == 0 else {"fg_color": ("gray70", "gray35")}
            ctk.CTkButton(
                button_frame,
                text=btn_text,
                command=lambda v=btn_value: choose(v),
                width=100,
                height=32,
                font=font,
                **extra,
            ).pack(side=tk.RIGHT, padx=(8, 0))

        dialog.update_idletasks()
        get_scale = getattr(dialog, "_get_window_scaling", None)
        scale = get_scale() if get_scale else 1.0
        max_height = min(int(dialog.winfo_screenheight() * 0.8 / scale), 640)

        # Long text scrolls instead of growing the dialog past max_height
        if dialog.winfo_reqheight() / scale > max_height:
            chrome = (
                dialog.winfo_reqheight() - content_frame.winfo_reqheight()
            ) / scale
            content_frame.destroy()
            content_frame = ctk.CTkScrollableFrame(
                main_frame,
                fg_color="transparent",
                width=wraplength + 60,
                height=int(max_height - chrome - 20),
            )
            content_frame.pack(fill=tk.BOTH, expand=True)
            bind_mousewheel(content_frame)
            build_content(content_frame)
            dialog.update_idletasks()

        width = max(dialog.winfo_reqwidth() / scale, 340)
        height = dialog.winfo_reqheight() / scale
        if position is None:
            center_window(
                dialog,
                round(width),
                round(height),
                parent=parent if parent else None,
            )
        else:
            px, py = position
            dialog.geometry(f"{round(width)}x{round(height)}+{px}+{py}")

        dialog.deiconify()
        force_render_dialog(dialog)
        dialog.attributes("-alpha", 1)
        try:
            dialog.wait_visibility()
            dialog.grab_set()
        except tk.TclError:
            pass

        # force_render_dialog focuses the dialog before it is mapped; focus it
        # again once visible so Enter and Escape reach it, not the parent.
        def take_focus():
            try:
                dialog.focus_force()
            except tk.TclError:
                pass

        take_focus()
        dialog.after(150, take_focus)

        cancel_value = buttons[-1][1]
        dialog.bind("<Return>", lambda _e: choose(buttons[0][1]))
        dialog.bind("<KP_Enter>", lambda _e: choose(buttons[0][1]))
        dialog.bind("<Escape>", lambda _e: choose(cancel_value))
        dialog.protocol("WM_DELETE_WINDOW", lambda: choose(cancel_value))

        dialog.wait_window()
        return result["value"] if "value" in result else None

    @staticmethod
    def showinfo(title, message, parent=None, font_size=13, position=None):
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
    def showwarning(title, message, parent=None, font_size=13, position=None):
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
    def showerror(title, message, parent=None, font_size=13, position=None):
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
    def askyesno(title, message, parent=None, font_size=13, position=None):
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
    def askokcancel(title, message, parent=None, font_size=13, position=None):
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
    def askyesnocancel(title, message, parent=None, font_size=13, position=None):
        return CTkMessageBox._create_dialog(
            parent,
            title,
            message,
            icon_type="question",
            buttons=[("Yes", True), ("No", False), ("Cancel", None)],
            font_size=font_size,
            position=position,
        )
