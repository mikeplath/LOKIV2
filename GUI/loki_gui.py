#!/usr/bin/env python3
"""
LOKI GUI - Graphical User Interface for the Localized Offline Knowledge Interface
This script provides a user-friendly chat-like interface for interacting with LOKI.
Features streaming text output and clickable source documents.
"""

import os
import sys
import json
import subprocess
import threading
import queue
import time
import platform
from datetime import datetime
from pathlib import Path
import tempfile
import re
import glob

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    import customtkinter as ctk
except ImportError as e:
    print(f"Error: Missing required package: {str(e)}")
    print("Please install required packages with: pip install tk customtkinter")
    sys.exit(1)

# Set appearance mode and default color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

# Check if running from correct directory
if not os.path.exists('/home/mike/LOKI'):
    print("Error: LOKI directory not found at /home/mike/LOKI")
    print("Please run this script from the LOKI directory or check your installation.")
    sys.exit(1)


class ScrolledTextWithPopupMenu(tk.Text):
    """A text widget with scrollbars and popup menu."""
    def __init__(self, master=None, **kwargs):
        tk.Text.__init__(self, master, **kwargs)
        
        # Create popup menu
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Copy", command=self.copy_text)
        self.popup_menu.add_command(label="Select All", command=self.select_all)
        
        # Bind right-click to show popup menu
        self.bind("<Button-3>", self.show_popup_menu)
        
        # Bind standard copy shortcut
        self.bind("<Control-c>", self.copy_text)
        self.bind("<Control-a>", self.select_all)
    
    def show_popup_menu(self, event):
        """Show the popup menu at the cursor position."""
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()
    
    def copy_text(self, event=None):
        """Copy selected text to clipboard."""
        try:
            selected_text = self.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            pass  # No selection
        return "break"  # Prevent default handling
    
    def select_all(self, event=None):
        """Select all text in the widget."""
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, "1.0")
        self.see(tk.INSERT)
        return "break"  # Prevent default handling


class ChatText(ScrolledTextWithPopupMenu):
    """A text widget for displaying chat messages with clickable sources."""
    def __init__(self, master=None, **kwargs):
        ScrolledTextWithPopupMenu.__init__(self, master, **kwargs)
        self.config(state=tk.DISABLED)
        
        # Configure tags for different message types
        self.tag_configure("user", foreground="#003366", font=("TkDefaultFont", 11, "bold"))
        self.tag_configure("system", foreground="#006633", font=("TkDefaultFont", 11, "italic"))
        self.tag_configure("error", foreground="#CC0000", font=("TkDefaultFont", 11, "italic"))
        self.tag_configure("ai", foreground="#330066", font=("TkDefaultFont", 11))
        
        # Configure tag for clickable sources
        self.tag_configure("clickable", foreground="blue", underline=1)
        self.tag_bind("clickable", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("clickable", "<Leave>", lambda e: self.config(cursor=""))
        
        # Store source references
        self.sources = {}
    
    def append_message(self, message, tag=None):
        """Add a message to the chat display."""
        self.config(state=tk.NORMAL)
        
        # Add timestamp for new messages
        if not message.startswith("\n"):
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            self.insert(tk.END, timestamp, "system")
        
        # Add the message with appropriate tag
        self.insert(tk.END, message + "\n", tag)
        
        # Scroll to the end
        self.see(tk.END)
        self.config(state=tk.DISABLED)
    
    def append_streaming_text(self, text):
        """Append text to the chat display in a streaming fashion."""
        self.config(state=tk.NORMAL)
        self.insert(tk.END, text)
        self.see(tk.END)
        self.config(state=tk.DISABLED)
    
    def add_source_reference(self, source_num, source_info):
        """Add a reference to a source."""
        self.sources[str(source_num)] = source_info
    
    def add_clickable_source(self, source_num, category, filename, callback):
        """Add a clickable source link to the chat display."""
        self.config(state=tk.NORMAL)
        
        # Create a unique tag for this source
        source_tag = f"source_{source_num}"
        
        # Insert the source text
        source_text = f"[Source {source_num}: {category}/{filename}]"
        self.insert(tk.END, source_text, ("clickable", source_tag))
        self.insert(tk.END, "\n")
        
        # Bind click event to the source tag
        self.tag_bind(source_tag, "<Button-1>", callback)
        
        # Scroll to the end
        self.see(tk.END)
        self.config(state=tk.DISABLED)
    
    def clear(self):
        """Clear all text in the widget."""
        self.config(state=tk.NORMAL)
        self.delete(1.0, tk.END)
        self.config(state=tk.DISABLED)
        # Clear source references
        self.sources.clear()


class LokiSettingsDialog(tk.Toplevel):
    """Dialog for LLM settings."""
    
    def __init__(self, parent, context_size=8192, temperature=0.7):
        super().__init__(parent)
        
        self.title("LOKI Settings")
        self.geometry("400x200")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Set initial values
        self.context_size = tk.StringVar(value=str(context_size))
        self.temperature = tk.StringVar(value=str(temperature))
        self.result = None
        
        # Create frame
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Context size
        ttk.Label(frame, text="Context Size:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.context_size, width=10).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(frame, text="(Default: 8192)").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # Temperature
        ttk.Label(frame, text="Temperature:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.temperature, width=10).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(frame, text="(Range: 0.0-1.0, Default: 0.7)").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        
        # Help text
        help_text = ("Context Size: Larger values allow the LLM to process more text at once, but require more memory.\n"
                    "Temperature: Controls randomness. Lower values make responses more focused, higher values more creative.")
        help_label = ttk.Label(frame, text=help_text, wraplength=380, justify=tk.LEFT)
        help_label.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Set focus to the dialog and wait for it to be closed
        self.focus_set()
        self.wait_window()
    
    def on_ok(self):
        """Handle OK button click."""
        try:
            context_size = int(self.context_size.get())
            temperature = float(self.temperature.get())
            
            if temperature < 0.0 or temperature > 1.0:
                raise ValueError("Temperature must be between 0.0 and 1.0")
            
            if context_size <= 0:
                raise ValueError("Context size must be a positive integer")
            
            self.result = {
                "context_size": context_size,
                "temperature": temperature
            }
            
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
    
    def on_cancel(self):
        """Handle Cancel button click."""
        self.destroy()


class StreamingSubprocessRunner:
    """Class to handle running subprocesses with streaming output."""
    
    def __init__(self, cmd, output_callback, completion_callback=None):
        """Initialize with command and callbacks."""
        self.cmd = cmd
        self.output_callback = output_callback
        self.completion_callback = completion_callback
        self.process = None
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the subprocess in a new thread."""
        if self.running:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._run_process, daemon=True)
        self.thread.start()
        return True
    
    def _run_process(self):
        """Run the subprocess and stream output."""
        try:
            # Create and start the process
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output line by line as it's generated
            for line in iter(self.process.stdout.readline, ''):
                if self.output_callback:
                    self.output_callback(line)
            
            # Process has completed, close stdout and get return code
            self.process.stdout.close()
            return_code = self.process.wait()
            
            # Call completion callback if provided
            if self.completion_callback:
                self.completion_callback(return_code)
            
        except Exception as e:
            if self.output_callback:
                self.output_callback(f"Error: {str(e)}\n")
            if self.completion_callback:
                self.completion_callback(-1)
        
        finally:
            self.running = False
    
    def stop(self):
        """Stop the subprocess if it's running."""
        if self.running and self.process:
            try:
                # Try to terminate gracefully first
                self.process.terminate()
                
                # Give it a moment to terminate
                time.sleep(0.5)
                
                # If still running, kill it
                if self.process.poll() is None:
                    self.process.kill()
                
                return True
            except Exception:
                return False
        
        return False

class LokiGUI(ctk.CTk):
    """Main LOKI GUI application."""
    
    def __init__(self):
        """Initialize the LOKI GUI."""
        super().__init__()
        
        # Set window properties
        self.title("LOKI - Localized Offline Knowledge Interface")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Set paths
        self.loki_dir = '/home/mike/LOKI'
        self.vector_db_dir = os.path.join(self.loki_dir, 'vector_db')
        self.logs_dir = os.path.join(self.loki_dir, 'logs')
        self.llm_dir = os.path.join(self.loki_dir, 'LLM')
        self.models_dir = os.path.join(self.llm_dir, 'models')
        self.database_dir = os.path.join(self.loki_dir, 'DATABASE')
        
        # Make sure directories exist
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Set variables
        self.search_query = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready")
        self.selected_model_path = tk.StringVar()
        self.context_size = tk.StringVar(value="8192")
        self.temperature = tk.StringVar(value="0.7")
        self.search_mode = tk.StringVar(value="vector_llm")
        
        # Track current subprocess runner
        self.current_process = None
        
        # Track if waiting for a source number
        self.expecting_source_number = False
        
        # Create UI components
        self.create_menu()
        self.create_main_frame()
        
        # Check if vector database exists
        self.check_vector_database()
        
        # Find available models
        self.available_models = self.find_models()
        self.update_model_dropdown()
        
        # Write initial message
        self.chat_text.append_message("Welcome to LOKI - Localized Offline Knowledge Interface", "system")
        self.chat_text.append_message("Ask a question below to search the survival knowledge database", "system")
        
        # Set focus to the input field
        self.after(100, self.input_field.focus_set)
    
    def create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Check Database Status", command=self.check_vector_database)
        file_menu.add_command(label="Select Model File", command=self.browse_model)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", command=self.copy_selected_text)
        edit_menu.add_command(label="Select All", command=self.select_all_text)
        edit_menu.add_command(label="Clear Chat", command=self.clear_chat)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="LLM Settings", command=self.show_llm_settings)
        tools_menu.add_separator()
        tools_menu.add_command(label="Run Vector Database Creation", command=self.run_vector_db_creation)
        tools_menu.add_command(label="Run Search Interface", command=self.run_search_interface)
        tools_menu.add_command(label="Run LLM Interface", command=self.run_llm_interface)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About LOKI", command=self.show_about)
        help_menu.add_command(label="Usage Instructions", command=self.show_help)
    
    def create_main_frame(self):
        """Create the main application frame."""
        # Create main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=0)  # Mode selector
        main_frame.grid_rowconfigure(1, weight=1)  # Main content area
        main_frame.grid_rowconfigure(2, weight=0)  # Input area
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create mode selection frame
        mode_frame = ctk.CTkFrame(main_frame)
        mode_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        mode_label = ctk.CTkLabel(mode_frame, text="Search Mode:")
        mode_label.pack(side=tk.LEFT, padx=(10, 5))
        
        # Add three radio buttons for search modes
        vector_radio = ctk.CTkRadioButton(mode_frame, text="Vector Search Only", 
                                          variable=self.search_mode, value="vector")
        vector_radio.pack(side=tk.LEFT, padx=5)
        
        llm_radio = ctk.CTkRadioButton(mode_frame, text="Vector + LLM", 
                                       variable=self.search_mode, value="vector_llm")
        llm_radio.pack(side=tk.LEFT, padx=5)
        
        chat_radio = ctk.CTkRadioButton(mode_frame, text="LLM Chat Only", 
                                        variable=self.search_mode, value="llm_chat")
        chat_radio.pack(side=tk.LEFT, padx=5)
        
        # Create model selection dropdown in the mode frame
        model_label = ctk.CTkLabel(mode_frame, text="LLM Model:")
        model_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.model_dropdown = ctk.CTkOptionMenu(mode_frame, width=250, values=["No models found"])
        self.model_dropdown.pack(side=tk.LEFT, padx=5)
        
        model_browse = ctk.CTkButton(mode_frame, text="Browse...", command=self.browse_model)
        model_browse.pack(side=tk.LEFT, padx=5)
        
        # Create notebook for chat and log
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        
        # Create chat tab
        chat_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(chat_frame, text="Chat")
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_text = ChatText(chat_frame, wrap=tk.WORD, font=("TkDefaultFont", 11))
        self.chat_text.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        chat_scrollbar = ctk.CTkScrollbar(chat_frame, command=self.chat_text.yview)
        chat_scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)
        
        # Create log tab
        log_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(log_frame, text="Log")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_text = ScrolledTextWithPopupMenu(log_frame, wrap=tk.WORD, font=("TkDefaultFont", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.log_text.config(state=tk.DISABLED)
        
        log_scrollbar = ctk.CTkScrollbar(log_frame, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Create input area at the bottom (chat-like interface)
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Create multiline input field
        self.input_field = ctk.CTkTextbox(input_frame, height=70, wrap="word", font=("TkDefaultFont", 11))
        self.input_field.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_field.bind("<Return>", self.on_enter_key)
        self.input_field.bind("<Control-Return>", lambda e: None)  # Allow Ctrl+Enter for newlines
        
        # Create send button
        send_button = ctk.CTkButton(input_frame, text="Send", command=self.handle_input)
        send_button.grid(row=0, column=1)
        
        # Create status bar
        status_frame = ctk.CTkFrame(self, height=25)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        status_label = ctk.CTkLabel(status_frame, textvariable=self.status_text)
        status_label.pack(side=tk.LEFT, padx=10)
        
        # Write to log
        self.log(f"LOKI GUI started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def on_enter_key(self, event):
        """Handle Enter key in the input field."""
        # If shift or control is held, allow regular Enter behavior (new line)
        if event.state & 0x4 or event.state & 0x1:  # Control or Shift
            return
        
        # Otherwise, send the message and prevent default Enter behavior
        self.handle_input()
        return "break"
    
    def handle_input(self):
        """Process user input, whether it's a query or a source number."""
        # Get text from input field
        user_input = self.input_field.get("1.0", tk.END).strip()
        
        if not user_input:
            return
            
        # Clear input field
        self.input_field.delete("1.0", tk.END)
        
        # If we're expecting a source number, check if this is it
        if self.expecting_source_number and user_input.isdigit():
            source_num = user_input
            if source_num in self.chat_text.sources:
                self.open_source(source_num)
                return
                
        # Otherwise, treat as a regular query
        self.expecting_source_number = False
        self.perform_search(user_input)
    
    def show_llm_settings(self):
        """Show dialog to configure LLM settings."""
        dialog = LokiSettingsDialog(
            self, 
            context_size=int(self.context_size.get()),
            temperature=float(self.temperature.get())
        )
        
        if dialog.result:
            self.context_size.set(str(dialog.result["context_size"]))
            self.temperature.set(str(dialog.result["temperature"]))
            self.log(f"Settings updated: Context Size={dialog.result['context_size']}, Temperature={dialog.result['temperature']}")
    
    def copy_selected_text(self):
        """Copy currently selected text from active text widget."""
        try:
            # Determine which widget has focus
            focused_widget = self.focus_get()
            if isinstance(focused_widget, tk.Text):
                focused_widget.event_generate("<<Copy>>")
            else:
                # Default to chat text
                self.chat_text.event_generate("<<Copy>>")
        except Exception as e:
            self.log(f"Error copying text: {str(e)}")
    
    def select_all_text(self):
        """Select all text in active text widget."""
        try:
            # Determine which widget has focus
            focused_widget = self.focus_get()
            if isinstance(focused_widget, tk.Text):
                focused_widget.tag_add(tk.SEL, "1.0", tk.END)
                focused_widget.mark_set(tk.INSERT, "1.0")
                focused_widget.see(tk.INSERT)
            else:
                # Default to chat text
                self.chat_text.tag_add(tk.SEL, "1.0", tk.END)
                self.chat_text.mark_set(tk.INSERT, "1.0")
                self.chat_text.see(tk.INSERT)
        except Exception as e:
            self.log(f"Error selecting text: {str(e)}")
    
    def log(self, message):
        """Add a message to both the log file and log display."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Make sure the logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Write to the log file
        log_file = os.path.join(self.logs_dir, f"loki_gui_{datetime.now().strftime('%Y-%m-%d')}.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
        
        # Also update the log display
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def check_vector_database(self):
        """Check if the vector database exists and is valid."""
        if not os.path.exists(self.vector_db_dir):
            self.log("Vector database directory not found.")
            self.status_text.set("Database not found")
            self.chat_text.append_message("Vector database directory not found. Please create the vector database first.", "error")
            messagebox.showwarning(
                "Database Not Found", 
                "Vector database directory not found. Please create the vector database first."
            )
            return False
        
        index_file = os.path.join(self.vector_db_dir, "faiss_index.bin")
        chunks_file = os.path.join(self.vector_db_dir, "chunks.pkl")
        metadata_file = os.path.join(self.vector_db_dir, "metadata.pkl")
        
        if not (os.path.exists(index_file) and os.path.exists(chunks_file) and os.path.exists(metadata_file)):
            self.log("Vector database files incomplete.")
            self.status_text.set("Database incomplete")
            self.chat_text.append_message("Vector database files are incomplete. Please recreate the vector database.", "error")
            messagebox.showwarning(
                "Database Incomplete", 
                "Vector database files are incomplete. Please recreate the vector database."
            )
            return False
        
        # Load database info
        info_file = os.path.join(self.vector_db_dir, "db_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    info = json.load(f)
                
                self.log(f"Vector database found: {info.get('num_chunks', 'Unknown')} chunks")
                self.log(f"Creation date: {info.get('creation_date', 'Unknown')}")
                self.log(f"Model: {info.get('model_name', 'Unknown')}")
                
                self.status_text.set(f"Database ready: {info.get('num_chunks', 'Unknown')} chunks")
                return True
            except Exception as e:
                self.log(f"Error reading database info: {str(e)}")
        else:
            self.log("Vector database found, but no info file available.")
            self.status_text.set("Database ready")
        
        return True
    
    def find_models(self):
        """Find available LLM models in common directories."""
        model_dirs = [
            os.path.join(self.loki_dir, 'LLM', 'models'),
            os.path.join(self.loki_dir, 'models'),
            os.path.expanduser("~/models"),
            os.path.expanduser("~/.cache/lm-studio/models")
        ]
        
        extensions = [".gguf", ".bin"]
        models = []
        
        # First, add all models directly in the models folder
        for ext in extensions:
            for model_file in glob.glob(os.path.join(self.models_dir, f"*{ext}")):
                models.append(model_file)
        
        # Then check other directories
        for directory in model_dirs:
            if not os.path.exists(directory) or directory == self.models_dir:
                continue
            
            for ext in extensions:
                for model_file in Path(directory).glob(f"**/*{ext}"):
                    model_path = str(model_file)
                    if model_path not in models:
                        models.append(model_path)
        
        if models:
            self.log(f"Found {len(models)} model(s)")
            for model in models:
                self.log(f"  - {os.path.basename(model)}")
        else:
            self.log("No models found in standard locations")
        
        return models
    
    def update_model_dropdown(self):
        """Update the model dropdown with available models."""
        if not self.available_models:
            self.model_dropdown.configure(values=["No models found"])
            self.model_dropdown.set("No models found")
            return
        
        model_names = [os.path.basename(m) for m in self.available_models]
        self.model_dropdown.configure(values=model_names)
        self.model_dropdown.set(model_names[0])  # Select the first model
    
    def browse_model(self):
        """Open a file dialog to select a model file."""
        file_path = filedialog.askopenfilename(
            title="Select LLM Model File",
            filetypes=[("Model Files", "*.gguf *.bin"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.selected_model_path.set(file_path)
            self.log(f"Selected model: {os.path.basename(file_path)}")
            
            # Add to dropdown if not already there
            if file_path not in self.available_models:
                self.available_models.append(file_path)
                self.update_model_dropdown()
            
            # Set the dropdown to the selected model
            model_name = os.path.basename(file_path)
            for i, name in enumerate(self.model_dropdown.cget("values")):
                if name == model_name:
                    self.model_dropdown.set(name)
                    break
    
    def get_selected_model_path(self):
        """Get the path of the selected model."""
        model_name = self.model_dropdown.get()
        
        if model_name in ["No models found"]:
            return None
        
        # Find the model path based on name
        for path in self.available_models:
            if os.path.basename(path) == model_name:
                return path
        
        # If a specific path was manually selected
        if self.selected_model_path.get():
            return self.selected_model_path.get()
        
        return None
    
    def perform_search(self, query):
        """Execute a search based on the current mode."""
        if self.search_mode.get() == "llm_chat" and not self.check_llm_available():
            return
            
        if self.search_mode.get() != "llm_chat" and not self.check_vector_database():
            return
        
        # Display user query
        self.chat_text.append_message(f"You: {query}", "user")
        
        # Update status
        self.status_text.set("Processing...")
        
        # Choose search method based on mode
        if self.search_mode.get() == "vector":
            self.run_vector_search(query)
        elif self.search_mode.get() == "vector_llm":
            self.run_llm_search(query)
        else:  # llm_chat mode
            self.run_llm_chat(query)
    
    def check_llm_available(self):
        """Check if an LLM model is selected and available."""
        model_path = self.get_selected_model_path()
        if not model_path:
            self.chat_text.append_message("Error: No LLM model selected. Please select a model first.", "error")
            return False
            
        if not os.path.exists(model_path):
            self.chat_text.append_message(f"Error: Selected model not found at {model_path}", "error")
            return False
            
        return True
    
    def run_vector_search(self, query):
        """Run a vector search without LLM."""
        self.log(f"Running vector search for: {query}")
        
        # Build command
        cmd = [
            "python3", 
            os.path.join(self.loki_dir, "loki_search.py"),
            "--query", query
        ]
        
        # Prepare for output
        self.chat_text.append_message("LOKI: Searching the knowledge database...", "system")
        
        # Create and start the subprocess runner
        self.current_process = StreamingSubprocessRunner(
            cmd=cmd,
            output_callback=self.process_search_output,
            completion_callback=self.search_completed
        )
        self.current_process.start()
    
    def run_llm_search(self, query):
        """Run a search with vector search + LLM."""
        self.log(f"Running LLM search for: {query}")
        
        # Get model path
        model_path = self.get_selected_model_path()
        
        if not model_path:
            self.chat_text.append_message("LOKI: No model selected. Running in search-only mode.", "system")
            self.log("No model selected, falling back to vector search")
            self.run_vector_search(query)
            return
        
        # Create script for modified search that shows sources and then LLM response
        temp_script = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py')
        temp_script.write(f'''
import os
import sys
import json
import time
import subprocess
from pathlib import Path

# Ensure the necessary packages are available
try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: Missing required packages. Please install with:")
    print("pip install faiss-cpu sentence-transformers")
    sys.exit(1)

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("LLama CPP not available, running in search-only mode")

# Vector search function
def vector_search(query, vector_db_path="/home/mike/LOKI/vector_db", top_k=5):
    # Load the vector database
    try:
        # Load embedding model
        model_name = "all-MiniLM-L6-v2"
        print(f"Loading embedding model: {{model_name}}")
        model = SentenceTransformer(model_name)
        
        # Load FAISS index
        index_path = os.path.join(vector_db_path, "faiss_index.bin")
        index = faiss.read_index(index_path)
        
        # Load chunks and metadata
        import pickle
        chunks_path = os.path.join(vector_db_path, "chunks.pkl")
        metadata_path = os.path.join(vector_db_path, "metadata.pkl")
        
        with open(chunks_path, 'rb') as f:
            chunks = pickle.load(f)
        
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        info_path = os.path.join(vector_db_path, "db_info.json")
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                db_info = json.load(f)
                print(f"Total documents: {{db_info.get('num_documents', len(chunks))}}")
        
        # Encode the query
        query_embedding = model.encode([query])[0].reshape(1, -1)
        
        # Search the index
        distances, indices = index.search(query_embedding, top_k)
        
        # Format the results
        results = []
        sources = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(chunks):
                chunk = chunks[idx]
                meta = metadata[idx]
                distance = float(distances[0][i])
                similarity = 1.0 / (1.0 + distance)
                
                # Format source information
                category = meta.get("category", "Unknown").replace("library-", "")
                file_name = meta.get("file_name", "Unknown")
                page_num = meta.get("page_num", 0)
                
                # Add to results
                results.append({{
                    "chunk": chunk,
                    "metadata": meta,
                    "similarity": similarity * 100  # Convert to percentage
                }})
                
                # Display source information
                print(f"\\n[Source {{i+1}}: {{category}}/{{file_name}}]")
                print(f"  Page        {{page_num}}")
                print(f"  Relevance   {{similarity*100:.1f}}%")
                print()
                
                # Also print the actual content (new addition)
                print("Content:")
                print(chunk)
                print("\\n" + "-"*50 + "\\n")
                
                # Save source info for LLM
                sources.append(f"[Source {{i+1}}: {{category}}/{{file_name}}, Page {{page_num}}, Relevance: {{similarity*100:.1f}}%]\\n{{chunk}}\\n")
        
        return results, "\\n".join(sources)
    
    except Exception as e:
        print(f"Error in vector search: {{str(e)}}")
        import traceback
        traceback.print_exc()
        return [], ""

# LLM integration
def run_llm(query, context, model_path="{model_path}", context_size={self.context_size.get()}, temperature={self.temperature.get()}):
    if not LLAMA_CPP_AVAILABLE:
        print("LLM integration not available. Install llama_cpp package first.")
        return False
    
    try:
        # Load the model
        print(f"Loading LLM model: {{os.path.basename(model_path)}}")
        model = Llama(
            model_path=model_path,
            n_ctx=context_size,
            verbose=False
        )
        
        print("Model loaded and ready")
        
        # Generate prompt
        prompt = f"""
You are LOKI, the Localized Offline Knowledge Interface. You're an AI assistant with access to a vast library of survival knowledge.
Answer the following question based on the information provided in the context.
If the context doesn't contain enough information to answer the question fully, say so and answer to the best of your ability.
For each fact you include in your answer, specify which source (by number) it came from.
Keep your answer focused and to the point without unnecessary repetition.

Context information from the survival library:
{{context}}

Question: {{query}}

Answer:
"""
        
        print("\\nGenerating answer...")
        
        # Generate answer with streaming
        for chunk in model(
            prompt,
            max_tokens=1024,
            temperature=temperature,
            stop=["Question:", "\\n\\n\\n"],
            stream=True
        ):
            chunk_text = chunk["choices"][0]["text"]
            print(chunk_text, end="", flush=True)
        
        return True
    
    except Exception as e:
        print(f"Error in LLM processing: {{str(e)}}")
        import traceback
        traceback.print_exc()
        return False

# Main execution
if __name__ == "__main__":
    query = "{query}"
    
    # Perform vector search
    results, context = vector_search(query)
    
    if context:
        # Run LLM with context
        run_llm(query, context)
    else:
        print("No relevant information found in the database.")
''')
        temp_script.close()
        
        # Make the script executable
        os.chmod(temp_script.name, 0o755)
        
        # Build command
        cmd = [
            "python3", 
            temp_script.name
        ]
        
        # Prepare for output
        self.chat_text.append_message("LOKI: Searching the knowledge database...", "system")
        
        # Create and start the subprocess runner
        self.current_process = StreamingSubprocessRunner(
            cmd=cmd,
            output_callback=self.process_vector_llm_output,
            completion_callback=lambda rc: self.vector_llm_completed(rc, temp_script.name)
        )
        self.current_process.start()
    
    def run_llm_chat(self, query):
        """Run a direct chat with LLM (no vector search)."""
        self.log(f"Running LLM chat for: {query}")
        
        # Get model path
        model_path = self.get_selected_model_path()
        
        if not model_path:
            self.chat_text.append_message("Error: No LLM model selected. Please select a model first.", "error")
            return
        
        # Build command for direct LLM chat
        # Create a temporary prompt file to avoid command line length issues
        temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
        
        # Write the prompt to the temp file
        prompt = f"""You are LOKI (Localized Offline Knowledge Interface), an AI assistant specializing in survival and practical knowledge.
The user is asking for information. Please provide a helpful, accurate response.

User: {query}

LOKI:"""
        
        temp_file.write(prompt)
        temp_file.close()
        
        # Build command
        cmd = [
            "python3", 
            "-c",
            f"""
import sys
from llama_cpp import Llama

try:
    # Load the model
    print("Loading LLM model: {os.path.basename(model_path)}")
    model = Llama(
        model_path="{model_path}",
        n_ctx={self.context_size.get()},
        verbose=False
    )
    print("Model loaded and ready")

    # Read prompt from file
    with open("{temp_file.name}", "r") as f:
        prompt = f.read()

    print("Generating response...")
    
    # Generate response with streaming
    for chunk in model(
        prompt,
        max_tokens=2048,
        temperature={self.temperature.get()},
        stop=["User:", "\\nUser:"],
        stream=True
    ):
        chunk_text = chunk["choices"][0]["text"]
        print(chunk_text, end="", flush=True)
        
except Exception as e:
    print(f"Error: {{e}}")
    import traceback
    traceback.print_exc()
"""
        ]
        
        # Prepare for output
        self.chat_text.append_message("LOKI: ", "ai")
        
        # Create and start the subprocess runner
        self.current_process = StreamingSubprocessRunner(
            cmd=cmd,
            output_callback=self.process_chat_output,
            completion_callback=lambda rc: self.chat_completed(rc, temp_file.name)
        )
        self.current_process.start()
    
    def process_search_output(self, line):
        """Process output from the search command."""
        # Log raw output for debugging
        self.log(line.strip())
        
        # Skip system info lines that contain database loading info
        if any(skip_text in line for skip_text in [
            "Loading LOKI Vector Database", 
            "Vector database loaded", 
            "Creation date", 
            "Total chunks",
            "Loading embedding model"
        ]):
            return
            
        # Process source information
        if "[Source " in line and "Relevance" in line:
            try:
                # Parse source information from the text
                match = re.search(r"\[Source (\d+): ([^/]+)/([^,\]]+)]", line)
                if match:
                    source_num = match.group(1)
                    category = match.group(2).strip()
                    file_name = match.group(3).strip()
                    
                    # Extract page and relevance if available
                    page_match = re.search(r"Page\s+(\d+)", line)
                    page_num = page_match.group(1) if page_match else "0"
                    
                    relevance_match = re.search(r"Relevance\s+([\d\.]+)%", line)
                    relevance = relevance_match.group(1) if relevance_match else "0"
                    
                    # Store source info
                    source_info = {
                        "source_num": source_num,
                        "category": category,
                        "file_name": file_name,
                        "page_num": page_num,
                        "relevance": relevance
                    }
                    
                    # Add to sources dictionary
                    self.chat_text.add_source_reference(source_num, source_info)
                    
                    # Create clickable link
                    def open_this_source(event, src=source_info):
                        self.open_source_file(src)
                    
                    self.chat_text.add_clickable_source(
                        source_num=source_num,
                        category=category,
                        filename=file_name,
                        callback=open_this_source
                    )
                    
                    return
            except Exception as e:
                self.log(f"Error parsing source: {str(e)}")
        
        # Normal text output
        self.chat_text.append_streaming_text(line)
    
    def process_vector_llm_output(self, line):
        """Process output from the vector+LLM search."""
        # Log raw output for debugging
        self.log(line.strip())
        
        # Skip system info lines about loading
        if any(skip_text in line for skip_text in [
            "Loading embedding model", 
            "Total documents",
            "Loading LLM model",
            "llama_context",
            "n_ctx_per_seq"
        ]):
            return
            
        # Replace "Model loaded successfully" with "Model loaded and ready"
        if "Model loaded successfully" in line:
            self.chat_text.append_streaming_text("Model loaded and ready\n")
            return
        
        # Replace "This may take a few moments" with nothing
        if "This may take a few moments" in line:
            return
            
        # Process source information
        if "[Source " in line and "/" in line and "]" in line:
            try:
                # Parse source information
                match = re.search(r"\[Source (\d+): ([^/]+)/([^\]]+)\]", line)
                if match:
                    source_num = match.group(1)
                    category = match.group(2).strip()
                    file_name = match.group(3).strip()
                    
                    # Store source info (will get more info later)
                    source_info = {
                        "source_num": source_num,
                        "category": category,
                        "file_name": file_name
                    }
                    
                    # Parse page and relevance if in the same line
                    page_match = re.search(r"Page (\d+)", line)
                    if page_match:
                        source_info["page_num"] = page_match.group(1)
                        
                    relevance_match = re.search(r"Relevance: ([\d\.]+)%", line)
                    if relevance_match:
                        source_info["relevance"] = relevance_match.group(1)
                    
                    # Add to sources dictionary
                    self.chat_text.add_source_reference(source_num, source_info)
                    
                    # Create clickable link
                    def open_this_source(event, src=source_info):
                        self.open_source_file(src)
                    
                    self.chat_text.add_clickable_source(
                        source_num=source_num,
                        category=category,
                        filename=file_name,
                        callback=open_this_source
                    )
                    
                    return
            except Exception as e:
                self.log(f"Error parsing source: {str(e)}")
        
        # Process page and relevance info
        if hasattr(self, 'current_source_num'):
            # Check for page info
            if "Page" in line:
                match = re.search(r"Page\s+(\d+)", line)
                if match and match.group(1).isdigit():
                    page_num = match.group(1)
                    if str(self.current_source_num) in self.chat_text.sources:
                        self.chat_text.sources[str(self.current_source_num)]["page_num"] = page_num
                    
            # Check for relevance info
            if "Relevance" in line:
                match = re.search(r"Relevance\s+([\d\.]+)%", line)
                if match:
                    relevance = match.group(1)
                    if str(self.current_source_num) in self.chat_text.sources:
                        self.chat_text.sources[str(self.current_source_num)]["relevance"] = relevance
                    # Clear current source num after getting all info
                    del self.current_source_num
                    return
        
        # Detect "Content:" as a separator
        if line.strip() == "Content:":
            # Skip this line
            return
            
        # Check if line starts with "Generating answer..." and skip it
        if "Generating answer" in line:
            return
        
        # Normal text output
        self.chat_text.append_streaming_text(line)
    
    def process_llm_output(self, line):
        """Process output from the LLM command with streaming support."""
        # Log raw output for debugging
        self.log(line.strip())
        
        # Skip system info lines
        if any(skip_text in line for skip_text in [
            "Loading LOKI Vector Database", 
            "Vector database loaded", 
            "Creation date", 
            "Total chunks",
            "Loading LLM model",
            "This may take a few moments",
            "llama_context",
            "Found",
            "relevant documents",
            "Generating answer"
        ]):
            return
            
        # Replace "Model loaded successfully" with "Model loaded and ready"
        if "Model loaded successfully" in line:
            self.chat_text.append_streaming_text("Model loaded and ready\n")
            return
            
        # Skip box-drawing characters and panels
        if line.strip() and any(c in line for c in "╭╮╰╯│"):
            return
        
        # Process source information
        if "Source Information" in line:
            self.expecting_source_number = True
            return
        
        # Process category/file/page information from the source table format
        if line.strip().startswith("Source") and len(line.strip().split()) >= 2:
            try:
                parts = line.strip().split()
                current_source = parts[1]
                self.current_source = {"source_num": current_source}
                return
            except:
                pass
        
        if hasattr(self, 'current_source') and line.strip().startswith("Category"):
            try:
                category = line.strip().split()[1]
                self.current_source["category"] = category
                return
            except:
                pass
                
        if hasattr(self, 'current_source') and line.strip().startswith("File"):
            try:
                file_name = line.strip().split()[1]
                self.current_source["file_name"] = file_name
                
                # If we have page info too
                if hasattr(self, 'current_source') and "page" in line.lower():
                    try:
                        page_num = line.strip().split()[1]
                        self.current_source["page_num"] = page_num
                    except:
                        self.current_source["page_num"] = "0"
                
                # We have enough information to create a source
                if "category" in self.current_source and "file_name" in self.current_source:
                    source_info = self.current_source
                    source_num = source_info["source_num"]
                    category = source_info["category"]
                    file_name = source_info["file_name"]
                    
                    # Store source
                    self.chat_text.add_source_reference(source_num, source_info)
                    
                    # Add clickable link
                    def open_this_source(event, src=source_info):
                        self.open_source_file(src)
                    
                    self.chat_text.add_clickable_source(
                        source_num=source_num,
                        category=category,
                        filename=file_name,
                        callback=open_this_source
                    )
                    
                    # Clear current source
                    del self.current_source
                    
                return
            except Exception as e:
                self.log(f"Error processing source: {str(e)}")
                if hasattr(self, 'current_source'):
                    del self.current_source
                
        # Check for "To open this source" line and skip it
        if "To open this source" in line:
            return
        
        # Process regular output text
        self.chat_text.append_streaming_text(line)
    
    def process_chat_output(self, line):
        """Process output from the direct LLM chat."""
        # Log the raw output for debugging
        self.log(line.strip())
        
        # Skip loading messages
        if "Loading LLM model" in line:
            return
            
        # Replace "Model loaded successfully" with "Model loaded and ready"
        if "Model loaded successfully" in line:
            self.chat_text.append_streaming_text("Model loaded and ready\n")
            return
        
        # Skip llama_context message
        if "llama_context" in line or "n_ctx_per_seq" in line:
            return
            
        # Skip "Generating response" message
        if "Generating response" in line:
            return
            
        # Stream directly to the chat window
        self.chat_text.append_streaming_text(line)
    
    def search_completed(self, return_code):
        """Handle search process completion."""
        if return_code == 0:
            self.status_text.set("Ready")
            self.log("Search completed successfully")
        else:
            self.status_text.set("Error")
            self.log(f"Search process returned with code {return_code}")
            self.chat_text.append_message(f"\nError: Search process exited with code {return_code}", "error")
        
        # Clear the current process
        self.current_process = None
    
    def vector_llm_completed(self, return_code, temp_file):
        """Handle vector+LLM process completion and clean up."""
        try:
            # Remove temporary file
            os.unlink(temp_file)
        except:
            pass
        
        # Update status
        if return_code == 0:
            self.status_text.set("Ready")
            self.log("Vector+LLM search completed successfully")
        else:
            self.status_text.set("Error")
            self.log(f"Vector+LLM search returned with code {return_code}")
            self.chat_text.append_message(f"\nError: Vector+LLM search exited with code {return_code}", "error")
        
        # Clear the current process
        self.current_process = None
    
    def chat_completed(self, return_code, temp_file):
        """Handle chat process completion and clean up temp files."""
        try:
            # Remove temporary file
            os.unlink(temp_file)
        except:
            pass
        
        # Update status
        if return_code == 0:
            self.status_text.set("Ready")
            self.log("Chat completed successfully")
        else:
            self.status_text.set("Error")
            self.log(f"Chat process returned with code {return_code}")
            self.chat_text.append_message(f"\nError: Chat process exited with code {return_code}", "error")
        
        # Clear the current process
        self.current_process = None
    
    def open_source(self, source_num):
        """Open a source file by its reference number."""
        if source_num in self.chat_text.sources:
            source_info = self.chat_text.sources[source_num]
            self.open_source_file(source_info)
        else:
            self.chat_text.append_message(f"Error: Source {source_num} not found.", "error")
    
    def open_source_file(self, source_info):
        """Open the source file when clicked."""
        try:
            category = source_info.get("category", "").replace("library-", "")
            file_name = source_info.get("file_name", "")
            
            if not category or not file_name:
                self.log("Error: Missing category or file name")
                return
            
            # Construct potential file paths
            potential_paths = [
                # Try DATABASE/survivorlibrary/category/filename
                os.path.join(self.database_dir, "survivorlibrary", category, file_name),
                
                # Try DATABASE/category/filename
                os.path.join(self.database_dir, category, file_name),
                
                # Try just DATABASE/filename
                os.path.join(self.database_dir, file_name),
                
                # Also try without the database path
                os.path.join("/home/mike/DATABASE/survivorlibrary", category, file_name),
                os.path.join("/home/mike/DATABASE", category, file_name),
                os.path.join("/home/mike/DATABASE", file_name),
                
                # Try just with category and filename
                os.path.join(category, file_name),
            ]
            
            # Find the first path that exists
            file_path = None
            for path in potential_paths:
                if os.path.exists(path):
                    file_path = path
                    break
            
            if not file_path:
                # Try a more extensive search
                self.chat_text.append_message(f"Searching for file {file_name}...", "system")
                
                found_files = []
                for root, dirs, files in os.walk(self.database_dir):
                    if file_name in files:
                        found_files.append(os.path.join(root, file_name))
                
                if found_files:
                    file_path = found_files[0]  # Take the first match
                
            if not file_path:
                self.log(f"Error: Could not find file {file_name} in category {category}")
                self.chat_text.append_message(f"Error: Could not find file {file_name}", "error")
                return
            
            # Open the file
            self.log(f"Opening source file: {file_path}")
            self.chat_text.append_message(f"Opening {file_name}...", "system")
            
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", file_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", file_path])
        
        except Exception as e:
            self.log(f"Error opening source file: {str(e)}")
            self.chat_text.append_message(f"Error opening file: {str(e)}", "error")
    
    def clear_chat(self):
        """Clear the chat display."""
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear all chat history?"):
            self.chat_text.clear()
            self.chat_text.append_message("Chat history cleared.", "system")
    
    def get_terminal_command(self):
        """Get the appropriate terminal command for the current platform."""
        if platform.system() == "Windows":
            return ["cmd", "/c", "start"]
        elif platform.system() == "Darwin":  # macOS
            return ["open", "-a", "Terminal"]
        
        # For Linux, check for common terminals
        linux_terminals = {
            "gnome-terminal": ["gnome-terminal", "--"],
            "konsole": ["konsole", "-e"],
            "xterm": ["xterm", "-e"],
            "terminator": ["terminator", "-e"],
            "xfce4-terminal": ["xfce4-terminal", "--execute"]
        }
        
        # Check for installed terminals
        for cmd, args in linux_terminals.items():
            if self.command_exists(cmd):
                return args
        
        # Fallback to xterm
        return ["xterm", "-e"]
    
    def command_exists(self, cmd):
        """Check if a command exists in PATH."""
        for path in os.environ["PATH"].split(os.pathsep):
            cmd_path = os.path.join(path, cmd)
            if os.path.exists(cmd_path) and os.access(cmd_path, os.X_OK):
                return True
        return False
    
    def run_vector_db_creation(self):
        """Run the vector database creation script."""
        # Ask for confirmation
        if messagebox.askyesno("Create Vector Database", 
                              "This will start the vector database creation process, which may take several hours. Continue?"):
            
            try:
                # Get terminal command for the current platform
                terminal_cmd = self.get_terminal_command()
                
                # Build the command based on platform
                if platform.system() == "Windows":
                    cmd = terminal_cmd + [f"{self.loki_dir}\\create_vector_db.sh"]
                elif platform.system() == "Darwin":  # macOS
                    cmd = terminal_cmd + [f"{self.loki_dir}/create_vector_db.sh"]
                else:  # Linux
                    cmd = terminal_cmd + [f"bash {self.loki_dir}/create_vector_db.sh"]
                
                # Execute in a terminal
                self.log("Starting vector database creation...")
                self.chat_text.append_message("Starting vector database creation in a new terminal window...", "system")
                subprocess.Popen(cmd, shell=(platform.system() == "Windows"))
                
            except Exception as e:
                self.log(f"Error starting vector database creation: {str(e)}")
                self.chat_text.append_message(f"Error starting vector database creation: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to start vector database creation: {str(e)}")
    
    def run_search_interface(self):
        """Run the search interface in a terminal."""
        try:
            # Get terminal command for the current platform
            terminal_cmd = self.get_terminal_command()
            
            # Build the command based on platform
            if platform.system() == "Windows":
                cmd = terminal_cmd + [f"{self.loki_dir}\\loki.sh"]
            elif platform.system() == "Darwin":  # macOS
                cmd = terminal_cmd + [f"{self.loki_dir}/loki.sh"]
            else:  # Linux
                cmd = terminal_cmd + [f"bash {self.loki_dir}/loki.sh"]
            
            # Execute in a terminal
            self.log("Starting search interface...")
            self.chat_text.append_message("Starting search interface in a new terminal window...", "system")
            subprocess.Popen(cmd, shell=(platform.system() == "Windows"))
            
        except Exception as e:
            self.log(f"Error starting search interface: {str(e)}")
            self.chat_text.append_message(f"Error starting search interface: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to start search interface: {str(e)}")
    
    def run_llm_interface(self):
        """Run the LLM interface in a terminal."""
        try:
            # Get terminal command for the current platform
            terminal_cmd = self.get_terminal_command()
            
            # Build the command based on platform
            if platform.system() == "Windows":
                cmd = terminal_cmd + [f"{self.loki_dir}\\loki_llm.sh"]
            elif platform.system() == "Darwin":  # macOS
                cmd = terminal_cmd + [f"{self.loki_dir}/loki_llm.sh"]
            else:  # Linux
                cmd = terminal_cmd + [f"bash {self.loki_dir}/loki_llm.sh"]
            
            # Execute in a terminal
            self.log("Starting LLM interface...")
            self.chat_text.append_message("Starting LLM interface in a new terminal window...", "system")
            subprocess.Popen(cmd, shell=(platform.system() == "Windows"))
            
        except Exception as e:
            self.log(f"Error starting LLM interface: {str(e)}")
            self.chat_text.append_message(f"Error starting LLM interface: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to start LLM interface: {str(e)}")
    
    def show_about(self):
        """Show the about dialog."""
        messagebox.showinfo(
            "About LOKI",
            "LOKI - Localized Offline Knowledge Interface\n\n"
            "Version 1.0\n\n"
            "An offline database of indexed survival information with LLM integration."
        )
    
    def show_help(self):
        """Show the help dialog."""
        help_text = """
LOKI Usage Instructions:

1. Search Modes:
   - Vector Search Only: Uses vector search to find relevant information
   - Vector + LLM: Uses both vector search and LLM to answer questions
   - LLM Chat Only: Direct chat with the LLM without searching the database

2. To search:
   - Enter your query in the text box at the bottom
   - Press Enter or click "Send"
   - Use Shift+Enter or Ctrl+Enter for new lines in your query

3. Using Sources:
   - Blue clickable links will appear for source documents
   - Click on any source link to open the original PDF document
   - You can also type the source number in the input box to open it

4. LLM Settings:
   - Select an LLM model from the dropdown
   - Adjust settings in Tools → LLM Settings

5. Tools Menu:
   - LLM Settings: Configure context size and temperature
   - Run Vector Database Creation: Create/recreate the vector database
   - Run Search Interface: Open the command-line search interface
   - Run LLM Interface: Open the command-line LLM interface
        """
        
        help_window = tk.Toplevel(self)
        help_window.title("LOKI Help")
        help_window.geometry("600x400")
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=("TkDefaultFont", 12))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)


def main():
    """Main function to run the LOKI GUI."""
    app = LokiGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
