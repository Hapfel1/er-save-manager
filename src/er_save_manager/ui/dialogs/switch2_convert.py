import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from er_save_manager.transfer.switch2 import convert_pc_character
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import open_folder


def open_switch2_converter(parent) -> None:
    dialog = ds.create(parent, "Elden Ring Switch 2 conversion")
    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    paths = {
        "pc": tk.StringVar(),
        "switch": tk.StringVar(),
        "output": tk.StringVar(),
    }
    source_slot = tk.StringVar(value="1")
    target_slot = tk.StringVar(value="1")
    converted_folder: Path | None = None

    def choose_pc() -> None:
        selected = filedialog.askopenfilename(
            parent=dialog,
            title="Choose Elden Ring PC save",
            filetypes=[("Elden Ring save", "*.sl2"), ("All files", "*")],
        )
        if selected:
            paths["pc"].set(selected)

    def choose_directory(key: str, title: str) -> None:
        selected = filedialog.askdirectory(parent=dialog, title=title, mustexist=True)
        if selected:
            paths[key].set(selected)

    def add_path_row(label: str, key: str, command) -> None:
        row = ctk.CTkFrame(main, fg_color="transparent")
        row.pack(fill=tk.X, pady=(10, 0))
        ctk.CTkLabel(row, text=label, font=ds.FONT, anchor="w", width=150).pack(
            side=tk.LEFT
        )
        ctk.CTkEntry(
            row,
            textvariable=paths[key],
            state="readonly",
            font=ds.FONT,
            width=330,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ds.button(row, "Browse…", command, width=90).pack(side=tk.RIGHT)

    def convert() -> None:
        nonlocal converted_folder
        if any(not value.get() for value in paths.values()):
            CTkMessageBox.showwarning(
                "Choose save files",
                "Choose a PC save, Switch SaveKit backup and empty output folder.",
                parent=dialog,
            )
            return
        converted_folder = None
        open_button.configure(state="disabled")
        status.pack_forget()
        status.configure(text="")
        convert_button.configure(state="disabled")
        dialog.update_idletasks()
        try:
            converted_folder = convert_pc_character(
                Path(paths["pc"].get()),
                Path(paths["switch"].get()),
                Path(paths["output"].get()),
                int(source_slot.get()) - 1,
                int(target_slot.get()) - 1,
            )
        except (OSError, ValueError) as error:
            CTkMessageBox.showerror("Conversion failed", str(error), parent=dialog)
            return
        finally:
            convert_button.configure(state="normal")
        open_button.configure(state="normal")
        status.configure(
            text=f"Converted files: {converted_folder}\nWrite this folder with mac2jb SaveKit."
        )
        status.pack(fill=tk.X, pady=(12, 0))
        ds.refit(dialog)

    def open_result() -> None:
        if converted_folder is not None and not open_folder(converted_folder):
            CTkMessageBox.showerror(
                "Could not open folder", str(converted_folder), parent=dialog
            )

    ds.header(main, "Elden Ring Switch 2 conversion", font=ds.TITLE_LARGE)

    add_path_row("PC .sl2 save", "pc", choose_pc)
    add_path_row(
        "Switch SaveKit backup",
        "switch",
        lambda: choose_directory("switch", "Choose complete Switch SaveKit backup"),
    )
    add_path_row(
        "Empty output folder",
        "output",
        lambda: choose_directory("output", "Choose empty output folder"),
    )

    slots = ctk.CTkFrame(main, fg_color="transparent")
    slots.pack(fill=tk.X, pady=(14, 0))
    ctk.CTkLabel(slots, text="PC character", font=ds.FONT).pack(side=tk.LEFT)
    ctk.CTkOptionMenu(
        slots, variable=source_slot, values=[str(i) for i in range(1, 11)], width=60
    ).pack(side=tk.LEFT, padx=(8, 24))
    ctk.CTkLabel(slots, text="Switch character", font=ds.FONT).pack(side=tk.LEFT)
    ctk.CTkOptionMenu(
        slots, variable=target_slot, values=[str(i) for i in range(1, 11)], width=60
    ).pack(side=tk.LEFT, padx=(8, 0))

    status = ctk.CTkLabel(
        main,
        text="",
        font=ds.SMALL,
        text_color=ds.MUTED,
        wraplength=560,
        justify=tk.LEFT,
        anchor="w",
    )
    _, (convert_button, open_button, _) = ds.button_row(
        main,
        [
            {"text": "Convert character", "command": convert, "width": 150},
            {
                "text": "Open converted files",
                "command": open_result,
                "primary": False,
                "width": 155,
            },
            {"text": "Close", "command": dialog.destroy, "primary": False},
        ],
    )
    open_button.configure(state="disabled")
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    ds.finish(dialog, parent, min_width=650)
