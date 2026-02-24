"""
Troubleshooter Installation Dialog
Shows when user clicks Troubleshooting button
"""

import threading
import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import force_render_dialog


def show_troubleshooter_dialog(parent, addon_manager):
    """
    Show troubleshooter installation/launch dialog

    Args:
        parent: Parent window
        addon_manager: TroubleshooterAddon instance
    """

    # Check installation status and updates
    is_installed = addon_manager.is_installed()
    has_update, latest_version = addon_manager.check_for_updates()
    installed_version = addon_manager.get_installed_version()

    # If installed and no updates, just launch
    if is_installed and not has_update:

        def show_error(msg):
            CTkMessageBox.showerror("Launch Failed", msg, parent=parent)

        if addon_manager.launch(show_error=show_error):
            return
        else:
            return

    # Show install/update dialog
    dialog = ctk.CTkToplevel(parent)

    if is_installed:
        dialog.title("Troubleshooter Update Available")
    else:
        dialog.title("Install Troubleshooter Addon")

    dialog.geometry("550x400")
    dialog.resizable(False, False)
    dialog.transient(parent)

    force_render_dialog(dialog)
    dialog.grab_set()

    # Center dialog
    dialog.update_idletasks()
    parent.update_idletasks()
    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    x = parent_x + (parent_width // 2) - (275)
    y = parent_y + (parent_height // 2) - (200)
    dialog.geometry(f"550x400+{x}+{y}")

    main_frame = ctk.CTkFrame(dialog)
    main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

    # Title
    if is_installed:
        title_text = "Update Available"
        subtitle_text = f"Version {latest_version} is available"
    else:
        title_text = "FromSoftware Troubleshooter"
        subtitle_text = "Diagnostic tool addon for common issues"

    ctk.CTkLabel(
        main_frame,
        text=title_text,
        font=("Segoe UI", 16, "bold"),
    ).pack(pady=(0, 5))

    ctk.CTkLabel(
        main_frame,
        text=subtitle_text,
        font=("Segoe UI", 11),
        text_color=("gray40", "gray70"),
    ).pack(pady=(0, 15))

    # Version info
    info_frame = ctk.CTkFrame(main_frame, fg_color=("gray90", "gray20"))
    info_frame.pack(fill=tk.X, pady=(0, 15))

    if is_installed:
        ctk.CTkLabel(
            info_frame,
            text=f"Current Version: {installed_version}\nLatest Version: {latest_version}",
            font=("Segoe UI", 11),
        ).pack(padx=12, pady=10)
    else:
        ctk.CTkLabel(
            info_frame,
            text=f"Latest Version: {latest_version}",
            font=("Segoe UI", 11),
        ).pack(padx=12, pady=10)

    # Description
    desc_frame = ctk.CTkFrame(main_frame, fg_color=("gray90", "gray20"))
    desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

    desc_text = """The FromSoftware Troubleshooter helps diagnose and fix common issues:

✓ Game installation & folder
✓ Problematic running processes
✓ VPN clients
✓ Steam running as administrator

Source: github.com/Hapfel1/fromsoftware-troubleshooter"""

    ctk.CTkLabel(
        desc_frame,
        text=desc_text,
        font=("Segoe UI", 11),
        justify=tk.LEFT,
    ).pack(padx=12, pady=10, anchor="w")

    # Progress label (hidden initially)
    progress_var = tk.StringVar(value="")
    progress_label = ctk.CTkLabel(
        main_frame,
        textvariable=progress_var,
        font=("Segoe UI", 11),
        text_color=("gray40", "gray70"),
    )

    # Buttons
    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(pady=(10, 0))

    def on_install():
        """Install/update handler"""
        # Disable buttons
        install_btn.configure(state="disabled")
        cancel_btn.configure(state="disabled")

        # Show progress
        progress_label.pack(pady=(10, 0))

        def install_thread():
            def update_progress(msg):
                progress_var.set(msg)

            success = addon_manager.download_and_install(
                latest_version, progress_callback=update_progress
            )

            # Update UI on main thread
            dialog.after(0, lambda: on_install_complete(success))

        threading.Thread(target=install_thread, daemon=True).start()

    def on_install_complete(success):
        """Handle installation completion"""
        if success:
            dialog.destroy()

            # Launch the troubleshooter
            def show_error(msg):
                CTkMessageBox.showwarning("Launch Failed", msg, parent=parent)

            if addon_manager.launch(show_error=show_error):
                CTkMessageBox.showinfo(
                    "Success",
                    "Troubleshooter installed and launched successfully!",
                    parent=parent,
                )
        else:
            progress_var.set("Installation failed!")
            install_btn.configure(state="normal")
            cancel_btn.configure(state="normal")

    def on_launch_skip():
        """Launch existing installation or cancel"""
        if is_installed:
            dialog.destroy()

            def show_error(msg):
                CTkMessageBox.showerror("Launch Failed", msg, parent=parent)

            addon_manager.launch(show_error=show_error)
        else:
            dialog.destroy()

    if is_installed:
        install_btn = ctk.CTkButton(
            button_frame,
            text="Update & Launch",
            command=on_install,
            width=150,
        )
    else:
        install_btn = ctk.CTkButton(
            button_frame,
            text="Install & Launch",
            command=on_install,
            width=150,
        )
    install_btn.pack(side=tk.LEFT, padx=5)

    if is_installed:
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Launch Current Version",
            command=on_launch_skip,
            width=180,
            fg_color=("gray70", "gray30"),
        )
    else:
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            width=100,
            fg_color=("gray70", "gray30"),
        )
    cancel_btn.pack(side=tk.LEFT, padx=5)
