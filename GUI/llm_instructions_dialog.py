#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import customtkinter as ctk

class LLMInstructionsDialog(tk.Toplevel):
    """Dialog for editing LLM instructions."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Set window properties
        self.title("LOKI - LLM Instructions Editor")
        self.geometry("800x600")
        self.resizable(True, True)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Set paths
        self.loki_dir = '/home/mike/LOKI'
        self.instructions_dir = os.path.join(self.loki_dir, 'LLM', 'instructions')
        self.default_instructions_path = os.path.join(self.instructions_dir, 'default_instructions.txt')
        self.user_instructions_path = os.path.join(self.instructions_dir, 'user_instructions.txt')
        
        # Make sure directories exist
        os.makedirs(self.instructions_dir, exist_ok=True)
        
        # Set variables
        self.result = None
        self.use_custom_instructions = tk.BooleanVar(value=True)
        
        # Create UI components
        self.create_widgets()
        
        # Load instructions
        self.load_instructions()
        
        # Center the dialog on the parent window
        self.center_on_parent()
        
        # Set focus to the dialog and wait for it to be closed
        self.focus_set()
        self.wait_window()
    
    def center_on_parent(self):
        """Center the dialog on the parent window."""
        parent = self.master
        
        # Calculate position
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        
        # Set position
        self.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """Create the UI elements."""
        # Create main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header label
        header_label = ttk.Label(main_frame, text="LLM Instructions Editor", 
                              font=("TkDefaultFont", 16, "bold"))
        header_label.pack(fill=tk.X, pady=(0, 10))
        
        # Create help text
        help_text = "These instructions control how the AI responds to queries. The instructions are provided to the LLM for every query."
        help_text += "\nBe direct and specific in your instructions to get the best results."
        
        help_label = ttk.Label(main_frame, text=help_text, wraplength=780, justify="left")
        help_label.pack(fill=tk.X, pady=(0, 10))
        
        # Create text area
        self.text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=("TkFixedFont", 12))
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create checkbox for using custom instructions
        use_custom_checkbox = ttk.Checkbutton(
            main_frame, 
            text="Use custom instructions (when unchecked, default instructions are used)",
            variable=self.use_custom_instructions
        )
        use_custom_checkbox.pack(fill=tk.X, pady=(10, 5))
        
        # Create buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Create reset button
        reset_button = ttk.Button(buttons_frame, text="Reset to Default", command=self.reset_to_default)
        reset_button.pack(side=tk.LEFT, padx=5)
        
        # Create spacer
        spacer = ttk.Frame(buttons_frame)
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create cancel button
        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Create save button
        save_button = ttk.Button(buttons_frame, text="Save", command=self.on_save)
        save_button.pack(side=tk.RIGHT, padx=5)
    
    def load_instructions(self):
        """Load the instructions from file."""
        try:
            # Try to load user instructions first
            if os.path.exists(self.user_instructions_path):
                with open(self.user_instructions_path, 'r', encoding='utf-8') as f:
                    instructions = f.read()
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, instructions)
                    self.use_custom_instructions.set(True)
            
            # If no user instructions, load default instructions
            elif os.path.exists(self.default_instructions_path):
                with open(self.default_instructions_path, 'r', encoding='utf-8') as f:
                    instructions = f.read()
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, instructions)
                    
                    # Also create a user copy
                    with open(self.user_instructions_path, 'w', encoding='utf-8') as f_user:
                        f_user.write(instructions)
                    
                    self.use_custom_instructions.set(True)
            
            else:
                # If neither file exists, show an error
                messagebox.showerror("Error", "Could not find instructions files.")
                self.on_cancel()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load instructions: {str(e)}")
            self.on_cancel()
    
    def reset_to_default(self):
        """Reset to default instructions."""
        try:
            if os.path.exists(self.default_instructions_path):
                with open(self.default_instructions_path, 'r', encoding='utf-8') as f:
                    default_instructions = f.read()
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, default_instructions)
            else:
                messagebox.showwarning("Warning", "Default instructions file not found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset instructions: {str(e)}")
    
    def on_save(self):
        """Handle Save button click."""
        try:
            # Get text from text area
            instructions = self.text_area.get(1.0, tk.END)
            
            # Make sure the directory exists
            os.makedirs(os.path.dirname(self.user_instructions_path), exist_ok=True)
            
            # Write to file
            with open(self.user_instructions_path, 'w', encoding='utf-8') as f:
                f.write(instructions)
            
            # Save the use_custom_instructions setting
            self.save_settings()
            
            self.result = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save instructions: {str(e)}")
    
    def on_cancel(self):
        """Handle Cancel button click."""
        self.result = False
        self.destroy()
    
    def save_settings(self):
        """Save the settings file."""
        try:
            settings_dir = os.path.join(self.loki_dir, 'LLM')
            settings_path = os.path.join(settings_dir, 'llm_settings.json')
            
            import json
            
            # Load existing settings if available
            settings = {}
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except:
                    pass
            
            # Update settings
            settings['use_custom_instructions'] = self.use_custom_instructions.get()
            
            # Save settings
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
        
        except Exception as e:
            print(f"Error saving settings: {str(e)}")
