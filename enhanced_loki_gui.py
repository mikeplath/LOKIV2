#!/usr/bin/env python3
"""
LOKI Enhanced GUI - Complete Rewrite - Part 1
Localized Offline Knowledge Interface with enhanced features:
- STOP/PLAY command functionality
- Library browser
- Better streaming and error handling
- Simplified interface with 2 dropdowns
- Professional appearance and user experience
"""

import os
import sys
import json
import subprocess
import threading
import queue
import time
import platform
import logging
from datetime import datetime
from pathlib import Path
import tempfile
import re
import glob
from typing import Optional, Dict, Any

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    import customtkinter as ctk
except ImportError as e:
    print(f"Error: Missing required package: {str(e)}")
    print("Please install required packages with: pip install tk customtkinter")
    sys.exit(1)

# Add parent directory for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from loki_config import get_config
    from loki_settings_dialog import EnhancedSettingsDialog
    from loki_db_manager import DatabaseManagerDialog
except ImportError as e:
    print(f"Import Error: Could not import required modules: {e}")
    print("Please ensure loki_config.py, loki_settings_dialog.py, and loki_db_manager.py are in the same directory")
    sys.exit(1)

# Set CustomTkinter appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScrolledTextWithPopupMenu(tk.Text):
    """Enhanced text widget with popup menu and better functionality"""
    
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Copy", command=self.copy_text)
        self.popup_menu.add_command(label="Select All", command=self.select_all)
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="Clear", command=self.clear_text)
        self.popup_menu.add_command(label="Save...", command=self.save_text)
        
        self.bind("<Button-3>", self.show_popup_menu)
        self.bind("<Control-c>", self.copy_text)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-s>", self.save_text)
    
    def show_popup_menu(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()
    
    def copy_text(self, event=None):
        try:
            selected_text = self.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            pass
        return "break"
    
    def select_all(self, event=None):
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, "1.0")
        self.see(tk.INSERT)
        return "break"
    
    def clear_text(self):
        if messagebox.askyesno("Clear Text", "Clear all text in this area?"):
            self.delete("1.0", tk.END)
    
    def save_text(self, event=None):
        try:
            filename = filedialog.asksaveasfilename(
                title="Save Text",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.get("1.0", tk.END))
                messagebox.showinfo("Saved", f"Text saved to {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save text: {e}")
        return "break"


class EnhancedChatText(ScrolledTextWithPopupMenu):
    """Enhanced chat display with clickable sources and better formatting"""
    
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(state=tk.DISABLED, wrap=tk.WORD)
        
        self.tag_configure("user", foreground="#1e3a8a", font=("Segoe UI", 11, "bold"))
        self.tag_configure("system", foreground="#059669", font=("Segoe UI", 10, "italic"))
        self.tag_configure("error", foreground="#dc2626", font=("Segoe UI", 10, "bold"))
        self.tag_configure("ai", foreground="#7c2d12", font=("Segoe UI", 11))
        self.tag_configure("timestamp", foreground="#6b7280", font=("Segoe UI", 9))
        
        self.tag_configure("source_link", foreground="#2563eb", underline=1, font=("Segoe UI", 10, "bold"))
        self.tag_bind("source_link", "<Enter>", lambda e: self.configure(cursor="hand2"))
        self.tag_bind("source_link", "<Leave>", lambda e: self.configure(cursor=""))
        
        self.sources = {}
        self.source_callbacks = {}
    
    def append_message(self, message: str, tag: Optional[str] = None, show_timestamp: bool = True):
        self.configure(state=tk.NORMAL)
        if show_timestamp and not message.startswith("\n"):
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            self.insert(tk.END, timestamp, "timestamp")
        self.insert(tk.END, message + "\n", tag)
        self.see(tk.END)
        self.configure(state=tk.DISABLED)
    
    def append_streaming_text(self, text: str):
        self.configure(state=tk.NORMAL)
        self.insert(tk.END, text)
        self.see(tk.END)
        self.configure(state=tk.DISABLED)
    
    def add_clickable_source(self, source_num: str, category: str, filename: str, callback):
        self.configure(state=tk.NORMAL)
        source_tag = f"source_{source_num}"
        source_text = f"📄 [Source {source_num}: {category}/{filename}]"
        self.insert(tk.END, source_text, ("source_link", source_tag))
        self.insert(tk.END, "\n")
        self.source_callbacks[source_tag] = callback
        self.tag_bind(source_tag, "<Button-1>", callback)
        self.see(tk.END)
        self.configure(state=tk.DISABLED)
    
    def clear(self):
        self.configure(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.configure(state=tk.DISABLED)
        self.sources.clear()
        self.source_callbacks.clear()


class StreamingProcessor:
    """Enhanced streaming processor with STOP command support"""
    
    def __init__(self, cmd: list, output_callback, completion_callback=None):
        self.cmd = cmd
        self.output_callback = output_callback
        self.completion_callback = completion_callback
        self.process = None
        self.thread = None
        self.running = False
        self.stop_requested = False
        self.config = get_config()
    
    def start(self) -> bool:
        if self.running: return False
        self.running = True
        self.stop_requested = False
        self.thread = threading.Thread(target=self._run_process, daemon=True)
        self.thread.start()
        return True
    
    def request_stop(self):
        self.stop_requested = True
        if self.process:
            try:
                self.process.terminate()
                time.sleep(0.5)
                if self.process.poll() is None: self.process.kill()
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
    
    def _run_process(self):
        try:
            self.process = subprocess.Popen(
                self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, universal_newlines=True
            )
            for line in iter(self.process.stdout.readline, ''):
                if self.stop_requested: break
                if self.output_callback: self.output_callback(line)
            
            return_code = self.process.wait() if not self.stop_requested else -1
            if self.completion_callback: self.completion_callback(return_code)
        except Exception as e:
            if self.output_callback: self.output_callback(f"Error: {str(e)}\n")
            if self.completion_callback: self.completion_callback(-1)
        finally:
            self.running = False


class LibraryBrowserDialog(ctk.CTkToplevel):
    """Library browser for exploring the survival database"""
    
    def __init__(self, parent, database_path: str):
        super().__init__(parent)
        self.title("LOKI - Library Browser")
        self.geometry("900x650")
        self.database_path = Path(database_path)
        self.transient(parent)
        self.create_interface()
        self.load_directory_tree()
        self.center_window()
        self.after(100, self.grab_set)
    
    def center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_interface(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ctk.CTkLabel(search_frame, text="Search:").pack(side=tk.LEFT, padx=10)
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))
        self.search_entry.bind('<KeyRelease>', self.filter_files)
        
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tree_frame = ctk.CTkFrame(content_frame)
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        ctk.CTkLabel(tree_frame, text="Categories").pack(pady=5)
        
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        self.tree = ttk.Treeview(tree_frame, style="Treeview")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree.bind('<<TreeviewSelect>>', self.on_category_select)
        
        files_frame = ctk.CTkFrame(content_frame)
        files_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        ctk.CTkLabel(files_frame, text="Files").pack(pady=5)
        self.files_listbox = tk.Listbox(files_frame, font=("Segoe UI", 10))
        self.files_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.files_listbox.bind('<Double-Button-1>', self.open_selected_file)
        
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill=tk.X)
        ctk.CTkButton(button_frame, text="Open File", command=self.open_selected_file).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Refresh", command=self.refresh_view).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)
    
    def load_directory_tree(self):
        try:
            if not self.database_path.exists(): return
            for item in sorted(self.database_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    file_count = len(list(item.glob('*.pdf')))
                    display_name = f"{item.name.replace('library-', '')} ({file_count} files)"
                    self.tree.insert('', 'end', values=(str(item),), text=display_name)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load directory: {e}")
    
    def on_category_select(self, event=None):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            category_path = Path(item['values'][0])
            self.load_files_for_category(category_path)
    
    def load_files_for_category(self, category_path: Path):
        self.files_listbox.delete(0, tk.END)
        try:
            for pdf_file in sorted(category_path.glob('*.pdf')):
                file_size = pdf_file.stat().st_size / (1024 * 1024)
                self.files_listbox.insert(tk.END, f"{pdf_file.name} ({file_size:.1f} MB)")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load files: {e}")
    
    def filter_files(self, event=None):
        query = self.search_var.get().lower()
        self.files_listbox.delete(0, tk.END)
        if not query:
            if self.tree.selection(): self.on_category_select(None)
            return
        try:
            for category in self.database_path.iterdir():
                if category.is_dir():
                    for pdf_file in category.glob('*.pdf'):
                        if query in pdf_file.name.lower():
                            file_size = pdf_file.stat().st_size / (1024 * 1024)
                            display_name = f"{pdf_file.name} ({file_size:.1f} MB) - {category.name.replace('library-', '')}"
                            self.files_listbox.insert(tk.END, display_name)
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
    
    def open_selected_file(self, event=None):
        if not self.files_listbox.curselection():
            messagebox.showwarning("No Selection", "Please select a file to open.")
            return
        try:
            selected_text = self.files_listbox.get(self.files_listbox.curselection()[0])
            filename = selected_text.split(' (')[0]
            for category in self.database_path.iterdir():
                if category.is_dir() and (file_path := category / filename).exists():
                    self.open_file(file_path)
                    return
            messagebox.showerror("Error", "Could not find the selected file.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def open_file(self, file_path: Path):
        try:
            if platform.system() == "Windows": os.startfile(str(file_path))
            else: subprocess.run(["xdg-open", str(file_path)], check=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def refresh_view(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        self.files_listbox.delete(0, tk.END)
        self.load_directory_tree()


class EnhancedLokiGUI(ctk.CTk):
    """Enhanced LOKI GUI with all planned features"""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.current_process = None
        self.settings_dialog = None
        self.library_browser = None
        self.db_manager_dialog = None
        self.setup_window()
        self.create_interface()
        self.setup_logging()
        self.load_initial_settings()
        self.show_welcome_message()
        self.after(100, self.input_field.focus_set)
    
    def setup_window(self):
        self.title("LOKI - Localized Offline Knowledge Interface")
        geometry = self.config.get("gui.window_geometry", "1200x800+100+100")
        self.geometry(geometry)
        self.minsize(900, 600)
        ctk.set_appearance_mode(self.config.get("gui.theme", "system"))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_interface(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        self.create_header(main_frame)
        self.create_chat_area(main_frame)
        self.create_input_area(main_frame)
        self.create_status_bar(main_frame)
        self.create_menu()
    
    def create_header(self, parent):
        header_frame = ctk.CTkFrame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_columnconfigure(2, weight=1)
        
        model_frame = ctk.CTkFrame(header_frame)
        model_frame.grid(row=0, column=0, sticky="w", padx=(15, 10), pady=10)
        ctk.CTkLabel(model_frame, text="🤖 Model:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(10, 5))
        self.model_var = tk.StringVar()
        self.model_dropdown = ctk.CTkOptionMenu(model_frame, variable=self.model_var, values=["Loading..."], width=200, font=("Segoe UI", 11))
        self.model_dropdown.pack(side=tk.LEFT, padx=5)
        
        mode_frame = ctk.CTkFrame(header_frame)
        mode_frame.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        ctk.CTkLabel(mode_frame, text="💭 Mode:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(10, 5))
        self.conversation_mode = tk.StringVar(value="vector_llm")
        self.mode_dropdown = ctk.CTkOptionMenu(mode_frame, variable=self.conversation_mode, values=["Vector Search", "Vector+LLM", "LLM Chat"], width=200, font=("Segoe UI", 11))
        self.mode_dropdown.pack(side=tk.LEFT, padx=5)
        
        actions_frame = ctk.CTkFrame(header_frame)
        actions_frame.grid(row=0, column=3, sticky="e", padx=(10, 15), pady=10)
        ctk.CTkButton(actions_frame, text="📚 Browse Library", command=self.open_library_browser, width=140, font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=5)
    
    def create_chat_area(self, parent):
        self.notebook = ctk.CTkTabview(parent)
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        chat_tab = self.notebook.add("💬 Chat")
        chat_tab.grid_rowconfigure(0, weight=1)
        chat_tab.grid_columnconfigure(0, weight=1)
        self.chat_text = EnhancedChatText(chat_tab, font=("Segoe UI", self.config.get("gui.font_size", 11)), bg="#fafafa", relief="flat", borderwidth=0)
        self.chat_text.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        chat_scrollbar = ctk.CTkScrollbar(chat_tab, command=self.chat_text.yview)
        chat_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)
        log_tab = self.notebook.add("📋 Logs")
        log_tab.grid_rowconfigure(0, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)
        self.log_text = ScrolledTextWithPopupMenu(log_tab, font=("Consolas", 10), bg="#f8f9fa", relief="flat", borderwidth=0)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        self.log_text.configure(state=tk.DISABLED)
        log_scrollbar = ctk.CTkScrollbar(log_tab, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
    
    def create_input_area(self, parent):
        input_frame = ctk.CTkFrame(parent)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.input_field = ctk.CTkTextbox(input_frame, height=80, font=("Segoe UI", 11), corner_radius=8)
        self.input_field.grid(row=0, column=0, sticky="ew", padx=(15, 10), pady=15)
        self.input_field.bind("<Return>", self.on_enter_key)
        
        button_frame = ctk.CTkFrame(input_frame)
        button_frame.grid(row=0, column=1, sticky="ns", padx=(0, 15), pady=15)
        self.send_button = ctk.CTkButton(button_frame, text="Send", command=self.handle_user_input, width=80, height=35, font=("Segoe UI", 11, "bold"))
        self.send_button.pack(pady=(0, 5))
        ctk.CTkButton(button_frame, text="Clear", command=self.clear_input, width=80, height=25, font=("Segoe UI", 10)).pack()
        
        tip_frame = ctk.CTkFrame(input_frame)
        tip_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=15, pady=(0,5))
        ctk.CTkLabel(tip_frame, text="💡 Tip: Type 'STOP' to halt AI responses. Type 'PLAY' to launch a game.", font=("Segoe UI", 9), text_color="gray").pack(side=tk.LEFT)
    
    def create_status_bar(self, parent):
        status_frame = ctk.CTkFrame(parent)
        status_frame.grid(row=3, column=0, sticky="ew")
        self.status_text = tk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(status_frame, textvariable=self.status_text, font=("Segoe UI", 10))
        self.status_label.pack(side=tk.LEFT, padx=15, pady=8)
        self.create_status_indicators(status_frame)
    
    def create_status_indicators(self, parent):
        indicators_frame = ctk.CTkFrame(parent)
        indicators_frame.pack(side=tk.RIGHT, padx=15, pady=5)
        self.db_status = ctk.CTkLabel(indicators_frame, text="🗃 DB: Checking...", font=("Segoe UI", 9))
        self.db_status.pack(side=tk.LEFT, padx=5)
        self.model_status = ctk.CTkLabel(indicators_frame, text="🤖 Model: None", font=("Segoe UI", 9))
        self.model_status.pack(side=tk.LEFT, padx=5)
    
    def create_menu(self):
        menubar = tk.Menu(self)
        self.configure(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Chat", command=self.new_chat)
        file_menu.add_command(label="Save Chat...", command=self.save_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Settings", command=self.open_settings)
        tools_menu.add_command(label="Browse Library", command=self.open_library_browser)
        tools_menu.add_separator()
        tools_menu.add_command(label="Manage Database", command=self.open_db_manager)
        tools_menu.add_command(label="Refresh Models", command=self.refresh_models)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="How to Use LOKI", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)

    def load_initial_settings(self):
        self.refresh_models()
        self.check_database_status()
        mode_map = {"vector": "Vector Search", "vector_llm": "Vector+LLM", "llm_chat": "LLM Chat"}
        self.mode_dropdown.set(mode_map.get(self.config.get("gui.search_mode", "vector_llm"), "Vector+LLM"))
    
    def refresh_models(self):
        try:
            models = self.config.list_available_models()
            if models:
                model_names = [os.path.basename(model) for model in models]
                self.model_dropdown.configure(values=model_names)
                default_model = self.config.get("llm.default_model")
                if default_model and os.path.basename(default_model) in model_names:
                    self.model_dropdown.set(os.path.basename(default_model))
                else: self.model_dropdown.set(model_names[0])
                self.model_status.configure(text=f"🤖 Model: {self.model_var.get()[:20]}...")
            else:
                self.model_dropdown.configure(values=["No models found"])
                self.model_dropdown.set("No models found")
                self.model_status.configure(text="🤖 Model: None")
        except Exception as e:
            logger.error(f"Error refreshing models: {e}")
            self.model_dropdown.configure(values=["Error"])
    
    def check_database_status(self):
        try:
            vector_db_path = Path(self.config.get("paths.vector_db_dir"))
            if not vector_db_path.exists(): self.db_status.configure(text="🗃 DB: Not Found")
            elif any(not (vector_db_path / f).exists() for f in ["faiss_index.bin", "chunks.pkl", "metadata.pkl"]):
                self.db_status.configure(text="🗃 DB: Incomplete")
            else:
                info_file = vector_db_path / "db_info.json"
                if info_file.exists():
                    with open(info_file, 'r') as f: info = json.load(f)
                    self.db_status.configure(text=f"🗃 DB: Ready ({info.get('num_chunks', 'N/A')} chunks)")
                else: self.db_status.configure(text="🗃 DB: Ready")
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            self.db_status.configure(text="🗃 DB: Error")
    
    def setup_logging(self):
        logging.getLogger().addHandler(LogToTextHandler(self.log_text))
    
    def show_welcome_message(self):
        self.chat_text.append_message("🌟 Welcome to LOKI - Localized Offline Knowledge Interface\n\nAsk a question about survival or emergency preparedness to begin.", "system", show_timestamp=False)
    
    def on_enter_key(self, event):
        if not (event.state & 0x1 or event.state & 0x4):
            self.handle_user_input()
            return "break"
    
    def handle_user_input(self):
        user_input = self.input_field.get("1.0", tk.END).strip()
        if not user_input: return
        
        if user_input.upper() == self.config.get("emergency.stop_command_word", "STOP"):
            self.execute_stop_command()
        elif user_input.upper() == "PLAY":
            self.execute_play_command()
        else:
            self.clear_input()
            self.chat_text.append_message(f"You: {user_input}", "user")
            self.process_query(user_input)
    
    def execute_stop_command(self):
        if self.current_process and self.current_process.running:
            self.current_process.request_stop()
            self.chat_text.append_message("🛑 STOP command executed. AI response halted.", "error")
            self.status_text.set("Response stopped by user")
        else: self.chat_text.append_message("ℹ️ No active response to stop.", "system")
        self.clear_input()

    def execute_play_command(self):
        self.clear_input()
        self.chat_text.append_message("🎮 Launching LOKI Games...", "system")
        game_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loki_games.py")

        if not os.path.exists(game_script_path):
            logger.error(f"Game script not found at path: {game_script_path}")
            messagebox.showerror("Game Not Found", f"The game script 'loki_games.py' was not found in the LOKI directory.")
            return

        terminals = {
            "gnome-terminal": "--",
            "konsole": "-e",
            "xfce4-terminal": "--command=",
            "xterm": "-e"
        }
        
        launched = False
        for terminal, flag in terminals.items():
            try:
                command_to_run = f"python3 {game_script_path}; exec bash"
                if "=" in flag: # Special case for xfce4-terminal
                    command = [terminal, f"{flag}{command_to_run}"]
                else:
                    command = [terminal, flag, "bash", "-c", command_to_run]

                subprocess.Popen(command)
                launched = True
                logger.info(f"Launched games with {terminal}.")
                break
            except FileNotFoundError:
                logger.warning(f"Terminal '{terminal}' not found, trying next.")
                continue
            except Exception as e:
                logger.error(f"Failed to launch game with {terminal}: {e}")
                continue
        
        if not launched:
            error_msg = "Could not find a compatible terminal emulator.\nPlease install one of 'gnome-terminal', 'konsole', 'xfce4-terminal', or 'xterm' to launch the game window."
            logger.error(error_msg)
            messagebox.showerror("Terminal Not Found", error_msg)

    def clear_input(self):
        self.input_field.delete("1.0", tk.END)
    
    def process_query(self, query: str):
        mode = self.get_current_search_mode()
        self.status_text.set(f"Processing in {mode} mode...")
        self.chat_text.append_message(f"🤖 Using Model: {self.model_var.get()} | Mode: {mode.upper()}", "system")
        
        handler_map = {"vector": self.run_vector_search, "vector_llm": self.run_vector_llm_search, "llm_chat": self.run_llm_chat}
        if handler := handler_map.get(mode): handler(query)
    
    def run_search(self, mode, query, output_callback, completion_callback):
        model_name = self.model_var.get() if "llm" in mode else None
        if "llm" in mode and "No models" in model_name:
            self.chat_text.append_message("❌ No LLM model selected. Please select a model first.", "error")
            self.status_text.set("Ready")
            return
        try:
            temp_script = self.create_script(mode, query, model_name=model_name)
            cmd = ["python3", temp_script]
            self.current_process = StreamingProcessor(cmd, output_callback, lambda rc: completion_callback(rc, temp_script))
            self.current_process.start()
        except Exception as e:
            logger.error(f"Error starting {mode} search: {e}")
            self.chat_text.append_message(f"❌ Error: {e}", "error")
            self.status_text.set("Error occurred")

    def run_vector_search(self, query: str): self.run_search("vector", query, self.process_vector_output, self.search_completed)
    def run_vector_llm_search(self, query: str): self.run_search("vector_llm", query, self.process_vector_llm_output, self.vector_llm_completed)
    def run_llm_chat(self, query: str): self.run_search("llm_chat", query, self.process_chat_output, self.chat_completed)

    def create_script(self, mode: str, query: str, model_name: str = None) -> str:
        vector_db_path = self.config.get("paths.vector_db_dir")
        top_k = self.config.get("search.max_results", 5)
        model_path = ""
        if model_name:
            models = self.config.list_available_models()
            model_path = next((p for p in models if os.path.basename(p) == model_name), "")
        context_size = self.config.get("llm.context_size", 8192)
        max_tokens = self.config.get("llm.max_tokens", 2048)
        temperature = self.config.get("llm.temperature", 0.7)

        script_content = f'''#!/usr/bin/env python3
import os, sys, pickle
from pathlib import Path
from contextlib import redirect_stderr

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError: FAISS_AVAILABLE = False
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError: LLAMA_AVAILABLE = False

def vector_search(query, db_path, k):
    if not FAISS_AVAILABLE: return print("❌ Missing vector search packages."), ""
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2", device='cpu')
        index = faiss.read_index(os.path.join(db_path, "faiss_index.bin"))
        with open(os.path.join(db_path, "chunks.pkl"), 'rb') as f: chunks = pickle.load(f)
        with open(os.path.join(db_path, "metadata.pkl"), 'rb') as f: metadata = pickle.load(f)
        
        embedding = model.encode([query])[0].reshape(1, -1)
        _, indices = index.search(embedding, k)
        
        context, sources = [], []
        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(chunks):
                meta = metadata[idx]
                category = meta.get("category", "Unknown").replace("library-", "")
                file_name = meta.get("file_name", "Unknown")
                page_num = meta.get("page_num", 0)
                page_str = f", Page {{page_num}}" if int(page_num) > 0 else ""
                sources.append(f"📄 [Source {{i+1}}: {{category}}/{{file_name}}]")
                context.append(f"[Source {{i+1}}: {{category}}/{{file_name}}{{page_str}}]\\n{{chunks[idx]}}\\n")
        
        print("\\n".join(sources))
        return "\\n".join(context)
    except Exception as e:
        return print(f"❌ Vector search error: {{e}}"), ""

def run_llm(query, context, model_p, ctx_size, max_tok, temp):
    if not LLAMA_AVAILABLE: return print("❌ Missing LLM packages.")
    try:
        with open(os.devnull, 'w') as f, redirect_stderr(f):
            model = Llama(model_path=model_p, n_ctx=ctx_size, verbose=False)
        
        prompt = f"""INSTRUCTIONS: You are a helpful assistant. Your task is to answer the user's QUESTION using ONLY the provided CONTEXT.
- If the CONTEXT contains a direct answer, quote the relevant sentences word-for-word and end with the citation, like this: "The text states that '...' [Source 1]".
- If the CONTEXT does not directly answer the question, synthesize the information and provide a helpful response, citing the sources you used.
- Do not use any outside knowledge.
- At the end of your entire response, add the following disclaimer, exactly as written:
---
*Disclaimer: This response is based on the provided context. Always consult original source materials and seek professional guidance when necessary. Plath Incorporated is not responsible for any injuries or damages resulting from the use of this information.*

CONTEXT:
{{context}}
QUESTION: {{query}}
RESPONSE:"""
        
        print("\\n\\n--- AI ANALYSIS ---\\n")
        for chunk in model(prompt, max_tokens=max_tok, temperature=temp, stop=["QUESTION:", "CONTEXT:"], stream=True):
            print(chunk["choices"][0]["text"], end="", flush=True)
    except Exception as e: print(f"❌ LLM error: {{e}}")

def run_chat(query, model_p, ctx_size, max_tok, temp):
    if not LLAMA_AVAILABLE: return print("❌ Missing LLM packages.")
    try:
        with open(os.devnull, 'w') as f, redirect_stderr(f):
            model = Llama(model_path=model_p, n_ctx=ctx_size, verbose=False)
        prompt = f"User: {{query}}\\nLOKI:"
        for chunk in model(prompt, max_tokens=max_tok, temperature=temp, stop=["User:"], stream=True):
            print(chunk["choices"][0]["text"], end="", flush=True)
    except Exception as e: print(f"❌ LLM error: {{e}}")

if __name__ == "__main__":
    mode = "{mode}"
    query = """{query}"""
    if mode == "vector": vector_search(query, "{vector_db_path}", {top_k})
    elif mode == "vector_llm":
        context = vector_search(query, "{vector_db_path}", {top_k})
        if context: run_llm(query, context, r"{model_path}", {context_size}, {max_tokens}, {temperature})
    elif mode == "llm_chat": run_chat(query, r"{model_path}", {context_size}, {max_tokens}, {temperature})
'''
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py', encoding='utf-8') as f:
            f.write(script_content)
            temp_script_path = f.name
        os.chmod(temp_script_path, 0o755)
        return temp_script_path

    def process_vector_output(self, line: str):
        if "📄 [Source " in line: self.process_source_line(line)
        else: self.chat_text.append_streaming_text(line)
    
    def process_vector_llm_output(self, line: str):
        if "📄 [Source " in line: self.process_source_line(line)
        elif "--- AI ANALYSIS ---" in line: self.chat_text.append_message("\nResponse:", "system")
        else: self.chat_text.append_streaming_text(line)
    
    def process_chat_output(self, line: str):
        self.chat_text.append_streaming_text(line)
    
    def process_source_line(self, line: str):
        try:
            match = re.search(r"\[Source (\d+): ([^/]+)/([^\]]+)\]", line)
            if match:
                source_num, category, filename = match.groups()
                self.chat_text.add_clickable_source(source_num, category.strip(), filename.strip(), lambda e, c=category, f=filename: self.open_source_file(c, f))
        except Exception as e:
            logger.error(f"Error processing source line: {e}")
            self.chat_text.append_streaming_text(line)
    
    def _on_process_complete(self, return_code: int, temp_file: str, success_msg: str, error_msg: str):
        if temp_file and os.path.exists(temp_file):
            try: os.unlink(temp_file)
            except OSError as e: logger.error(f"Error removing temp file {temp_file}: {e}")
        self.current_process = None
        if return_code == 0:
            self.status_text.set("Completed successfully")
            self.chat_text.append_message(success_msg, "system")
        else:
            self.status_text.set("Completed with errors")
            self.chat_text.append_message(error_msg, "system")

    def search_completed(self, rc, tf): self._on_process_complete(rc, tf, "✅ Search complete.", "⚠️ Search error.")
    def vector_llm_completed(self, rc, tf): self._on_process_complete(rc, tf, "✅ Response complete.", "⚠️ Response error.")
    def chat_completed(self, rc, tf): self._on_process_complete(rc, tf, "✅ Chat complete.", "⚠️ Chat error.")

    def open_source_file(self, category: str, filename: str):
        try:
            lib_path = Path(self.config.get("paths.database_dir")) / "survivorlibrary"
            possible_paths = [lib_path / category / filename, lib_path / f"library-{category}" / filename]
            for path in possible_paths:
                if path.exists(): return self.open_file_with_system(path)
            for found_file in lib_path.rglob(filename):
                if found_file.is_file(): return self.open_file_with_system(found_file)
            messagebox.showerror("File Not Found", f"Could not find '{filename}' in the library.")
        except Exception as e:
            logger.error(f"Error opening source file: {e}")
            messagebox.showerror("Error", f"Error opening file: {e}")
    
    def open_file_with_system(self, file_path: Path):
        try:
            if platform.system() == "Windows": os.startfile(file_path)
            else: subprocess.run(["xdg-open", file_path], check=True)
            self.chat_text.append_message(f"📖 Opened: {file_path.name}", "system")
        except Exception as e:
            logger.error(f"Could not open file: {e}")
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def open_library_browser(self):
        if self.library_browser and self.library_browser.winfo_exists(): return self.library_browser.focus()
        try:
            db_path = Path(self.config.get("paths.database_dir")) / "survivorlibrary"
            if db_path.exists(): self.library_browser = LibraryBrowserDialog(self, str(db_path))
            else: messagebox.showwarning("Library Not Found", f"Could not find library at:\n{db_path}")
        except Exception as e:
            logger.error(f"Could not open library browser: {e}")
            messagebox.showerror("Error", f"Could not open library browser: {e}")
    
    def open_settings(self):
        if self.settings_dialog and self.settings_dialog.winfo_exists(): return self.settings_dialog.focus()
        try:
            self.settings_dialog = EnhancedSettingsDialog(self)
            self.wait_window(self.settings_dialog)
            if hasattr(self.settings_dialog, 'result') and self.settings_dialog.result == "ok":
                self.refresh_models()
                self.check_database_status()
                ctk.set_appearance_mode(self.config.get("gui.theme", "system"))
                self.chat_text.configure(font=("Segoe UI", self.config.get("gui.font_size", 11)))
                self.chat_text.append_message("⚙️ Settings updated successfully!", "system")
        except Exception as e:
            if not isinstance(e, tk.TclError): logger.error(f"Error with settings: {e}")
        finally: self.settings_dialog = None

    def open_db_manager(self):
        if self.db_manager_dialog and self.db_manager_dialog.winfo_exists(): return self.db_manager_dialog.focus()
        try:
            self.db_manager_dialog = DatabaseManagerDialog(self)
        except Exception as e:
            logger.error(f"Could not open DB Manager: {e}")
            messagebox.showerror("Error", f"Could not open DB Manager: {e}")

    def new_chat(self):
        if messagebox.askyesno("New Chat", "Clear the current chat and start fresh?"):
            self.chat_text.clear()
            self.show_welcome_message()
            self.status_text.set("Ready")
    
    def save_chat(self):
        try:
            filename = filedialog.asksaveasfilename(title="Save Chat History", defaultextension=".txt", filetypes=[("Text", "*.txt"), ("Markdown", "*.md")])
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"# LOKI Chat\n**Date:** {datetime.now():%Y-%m-%d %H:%M:%S}\n**Model:** {self.model_var.get()}\n**Mode:** {self.conversation_mode.get()}\n{'='*50}\n\n{self.chat_text.get('1.0', tk.END)}")
                messagebox.showinfo("Saved", f"Chat saved to {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save chat: {e}")
    
    def show_help(self):
        help_text = """
# LOKI - How to Use

This guide explains the settings available in `Tools -> Settings`.

## 🤖 LLM Tab (Large Language Model)

- **Context Size:** How much text the AI can remember at once (like short-term memory). Higher values use more RAM but allow for longer conversations and documents.
- **Max Response Tokens:** The maximum length of a single AI response.
- **Temperature:** Controls AI creativity. Low values (e.g., 0.2) are factual and repetitive. High values (e.g., 0.9) are more creative but can be less accurate. 0.7 is a good balance.

## 🔍 Search Tab

- **Max Search Results (Top-K):** How many source documents are read to generate an answer. More documents can give better answers but take longer to process.

## 🎨 GUI Tab

- **Theme:** Changes the application's appearance (System, Dark, Light).
- **Chat Font Size:** The size of the text in the main chat window.

## 📁 Paths Tab

- **LOKI Directory:** The main folder for the application.
- **Vector DB Directory:** Where the searchable knowledge base is stored.
- **LLM Models Directory:** The folder where you should place your AI model files.

## Adding New AI Models

You can download other compatible models and use them with LOKI.
1.  Find models on websites like **Hugging Face**.
2.  Search for models in **GGUF** format.
3.  Download the model file (it will have a `.gguf` extension).
4.  Place the `.gguf` file into your **LLM Models Directory**.
5.  Restart LOKI. The new model will appear in the model dropdown menu.

## How to Download Files on Linux

You can use the `wget` command in your terminal. For example, to download a model:
`wget -O /path/to/your/models_dir/new_model.gguf "https://huggingface.co/..."`
Replace the path and the URL with the correct values.
"""
        # Create a scrollable Toplevel window for the help text
        help_window = ctk.CTkToplevel(self)
        help_window.title("LOKI Help")
        help_window.geometry("700x600")
        help_window.transient(self)

        text_box = ctk.CTkTextbox(help_window, wrap=tk.WORD, font=("Segoe UI", 12))
        text_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        text_box.insert("1.0", help_text)
        text_box.configure(state="disabled")
        
        help_window.after(100, help_window.grab_set)

    def show_about(self):
        about_text = "LOKI - Localized Offline Knowledge Interface\nVersion 2.0 Enhanced Edition\n\nCourtesy of Plath Incorporated"
        messagebox.showinfo("About LOKI", about_text)
    
    def on_closing(self):
        try:
            self.config.set("gui.window_geometry", self.geometry())
            self.config.set("gui.search_mode", self.get_current_search_mode())
            if "No models" not in self.model_var.get():
                models = self.config.list_available_models()
                for model_path in models:
                    if os.path.basename(model_path) == self.model_var.get():
                        self.config.set("llm.default_model", model_path)
                        break
            if self.current_process: self.current_process.request_stop()
            self.config.save()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self.destroy()
    
    def get_current_search_mode(self) -> str:
        mode_text = self.conversation_mode.get()
        if "Vector Search" in mode_text: return "vector"
        if "Vector+LLM" in mode_text: return "vector_llm"
        return "llm_chat"

class LogToTextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.text_widget.configure(state=tk.NORMAL)
            self.text_widget.insert(tk.END, f"{msg}\n")
            self.text_widget.see(tk.END)
            self.text_widget.configure(state=tk.DISABLED)
        except Exception: pass

def main():
    try:
        loki_dir = Path("/home/mike/LOKI")
        if not loki_dir.exists():
            messagebox.showerror("Directory Error", f"❌ LOKI directory not found at {loki_dir}")
            sys.exit(1)
        
        print("🚀 Starting LOKI Enhanced GUI...")
        app = EnhancedLokiGUI()
        
        def signal_handler(signum, frame):
            print("\n🛑 Shutdown signal received...")
            app.on_closing()
        
        import signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        app.mainloop()
        
    except Exception as e:
        error_msg = f"❌ Could not start LOKI GUI: {str(e)}"
        logger.critical(f"Fatal startup error: {e}", exc_info=True)
        try:
            root = ctk.CTk(); root.withdraw()
            messagebox.showerror("Startup Error", error_msg)
        except: pass
        sys.exit(1)

if __name__ == "__main__":
    main()
