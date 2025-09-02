#!/usr/bin/env python3
"""
Enhanced LOKI Settings Dialog
Comprehensive settings management using the new configuration system
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from loki_config import get_config
except ImportError as e:
    messagebox.showerror("Import Error", f"Could not import configuration system: {e}")
    sys.exit(1)


class EnhancedSettingsDialog(ctk.CTkToplevel):
    """Enhanced settings dialog with comprehensive configuration options"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Window setup
        self.title("LOKI - Enhanced Settings")
        self.geometry("800x600")
        self.minsize(700, 500)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Get configuration
        self.config = get_config()
        self.result = None
        self.changes_made = False
        
        # Create the interface
        self.create_interface()
        
        # Load current values
        self.load_current_settings()
        
        # Center the window
        self.center_window()
        
        # Focus and wait
        self.focus_set()
        
    def center_window(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_interface(self):
        """Create the settings interface"""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create notebook for different setting categories
        self.notebook = ctk.CTkTabview(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create tabs
        self.create_llm_tab()
        self.create_gui_tab()
        self.create_search_tab()
        self.create_performance_tab()
        self.create_emergency_tab()
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Buttons
        ctk.CTkButton(
            button_frame, 
            text="Apply", 
            command=self.apply_settings
        ).pack(side=tk.LEFT, padx=5)
        
        ctk.CTkButton(
            button_frame, 
            text="OK", 
            command=self.ok_clicked
        ).pack(side=tk.LEFT, padx=5)
        
        ctk.CTkButton(
            button_frame, 
            text="Cancel", 
            command=self.cancel_clicked
        ).pack(side=tk.LEFT, padx=5)
        
        ctk.CTkButton(
            button_frame, 
            text="Reset to Defaults", 
            command=self.reset_to_defaults
        ).pack(side=tk.RIGHT, padx=5)
        
        ctk.CTkButton(
            button_frame, 
            text="Validate", 
            command=self.validate_settings
        ).pack(side=tk.RIGHT, padx=5)
    
    def create_llm_tab(self):
        """Create LLM settings tab"""
        llm_tab = self.notebook.add("LLM Settings")
        
        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(llm_tab)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Model selection
        model_frame = ctk.CTkFrame(scroll_frame)
        model_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(model_frame, text="Default Model:").pack(anchor=tk.W, padx=10, pady=5)
        
        model_select_frame = ctk.CTkFrame(model_frame)
        model_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.model_var = tk.StringVar()
        self.model_dropdown = ctk.CTkOptionMenu(
            model_select_frame, 
            variable=self.model_var,
            values=["Loading..."]
        )
        self.model_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ctk.CTkButton(
            model_select_frame,
            text="Browse...",
            command=self.browse_model
        ).pack(side=tk.RIGHT)
        
        ctk.CTkButton(
            model_select_frame,
            text="Refresh",
            command=self.refresh_models
        ).pack(side=tk.RIGHT, padx=(0, 5))
        
        # Context size
        context_frame = ctk.CTkFrame(scroll_frame)
        context_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(context_frame, text="Context Size:").pack(anchor=tk.W, padx=10, pady=5)
        
        context_input_frame = ctk.CTkFrame(context_frame)
        context_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.context_var = tk.StringVar()
        context_entry = ctk.CTkEntry(
            context_input_frame, 
            textvariable=self.context_var,
            width=100
        )
        context_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ctk.CTkLabel(
            context_input_frame, 
            text="Range: 512-32768 (Default: 8192)\nLarger values use more memory but allow longer conversations"
        ).pack(side=tk.LEFT, anchor=tk.W)
        
        # Temperature
        temp_frame = ctk.CTkFrame(scroll_frame)
        temp_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(temp_frame, text="Temperature:").pack(anchor=tk.W, padx=10, pady=5)
        
        temp_input_frame = ctk.CTkFrame(temp_frame)
        temp_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.temp_var = tk.StringVar()
        temp_entry = ctk.CTkEntry(
            temp_input_frame, 
            textvariable=self.temp_var,
            width=100
        )
        temp_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ctk.CTkLabel(
            temp_input_frame, 
            text="Range: 0.0-1.0 (Default: 0.7)\nLower = more focused, Higher = more creative"
        ).pack(side=tk.LEFT, anchor=tk.W)
        
        # Max tokens
        tokens_frame = ctk.CTkFrame(scroll_frame)
        tokens_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(tokens_frame, text="Max Response Tokens:").pack(anchor=tk.W, padx=10, pady=5)
        
        tokens_input_frame = ctk.CTkFrame(tokens_frame)
        tokens_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.tokens_var = tk.StringVar()
        tokens_entry = ctk.CTkEntry(
            tokens_input_frame, 
            textvariable=self.tokens_var,
            width=100
        )
        tokens_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ctk.CTkLabel(
            tokens_input_frame, 
            text="Range: 128-4096 (Default: 1024)\nMaximum length of AI responses"
        ).pack(side=tk.LEFT, anchor=tk.W)
        
        # Instructions
        instructions_frame = ctk.CTkFrame(scroll_frame)
        instructions_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(instructions_frame, text="Instructions:").pack(anchor=tk.W, padx=10, pady=5)
        
        self.use_custom_instructions = tk.BooleanVar()
        ctk.CTkCheckBox(
            instructions_frame,
            text="Use Custom Instructions",
            variable=self.use_custom_instructions,
            command=self.toggle_instructions
        ).pack(anchor=tk.W, padx=10)
        
        instr_select_frame = ctk.CTkFrame(instructions_frame)
        instr_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.instructions_var = tk.StringVar()
        self.instructions_dropdown = ctk.CTkOptionMenu(
            instr_select_frame,
            variable=self.instructions_var,
            values=["Loading..."]
        )
        self.instructions_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ctk.CTkButton(
            instr_select_frame,
            text="Edit...",
            command=self.edit_instructions
        ).pack(side=tk.RIGHT)
    
    def create_gui_tab(self):
        """Create GUI settings tab"""
        gui_tab = self.notebook.add("GUI Settings")
        
        scroll_frame = ctk.CTkScrollableFrame(gui_tab)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Theme
        theme_frame = ctk.CTkFrame(scroll_frame)
        theme_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(theme_frame, text="Theme:").pack(anchor=tk.W, padx=10, pady=5)
        
        self.theme_var = tk.StringVar()
        ctk.CTkOptionMenu(
            theme_frame,
            variable=self.theme_var,
            values=["system", "dark", "light"]
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        # Default search mode
        search_mode_frame = ctk.CTkFrame(scroll_frame)
        search_mode_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(search_mode_frame, text="Default Search Mode:").pack(anchor=tk.W, padx=10, pady=5)
        
        self.search_mode_var = tk.StringVar()
        ctk.CTkOptionMenu(
            search_mode_frame,
            variable=self.search_mode_var,
            values=["vector", "vector_llm", "llm_chat"]
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        # Font size
        font_frame = ctk.CTkFrame(scroll_frame)
        font_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(font_frame, text="Font Size:").pack(anchor=tk.W, padx=10, pady=5)
        
        font_input_frame = ctk.CTkFrame(font_frame)
        font_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.font_size_var = tk.StringVar()
        ctk.CTkEntry(
            font_input_frame,
            textvariable=self.font_size_var,
            width=60
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ctk.CTkLabel(
            font_input_frame,
            text="Range: 8-20 (Default: 11)"
        ).pack(side=tk.LEFT)
        
        # Options
        options_frame = ctk.CTkFrame(scroll_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(options_frame, text="Options:").pack(anchor=tk.W, padx=10, pady=5)
        
        self.auto_save_chat = tk.BooleanVar()
        ctk.CTkCheckBox(
            options_frame,
            text="Auto-save chat history",
            variable=self.auto_save_chat
        ).pack(anchor=tk.W, padx=10)
        
        self.show_timestamps = tk.BooleanVar()
        ctk.CTkCheckBox(
            options_frame,
            text="Show timestamps in chat",
            variable=self.show_timestamps
        ).pack(anchor=tk.W, padx=10)
    
    def create_search_tab(self):
        """Create search settings tab"""
        search_tab = self.notebook.add("Search Settings")
        
        scroll_frame = ctk.CTkScrollableFrame(search_tab)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Max results
        results_frame = ctk.CTkFrame(scroll_frame)
        results_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(results_frame, text="Maximum Results:").pack(anchor=tk.W, padx=10, pady=5)
        
        results_input_frame = ctk.CTkFrame(results_frame)
        results_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.max_results_var = tk.StringVar()
        ctk.CTkEntry(
            results_input_frame,
            textvariable=self.max_results_var,
            width=60
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ctk.CTkLabel(
            results_input_frame,
            text="Range: 1-20 (Default: 5)"
        ).pack(side=tk.LEFT)
        
        # Minimum similarity
        similarity_frame = ctk.CTkFrame(scroll_frame)
        similarity_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(similarity_frame, text="Minimum Similarity:").pack(anchor=tk.W, padx=10, pady=5)
        
        similarity_input_frame = ctk.CTkFrame(similarity_frame)
        similarity_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.min_similarity_var = tk.StringVar()
        ctk.CTkEntry(
            similarity_input_frame,
            textvariable=self.min_similarity_var,
            width=60
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ctk.CTkLabel(
            similarity_input_frame,
            text="Range: 0.0-1.0 (Default: 0.3)\nLower values return more results"
        ).pack(side=tk.LEFT)
    
    def create_performance_tab(self):
        """Create performance settings tab"""
        perf_tab = self.notebook.add("Performance")
        
        scroll_frame = ctk.CTkScrollableFrame(perf_tab)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Streaming
        streaming_frame = ctk.CTkFrame(scroll_frame)
        streaming_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(streaming_frame, text="Streaming:").pack(anchor=tk.W, padx=10, pady=5)
        
        self.enable_streaming = tk.BooleanVar()
        ctk.CTkCheckBox(
            streaming_frame,
            text="Enable streaming responses",
            variable=self.enable_streaming
        ).pack(anchor=tk.W, padx=10)
        
        batch_frame = ctk.CTkFrame(streaming_frame)
        batch_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(batch_frame, text="Streaming Batch Size:").pack(anchor=tk.W)
        
        self.streaming_batch_var = tk.StringVar()
        ctk.CTkEntry(
            batch_frame,
            textvariable=self.streaming_batch_var,
            width=60
        ).pack(anchor=tk.W, pady=5)
        
        # Timeout
        timeout_frame = ctk.CTkFrame(scroll_frame)
        timeout_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(timeout_frame, text="Response Timeout (seconds):").pack(anchor=tk.W, padx=10, pady=5)
        
        timeout_input_frame = ctk.CTkFrame(timeout_frame)
        timeout_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.timeout_var = tk.StringVar()
        ctk.CTkEntry(
            timeout_input_frame,
            textvariable=self.timeout_var,
            width=60
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ctk.CTkLabel(
            timeout_input_frame,
            text="Default: 300 (5 minutes)"
        ).pack(side=tk.LEFT)
    
    def create_emergency_tab(self):
        """Create emergency settings tab"""
        emergency_tab = self.notebook.add("Emergency")
        
        scroll_frame = ctk.CTkScrollableFrame(emergency_tab)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # STOP command
        stop_frame = ctk.CTkFrame(scroll_frame)
        stop_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(stop_frame, text="Emergency STOP Command:").pack(anchor=tk.W, padx=10, pady=5)
        
        self.enable_stop_command = tk.BooleanVar()
        ctk.CTkCheckBox(
            stop_frame,
            text="Enable STOP command",
            variable=self.enable_stop_command
        ).pack(anchor=tk.W, padx=10)
        
        stop_word_frame = ctk.CTkFrame(stop_frame)
        stop_word_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(stop_word_frame, text="STOP command word:").pack(anchor=tk.W)
        
        self.stop_word_var = tk.StringVar()
        ctk.CTkEntry(
            stop_word_frame,
            textvariable=self.stop_word_var,
            width=100
        ).pack(anchor=tk.W, pady=5)
        
        ctk.CTkLabel(
            stop_frame,
            text="Type this word (in all caps) to immediately halt AI responses",
            font=("Arial", 10)
        ).pack(anchor=tk.W, padx=10)
        
        # Offline mode
        offline_frame = ctk.CTkFrame(scroll_frame)
        offline_frame.pack(fill=tk.X, pady=5)
        
        self.offline_mode = tk.BooleanVar()
        ctk.CTkCheckBox(
            offline_frame,
            text="Offline mode (disable all network features)",
            variable=self.offline_mode
        ).pack(anchor=tk.W, padx=10, pady=10)
    
    def load_current_settings(self):
        """Load current settings from configuration"""
        # LLM settings
        self.context_var.set(str(self.config.get("llm.context_size", 8192)))
        self.temp_var.set(str(self.config.get("llm.temperature", 0.7)))
        self.tokens_var.set(str(self.config.get("llm.max_tokens", 1024)))
        self.use_custom_instructions.set(self.config.get("llm.use_custom_instructions", True))
        
        # GUI settings
        self.theme_var.set(self.config.get("gui.theme", "system"))
        self.search_mode_var.set(self.config.get("gui.search_mode", "vector_llm"))
        self.font_size_var.set(str(self.config.get("gui.font_size", 11)))
        self.auto_save_chat.set(self.config.get("gui.auto_save_chat", True))
        self.show_timestamps.set(self.config.get("gui.show_timestamps", True))
        
        # Search settings
        self.max_results_var.set(str(self.config.get("search.max_results", 5)))
        self.min_similarity_var.set(str(self.config.get("search.min_similarity", 0.3)))
        
        # Performance settings
        self.enable_streaming.set(self.config.get("performance.enable_streaming", True))
        self.streaming_batch_var.set(str(self.config.get("performance.streaming_batch_size", 64)))
        self.timeout_var.set(str(self.config.get("performance.response_timeout", 300)))
        
        # Emergency settings
        self.enable_stop_command.set(self.config.get("emergency.enable_stop_command", True))
        self.stop_word_var.set(self.config.get("emergency.stop_command_word", "STOP"))
        self.offline_mode.set(self.config.get("emergency.offline_mode", True))
        
        # Load models and instructions
        self.refresh_models()
        self.refresh_instructions()
        
        # Set current selections
        current_model = self.config.get("llm.default_model", "")
        if current_model:
            self.model_var.set(os.path.basename(current_model))
        
        current_instructions = self.config.get("llm.active_instructions", "")
        if current_instructions:
            self.instructions_var.set(current_instructions)
    
    def refresh_models(self):
        """Refresh the list of available models"""
        try:
            models = self.config.list_available_models()
            model_names = [os.path.basename(model) for model in models]
            
            if model_names:
                self.model_dropdown.configure(values=model_names)
            else:
                self.model_dropdown.configure(values=["No models found"])
        except Exception as e:
            messagebox.showerror("Error", f"Could not refresh models: {e}")
    
    def refresh_instructions(self):
        """Refresh the list of available instructions"""
        try:
            instructions = self.config.list_available_instructions()
            
            if instructions:
                self.instructions_dropdown.configure(values=instructions)
            else:
                self.instructions_dropdown.configure(values=["No instructions found"])
        except Exception as e:
            messagebox.showerror("Error", f"Could not refresh instructions: {e}")
    
    def browse_model(self):
        """Browse for a model file"""
        filetypes = [
            ("Model files", "*.gguf *.bin"),
            ("GGUF files", "*.gguf"),
            ("Binary files", "*.bin"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select LLM Model",
            filetypes=filetypes
        )
        
        if filename:
            self.model_var.set(os.path.basename(filename))
            self.config.set("llm.default_model", filename)
            self.changes_made = True
    
    def toggle_instructions(self):
        """Toggle instructions dropdown enabled state"""
        enabled = self.use_custom_instructions.get()
        state = "normal" if enabled else "disabled"
        self.instructions_dropdown.configure(state=state)
    
    def edit_instructions(self):
        """Open instructions editor (placeholder for now)"""
        messagebox.showinfo("Coming Soon", "Instructions editor will be available in the next update!")
    
    def validate_settings(self):
        """Validate current settings"""
        issues = []
        
        # Validate numeric inputs
        try:
            context_size = int(self.context_var.get())
            if context_size < 512 or context_size > 32768:
                issues.append("Context size must be between 512 and 32768")
        except ValueError:
            issues.append("Context size must be a valid number")
        
        try:
            temperature = float(self.temp_var.get())
            if temperature < 0.0 or temperature > 1.0:
                issues.append("Temperature must be between 0.0 and 1.0")
        except ValueError:
            issues.append("Temperature must be a valid number")
        
        try:
            max_tokens = int(self.tokens_var.get())
            if max_tokens < 128 or max_tokens > 4096:
                issues.append("Max tokens must be between 128 and 4096")
        except ValueError:
            issues.append("Max tokens must be a valid number")
        
        # Show validation results
        if issues:
            messagebox.showerror("Validation Failed", "\n".join(issues))
        else:
            messagebox.showinfo("Validation Passed", "All settings are valid!")
    
    def apply_settings(self):
        """Apply settings without closing dialog"""
        if self.save_settings():
            messagebox.showinfo("Settings Applied", "Settings have been saved successfully!")
    
    def save_settings(self):
        """Save current settings to configuration"""
        try:
            # LLM settings
            self.config.set("llm.context_size", int(self.context_var.get()))
            self.config.set("llm.temperature", float(self.temp_var.get()))
            self.config.set("llm.max_tokens", int(self.tokens_var.get()))
            self.config.set("llm.use_custom_instructions", self.use_custom_instructions.get())
            
            # Set model path
            model_name = self.model_var.get()
            if model_name and model_name != "No models found":
                model_path = self.config.get_model_path(model_name)
                if model_path:
                    self.config.set("llm.default_model", model_path)
            
            # Set instructions
            instructions_name = self.instructions_var.get()
            if instructions_name and instructions_name != "No instructions found":
                self.config.set("llm.active_instructions", instructions_name)
            
            # GUI settings
            self.config.set("gui.theme", self.theme_var.get())
            self.config.set("gui.search_mode", self.search_mode_var.get())
            self.config.set("gui.font_size", int(self.font_size_var.get()))
            self.config.set("gui.auto_save_chat", self.auto_save_chat.get())
            self.config.set("gui.show_timestamps", self.show_timestamps.get())
            
            # Search settings
            self.config.set("search.max_results", int(self.max_results_var.get()))
            self.config.set("search.min_similarity", float(self.min_similarity_var.get()))
            
            # Performance settings
            self.config.set("performance.enable_streaming", self.enable_streaming.get())
            self.config.set("performance.streaming_batch_size", int(self.streaming_batch_var.get()))
            self.config.set("performance.response_timeout", int(self.timeout_var.get()))
            
            # Emergency settings
            self.config.set("emergency.enable_stop_command", self.enable_stop_command.get())
            self.config.set("emergency.stop_command_word", self.stop_word_var.get())
            self.config.set("emergency.offline_mode", self.offline_mode.get())
            
            self.changes_made = True
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", 
                              "Are you sure you want to reset all settings to defaults? This cannot be undone."):
            self.config.reset_to_defaults()
            self.load_current_settings()
            messagebox.showinfo("Settings Reset", "All settings have been reset to defaults.")
    
    def ok_clicked(self):
        """Handle OK button click"""
        if self.save_settings():
            self.result = "ok"
            self.destroy()
    
    def cancel_clicked(self):
        """Handle Cancel button click"""
        if self.changes_made:
            if messagebox.askyesno("Unsaved Changes", 
                                 "You have unsaved changes. Are you sure you want to cancel?"):
                self.destroy()
        else:
            self.destroy()


def main():
    """Test the enhanced settings dialog"""
    root = ctk.CTk()
    root.withdraw()  # Hide the root window
    
    dialog = EnhancedSettingsDialog(root)
    root.mainloop()


if __name__ == "__main__":
    main()
