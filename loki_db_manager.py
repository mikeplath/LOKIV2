#!/usr/bin/env python3
"""
Database Manager Dialog for LOKI
Provides a GUI for adding new files and re-indexing the database.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

class DatabaseManagerDialog(ctk.CTkToplevel):
    """A dialog for managing the LOKI knowledge base."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("LOKI - Database Manager")
        self.geometry("800x600")
        self.transient(parent)

        self.create_widgets()
        self.center_window()
        self.after(100, self.grab_set)

    def center_window(self):
        """Center the dialog on the parent window."""
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """Create the widgets for the dialog."""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Placeholder label
        label = ctk.CTkLabel(main_frame, text="Database Management Feature - Coming Soon!", font=("Segoe UI", 16, "bold"))
        label.pack(pady=20)
        
        info_text = "This window will contain tools to:\n\n1. Add new PDF files to the library.\n2. Re-index the library to include new files.\n3. Update the vector database for searching."
        info_label = ctk.CTkLabel(main_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=10)

        close_button = ctk.CTkButton(main_frame, text="Close", command=self.destroy)
        close_button.pack(pady=20)

if __name__ == '__main__':
    # This is for testing the dialog independently
    app = ctk.CTk()
    app.title("DB Manager Test")
    
    def open_dialog():
        dialog = DatabaseManagerDialog(app)
        app.wait_window(dialog)

    button = ctk.CTkButton(app, text="Open DB Manager", command=open_dialog)
    button.pack(padx=20, pady=20)
    
    app.mainloop()
