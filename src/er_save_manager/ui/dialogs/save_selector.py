"""
Save Selector Dialog
Dialog for selecting from multiple save files
"""

import tkinter as tk
from tkinter import ttk


class SaveSelectorDialog:
    """Dialog for selecting from multiple save files"""
    
    @staticmethod
    def show(parent, saves, callback):
        """
        Show save selector dialog
        
        Args:
            parent: Parent window
            saves: List of Path objects for save files
            callback: Function to call with selected save path
        """
        dialog = tk.Toplevel(parent)
        dialog.title("Select Save File")
        dialog.geometry("600x350")
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"600x350+{x}+{y}")
        
        ttk.Label(
            dialog,
            text=f"Found {len(saves)} save files:",
            font=("Segoe UI", 11, "bold"),
            padding=15,
        ).pack()
        
        listbox_frame = ttk.Frame(dialog, padding=15)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(
            listbox_frame, yscrollcommand=scrollbar.set, font=("Consolas", 9)
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        for save in saves:
            listbox.insert(tk.END, str(save))
        
        def select_save():
            selection = listbox.curselection()
            if selection:
                callback(str(saves[selection[0]]))
                dialog.destroy()
        
        ttk.Button(
            dialog, text="Select", command=select_save, width=15
        ).pack(pady=15)
        
        listbox.bind("<Double-Button-1>", lambda e: select_save())
