"""
Toast Notification System - Clean Professional Rectangle
No transparency issues, clean Catppuccin style
"""

import tkinter as tk

import customtkinter as ctk

_active_toasts = []


def show_toast(root: tk.Tk, message: str, duration: int = 3000, type: str = "success"):
    """Show a toast notification with automatic stacking"""

    # Catppuccin Mocha colors
    colors = {
        "success": {
            "bg": "#a6e3a1",  # Green
            "fg": "#11111b",  # Crust
        },
        "info": {
            "bg": "#89b4fa",  # Blue
            "fg": "#11111b",
        },
        "warning": {
            "bg": "#f9e2af",  # Yellow
            "fg": "#11111b",
        },
        "error": {
            "bg": "#f38ba8",  # Red
            "fg": "#11111b",
        },
    }

    theme = colors.get(type, colors["success"])

    # Create clean rectangular toast
    toast = ctk.CTkToplevel(root)
    toast.withdraw()
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)

    # Transparency
    try:
        toast.attributes("-alpha", 0.96)
    except tk.TclError:
        pass

    # Simple label - clean and works
    toast.configure(fg_color=theme["bg"])

    label = ctk.CTkLabel(
        toast,
        text=message,
        text_color=theme["fg"],
        fg_color=theme["bg"],
        font=("Segoe UI", 12, "bold"),
        wraplength=400,
    )
    label.pack(padx=20, pady=12)

    # Get size
    toast.update_idletasks()
    toast_width = toast.winfo_reqwidth()
    toast_height = toast.winfo_reqheight()

    # Calculate position
    root.update_idletasks()
    app_x = root.winfo_rootx()
    app_y = root.winfo_rooty()
    app_width = root.winfo_width()

    x = app_x + (app_width - toast_width) // 2

    base_y = app_y + 20
    spacing = 12

    y = base_y
    for active_toast in _active_toasts:
        if active_toast["toast"].winfo_exists():
            toast_bottom = active_toast["y"] + active_toast["height"]
            y = toast_bottom + spacing

    toast_info = {
        "toast": toast,
        "x": x,
        "y": y,
        "width": toast_width,
        "height": toast_height,
        "duration": duration,
    }
    _active_toasts.append(toast_info)

    # Position and show
    toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")
    toast.deiconify()

    # Slide in
    start_y = y - 30
    toast.geometry(f"{toast_width}x{toast_height}+{x}+{start_y}")

    def slide_in(current_y, target_y, step=0):
        if step < 15:
            progress = step / 15
            eased = 1 - pow(1 - progress, 3)
            new_y = int(start_y + (target_y - start_y) * eased)
            if toast.winfo_exists():
                toast.geometry(f"{toast_width}x{toast_height}+{x}+{new_y}")
                root.after(16, lambda: slide_in(current_y, target_y, step + 1))

    slide_in(start_y, y)

    # Auto-dismiss
    def dismiss():
        if toast.winfo_exists():
            current_y = y

            def slide_out(step=0):
                if step < 12:
                    progress = step / 12
                    eased = pow(progress, 2)
                    new_y = int(current_y - 30 * eased)
                    if toast.winfo_exists():
                        toast.geometry(f"{toast_width}x{toast_height}+{x}+{new_y}")
                        root.after(16, lambda: slide_out(step + 1))
                else:
                    if toast.winfo_exists():
                        toast.destroy()
                    if toast_info in _active_toasts:
                        _active_toasts.remove(toast_info)
                    _reposition_toasts(root)

            slide_out()

    root.after(duration, dismiss)

    # Click to dismiss
    def on_click(event):
        dismiss()

    toast.bind("<Button-1>", on_click)
    label.bind("<Button-1>", on_click)


def _reposition_toasts(root):
    """Reposition remaining toasts to fill gaps"""
    root.update_idletasks()
    app_x = root.winfo_rootx()
    app_y = root.winfo_rooty()
    app_width = root.winfo_width()

    base_y = app_y + 20
    spacing = 12

    current_y = base_y
    for toast_info in _active_toasts:
        if toast_info["toast"].winfo_exists():
            old_y = toast_info["y"]
            new_y = current_y

            x_pos = app_x + (app_width - toast_info["width"]) // 2

            if old_y != new_y or x_pos != toast_info["x"]:
                toast = toast_info["toast"]
                w = toast_info["width"]
                h = toast_info["height"]

                def animate_move(
                    widget,
                    start_x,
                    start_y,
                    end_x,
                    end_y,
                    width,
                    height,
                    info_captured,
                    step=0,
                ):
                    if step < 10:
                        progress = step / 10
                        eased = 1 - pow(1 - progress, 2)
                        new_x = int(start_x + (end_x - start_x) * eased)
                        new_y_pos = int(start_y + (end_y - start_y) * eased)
                        if widget.winfo_exists():
                            widget.geometry(f"{width}x{height}+{new_x}+{new_y_pos}")
                            root.after(
                                16,
                                lambda: animate_move(
                                    widget,
                                    start_x,
                                    start_y,
                                    end_x,
                                    end_y,
                                    width,
                                    height,
                                    info_captured,
                                    step + 1,
                                ),
                            )
                    else:
                        info_captured["x"] = end_x
                        info_captured["y"] = end_y

                animate_move(
                    toast, toast_info["x"], old_y, x_pos, new_y, w, h, toast_info
                )

            current_y = new_y + toast_info["height"] + spacing
