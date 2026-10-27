"""
Troubleshooter Installation Dialog
Shows when user clicks Troubleshooting button
"""

import threading
import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.toast import notify


def show_troubleshooter_dialog(parent, addon_manager):
    """
    Show troubleshooter installation/launch dialog

    Args:
        parent: Parent window
        addon_manager: TroubleshooterAddon instance
    """

    is_installed = addon_manager.is_installed()
    has_update, latest_version = addon_manager.check_for_updates()
    installed_version = addon_manager.get_installed_version()

    if is_installed and not has_update:

        def show_error(msg):
            CTkMessageBox.showerror("Launch Failed", msg, parent=parent)

        if addon_manager.launch(show_error=show_error):
            return
        else:
            return

    dialog = ds.create(
        parent,
        "Troubleshooter Update Available"
        if is_installed
        else "Install Troubleshooter Addon",
    )
    main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=16)

    def on_install():
        """Install/update handler"""
        install_btn.configure(state="disabled")
        cancel_btn.configure(state="disabled")
        progress_label.configure(text_color=ds.MUTED)
        progress_label.pack(fill=tk.X, pady=(10, 0))

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

            def show_error(msg):
                CTkMessageBox.showwarning("Launch Failed", msg, parent=parent)

            if addon_manager.launch(show_error=show_error):
                notify(
                    parent,
                    "Troubleshooter installed and launched successfully.",
                    "success",
                )
        else:
            progress_var.set("Installation failed.")
            progress_label.configure(text_color=ds.ERROR)
            install_btn.configure(state="normal")
            cancel_btn.configure(state="normal")

    def on_launch_skip():
        """Launch the installed version without updating"""
        dialog.destroy()

        def show_error(msg):
            CTkMessageBox.showerror("Launch Failed", msg, parent=parent)

        addon_manager.launch(show_error=show_error)

    if is_installed:
        buttons = [
            {"text": "Update & Launch", "command": on_install, "width": 150},
            {
                "text": "Launch Current Version",
                "command": on_launch_skip,
                "primary": False,
                "width": 180,
            },
        ]
    else:
        buttons = [
            {"text": "Install & Launch", "command": on_install, "width": 150},
            {"text": "Cancel", "command": dialog.destroy, "primary": False},
        ]
    _, (install_btn, cancel_btn) = ds.button_row(main_frame, buttons)

    # Shown once an install starts
    progress_var = tk.StringVar(value="")
    progress_label = ctk.CTkLabel(
        main_frame,
        textvariable=progress_var,
        font=ds.FONT,
        text_color=ds.MUTED,
        anchor="w",
    )

    ds.header(
        main_frame,
        "Update Available" if is_installed else "FromSoftware Troubleshooter",
        font=ds.TITLE_LARGE,
    )
    ctk.CTkLabel(
        main_frame,
        text=f"Version {latest_version} is available"
        if is_installed
        else "Diagnostic tool addon for common issues",
        font=ds.FONT,
        text_color=ds.MUTED,
        anchor="w",
    ).pack(fill=tk.X, pady=(2, 0))

    versions = ds.box(main_frame, pady=(12, 10))
    rows = [("Latest version", latest_version)]
    if is_installed:
        rows.insert(0, ("Current version", installed_version))
    for i, (label, value) in enumerate(rows):
        pady = (8 if i == 0 else 2, 8 if i == len(rows) - 1 else 2)
        ctk.CTkLabel(versions, text=label, font=ds.FONT, text_color=ds.MUTED).grid(
            row=i, column=0, sticky="w", padx=(12, 24), pady=pady
        )
        ctk.CTkLabel(versions, text=str(value), font=ds.BOLD).grid(
            row=i, column=1, sticky="w", padx=(0, 12), pady=pady
        )

    ctk.CTkLabel(
        main_frame,
        text="The FromSoftware Troubleshooter helps diagnose and fix common issues:",
        font=ds.BOLD,
        anchor="w",
    ).pack(fill=tk.X, pady=(4, 2))
    checks = ds.box(main_frame, pady=(0, 0))
    items = (
        "Game installation & folder",
        "Problematic running processes",
        "VPN clients",
        "Steam running as administrator",
    )
    for i, text in enumerate(items):
        ctk.CTkLabel(checks, text=f"•  {text}", font=ds.FONT, anchor="w").pack(
            fill=tk.X,
            padx=12,
            pady=(8 if i == 0 else 2, 8 if i == len(items) - 1 else 2),
        )
    ctk.CTkLabel(
        main_frame,
        text="Source: github.com/Hapfel1/fromsoftware-troubleshooter",
        font=ds.SMALL,
        text_color=ds.MUTED,
        anchor="w",
    ).pack(fill=tk.X, pady=(8, 0))

    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    ds.finish(dialog, parent, min_width=440)
