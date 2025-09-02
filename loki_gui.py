#!/usr/bin/env python3
"""
LOKI Enhanced GUI - Complete Rewrite - Part 1
Localized Offline Knowledge Interface with enhanced features:
- STOP command functionality
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
except ImportError as e:
    print(f"Import Error: Could not import required modules: {e}")
    print("Please ensure loki_config.py and loki_settings_dialog.py are in the same directory")
    sys.exit(1)

# Set CustomTkinter appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrolledTextWithPopupMenu(tk.Text):
    """Enhanced text widget with popup menu and better functionality"""
    
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # Create enhanced popup menu
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Copy", command=self.copy_text)
        self.popup_menu.add_command(label="Select All", command=self.select_all)
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="Clear", command=self.clear_text)
        self.popup_menu.add_command(label="Save...", command=self.save_text)
        
        # Bind events
        self.bind("<Button-3>", self.show_popup_menu)
        self.bind("<Control-c>", self.copy_text)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-s>", self.save_text)
    
    def show_popup_menu(self, event):
        """Show the popup menu"""
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()
    
    def copy_text(self, event=None):
        """Copy selected text"""
        try:
            selected_text = self.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            pass
        return "break"
    
    def select_all(self, event=None):
        """Select all text"""
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, "1.0")
        self.see(tk.INSERT)
        return "break"
    
    def clear_text(self):
        """Clear all text"""
        if messagebox.askyesno("Clear Text", "Clear all text in this area?"):
            self.delete("1.0", tk.END)
    
    def save_text(self, event=None):
        """Save text to file"""
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
        self.config(state=tk.DISABLED, wrap=tk.WORD)
        
        # Configure text tags with better styling
        self.tag_configure("user", foreground="#1e3a8a", font=("Segoe UI", 11, "bold"))
        self.tag_configure("system", foreground="#059669", font=("Segoe UI", 10, "italic"))
        self.tag_configure("error", foreground="#dc2626", font=("Segoe UI", 10, "bold"))
        self.tag_configure("ai", foreground="#7c2d12", font=("Segoe UI", 11))
        self.tag_configure("timestamp", foreground="#6b7280", font=("Segoe UI", 9))
        
        # Source links with better styling
        self.tag_configure("source_link", foreground="#2563eb", underline=1, font=("Segoe UI", 10, "bold"))
        self.tag_bind("source_link", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("source_link", "<Leave>", lambda e: self.config(cursor=""))
        
        # Store sources for clickable links
        self.sources = {}
        self.source_callbacks = {}
    
    def append_message(self, message: str, tag: Optional[str] = None, show_timestamp: bool = True):
        """Add a message with optional timestamp"""
        self.config(state=tk.NORMAL)
        
        if show_timestamp and not message.startswith("\n"):
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            self.insert(tk.END, timestamp, "timestamp")
        
        self.insert(tk.END, message + "\n", tag)
        self.see(tk.END)
        self.config(state=tk.DISABLED)
    
    def append_streaming_text(self, text: str):
        """Append text for streaming responses"""
        self.config(state=tk.NORMAL)
        self.insert(tk.END, text)
        self.see(tk.END)
        self.config(state=tk.DISABLED)
    
    def add_clickable_source(self, source_num: str, category: str, filename: str, callback):
        """Add a clickable source link"""
        self.config(state=tk.NORMAL)
        
        source_tag = f"source_{source_num}"
        source_text = f"📄 [Source {source_num}: {category}/{filename}]"
        
        self.insert(tk.END, source_text, ("source_link", source_tag))
        self.insert(tk.END, "\n")
        
        # Store callback
        self.source_callbacks[source_tag] = callback
        self.tag_bind(source_tag, "<Button-1>", callback)
        
        self.see(tk.END)
        self.config(state=tk.DISABLED)
    
    def clear(self):
        """Clear all text and sources"""
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.config(state=tk.DISABLED)
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
        """Start the subprocess"""
        if self.running:
            return False
        
        self.running = True
        self.stop_requested = False
        self.thread = threading.Thread(target=self._run_process, daemon=True)
        self.thread.start()
        return True
    
    def request_stop(self):
        """Request the process to stop (STOP command)"""
        self.stop_requested = True
        if self.process:
            try:
                self.process.terminate()
                time.sleep(0.5)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
    
    def _run_process(self):
        """Run the subprocess with streaming output"""
        try:
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output with stop checking
            for line in iter(self.process.stdout.readline, ''):
                if self.stop_requested:
                    break
                if self.output_callback:
                    self.output_callback(line)
            
            # Get return code
            return_code = self.process.wait() if not self.stop_requested else -1
            
            if self.completion_callback:
                self.completion_callback(return_code)
                
        except Exception as e:
            if self.output_callback:
                self.output_callback(f"Error: {str(e)}\n")
            if self.completion_callback:
                self.completion_callback(-1)
        finally:
            self.running = False


class LibraryBrowserDialog(ctk.CTkToplevel):
    """Library browser for exploring the survival database"""
    
    def __init__(self, parent, database_path: str):
        super().__init__(parent)
        
        self.title("LOKI - Library Browser")
        self.geometry("900x650")
        
        self.database_path = Path(database_path)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self.create_interface()
        self.load_directory_tree()
        
        # Center window
        self.center_window()
    
    def center_window(self):
        """Center the window"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_interface(self):
        """Create the browser interface"""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Search frame
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ctk.CTkLabel(search_frame, text="Search:").pack(side=tk.LEFT, padx=10)
        
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))
        self.search_entry.bind('<KeyRelease>', self.filter_files)
        
        # Content frame
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Directory tree (left side)
        tree_frame = ctk.CTkFrame(content_frame)
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ctk.CTkLabel(tree_frame, text="Categories").pack(pady=5)
        
        # Use tkinter Treeview for the directory structure
        self.tree = ttk.Treeview(tree_frame)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree.bind('<<TreeviewSelect>>', self.on_category_select)
        
        # File list (right side)
        files_frame = ctk.CTkFrame(content_frame)
        files_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ctk.CTkLabel(files_frame, text="Files").pack(pady=5)
        
        # File listbox
        self.files_listbox = tk.Listbox(files_frame, font=("Segoe UI", 10))
        self.files_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.files_listbox.bind('<Double-Button-1>', self.open_selected_file)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ctk.CTkButton(button_frame, text="Open File", command=self.open_selected_file).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Refresh", command=self.refresh_view).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)
    
    def load_directory_tree(self):
        """Load the directory structure"""
        try:
            if not self.database_path.exists():
                return
            
            for item in sorted(self.database_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    # Count files in directory
                    file_count = len([f for f in item.glob('*.pdf')])
                    display_name = f"{item.name.replace('library-', '')} ({file_count} files)"
                    self.tree.insert('', 'end', values=(str(item),), text=display_name)
        
        except Exception as e:
            messagebox.showerror("Error", f"Could not load directory: {e}")
    
    def on_category_select(self, event):
        """Handle category selection"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            category_path = Path(item['values'][0])
            self.load_files_for_category(category_path)
    
    def load_files_for_category(self, category_path: Path):
        """Load files for selected category"""
        self.files_listbox.delete(0, tk.END)
        
        try:
            pdf_files = sorted(category_path.glob('*.pdf'))
            for pdf_file in pdf_files:
                file_size = pdf_file.stat().st_size / (1024 * 1024)  # MB
                display_name = f"{pdf_file.name} ({file_size:.1f} MB)"
                self.files_listbox.insert(tk.END, display_name)
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not load files: {e}")
    
    def filter_files(self, event=None):
        """Filter files based on search query"""
        query = self.search_var.get().lower()
        if not query:
            return
        
        # Simple search implementation
        self.files_listbox.delete(0, tk.END)
        
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
        """Open the selected file"""
        selection = self.files_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a file to open.")
            return
        
        try:
            selected_text = self.files_listbox.get(selection[0])
            filename = selected_text.split(' (')[0]  # Extract filename
            
            # Find the actual file
            for category in self.database_path.iterdir():
                if category.is_dir():
                    file_path = category / filename
                    if file_path.exists():
                        self.open_file(file_path)
                        return
            
            messagebox.showerror("Error", "Could not find the selected file.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def open_file(self, file_path: Path):
        """Open a file with the system's default application"""
        try:
            if platform.system() == "Windows":
                os.startfile(str(file_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(file_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(file_path)])
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def refresh_view(self):
        """Refresh the directory view"""
        # Clear current content
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.files_listbox.delete(0, tk.END)
        
        # Reload
        self.load_directory_tree()


class EnhancedLokiGUI(ctk.CTk):
    """Enhanced LOKI GUI with all planned features"""
    
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.config = get_config()
        
        # Setup window
        self.setup_window()
        
        # Initialize variables
        self.current_process = None
        self.stop_button = None
        
        # Create interface
        self.create_interface()
        
        # Load settings and initialize
        self.load_initial_settings()
        
        # Setup logging
        self.setup_logging()
        
        # Welcome message
        self.show_welcome_message()
        
        # Set focus
        self.after(100, self.input_field.focus_set)
    
    def setup_window(self):
        """Setup the main window"""
        self.title("LOKI - Localized Offline Knowledge Interface")
        
        # Get saved geometry or use default
        geometry = self.config.get("gui.window_geometry", "1200x800+100+100")
        self.geometry(geometry)
        self.minsize(900, 600)
        
        # Set theme
        theme = self.config.get("gui.theme", "system")
        ctk.set_appearance_mode(theme)
        
        # Save geometry on close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_interface(self):
        """Create the main interface"""
        # Create main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Configure grid
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create sections
        self.create_header(main_frame)
        self.create_chat_area(main_frame)
        self.create_input_area(main_frame)
        self.create_status_bar(main_frame)
        self.create_menu()
    
    def create_header(self, parent):
        """Create the simplified header with 2 dropdowns"""
        header_frame = ctk.CTkFrame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_columnconfigure(2, weight=1)  # Make middle section expand
        
        # Model selection
        model_frame = ctk.CTkFrame(header_frame)
        model_frame.grid(row=0, column=0, sticky="w", padx=(15, 10), pady=10)
        
        ctk.CTkLabel(model_frame, text="🤖 Model:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(10, 5))
        
        self.model_var = tk.StringVar()
        self.model_dropdown = ctk.CTkOptionMenu(
            model_frame,
            variable=self.model_var,
            values=["Loading models..."],
            width=200,
            font=("Segoe UI", 11)
        )
        self.model_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Conversation type selection
        mode_frame = ctk.CTkFrame(header_frame)
        mode_frame.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        
        ctk.CTkLabel(mode_frame, text="💭 Mode:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(10, 5))
        
        self.conversation_mode = tk.StringVar(value="vector_llm")
        self.mode_dropdown = ctk.CTkOptionMenu(
            mode_frame,
            variable=self.conversation_mode,
            values=[
                "Vector Search (Quick References)",
                "Vector+LLM (Smart Answers) ⭐",
                "LLM Chat (Direct Conversation)"
            ],
            width=250,
            font=("Segoe UI", 11)
        )
        self.mode_dropdown.pack(side=tk.LEFT, padx=5)
        self.mode_dropdown.set("Vector+LLM (Smart Answers) ⭐")  # Set default
        
        # Action buttons
        actions_frame = ctk.CTkFrame(header_frame)
        actions_frame.grid(row=0, column=3, sticky="e", padx=(10, 15), pady=10)
        
        ctk.CTkButton(
            actions_frame,
            text="📚 Browse Library",
            command=self.open_library_browser,
            width=140,
            font=("Segoe UI", 11)
        ).pack(side=tk.LEFT, padx=5)
        
        ctk.CTkButton(
            actions_frame,
            text="⚙️ Settings",
            command=self.open_settings,
            width=100,
            font=("Segoe UI", 11)
        ).pack(side=tk.LEFT, padx=5)
    
    def create_chat_area(self, parent):
        """Create the chat area with tabs"""
        # Notebook for chat and logs
        self.notebook = ctk.CTkTabview(parent)
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        
        # Chat tab
        chat_tab = self.notebook.add("💬 Chat")
        chat_tab.grid_rowconfigure(0, weight=1)
        chat_tab.grid_columnconfigure(0, weight=1)
        
        # Chat text with scrollbar
        self.chat_text = EnhancedChatText(
            chat_tab,
            font=("Segoe UI", self.config.get("gui.font_size", 11)),
            bg="#fafafa",
            relief="flat",
            borderwidth=0
        )
        self.chat_text.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        
        # Scrollbar
        chat_scrollbar = ctk.CTkScrollbar(chat_tab, command=self.chat_text.yview)
        chat_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)
        
        # Log tab
        log_tab = self.notebook.add("📋 Logs")
        log_tab.grid_rowconfigure(0, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)
        
        self.log_text = ScrolledTextWithPopupMenu(
            log_tab,
            font=("Consolas", 10),
            bg="#f8f9fa",
            relief="flat",
            borderwidth=0
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        self.log_text.config(state=tk.DISABLED)
        
        # Log scrollbar
        log_scrollbar = ctk.CTkScrollbar(log_tab, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
    
    def create_input_area(self, parent):
        """Create the input area with STOP command support"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Input text area
        self.input_field = ctk.CTkTextbox(
            input_frame,
            height=80,
            font=("Segoe UI", 11),
            corner_radius=8
        )
        self.input_field.grid(row=0, column=0, sticky="ew", padx=(15, 10), pady=15)
        self.input_field.bind("<Return>", self.on_enter_key)
        self.input_field.bind("<Control-Return>", lambda e: None)  # Allow Ctrl+Enter for newlines
        
        # Button frame
        button_frame = ctk.CTkFrame(input_frame)
        button_frame.grid(row=0, column=1, sticky="ns", padx=(0, 15), pady=15)
        
        # Send button
        self.send_button = ctk.CTkButton(
            button_frame,
            text="Send",
            command=self.handle_user_input,
            width=80,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        self.send_button.pack(pady=(0, 5))
        
        # Clear button
        ctk.CTkButton(
            button_frame,
            text="Clear",
            command=self.clear_input,
            width=80,
            height=25,
            font=("Segoe UI", 10)
        ).pack()
        
        # STOP command info
        stop_info = ctk.CTkLabel(
            input_frame,
            text="💡 Tip: Type 'STOP' in all caps to halt AI responses immediately",
            font=("Segoe UI", 9),
            text_color="gray"
        )
        stop_info.grid(row=1, column=0, columnspan=2, pady=(0, 5))
    
    def create_status_bar(self, parent):
        """Create the status bar"""
        status_frame = ctk.CTkFrame(parent)
        status_frame.grid(row=3, column=0, sticky="ew")
        
        self.status_text = tk.StringVar(value="Ready - Select a model and ask a question")
        self.status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_text,
            font=("Segoe UI", 10)
        )
        self.status_label.pack(side=tk.LEFT, padx=15, pady=8)
        
        # Status indicators
        self.create_status_indicators(status_frame)
    
    def create_status_indicators(self, parent):
        """Create status indicators"""
        indicators_frame = ctk.CTkFrame(parent)
        indicators_frame.pack(side=tk.RIGHT, padx=15, pady=5)
        
        # Database status
        self.db_status = ctk.CTkLabel(
            indicators_frame,
            text="🗃 DB: Checking...",
            font=("Segoe UI", 9)
        )
        self.db_status.pack(side=tk.LEFT, padx=5)
        
        # Model status
        self.model_status = ctk.CTkLabel(
            indicators_frame,
            text="🤖 Model: None",
            font=("Segoe UI", 9)
        )
        self.model_status.pack(side=tk.LEFT, padx=5)
    
    def create_menu(self):
        """Create the application menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Chat", command=self.new_chat)
        file_menu.add_command(label="Save Chat...", command=self.save_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Settings", command=self.open_settings)
        tools_menu.add_command(label="Browse Library", command=self.open_library_browser)
        tools_menu.add_separator()
        tools_menu.add_command(label="Check Database", command=self.check_database_status)
        tools_menu.add_command(label="Refresh Models", command=self.refresh_models)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="How to Use LOKI", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)

def load_initial_settings(self):
        """Load initial settings and setup"""
        # Load models
        self.refresh_models()
        
        # Check database
        self.check_database_status()
        
        # Set default conversation mode
        default_mode = self.config.get("gui.search_mode", "vector_llm")
        mode_map = {
            "vector": "Vector Search (Quick References)",
            "vector_llm": "Vector+LLM (Smart Answers) ⭐",
            "llm_chat": "LLM Chat (Direct Conversation)"
        }
        self.mode_dropdown.set(mode_map.get(default_mode, "Vector+LLM (Smart Answers) ⭐"))
    
    def refresh_models(self):
        """Refresh available models"""
        try:
            models = self.config.list_available_models()
            if models:
                model_names = [os.path.basename(model) for model in models]
                self.model_dropdown.configure(values=model_names)
                
                # Set default model
                default_model = self.config.get("llm.default_model")
                if default_model:
                    default_name = os.path.basename(default_model)
                    if default_name in model_names:
                        self.model_dropdown.set(default_name)
                        self.model_status.configure(text=f"🤖 Model: {default_name[:20]}...")
                    else:
                        self.model_dropdown.set(model_names[0])
                        self.model_status.configure(text=f"🤖 Model: {model_names[0][:20]}...")
                else:
                    self.model_dropdown.set(model_names[0])
                    self.model_status.configure(text=f"🤖 Model: {model_names[0][:20]}...")
            else:
                self.model_dropdown.configure(values=["No models found"])
                self.model_dropdown.set("No models found")
                self.model_status.configure(text="🤖 Model: None")
                
        except Exception as e:
            logger.error(f"Error refreshing models: {e}")
            self.model_dropdown.configure(values=["Error loading models"])
    
    def check_database_status(self):
        """Check vector database status"""
        try:
            vector_db_path = Path(self.config.get("paths.vector_db_dir"))
            
            if not vector_db_path.exists():
                self.db_status.configure(text="🗃 DB: Not Found")
                return False
            
            required_files = ["faiss_index.bin", "chunks.pkl", "metadata.pkl"]
            missing_files = [f for f in required_files if not (vector_db_path / f).exists()]
            
            if missing_files:
                self.db_status.configure(text="🗃 DB: Incomplete")
                return False
            
            # Check info file for stats
            info_file = vector_db_path / "db_info.json"
            if info_file.exists():
                with open(info_file, 'r') as f:
                    info = json.load(f)
                chunk_count = info.get("num_chunks", "Unknown")
                self.db_status.configure(text=f"🗃 DB: Ready ({chunk_count} chunks)")
            else:
                self.db_status.configure(text="🗃 DB: Ready")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            self.db_status.configure(text="🗃 DB: Error")
            return False
    
    def setup_logging(self):
        """Setup logging to the log tab"""
        log_handler = LogToTextHandler(self.log_text)
        log_handler.setLevel(logging.INFO)
        logger.addHandler(log_handler)
    
    def show_welcome_message(self):
        """Show welcome message"""
        welcome = """🌟 Welcome to LOKI - Localized Offline Knowledge Interface

Your offline survival knowledge assistant is ready! Here's how to get started:

🔹 Choose a Model: Select an AI model from the dropdown above
🔹 Pick Your Mode: 
   • Vector Search - Quick source references
   • Vector+LLM - Smart AI answers with sources (recommended)
   • LLM Chat - Direct conversation with AI

🔹 Ask Questions: Type survival or emergency questions below
🔹 Browse Library: Click "Browse Library" to explore files directly
🔹 Emergency Stop: Type "STOP" in all caps to halt responses

Ready to help you with survival knowledge, emergency procedures, and practical skills!"""

        self.chat_text.append_message(welcome, "system", show_timestamp=False)
    
    def on_enter_key(self, event):
        """Handle Enter key in input field"""
        # Allow Shift+Enter and Ctrl+Enter for new lines
        if event.state & 0x1 or event.state & 0x4:  # Shift or Ctrl
            return
        
        # Send message on Enter
        self.handle_user_input()
        return "break"
    
    def handle_user_input(self):
        """Process user input with STOP command support"""
        user_input = self.input_field.get("1.0", tk.END).strip()
        
        if not user_input:
            return
        
        # Check for STOP command
        if user_input.upper() == self.config.get("emergency.stop_command_word", "STOP"):
            self.execute_stop_command()
            return
        
        # Clear input
        self.clear_input()
        
        # Display user message
        self.chat_text.append_message(f"You: {user_input}", "user")
        
        # Process the query
        self.process_query(user_input)
    
    def execute_stop_command(self):
        """Execute the emergency STOP command"""
        if self.current_process:
            self.current_process.request_stop()
            self.chat_text.append_message("🛑 STOP command executed - halting AI response", "error")
            self.status_text.set("Response stopped by user")
            self.clear_input()
        else:
            self.chat_text.append_message("ℹ️ No active response to stop", "system")
            self.clear_input()
    
    def clear_input(self):
        """Clear the input field"""
        self.input_field.delete("1.0", tk.END)
    
    def process_query(self, query: str):
        """Process a user query based on selected mode"""
        # Determine mode
        mode_text = self.conversation_mode.get()
        if "Vector Search" in mode_text:
            mode = "vector"
        elif "Vector+LLM" in mode_text:
            mode = "vector_llm"
        else:
            mode = "llm_chat"
        
        # Update status
        self.status_text.set("Processing your question...")
        
        # Show processing message
        self.chat_text.append_message("📄 LOKI is processing your question...", "system")
        
        # Process based on mode
        if mode == "vector":
            self.run_vector_search(query)
        elif mode == "vector_llm":
            self.run_vector_llm_search(query)
        elif mode == "llm_chat":
            self.run_llm_chat(query)
    
    def run_vector_search(self, query: str):
        """Run vector search only"""
        try:
            cmd = [
                "python3",
                str(Path(self.config.get("paths.loki_dir")) / "loki_search.py"),
                "--query", query,
                "--top-k", str(self.config.get("search.max_results", 5))
            ]
            
            self.current_process = StreamingProcessor(
                cmd=cmd,
                output_callback=self.process_vector_output,
                completion_callback=self.search_completed
            )
            self.current_process.start()
            
        except Exception as e:
            logger.error(f"Error starting vector search: {e}")
            self.chat_text.append_message(f"❌ Error: {e}", "error")
            self.status_text.set("Error occurred")
    
    def run_vector_llm_search(self, query: str):
        """Run vector search + LLM processing"""
        try:
            # Get selected model
            model_name = self.model_var.get()
            if model_name in ["No models found", "Loading models...", "Error loading models"]:
                self.chat_text.append_message("📄 No LLM model selected. Using vector search only...", "system")
                self.run_vector_search(query)
                return
            
            # Find full model path
            models = self.config.list_available_models()
            model_path = None
            for path in models:
                if os.path.basename(path) == model_name:
                    model_path = path
                    break
            
            if not model_path or not os.path.exists(model_path):
                self.chat_text.append_message("❌ Selected model file not found. Using vector search only...", "error")
                self.run_vector_search(query)
                return
            
            # Create enhanced LLM integration script
            temp_script = self.create_vector_llm_script(query, model_path)
            
            cmd = ["python3", temp_script]
            
            self.current_process = StreamingProcessor(
                cmd=cmd,
                output_callback=self.process_vector_llm_output,
                completion_callback=lambda rc: self.vector_llm_completed(rc, temp_script)
            )
            self.current_process.start()
            
        except Exception as e:
            logger.error(f"Error starting vector+LLM search: {e}")
            self.chat_text.append_message(f"❌ Error: {e}", "error")
            self.status_text.set("Error occurred")
    
    def run_llm_chat(self, query: str):
        """Run direct LLM chat"""
        try:
            # Get selected model
            model_name = self.model_var.get()
            if model_name in ["No models found", "Loading models...", "Error loading models"]:
                self.chat_text.append_message("❌ No LLM model selected. Please select a model first.", "error")
                return
            
            # Find full model path
            models = self.config.list_available_models()
            model_path = None
            for path in models:
                if os.path.basename(path) == model_name:
                    model_path = path
                    break
            
            if not model_path or not os.path.exists(model_path):
                self.chat_text.append_message("❌ Selected model file not found.", "error")
                return
            
            # Create LLM chat script
            temp_script = self.create_llm_chat_script(query, model_path)
            
            cmd = ["python3", temp_script]
            
            self.current_process = StreamingProcessor(
                cmd=cmd,
                output_callback=self.process_chat_output,
                completion_callback=lambda rc: self.chat_completed(rc, temp_script)
            )
            self.current_process.start()
            
        except Exception as e:
            logger.error(f"Error starting LLM chat: {e}")
            self.chat_text.append_message(f"❌ Error: {e}", "error")
            self.status_text.set("Error occurred")
    
    def create_vector_llm_script(self, query: str, model_path: str) -> str:
        """Create the enhanced vector+LLM integration script"""
        temp_script = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py')
        
        script_content = f'''#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    import pickle
except ImportError:
    print("❌ Missing required packages. Please install: pip install faiss-cpu sentence-transformers")
    sys.exit(1)

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("⚠️ llama-cpp-python not available. Install with: pip install llama-cpp-python")

def vector_search(query, vector_db_path="/home/mike/LOKI/vector_db", top_k=5):
    """Enhanced vector search with better error handling"""
    try:
        print("🔍 Loading embedding model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        print("📊 Loading vector database...")
        # Load FAISS index
        index_path = os.path.join(vector_db_path, "faiss_index.bin")
        if not os.path.exists(index_path):
            print("❌ Vector database not found")
            return [], ""
            
        index = faiss.read_index(index_path)
        
        # Load chunks and metadata
        chunks_path = os.path.join(vector_db_path, "chunks.pkl")
        metadata_path = os.path.join(vector_db_path, "metadata.pkl")
        
        with open(chunks_path, 'rb') as f:
            chunks = pickle.load(f)
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        print(f"✅ Database loaded: {{len(chunks)}} chunks available")
        
        # Encode and search
        query_embedding = model.encode([query])[0].reshape(1, -1)
        distances, indices = index.search(query_embedding, top_k)
        
        results = []
        sources = []
        
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(chunks):
                chunk = chunks[idx]
                meta = metadata[idx]
                distance = float(distances[0][i])
                similarity = 1.0 / (1.0 + distance)
                
                category = meta.get("category", "Unknown").replace("library-", "")
                file_name = meta.get("file_name", "Unknown")
                page_num = meta.get("page_num", 0)
                
                print(f"\\n📄 [Source {{i+1}}: {{category}}/{{file_name}}]")
                print(f"   Page: {{page_num}} | Relevance: {{similarity*100:.1f}}%")
                print(f"   Content: {{chunk[:100]}}...")
                
                sources.append(f"[Source {{i+1}}: {{category}}/{{file_name}}, Page {{page_num}}]\\n{{chunk}}\\n")
        
        return results, "\\n".join(sources)
        
    except Exception as e:
        print(f"❌ Vector search error: {{e}}")
        return [], ""

def run_llm(query, context, model_path="{model_path}"):
    """Enhanced LLM processing with better prompting"""
    if not LLAMA_CPP_AVAILABLE:
        print("❌ LLM not available")
        return False
    
    try:
        print(f"🤖 Loading model: {{os.path.basename(model_path)}}")
        model = Llama(
            model_path=model_path,
            n_ctx={self.config.get("llm.context_size", 8192)},
            verbose=False
        )
        
        print("✅ Model ready - generating response...")
        
        # Enhanced prompt with better instructions
        prompt = f"""You are LOKI (Localized Offline Knowledge Interface), an expert survival assistant with access to comprehensive survival knowledge.

INSTRUCTIONS:
- Answer based on the provided context from the survival library
- Be specific and practical in your advice
- Reference source numbers when citing information
- If the context lacks information, acknowledge this and provide what you can
- Focus on actionable survival guidance

CONTEXT FROM SURVIVAL LIBRARY:
{{context}}

QUESTION: {{query}}

EXPERT RESPONSE:"""
        
        # Generate with streaming
        for chunk in model(
            prompt,
            max_tokens={self.config.get("llm.max_tokens", 2048)},
            temperature={self.config.get("llm.temperature", 0.7)},
            stop=["QUESTION:", "\\n\\nQUESTION:", "\\n\\n---"],
            stream=True
        ):
            print(chunk["choices"][0]["text"], end="", flush=True)
        
        return True
        
    except Exception as e:
        print(f"❌ LLM error: {{e}}")
        return False

# Main execution
if __name__ == "__main__":
    query = "{query}"
    
    # Run vector search
    results, context = vector_search(query)
    
    if context:
        print("\\n" + "="*50)
        print("🧠 AI ANALYSIS:")
        print("="*50)
        run_llm(query, context)
    else:
        print("❌ No relevant information found in the database.")
'''
        
        temp_script.write(script_content)
        temp_script.close()
        os.chmod(temp_script.name, 0o755)
        return temp_script.name
    
    def create_llm_chat_script(self, query: str, model_path: str) -> str:
        """Create direct LLM chat script"""
        temp_script = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py')
        
        script_content = f'''#!/usr/bin/env python3
import os
import sys

try:
    from llama_cpp import Llama
except ImportError:
    print("❌ llama-cpp-python not available. Install with: pip install llama-cpp-python")
    sys.exit(1)

try:
    print("🤖 Loading model...")
    model = Llama(
        model_path="{model_path}",
        n_ctx={self.config.get("llm.context_size", 8192)},
        verbose=False
    )
    
    print("✅ Model ready - generating response...")
    
    prompt = """You are LOKI (Localized Offline Knowledge Interface), a survival expert AI assistant.
Provide helpful, accurate guidance on survival, emergency preparedness, and practical skills.

User: {query}

LOKI:"""
    
    for chunk in model(
        prompt,
        max_tokens={self.config.get("llm.max_tokens", 2048)},
        temperature={self.config.get("llm.temperature", 0.7)},
        stop=["User:", "\\nUser:"],
        stream=True
    ):
        print(chunk["choices"][0]["text"], end="", flush=True)

except Exception as e:
    print(f"❌ Error: {{e}}")
'''
        
        temp_script.write(script_content)
        temp_script.close()
        os.chmod(temp_script.name, 0o755)
        return temp_script.name
    
    def process_vector_output(self, line: str):
        """Process vector search output"""
        # Skip system messages
        if any(skip in line for skip in [
            "Loading LOKI Vector Database",
            "Loading embedding model",
            "Vector database loaded"
        ]):
            return
        
        # Process source links
        if "[Source " in line and "]" in line:
            self.process_source_line(line)
            return
        
        # Regular output
        self.chat_text.append_streaming_text(line)
    
    def process_vector_llm_output(self, line: str):
        """Process vector+LLM output"""
        # Skip system loading messages
        if any(skip in line for skip in [
            "Loading embedding model", 
            "Loading vector database",
            "Database loaded:",
            "Loading model:",
            "Model ready"
        ]):
            return
        
        # Handle source information
        if "📄 [Source " in line:
            self.process_source_line(line)
            return
        
        # Skip separator lines
        if line.strip() in ["="*50, "🧠 AI ANALYSIS:", "EXPERT RESPONSE:"]:
            return
        
        # Regular output
        self.chat_text.append_streaming_text(line)
    
    def process_chat_output(self, line: str):
        """Process LLM chat output"""
        # Skip loading messages
        if any(skip in line for skip in [
            "Loading model",
            "Model ready"
        ]):
            return
        
        # Stream output
        self.chat_text.append_streaming_text(line)
    
    def process_source_line(self, line: str):
        """Process a line containing source information"""
        try:
            # Extract source information from enhanced format
            match = re.search(r"\[Source (\d+): ([^/]+)/([^\]]+)\]", line)
            if match:
                source_num = match.group(1)
                category = match.group(2).strip()
                filename = match.group(3).strip()
                
                # Create clickable source
                def open_source(event, cat=category, file=filename):
                    self.open_source_file(cat, file)
                
                self.chat_text.add_clickable_source(source_num, category, filename, open_source)
                
        except Exception as e:
            logger.error(f"Error processing source line: {e}")
            self.chat_text.append_streaming_text(line)
    
    def search_completed(self, return_code: int):
        """Handle search completion"""
        self.current_process = None
        
        if return_code == 0:
            self.status_text.set("Search completed successfully")
            self.chat_text.append_message("✅ Search completed! Click source links above to open documents.", "system")
        else:
            self.status_text.set("Search completed with errors")
            self.chat_text.append_message("⚠️ Search completed with some issues. Check the logs for details.", "system")
    
    def vector_llm_completed(self, return_code: int, temp_file: str):
        """Handle vector+LLM completion"""
        try:
            os.unlink(temp_file)
        except:
            pass
        
        self.current_process = None
        
        if return_code == 0:
            self.status_text.set("Response completed successfully")
            self.chat_text.append_message("✅ AI response completed! Click source links above to view references.", "system")
        else:
            self.status_text.set("Response completed with errors")
            self.chat_text.append_message("⚠️ Response completed with some issues. Check the logs for details.", "system")
    
    def chat_completed(self, return_code: int, temp_file: str):
        """Handle chat completion"""
        try:
            os.unlink(temp_file)
        except:
            pass
        
        self.current_process = None
        
        if return_code == 0:
            self.status_text.set("Chat completed successfully")
        else:
            self.status_text.set("Chat completed with errors")
            self.chat_text.append_message("⚠️ Chat completed with some issues. Check the logs for details.", "system")

def open_source_file(self, category: str, filename: str):
        """Open a source file with enhanced path resolution"""
        try:
            database_path = Path(self.config.get("paths.database_dir"))
            
            # Enhanced path resolution with multiple fallbacks
            possible_paths = [
                database_path / "survivorlibrary" / category / filename,
                database_path / "survivorlibrary" / f"library-{category}" / filename,
                database_path / category / filename,
                database_path / filename
            ]
            
            # Also try alternative database locations
            alt_database_paths = [
                Path("/home/mike/DATABASE"),
                Path("/home/mike/LOKI/DATABASE")
            ]
            
            for alt_path in alt_database_paths:
                if alt_path != database_path and alt_path.exists():
                    possible_paths.extend([
                        alt_path / "survivorlibrary" / category / filename,
                        alt_path / "survivorlibrary" / f"library-{category}" / filename,
                        alt_path / category / filename
                    ])
            
            # Find the first existing path
            for path in possible_paths:
                if path.exists():
                    self.open_file_with_system(path)
                    self.chat_text.append_message(f"📖 Opened: {filename}", "system")
                    return
            
            # If not found, do an extensive search
            self.chat_text.append_message(f"🔍 Searching for {filename}...", "system")
            
            found_files = []
            search_roots = [database_path] + alt_database_paths
            
            for search_root in search_roots:
                if search_root.exists():
                    for found_file in search_root.rglob(filename):
                        if found_file.is_file():
                            found_files.append(found_file)
            
            if found_files:
                # Use the first match
                self.open_file_with_system(found_files[0])
                self.chat_text.append_message(f"📖 Found and opened: {filename}", "system")
            else:
                self.chat_text.append_message(f"❌ Could not find file: {filename}", "error")
            
        except Exception as e:
            logger.error(f"Error opening source file: {e}")
            self.chat_text.append_message(f"❌ Error opening file: {e}", "error")
    
    def open_file_with_system(self, file_path: Path):
        """Open file with system default application"""
        try:
            if platform.system() == "Windows":
                os.startfile(str(file_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(file_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(file_path)])
        except Exception as e:
            raise Exception(f"Could not open file with system application: {e}")
    
    def open_library_browser(self):
        """Open the enhanced library browser dialog"""
        try:
            database_path = self.config.get("paths.database_dir")
            survivorlibrary_path = os.path.join(database_path, "survivorlibrary")
            
            if os.path.exists(survivorlibrary_path):
                LibraryBrowserDialog(self, survivorlibrary_path)
            else:
                # Try alternative paths
                alt_paths = [
                    os.path.join("/home/mike/DATABASE", "survivorlibrary"),
                    os.path.join("/home/mike/LOKI/DATABASE", "survivorlibrary")
                ]
                
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        LibraryBrowserDialog(self, alt_path)
                        return
                
                messagebox.showwarning(
                    "Library Not Found", 
                    f"Could not find the survival library.\nSearched locations:\n• {survivorlibrary_path}\n• {chr(10).join(alt_paths)}"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Could not open library browser: {e}")
    
    def open_settings(self):
        """Open the enhanced settings dialog"""
        try:
            dialog = EnhancedSettingsDialog(self)
            if dialog.result == "ok":
                # Reload settings
                self.refresh_models()
                self.check_database_status()
                
                # Apply theme if changed
                new_theme = self.config.get("gui.theme", "system")
                ctk.set_appearance_mode(new_theme)
                
                # Update font size if changed
                new_font_size = self.config.get("gui.font_size", 11)
                self.chat_text.configure(font=("Segoe UI", new_font_size))
                
                self.chat_text.append_message("⚙️ Settings updated successfully!", "system")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open settings: {e}")
    
    def new_chat(self):
        """Start a new chat session"""
        if messagebox.askyesno("New Chat", "Clear the current chat and start fresh?"):
            self.chat_text.clear()
            self.show_welcome_message()
            self.status_text.set("Ready - Select a model and ask a question")
    
    def save_chat(self):
        """Save chat history with enhanced formatting"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Save Chat History",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Markdown files", "*.md"),
                    ("All files", "*.*")
                ]
            )
            if filename:
                chat_content = self.chat_text.get("1.0", tk.END)
                
                # Enhanced save with metadata
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("# LOKI Chat History\n")
                    f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"**Model:** {self.model_var.get()}\n")
                    f.write(f"**Mode:** {self.conversation_mode.get()}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(chat_content)
                
                messagebox.showinfo("Saved", f"Chat history saved to {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save chat: {e}")
    
    def show_help(self):
        """Show comprehensive help dialog"""
        help_text = """# LOKI - How to Use Your Offline Survival Assistant

## 🚀 Getting Started
1. **Select a Model**: Choose an AI model from the dropdown above
2. **Pick Your Mode**: 
   - **Vector Search**: Quick references to source documents
   - **Vector+LLM**: AI answers based on database + knowledge (recommended)
   - **LLM Chat**: Direct conversation with the AI

## 💬 Asking Questions
- Type questions about survival, emergency procedures, or practical skills
- Be specific for better results
- **Examples**: 
  - "How to purify water in emergency situations"
  - "Treating burns without access to hospital"
  - "Building emergency shelter in winter"

## ✨ Special Features
- **🛑 STOP Command**: Type "STOP" in all caps to halt AI responses immediately
- **📚 Library Browser**: Click "Browse Library" to explore files directly  
- **📄 Clickable Sources**: Click blue source links to open documents
- **⚙️ Multiple Modes**: Switch between search types as needed
- **💾 Save Chats**: File → Save Chat to keep important conversations

## 🎯 Tips for Best Results
- **Vector+LLM mode** gives the most comprehensive answers
- Use **Vector Search** for quick reference lookups
- **Be specific** in your questions for targeted results
- **Use natural language** - ask questions as you would to an expert

## 🆘 Emergency Use
This system works **completely offline** - perfect for emergency situations where internet isn't available.

## 🔧 Settings
Access **Settings** to customize:
- Model parameters (temperature, context size)
- Search behavior and result limits
- Interface appearance and themes
- File paths and directories

## 📖 Library Browser
- Browse all survival documents by category
- Search across all files instantly
- Open any document directly from the interface

Ready to help you with survival knowledge, emergency procedures, and practical skills!"""
        
        help_window = ctk.CTkToplevel(self)
        help_window.title("LOKI - Complete User Guide")
        help_window.geometry("700x600")
        help_window.transient(self)
        
        # Create scrollable text area
        text_frame = ctk.CTkFrame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        text_widget = ScrolledTextWithPopupMenu(text_frame, wrap=tk.WORD, font=("Segoe UI", 11))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert("1.0", help_text)
        text_widget.config(state=tk.DISABLED)
    
    def show_about(self):
        """Show enhanced about dialog"""
        about_text = """LOKI - Localized Offline Knowledge Interface

🌟 Version 2.0 Enhanced Edition 🌟

Your comprehensive offline survival knowledge assistant featuring:

🔹 Advanced vector database search
🔹 Local LLM integration for intelligent responses  
🔹 Emergency STOP command for immediate control
🔹 Interactive library browser
🔹 Professional user interface with modern design
🔹 Complete offline operation - no internet required

🛡️ Perfect for Emergency Preparedness 🛡️

Designed for reliable offline operation in any situation where you need survival knowledge and practical guidance.

Built with reliability, usability, and emergency readiness in mind."""
        
        # Create a custom about dialog
        about_window = ctk.CTkToplevel(self)
        about_window.title("About LOKI")
        about_window.geometry("500x400")
        about_window.transient(self)
        about_window.resizable(False, False)
        
        # Center the window
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (about_window.winfo_width() // 2)
        y = (about_window.winfo_screenheight() // 2) - (about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")
        
        # Content frame
        content_frame = ctk.CTkFrame(about_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # About text
        about_label = ctk.CTkLabel(
            content_frame,
            text=about_text,
            font=("Segoe UI", 12),
            justify="left"
        )
        about_label.pack(expand=True, pady=20)
        
        # OK button
        ctk.CTkButton(
            content_frame,
            text="OK",
            command=about_window.destroy,
            width=100
        ).pack(pady=(0, 10))
    
    def on_closing(self):
        """Handle application closing with cleanup"""
        try:
            # Save current window geometry
            self.config.set("gui.window_geometry", self.geometry())
            
            # Save current settings
            self.config.set("gui.search_mode", self.get_current_search_mode())
            if self.model_var.get() not in ["No models found", "Loading models...", "Error loading models"]:
                # Save selected model
                models = self.config.list_available_models()
                for model_path in models:
                    if os.path.basename(model_path) == self.model_var.get():
                        self.config.set("llm.default_model", model_path)
                        break
            
            # Stop any running processes
            if self.current_process:
                self.current_process.request_stop()
                # Give it a moment to stop
                time.sleep(0.5)
            
            # Final save
            self.config.save()
            
            self.destroy()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            # Force close if there's an error
            self.destroy()
    
    def get_current_search_mode(self) -> str:
        """Get the current search mode as config value"""
        mode_text = self.conversation_mode.get()
        if "Vector Search" in mode_text:
            return "vector"
        elif "Vector+LLM" in mode_text:
            return "vector_llm"
        else:
            return "llm_chat"


class LogToTextHandler(logging.Handler):
    """Custom logging handler to display logs in the GUI"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        """Emit a log record to the text widget"""
        try:
            msg = self.format(record)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Format the log message
            if record.levelname == "ERROR":
                formatted_msg = f"[{timestamp}] ❌ ERROR: {msg}"
            elif record.levelname == "WARNING":
                formatted_msg = f"[{timestamp}] ⚠️ WARNING: {msg}"
            elif record.levelname == "INFO":
                formatted_msg = f"[{timestamp}] ℹ️ INFO: {msg}"
            else:
                formatted_msg = f"[{timestamp}] {record.levelname}: {msg}"
            
            # Add to text widget
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, f"{formatted_msg}\n")
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
            
        except Exception:
            pass  # Silently handle logging errors


def check_dependencies():
    """Check for required dependencies and provide helpful error messages"""
    missing_deps = []
    
    # Check for required packages
    try:
        import customtkinter
    except ImportError:
        missing_deps.append("customtkinter")
    
    try:
        import sentence_transformers
    except ImportError:
        missing_deps.append("sentence-transformers")
    
    try:
        import faiss
    except ImportError:
        missing_deps.append("faiss-cpu")
    
    if missing_deps:
        error_msg = f"""❌ Missing required dependencies: {', '.join(missing_deps)}

To install the missing packages, run:
pip install {' '.join(missing_deps)}

For the complete LOKI setup, run:
pip install -r requirements.txt"""
        
        print(error_msg)
        if 'tkinter' in str(sys.modules):
            messagebox.showerror("Missing Dependencies", error_msg)
        sys.exit(1)


def main():
    """Main function to run the enhanced LOKI GUI"""
    try:
        # Check dependencies first
        check_dependencies()
        
        # Check if LOKI directory exists
        loki_dir = Path("/home/mike/LOKI")
        if not loki_dir.exists():
            error_msg = f"""❌ LOKI directory not found at {loki_dir}

Please ensure:
1. LOKI is installed in the correct location
2. You have the necessary permissions
3. The directory structure is intact"""
            
            print(error_msg)
            messagebox.showerror("Directory Error", error_msg)
            sys.exit(1)
        
        # Initialize and run the application
        print("🚀 Starting LOKI Enhanced GUI...")
        app = EnhancedLokiGUI()
        
        # Set up proper shutdown handling
        def signal_handler(signum, frame):
            print("\n🛑 Shutdown signal received...")
            app.on_closing()
        
        import signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the main loop
        app.mainloop()
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"❌ Could not start LOKI GUI: {str(e)}"
        print(error_msg)
        logger.error(f"Startup error: {e}", exc_info=True)
        
        # Show error dialog if possible
        try:
            messagebox.showerror("Startup Error", error_msg)
        except:
            pass  # Ignore if GUI can't show error dialog
        
        sys.exit(1)


if __name__ == "__main__":
    main()
