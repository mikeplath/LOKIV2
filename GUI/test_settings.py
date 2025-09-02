#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import customtkinter as ctk
from loki_settings_dialog import EnhancedSettingsDialog

def test_settings():
    root = ctk.CTk()
    root.geometry("400x300")
    root.title("Test Parent Window")
    
    def open_settings():
        dialog = EnhancedSettingsDialog(root)
    
    button = ctk.CTkButton(root, text="Open Settings", command=open_settings)
    button.pack(pady=50)
    
    root.mainloop()

if __name__ == "__main__":
    test_settings()
