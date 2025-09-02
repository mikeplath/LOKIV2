#!/usr/bin/env python3
"""
LOKI Enhanced GUI - Self-Contained Final Version
This script contains all GUI components, including the settings dialog,
to prevent import errors and provide full functionality.
"""

import os
import sys
import json
import subprocess
import threading
import time
import platform
import logging
from datetime import datetime
from pathlib import Path
import re
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    import customtkinter as ctk
except ImportError as e:
    print(f"CRITICAL ERROR: Missing required Python package: {str(e)}")
    print("Please install it by running this command in your terminal: pip install tk customtkinter")
    sys.exit(1)

# --- Add parent directory to Python path ---
# This ensures that 'from loki_config import LokiConfig' works correctly.
# It assumes this script is in /home/mike/LOKI/GUI and loki_config.py is in /home/mike/LOKI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from loki_config import LokiConfig
except ImportError as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Fatal Import Error", f"Could not import the LOKI configuration system.\n\nError: {e}\n\nPlease ensure 'loki_config.py' is in the '/home/mike/LOKI/' directory.")
    sys.exit(1)

# --- Integrated EnhancedSettingsDialog Class ---
class EnhancedSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.config = parent.config
        self.result = None

        self.title("LOKI - Enhanced Settings")
        self.geometry("800x650")
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.load_settings()
        self.center_window()
        self.wait_window(self)

    def center_window(self):
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.tab_view = ctk.CTkTabview(main_frame)
        self.tab_view.pack(fill="both", expand=True)
        self.tab_view.add("Paths")
        self.tab_view.add("LLM")
        self.tab_view.add("Search")
        self.tab_view.add("GUI")
        self.create_paths_tab(self.tab_view.tab("Paths"))
        self.create_llm_tab(self.tab_view.tab("LLM"))
        self.create_search_tab(self.tab_view.tab("Search"))
        self.create_gui_tab(self.tab_view.tab("GUI"))
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        ctk.CTkButton(button_frame, text="Save", command=self.save_and_close).pack(side="right", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=self.cancel).pack(side="right", padx=5)
        ctk.CTkButton(button_frame, text="Apply", command=self.apply_settings).pack(side="right", padx=5)

    def create_path_entry(self, parent, label_text: str, key: str):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=label_text, width=150, anchor="w").pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame)
        entry.pack(side="left", expand=True, fill="x", padx=5)
        button = ctk.CTkButton(frame, text="Browse...", width=80, command=lambda e=entry: self.browse_directory(e))
        button.pack(side="left", padx=5)
        setattr(self, key, entry)
        return entry

    def browse_directory(self, entry_widget: ctk.CTkEntry):
        directory = filedialog.askdirectory(title="Select Directory")
        if directory:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, directory)

    def create_paths_tab(self, tab):
        ctk.CTkLabel(tab, text="Core Application Paths", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, anchor="w")
        self.loki_dir_entry = self.create_path_entry(tab, "LOKI Directory:", "loki_dir_entry")
        self.database_dir_entry = self.create_path_entry(tab, "Database Directory:", "database_dir_entry")
        self.vector_db_dir_entry = self.create_path_entry(tab, "Vector DB Directory:", "vector_db_dir_entry")
        self.models_dir_entry = self.create_path_entry(tab, "Models Directory:", "models_dir_entry")
        self.instructions_dir_entry = self.create_path_entry(tab, "Instructions Dir:", "instructions_dir_entry")
        self.logs_dir_entry = self.create_path_entry(tab, "Logs Directory:", "logs_dir_entry")

    def create_llm_tab(self, tab):
        ctk.CTkLabel(tab, text="Large Language Model Settings", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, anchor="w")
        model_frame = ctk.CTkFrame(tab)
        model_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(model_frame, text="Default Model:", width=150, anchor="w").pack(side="left", padx=10)
        self.default_model_var = ctk.StringVar()
        self.model_menu = ctk.CTkOptionMenu(model_frame, variable=self.default_model_var, values=["Loading..."])
        self.model_menu.pack(side="left", expand=True, fill="x", padx=5)
        ctk.CTkButton(model_frame, text="Refresh", width=80, command=self.populate_models).pack(side="left", padx=5)
        context_frame = ctk.CTkFrame(tab)
        context_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(context_frame, text="Context Size (tokens):", width=150, anchor="w").pack(side="left", padx=10)
        self.context_size_entry = ctk.CTkEntry(context_frame)
        self.context_size_entry.pack(side="left", expand=True, fill="x", padx=5)

    def create_search_tab(self, tab):
        ctk.CTkLabel(tab, text="Vector Search Settings", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, anchor="w")
        results_frame = ctk.CTkFrame(tab)
        results_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(results_frame, text="Max Search Results:", width=150, anchor="w").pack(side="left", padx=10)
        self.max_results_entry = ctk.CTkEntry(results_frame)
        self.max_results_entry.pack(side="left", expand=True, fill="x", padx=5)

    def create_gui_tab(self, tab):
        ctk.CTkLabel(tab, text="Graphical Interface Settings", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, anchor="w")
        theme_frame = ctk.CTkFrame(tab)
        theme_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(theme_frame, text="Theme:", width=150, anchor="w").pack(side="left", padx=10)
        self.theme_var = ctk.StringVar()
        self.theme_menu = ctk.CTkOptionMenu(theme_frame, variable=self.theme_var, values=["System", "Light", "Dark"])
        self.theme_menu.pack(side="left", expand=True, fill="x", padx=5)

    def load_settings(self):
        self.loki_dir_entry.delete(0, tk.END)
        self.loki_dir_entry.insert(0, self.config.get("paths.loki_dir", ""))
        self.database_dir_entry.delete(0, tk.END)
        self.database_dir_entry.insert(0, self.config.get("paths.database_dir", ""))
        self.vector_db_dir_entry.delete(0, tk.END)
        self.vector_db_dir_entry.insert(0, self.config.get("paths.vector_db_dir", ""))
        self.models_dir_entry.delete(0, tk.END)
        self.models_dir_entry.insert(0, self.config.get("paths.models_dir", ""))
        self.instructions_dir_entry.delete(0, tk.END)
        self.instructions_dir_entry.insert(0, self.config.get("paths.instructions_dir", ""))
        self.logs_dir_entry.delete(0, tk.END)
        self.logs_dir_entry.insert(0, self.config.get("paths.logs_dir", ""))
        self.populate_models()
        self.context_size_entry.delete(0, tk.END)
        self.context_size_entry.insert(0, str(self.config.get("llm.context_size", 8192)))
        self.max_results_entry.delete(0, tk.END)
        self.max_results_entry.insert(0, str(self.config.get("search.max_results", 5)))
        self.theme_var.set(self.config.get("gui.theme", "System"))

    def populate_models(self):
        try:
            models = self.config.list_available_models()
            model_names = [os.path.basename(m) for m in models] if models else ["No models found"]
            self.model_menu.configure(values=model_names)
            default_model = os.path.basename(self.config.get("llm.default_model", ""))
            if default_model in model_names:
                self.default_model_var.set(default_model)
            elif model_names:
                self.default_model_var.set(model_names[0])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load models: {e}", parent=self)

    def apply_settings(self):
        try:
            self.config.set("paths.loki_dir", self.loki_dir_entry.get())
            self.config.set("paths.database_dir", self.database_dir_entry.get())
            self.config.set("paths.vector_db_dir", self.vector_db_dir_entry.get())
            self.config.set("paths.models_dir", self.models_dir_entry.get())
            self.config.set("paths.instructions_dir", self.instructions_dir_entry.get())
            self.config.set("paths.logs_dir", self.logs_dir_entry.get())
            self.config.set("llm.default_model", self.default_model_var.get())
            self.config.set("llm.context_size", int(self.context_size_entry.get()))
            self.config.set("search.max_results", int(self.max_results_entry.get()))
            self.config.set("gui.theme", self.theme_var.get())
            self.config.save_config()
            return True
        except (ValueError, TypeError) as e:
            messagebox.showerror("Invalid Input", f"Please check your settings. Invalid value: {e}", parent=self)
            return False

    def save_and_close(self):
        if self.apply_settings():
            self.result = "ok"
            self.destroy()

    def cancel(self):
        self.result = "cancel"
        self.destroy()

# --- GUI Helper Classes ---
class ScrolledTextWithPopupMenu(tk.Text):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Copy", command=self.copy_text)
        self.bind("<Button-3>", self.show_popup_menu)
    def show_popup_menu(self, event):
        self.popup_menu.tk_popup(event.x_root, event.y_root)
    def copy_text(self, event=None):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.get(tk.SEL_FIRST, tk.SEL_LAST))
        except tk.TclError: pass

class EnhancedChatText(ScrolledTextWithPopupMenu):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.config(state=tk.DISABLED, wrap=tk.WORD)
        self.tag_configure("user", foreground="#1e3a8a", font=("Segoe UI", 11, "bold"))
        self.tag_configure("system", foreground="#059669", font=("Segoe UI", 10, "italic"))
        self.tag_configure("error", foreground="#dc2626", font=("Segoe UI", 10, "bold"))
        self.tag_configure("source_link", foreground="#2563eb", underline=1)
        self.tag_bind("source_link", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("source_link", "<Leave>", lambda e: self.config(cursor=""))

    def append_message(self, message: str, tag: Optional[str] = None):
        self.config(state=tk.NORMAL)
        self.insert(tk.END, message + "\n", tag)
        self.see(tk.END)
        self.config(state=tk.DISABLED)

    def add_clickable_source(self, source_num: str, category: str, filename: str, callback):
        self.config(state=tk.NORMAL)
        source_tag = f"source_{source_num}_{filename.replace('.', '_')}"
        source_text = f"📄 [Source {source_num}: {category}/{filename}]"
        self.insert(tk.END, source_text + "\n", ("source_link", source_tag))
        self.tag_bind(source_tag, "<Button-1>", callback)
        self.see(tk.END)
        self.config(state=tk.DISABLED)

class StreamingProcessor:
    def __init__(self, cmd: list, output_callback, completion_callback, config: LokiConfig):
        self.cmd = cmd
        self.output_callback = output_callback
        self.completion_callback = completion_callback
        self.config = config
        self.process = None
        self.thread = None
        self.stop_requested = False
    def start(self):
        self.stop_requested = False
        self.thread = threading.Thread(target=self._run_process, daemon=True)
        self.thread.start()
    def request_stop(self):
        self.stop_requested = True
        if self.process:
            try: self.process.terminate()
            except: pass
    def _run_process(self):
        try:
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            for line in iter(self.process.stdout.readline, ''):
                if self.stop_requested: break
                if self.output_callback: self.output_callback(line)
            self.process.wait()
            if self.completion_callback: self.completion_callback(0 if not self.stop_requested else -1)
        except Exception as e:
            if self.output_callback: self.output_callback(f"Error: {e}\n")
            if self.completion_callback: self.completion_callback(-1)

# --- Main LOKI GUI Application ---
class EnhancedLokiGUI(ctk.CTk):
    def __init__(self, config: LokiConfig):
        super().__init__()
        self.config = config
        self.current_process = None
        self.setup_window()
        self.create_interface()
        self.load_initial_settings()

    def setup_window(self):
        self.title("LOKI - Localized Offline Knowledge Interface")
        self.geometry(self.config.get("gui.window_geometry", "1200x800+100+100"))
        self.minsize(900, 600)
        ctk.set_appearance_mode(self.config.get("gui.theme", "System"))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_interface(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        self.create_header(main_frame)
        self.create_chat_area(main_frame)
        self.create_input_area(main_frame)

    def create_header(self, parent):
        header_frame = ctk.CTkFrame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_columnconfigure(2, weight=1)
        
        # Model Dropdown
        ctk.CTkLabel(header_frame, text="🤖 Model:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(15,5))
        self.model_var = tk.StringVar()
        self.model_dropdown = ctk.CTkOptionMenu(header_frame, variable=self.model_var, values=["Loading..."])
        self.model_dropdown.pack(side=tk.LEFT, padx=5)

        # Mode Dropdown
        ctk.CTkLabel(header_frame, text="💭 Mode:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(15,5))
        self.conversation_mode = tk.StringVar()
        self.mode_dropdown = ctk.CTkOptionMenu(
            header_frame,
            variable=self.conversation_mode,
            values=[
                "Vector Search",
                "Vector+LLM",
                "LLM Chat"
            ]
        )
        self.mode_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Settings Button
        ctk.CTkButton(header_frame, text="⚙️ Settings", command=self.open_settings).pack(side=tk.RIGHT, padx=15)

    def create_chat_area(self, parent):
        chat_frame = ctk.CTkFrame(parent)
        chat_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_text = EnhancedChatText(chat_frame, font=("Segoe UI", 11))
        self.chat_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scrollbar = ctk.CTkScrollbar(chat_frame, command=self.chat_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.chat_text.configure(yscrollcommand=scrollbar.set)

    def create_input_area(self, parent):
        input_frame = ctk.CTkFrame(parent)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        self.input_field = ctk.CTkTextbox(input_frame, height=80, font=("Segoe UI", 11))
        self.input_field.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        self.input_field.bind("<Return>", self.on_enter_key)
        button_frame = ctk.CTkFrame(input_frame)
        button_frame.grid(row=0, column=1, sticky="ns", padx=(0, 15), pady=15)
        ctk.CTkButton(button_frame, text="Send", command=self.handle_user_input).pack(expand=True, fill="both")

    def load_initial_settings(self):
        self.refresh_models()
        self.mode_dropdown.set("Vector+LLM")
        self.chat_text.append_message("🌟 Welcome to LOKI. Your offline knowledge assistant is ready.", "system")

    def refresh_models(self):
        try:
            models = self.config.list_available_models()
            model_names = [os.path.basename(m) for m in models] if models else ["No models found"]
            self.model_dropdown.configure(values=model_names)
            default_model = os.path.basename(self.config.get("llm.default_model", ""))
            if default_model in model_names: self.model_var.set(default_model)
            elif model_names: self.model_var.set(model_names[0])
        except Exception as e:
            self.chat_text.append_message(f"Error loading models: {e}", "error")

    def on_enter_key(self, event):
        self.handle_user_input()
        return "break"

    def handle_user_input(self):
        user_input = self.input_field.get("1.0", tk.END).strip()
        if not user_input: return
        
        if user_input.upper() == self.config.get("emergency.stop_command_word", "STOP"):
            self.execute_stop_command()
            return

        self.input_field.delete("1.0", tk.END)
        self.chat_text.append_message(f"You: {user_input}", "user")
        self.process_query(user_input)

    def execute_stop_command(self):
        if self.current_process:
            self.current_process.request_stop()
            self.chat_text.append_message("🛑 STOP command executed. AI response halted.", "error")
        else:
            self.chat_text.append_message("ℹ️ No active response to stop.", "system")

    def process_query(self, query: str):
        self.chat_text.append_message("LOKI is thinking...", "system")
        try:
            loki_dir = self.config.get("paths.loki_dir", "/home/mike/LOKI")
            script_path = os.path.join(loki_dir, "loki_search.py")
            cmd = ["python3", script_path, "--query", query, "--top-k", str(self.config.get("search.max_results", 5))]
            self.current_process = StreamingProcessor(cmd, self.process_search_output, self.search_completed, self.config)
            self.current_process.start()
        except Exception as e:
            self.chat_text.append_message(f"❌ Error starting search process: {e}", "error")

    def process_search_output(self, line: str):
        match = re.search(r"\[Source (\d+): ([^/]+)/([^\]]+)\]", line)
        if match:
            source_num, category, filename = match.groups()
            callback = lambda e, cat=category, file=filename: self.open_source_file(cat, file)
            self.chat_text.add_clickable_source(source_num, category, filename, callback)
        else:
            # Avoid printing system messages from the search script
            if "Loading LOKI" not in line and "Loading embedding" not in line and "Vector database loaded" not in line:
                 self.chat_text.append_message(line.strip())

    def search_completed(self, return_code: int):
        self.current_process = None
        if return_code == 0:
            self.chat_text.append_message("✅ Search complete.", "system")
        else:
            self.chat_text.append_message("⚠️ Search stopped or encountered an error.", "error")

    def open_source_file(self, category: str, filename: str):
        try:
            db_path = Path(self.config.get("paths.database_dir"))
            # The search script uses category names like 'medical', but the folder might be 'library-medical'
            file_path = db_path / "survivorlibrary" / f"library-{category}" / filename
            if not file_path.exists():
                 # Fallback for other structures
                 file_path = db_path / "survivorlibrary" / category / filename

            if file_path.exists():
                if platform.system() == "Windows": os.startfile(str(file_path))
                elif platform.system() == "Darwin": subprocess.run(["open", str(file_path)])
                else: subprocess.run(["xdg-open", str(file_path)])
                self.chat_text.append_message(f"📖 Opened: {filename}", "system")
            else:
                self.chat_text.append_message(f"❌ Could not find file: {file_path}", "error")
        except Exception as e:
            self.chat_text.append_message(f"❌ Error opening file: {e}", "error")

    def open_settings(self):
        dialog = EnhancedSettingsDialog(self)
        if dialog.result == "ok":
            self.refresh_models()
            self.chat_text.append_message("⚙️ Settings updated successfully!", "system")
            ctk.set_appearance_mode(self.config.get("gui.theme", "System"))

    def on_closing(self):
        self.config.set("gui.window_geometry", self.geometry())
        self.config.save_config()
        if self.current_process: self.current_process.request_stop()
        self.destroy()

def main():
    try:
        config = LokiConfig()
        app = EnhancedLokiGUI(config)
        app.mainloop()
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("LOKI Fatal Error", f"A critical error occurred on startup:\n\n{e}\n\nThe application will now exit.")
        sys.exit(1)

if __name__ == "__main__":
    main()
