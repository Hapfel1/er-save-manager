"""Utility functions for UI components."""


def bind_mousewheel(widget, target_widget=None):
    """
    Bind mousewheel scrolling to a CTkScrollableFrame.

    Args:
        widget: The widget to bind events to (usually the scrollable frame)
        target_widget: The widget to scroll (defaults to widget if None)
    """
    if target_widget is None:
        target_widget = widget

    def _on_mousewheel(event):
        # For CTkScrollableFrame, use _parent_canvas
        if hasattr(target_widget, "_parent_canvas"):
            try:
                canvas = target_widget._parent_canvas
                if canvas and hasattr(canvas, "yview_scroll"):
                    # Scroll up (negative delta) or down (positive delta)
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        # Fallback for regular tk Canvas/Frame
        elif hasattr(target_widget, "yview_scroll"):
            try:
                target_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

    # Bind to the main widget
    try:
        widget.bind("<MouseWheel>", _on_mousewheel, add="+")
    except Exception:
        pass

    # Recursively bind to all children up to a reasonable depth
    def bind_children(w, depth=0):
        if depth > 5:  # Prevent infinite recursion
            return
        try:
            for child in w.winfo_children():
                child.bind("<MouseWheel>", _on_mousewheel, add="+")
                bind_children(child, depth + 1)
        except Exception:
            pass

    bind_children(widget)
