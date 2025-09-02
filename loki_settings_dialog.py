#!/usr/bin/env python3
"""
LOKI Enhanced Settings Dialog
Advanced settings management with tabbed interface and validation
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from loki_config import get_config
except ImportError:
    # Fallback if loki_config not available
    class DummyConfig:
        def get(self, key, default=None):
            return default
        def set(self, key, value):
            pass
        def save(self):
            pass
        def list_available_models(self):
            return []
    
    def get_config():
        return DummyConfig()


class EnhancedSettingsDialog(ctk.CTkToplevel):
    """Enhanced settings dialog with tabbed interface"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("LOKI - Enhanced Settings")
        self.geometry("700x550")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Result tracking
        self.result = None
        self.config = get_config()
        
        # Create the interface
        self.create_interface()
        
        # Load current settings
        self.load_current_settings()
        
        # Center window
        self.center_window()
        
        # Wait for dialog completion
        self.wait_window()
    
    def center_window(self):
        """Center the dialog window"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_interface(self):
        """Create the main interface"""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create tabbed interface
        self.notebook = ctk.CTkTabview(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create tabs
        self.create_llm_tab()
        self.create_search_tab()
        self.create_paths_tab()
        self.create_appearance_tab()
        self.create_advanced_tab()
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Buttons
        ctk.CTkButton(button_frame, text="OK", command=self.on_ok, width=100).pack(side=tk.RIGHT, padx=(5, 0))
        ctk.CTkButton(button_frame, text="Cancel", command=self.on_cancel, width=100).pack(side=tk.RIGHT, padx=(5, 5))
        ctk.CTkButton(button_frame, text="Apply", command=self.on_apply, width=100).pack(side=tk.RIGHT, padx=(5, 5))
        ctk.CTkButton(button_frame, text="Reset to Defaults", command=self.reset_defaults, width=150).pack(side=tk.LEFT)
    
    def create_llm_tab(self):
        """Create LLM settings tab"""
        llm_tab = self.notebook.add("🤖 LLM")
        
        # Model selection section
        model_frame = ctk.CTkFrame(llm_tab)
        model_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctk.CTkLabel(model_frame, text="Model Configuration", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Default model
        model_select_frame = ctk.CTkFrame(model_frame)
        model_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(model_select_frame, text="Default Model:").pack(side=tk.LEFT, padx=10)
        
        self.default_model_var = tk.StringVar()
        self.model_dropdown = ctk.CTkOptionMenu(
            model_select_frame, 
            variable=self.default_model_var,
            values=["Loading..."],
            width=300
        )
        self.model_dropdown.pack(side=tk.LEFT, padx=10)
        
        ctk.CTkButton(
            model_select_frame, 
            text="Browse...", 
            command=self.browse_model,
            width=100
        ).pack(side=tk.RIGHT, padx=10)
        
        # LLM Parameters section
        params_frame = ctk.CTkFrame(llm_tab)
        params_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctk.CTkLabel(params_frame, text="LLM Parameters", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Context size
        ctx_frame = ctk.CTkFrame(params_frame)
        ctx_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(ctx_frame, text="Context Size:").pack(side=tk.LEFT, padx=10)
        self.context_size_var = tk.StringVar()
        ctx_entry = ctk.CTkEntry(ctx_frame, textvariable=self.context_size_var, width=100)
        ctx_entry.pack(side=tk.LEFT, padx=10)
        ctk.CTkLabel(ctx_frame, text="(Default: 8192, Range: 1024-32768)", text_color="gray").pack(side=tk.LEFT, padx=10)
        
        # Temperature
        temp_frame = ctk.CTkFrame(params_frame)
        temp_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(temp_frame, text="Temperature:").pack(side=tk.LEFT, padx=10)
        self.temperature_var = tk.StringVar()
        temp_entry = ctk.CTkEntry(temp_frame, textvariable=self.temperature_var, width=100)
        temp_entry.pack(side=tk.LEFT, padx=10)
        ctk.CTkLabel(temp_frame, text="(Default: 0.7, Range: 0.0-1.0)", text_color="gray").pack(side=tk.LEFT, padx=10)
        
        # Max tokens
        tokens_frame = ctk.CTkFrame(params_frame)
        tokens_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(tokens_frame, text="Max Tokens:").pack(side=tk.LEFT, padx=10)
        self.max_tokens_var = tk.StringVar()
        tokens_entry = ctk.CTkEntry(tokens_frame, textvariable=self.max_tokens_var, width=100)
        tokens_entry.pack(side=tk.LEFT, padx=10)
        ctk.CTkLabel(tokens_frame, text="(Default: 2048)", text_color="gray").pack(side=tk.LEFT, padx=10)
        
        # Help text
        help_frame = ctk.CTkFrame(params_frame)
        help_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        help_text = """💡 Parameter Guide:
• Context Size: How much text the model can process at once (higher = more memory)
• Temperature: Controls randomness (0.1 = focused, 0.9 = creative)
• Max Tokens: Maximum length of generated responses"""
        
        ctk.CTkLabel(help_frame, text=help_text, justify="left").pack(anchor="w", padx=10, pady=10)
    
    def create_search_tab(self):
        """Create search settings tab"""
        search_tab = self.notebook.add("🔍 Search")
        
        # Search parameters
        params_frame = ctk.CTkFrame(search_tab)
        params_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctk.CTkLabel(params_frame, text="Search Configuration", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Max results
        results_frame = ctk.CTkFrame(params_frame)
        results_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(results_frame, text="Max Results:").pack(side=tk.LEFT, padx=10)
        self.max_results_var = tk.StringVar()
        results_entry = ctk.CTkEntry(results_frame, textvariable=self.max_results_var, width=100)
        results_entry.pack(side=tk.LEFT, padx=10)
        ctk.CTkLabel(results_frame, text="(Default: 5, Range: 1-20)", text_color="gray").pack(side=tk.LEFT, padx=10)
        
        # Minimum similarity
        similarity_frame = ctk.CTkFrame(params_frame)
        similarity_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(similarity_frame, text="Min Similarity:").pack(side=tk.LEFT, padx=10)
        self.min_similarity_var = tk.StringVar()
        similarity_entry = ctk.CTkEntry(similarity_frame, textvariable=self.min_similarity_var, width=100)
        similarity_entry.pack(side=tk.LEFT, padx=10)
        ctk.CTkLabel(similarity_frame, text="(Default: 0.0, Range: 0.0-1.0)", text_color="gray").pack(side=tk.LEFT, padx=10)
        
        # Default search mode
        mode_frame = ctk.CTkFrame(params_frame)
        mode_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        ctk.CTkLabel(mode_frame, text="Default Search Mode:").pack(side=tk.LEFT, padx=10)
        self.search_mode_var = tk.StringVar()
        mode_dropdown = ctk.CTkOptionMenu(
            mode_frame,
            variable=self.search_mode_var,
            values=["vector", "vector_llm", "llm_chat"],
            width=200
        )
        mode_dropdown.pack(side=tk.LEFT, padx=10)
    
    def create_paths_tab(self):
        """Create paths settings tab"""
        paths_tab = self.notebook.add("📁 Paths")
        
        # Path configuration
        paths_frame = ctk.CTkFrame(paths_tab)
        paths_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(paths_frame, text="Directory Paths", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Store path variables
        self.path_vars = {}
        path_labels = {
            "vector_db_dir": "Vector Database:",
            "database_dir": "Survival Library:",
            "logs_dir": "Logs Directory:",
            "models_dir": "Models Directory:"
        }
        
        for key, label in path_labels.items():
            path_frame = ctk.CTkFrame(paths_frame)
            path_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ctk.CTkLabel(path_frame, text=label).pack(side=tk.LEFT, padx=10)
            
            self.path_vars[key] = tk.StringVar()
            path_entry = ctk.CTkEntry(path_frame, textvariable=self.path_vars[key], width=400)
            path_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            
            ctk.CTkButton(
                path_frame, 
                text="Browse...", 
                command=lambda k=key: self.browse_directory(k),
                width=100
            ).pack(side=tk.RIGHT, padx=10)
    
    def create_appearance_tab(self):
        """Create appearance settings tab"""
        appearance_tab = self.notebook.add("🎨 Appearance")
        
        # Appearance settings
        appearance_frame = ctk.CTkFrame(appearance_tab)
        appearance_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctk.CTkLabel(appearance_frame, text="Interface Appearance", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Theme selection
        theme_frame = ctk.CTkFrame(appearance_frame)
        theme_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side=tk.LEFT, padx=10)
        self.theme_var = tk.StringVar()
        theme_dropdown = ctk.CTkOptionMenu(
            theme_frame,
            variable=self.theme_var,
            values=["system", "light", "dark"],
            width=200
        )
        theme_dropdown.pack(side=tk.LEFT, padx=10)
        
        # Font size
        font_frame = ctk.CTkFrame(appearance_frame)
        font_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        ctk.CTkLabel(font_frame, text="Font Size:").pack(side=tk.LEFT, padx=10)
        self.font_size_var = tk.StringVar()
        font_entry = ctk.CTkEntry(font_frame, textvariable=self.font_size_var, width=100)
        font_entry.pack(side=tk.LEFT, padx=10)
        ctk.CTkLabel(font_frame, text="(Default: 11, Range: 8-16)", text_color="gray").pack(side=tk.LEFT, padx=10)
    
    def create_advanced_tab(self):
        """Create advanced settings tab"""
        advanced_tab = self.notebook.add("⚙️ Advanced")
        
        # Emergency settings
        emergency_frame = ctk.CTkFrame(advanced_tab)
        emergency_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctk.CTkLabel(emergency_frame, text="Emergency Controls", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Stop command
        stop_frame = ctk.CTkFrame(emergency_frame)
        stop_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        ctk.CTkLabel(stop_frame, text="Stop Command Word:").pack(side=tk.LEFT, padx=10)
        self.stop_command_var = tk.StringVar()
        stop_entry = ctk.CTkEntry(stop_frame, textvariable=self.stop_command_var, width=100)
        stop_entry.pack(side=tk.LEFT, padx=10)
        ctk.CTkLabel(stop_frame, text="(Default: STOP)", text_color="gray").pack(side=tk.LEFT, padx=10)
        
        # Performance settings
        performance_frame = ctk.CTkFrame(advanced_tab)
        performance_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctk.CTkLabel(performance_frame, text="Performance & Logging", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Checkboxes for various options
        self.enable_logging_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            performance_frame,
            text="Enable detailed logging",
            variable=self.enable_logging_var
        ).pack(anchor="w", padx=10, pady=5)
        
        self.save_chat_history_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            performance_frame,
            text="Auto-save chat history",
            variable=self.save_chat_history_var
        ).pack(anchor="w", padx=10, pady=5)
        
        self.check_updates_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            performance_frame,
            text="Check for database updates on startup",
            variable=self.check_updates_var
        ).pack(anchor="w", padx=10, pady=(5, 10))
    
    def load_current_settings(self):
        """Load current settings from configuration"""
        # LLM settings
        self.context_size_var.set(str(self.config.get("llm.context_size", 8192)))
        self.temperature_var.set(str(self.config.get("llm.temperature", 0.7)))
        self.max_tokens_var.set(str(self.config.get("llm.max_tokens", 2048)))
        
        # Search settings
        self.max_results_var.set(str(self.config.get("search.max_results", 5)))
        self.min_similarity_var.set(str(self.config.get("search.min_similarity", 0.0)))
        self.search_mode_var.set(self.config.get("gui.search_mode", "vector_llm"))
        
        # Paths
        for key in self.path_vars:
            path_value = self.config.get(f"paths.{key}", "")
            self.path_vars[key].set(path_value)
        
        # Appearance
        self.theme_var.set(self.config.get("gui.theme", "system"))
        self.font_size_var.set(str(self.config.get("gui.font_size", 11)))
        
        # Advanced
        self.stop_command_var.set(self.config.get("emergency.stop_command_word", "STOP"))
        
        # Load available models
        self.refresh_models()
    
    def refresh_models(self):
        """Refresh the list of available models"""
        try:
            models = self.config.list_available_models()
            if models:
                model_names = [os.path.basename(model) for model in models]
                self.model_dropdown.configure(values=model_names)
                
                # Set current default
                current_default = self.config.get("llm.default_model", "")
                if current_default:
                    current_name = os.path.basename(current_default)
                    if current_name in model_names:
                        self.default_model_var.set(current_name)
                    elif model_names:
                        self.default_model_var.set(model_names[0])
                elif model_names:
                    self.default_model_var.set(model_names[0])
            else:
                self.model_dropdown.configure(values=["No models found"])
                self.default_model_var.set("No models found")
        except Exception as e:
            print(f"Error loading models: {e}")
            self.model_dropdown.configure(values=["Error loading models"])
    
    def browse_model(self):
        """Browse for a model file"""
        file_path = filedialog.askopenfilename(
            title="Select LLM Model File",
            filetypes=[
                ("Model Files", "*.gguf *.bin"),
                ("GGUF Files", "*.gguf"),
                ("Binary Files", "*.bin"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            # Add to config and refresh dropdown
            model_name = os.path.basename(file_path)
            current_values = list(self.model_dropdown.cget("values"))
            if model_name not in current_values:
                current_values.append(model_name)
                self.model_dropdown.configure(values=current_values)
            self.default_model_var.set(model_name)
    
    def browse_directory(self, key: str):
        """Browse for a directory"""
        directory = filedialog.askdirectory(
            title=f"Select directory for {key}",
            initialdir=self.path_vars[key].get() or str(Path.home())
        )
        
        if directory:
            self.path_vars[key].set(directory)
    
    def validate_settings(self) -> bool:
        """Validate all settings before saving"""
        try:
            # Validate numeric values
            context_size = int(self.context_size_var.get())
            if not 1024 <= context_size <= 32768:
                raise ValueError("Context size must be between 1024 and 32768")
            
            temperature = float(self.temperature_var.get())
            if not 0.0 <= temperature <= 1.0:
                raise ValueError("Temperature must be between 0.0 and 1.0")
            
            max_tokens = int(self.max_tokens_var.get())
            if max_tokens < 1:
                raise ValueError("Max tokens must be positive")
            
            max_results = int(self.max_results_var.get())
            if not 1 <= max_results <= 20:
                raise ValueError("Max results must be between 1 and 20")
            
            min_similarity = float(self.min_similarity_var.get())
            if not 0.0 <= min_similarity <= 1.0:
                raise ValueError("Min similarity must be between 0.0 and 1.0")
            
            font_size = int(self.font_size_var.get())
            if not 8 <= font_size <= 16:
                raise ValueError("Font size must be between 8 and 16")
            
            return True
            
        except ValueError as e:
            messagebox.showerror("Invalid Settings", str(e))
            return False
    
    def save_settings(self):
        """Save all settings to configuration"""
        if not self.validate_settings():
            return False
        
        try:
            # LLM settings
            self.config.set("llm.context_size", int(self.context_size_var.get()))
            self.config.set("llm.temperature", float(self.temperature_var.get()))
            self.config.set("llm.max_tokens", int(self.max_tokens_var.get()))
            
            # Save model selection
            selected_model = self.default_model_var.get()
            if selected_model and selected_model != "No models found":
                # Find full path
                models = self.config.list_available_models()
                for model_path in models:
                    if os.path.basename(model_path) == selected_model:
                        self.config.set("llm.default_model", model_path)
                        break
            
            # Search settings
            self.config.set("search.max_results", int(self.max_results_var.get()))
            self.config.set("search.min_similarity", float(self.min_similarity_var.get()))
            self.config.set("gui.search_mode", self.search_mode_var.get())
            
            # Paths
            for key, var in self.path_vars.items():
                path_value = var.get().strip()
                if path_value:
                    self.config.set(f"paths.{key}", path_value)
            
            # Appearance
            self.config.set("gui.theme", self.theme_var.get())
            self.config.set("gui.font_size", int(self.font_size_var.get()))
            
            # Advanced
            self.config.set("emergency.stop_command_word", self.stop_command_var.get().strip() or "STOP")
            
            # Save configuration
            self.config.save()
            return True
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save settings: {str(e)}")
            return False
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to default values?"):
            # Reset to defaults
            self.context_size_var.set("8192")
            self.temperature_var.set("0.7")
            self.max_tokens_var.set("2048")
            self.max_results_var.set("5")
            self.min_similarity_var.set("0.0")
            self.search_mode_var.set("vector_llm")
            self.theme_var.set("system")
            self.font_size_var.set("11")
            self.stop_command_var.set("STOP")
            
            # Reset paths to defaults
            loki_dir = Path("/home/mike/LOKI")
            self.path_vars["vector_db_dir"].set(str(loki_dir / "vector_db"))
            self.path_vars["database_dir"].set(str(loki_dir / "DATABASE"))
            self.path_vars["logs_dir"].set(str(loki_dir / "logs"))
            self.path_vars["models_dir"].set(str(loki_dir / "LLM" / "models"))
    
    def on_apply(self):
        """Apply settings without closing dialog"""
        if self.save_settings():
            messagebox.showinfo("Settings Applied", "Settings have been applied successfully!")
    
    def on_ok(self):
        """Save settings and close dialog"""
        if self.save_settings():
            self.result = "ok"
            self.destroy()
    
    def on_cancel(self):
        """Close dialog without saving"""
        self.result = "cancel"
        self.destroy()


def main():
    """Test the settings dialog"""
    root = ctk.CTk()
    root.withdraw()  # Hide main window
    
    dialog = EnhancedSettingsDialog(root)
    print(f"Dialog result: {dialog.result}")
    
    root.destroy()


if __name__ == "__main__":
    main()
