"""
Enhanced Toast Notification System with Queue Support
Catppuccin-themed with modern styling
"""

import tkinter as tk

import customtkinter as ctk

# Global queue to track active toasts
_active_toasts = []


def show_toast(root: tk.Tk, message: str, duration: int = 3000, type: str = "success"):
    """
    Show a toast notification with automatic stacking

    Args:
        root: Root window
        message: Message to display
        duration: How long to show (ms)
        type: Toast type (success/info/warning/error)
    """
    # Catppuccin Mocha colors
    colors = {
        "success": {
            "bg": "#a6e3a1",  # Green
            "fg": "#1e1e2e",  # Base
        },
        "info": {
            "bg": "#89dceb",  # Sky
            "fg": "#1e1e2e",  # Base
        },
        "warning": {
            "bg": "#f9e2af",  # Yellow
            "fg": "#1e1e2e",  # Base
        },
        "error": {
            "bg": "#f38ba8",  # Red
            "fg": "#1e1e2e",  # Base
        },
    }

    theme = colors.get(type, colors["success"])

    # Create toplevel window
    toast = tk.Toplevel(root)
    toast.withdraw()  # Hide initially
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)

    # Make transparent on supported platforms
    try:
        toast.attributes("-alpha", 0.96)
    except tk.TclError:
        pass

    # Use CTkFrame for rounded corners and modern look
    frame = ctk.CTkFrame(
        toast,
        fg_color=theme["bg"],
        corner_radius=12,
        border_width=0,
    )
    frame.pack(padx=0, pady=0)

    # Use CTkLabel for better font rendering
    label = ctk.CTkLabel(
        frame,
        text=message,
        text_color=theme["fg"],
        font=("Segoe UI", 12, "bold"),
        wraplength=400,
    )
    label.pack(padx=24, pady=14)

    # Update to get proper size
    toast.update_idletasks()
    toast_width = toast.winfo_reqwidth()
    toast_height = toast.winfo_reqheight()

    # Calculate position - center over APPLICATION WINDOW
    root.update_idletasks()
    app_x = root.winfo_rootx()
    app_y = root.winfo_rooty()
    app_width = root.winfo_width()

    # Center horizontally over application window
    x = app_x + (app_width - toast_width) // 2

    # Stack vertically from top of application window
    base_y = app_y + 20  # 20px below window top
    spacing = 12  # Space between toasts

    # Find Y position by checking existing toasts
    y = base_y
    for active_toast in _active_toasts:
        if active_toast["toast"].winfo_exists():
            # Stack below this toast
            toast_bottom = active_toast["y"] + active_toast["height"]
            y = toast_bottom + spacing

    # Store toast info
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
    toast.geometry(f"+{x}+{y}")
    toast.deiconify()

    # Slide down animation
    start_y = y - 30
    toast.geometry(f"+{x}+{start_y}")

    def slide_in(current_y, target_y, step=0):
        if step < 15:
            # Cubic ease out
            progress = step / 15
            eased = 1 - pow(1 - progress, 3)
            new_y = int(start_y + (target_y - start_y) * eased)
            if toast.winfo_exists():
                toast.geometry(f"+{x}+{new_y}")
                root.after(16, lambda: slide_in(current_y, target_y, step + 1))

    slide_in(start_y, y)

    # Auto-dismiss
    def dismiss():
        if toast.winfo_exists():
            # Slide up animation
            current_y = y

            def slide_out(step=0):
                if step < 12:
                    progress = step / 12
                    eased = pow(progress, 2)
                    new_y = int(current_y - 30 * eased)
                    if toast.winfo_exists():
                        toast.geometry(f"+{x}+{new_y}")
                        root.after(16, lambda: slide_out(step + 1))
                else:
                    # Destroy and remove from queue
                    if toast.winfo_exists():
                        toast.destroy()
                    if toast_info in _active_toasts:
                        _active_toasts.remove(toast_info)

                    # Reposition remaining toasts
                    _reposition_toasts(root)

            slide_out()

    root.after(duration, dismiss)

    # Allow click to dismiss
    def on_click(event):
        dismiss()

    toast.bind("<Button-1>", on_click)
    frame.bind("<Button-1>", on_click)
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

            # Recalculate X in case window moved/resized
            x_pos = app_x + (app_width - toast_info["width"]) // 2

            if old_y != new_y or x_pos != toast_info["x"]:
                # Animate to new position
                toast = toast_info["toast"]

                # Capture variables in closure scope to avoid B023
                def animate_move(
                    widget, start_x, start_y, end_x, end_y, info_captured, step=0
                ):
                    if step < 10:
                        progress = step / 10
                        eased = 1 - pow(1 - progress, 2)
                        new_x = int(start_x + (end_x - start_x) * eased)
                        new_y_pos = int(start_y + (end_y - start_y) * eased)
                        if widget.winfo_exists():
                            widget.geometry(f"+{new_x}+{new_y_pos}")
                            root.after(
                                16,
                                lambda: animate_move(
                                    widget,
                                    start_x,
                                    start_y,
                                    end_x,
                                    end_y,
                                    info_captured,
                                    step + 1,
                                ),
                            )
                    else:
                        info_captured["x"] = end_x
                        info_captured["y"] = end_y

                animate_move(toast, toast_info["x"], old_y, x_pos, new_y, toast_info)

            current_y = new_y + toast_info["height"] + spacing
