#!/usr/bin/env python3
"""
LOKI - Localized Offline Knowledge Interface
GUI application for accessing offline knowledge database with LLM integration
"""

import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox
import os
import sys
import threading
import time
from datetime import datetime
import psutil
import glob
import subprocess
import traceback


class LokiApp:
    def __init__(self, root):
        """Initialize the LOKI GUI application"""
        # Set paths
        self.base_path = "/home/mike/LOKI"
        self.database_path = os.path.join(self.base_path, "DATABASE", "survivorlibrary")
        self.llm_path = os.path.join(self.base_path, "LLM")
        self.chat_history = []
        
        # LLM variables
        self.model = None
        self.model_name = None
        self.is_model_loaded = False
        self.model_loading = False
        
        # Setup GUI
        self.root = root
        self.root.title("LOKI - Localized Offline Knowledge Interface")
        self.root.geometry("1000x700")  # Set default window size
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # Handle window close
        
        # Configure the grid layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=0)  # Status bar
        self.root.grid_rowconfigure(1, weight=0)  # Model selection
        self.root.grid_rowconfigure(2, weight=1)  # Chat area
        self.root.grid_rowconfigure(3, weight=0)  # Input area
        
        # Create UI components
        self.create_status_bar()
        self.create_model_selector()
        self.create_chat_area()
        self.create_input_area()
        
        # Variable to store the currently displayed source window
        self.source_window = None
        
        # Initialize system status
        self.update_status("System initializing...")
        
        # Start system initialization in a separate thread
        threading.Thread(target=self.initialize_system, daemon=True).start()
    
    def on_close(self):
        """Handle window close event"""
        # Free resources if needed
        if self.model is not None:
            self.model = None
        self.root.destroy()
        
    def create_status_bar(self):
        """Create the status bar at the top of the window"""
        status_frame = tk.Frame(self.root, bg="#f0f0f0", padx=5, pady=5)
        status_frame.grid(row=0, column=0, sticky="ew")
        
        # Status label
        self.status_label = tk.Label(status_frame, text="Status: Initializing...", anchor="w")
        self.status_label.pack(side=tk.LEFT)
        
        # Hardware info label
        self.hardware_label = tk.Label(status_frame, text="Hardware: Detecting...", anchor="e")
        self.hardware_label.pack(side=tk.RIGHT)
    
    def create_model_selector(self):
        """Create the model selection dropdown"""
        model_frame = tk.Frame(self.root, padx=10, pady=5)
        model_frame.grid(row=1, column=0, sticky="ew")
        
        # Model label
        model_label = tk.Label(model_frame, text="Select Model:")
        model_label.pack(side=tk.LEFT)
        
        # Model dropdown
        self.model_var = tk.StringVar(value="")
        self.model_dropdown = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly", width=40)
        self.model_dropdown.pack(side=tk.LEFT, padx=(5, 10))
        
        # Load model button
        self.load_button = tk.Button(model_frame, text="Load Model", command=self.load_selected_model)
        self.load_button.pack(side=tk.LEFT)
        
        # Model status label
        self.model_status = tk.Label(model_frame, text="Model: Not loaded", fg="red")
        self.model_status.pack(side=tk.RIGHT)
    
    def create_chat_area(self):
        """Create the main chat display area"""
        chat_frame = tk.Frame(self.root)
        chat_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Make the chat frame expandable
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)
        
        # Create scrolled text widget for chat display
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD,
            bg="#ffffff",
            font=("TkDefaultFont", 11)
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        self.chat_display.config(state=tk.DISABLED)  # Make it read-only
        
        # Configure tags for different message types
        self.chat_display.tag_configure("user", foreground="#003366", font=("TkDefaultFont", 11, "bold"))
        self.chat_display.tag_configure("system", foreground="#006633", font=("TkDefaultFont", 11, "italic"))
        self.chat_display.tag_configure("error", foreground="#CC0000", font=("TkDefaultFont", 11, "italic"))
        self.chat_display.tag_configure("ai", foreground="#330066", font=("TkDefaultFont", 11))
        self.chat_display.tag_configure("source", foreground="#990000", underline=True)
        
        # Welcome message
        self.append_to_chat("Welcome to LOKI - Localized Offline Knowledge Interface", "system")
        self.append_to_chat("System is initializing. Please wait...", "system")
    
    def create_input_area(self):
        """Create the user input area at the bottom"""
        input_frame = tk.Frame(self.root, padx=10, pady=10)
        input_frame.grid(row=3, column=0, sticky="ew")
        
        # Make the input frame columns expandable
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_columnconfigure(1, weight=0)
        
        # Create the text input field
        self.input_field = tk.Text(input_frame, height=3, wrap=tk.WORD, font=("TkDefaultFont", 11))
        self.input_field.grid(row=0, column=0, sticky="ew")
        
        # Bind Enter key to send message (Shift+Enter for new line)
        self.input_field.bind("<Return>", self.on_enter_key)
        
        # Create send button
        self.send_button = tk.Button(input_frame, text="Send", command=self.send_message, width=10)
        self.send_button.grid(row=0, column=1, padx=(10, 0))
        
        # Initially disable the input field and send button (until model is loaded)
        self.input_field.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
    
    def on_enter_key(self, event):
        """Handle Enter key in the input field"""
        # If shift is held, allow regular Enter behavior (new line)
        if event.state & 0x1:  # Check if Shift is pressed
            return
        
        # Otherwise, send the message and prevent default Enter behavior
        self.send_message()
        return "break"
    
    def find_model_files(self):
        """Find all available model files in the LLM directory"""
        if not os.path.exists(self.llm_path):
            return []
            
        # Look for .gguf files
        model_files = glob.glob(os.path.join(self.llm_path, "*.gguf"))
        
        # Format for display: filename (size)
        model_options = []
        for file_path in model_files:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024 * 1024)  # Size in GB
            model_options.append(f"{file_name} ({file_size:.1f} GB)")
            
        return model_options
    
    def get_model_path_from_display_name(self, display_name):
        """Convert display name back to file path"""
        if not display_name:
            return None
            
        # Extract the filename from the display name (remove size info)
        file_name = display_name.split(" (")[0]
        
        # Return the full path
        return os.path.join(self.llm_path, file_name)
    
    def load_selected_model(self):
        """Load the selected model"""
        # Get selected model
        selected = self.model_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a model first.")
            return
            
        # Get model path
        model_path = self.get_model_path_from_display_name(selected)
        if not model_path or not os.path.exists(model_path):
            messagebox.showerror("Error", f"Model file not found: {model_path}")
            return
            
        # Update UI
        self.model_status.config(text="Model: Loading...", fg="orange")
        self.load_button.config(state=tk.DISABLED)
        self.model_dropdown.config(state="disabled")
        self.update_status(f"Loading model: {os.path.basename(model_path)}")
        self.model_loading = True
        
        # Load model in a separate thread
        threading.Thread(target=self._load_model_thread, args=(model_path,), daemon=True).start()
    
    def _load_model_thread(self, model_path):
        """Thread function to load the model without freezing the UI"""
        try:
            # Import here to avoid loading unnecessary modules if not needed
            from llama_cpp import Llama
            
            # Display loading message
            self.append_to_chat(f"Loading model {os.path.basename(model_path)}. This may take a few minutes...", "system")
            
            # Get RAM size to determine context size
            ram_gb = psutil.virtual_memory().total / (1024**3)
            n_ctx = 2048  # Default
            if ram_gb > 16:
                n_ctx = 4096
            if ram_gb > 32:
                n_ctx = 8192
            
            # Load the model
            self.model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=0  # Use CPU for now, can enable GPU layers if needed
            )
            
            # Update UI on success
            self.model_name = os.path.basename(model_path)
            self.is_model_loaded = True
            
            # Update status in the main thread
            self.root.after(0, self._model_loaded_success)
            
        except Exception as e:
            # Update status in the main thread
            error_traceback = traceback.format_exc()
            self.root.after(0, lambda: self._model_loaded_error(f"{str(e)}\n{error_traceback}"))
    
    def _model_loaded_success(self):
        """Update UI after successful model loading"""
        self.model_status.config(text=f"Model: {self.model_name} (Loaded)", fg="green")
        self.load_button.config(state=tk.NORMAL)
        self.model_dropdown.config(state="readonly")
        self.model_loading = False
        self.update_status("Model loaded successfully")
        self.append_to_chat(f"Model {self.model_name} loaded successfully. You can now chat with LOKI.", "system")
        
        # Enable input field and send button
        self.input_field.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
    
    def _model_loaded_error(self, error_message):
        """Update UI after model loading error"""
        self.model_status.config(text="Model: Failed to load", fg="red")
        self.load_button.config(state=tk.NORMAL)
        self.model_dropdown.config(state="readonly")
        self.model_loading = False
        self.update_status("Error loading model")
        self.append_to_chat(f"Error loading model: {error_message}", "error")
    
    def send_message(self):
        """Process user input and send to chat"""
        user_input = self.input_field.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        # Check if model is loaded
        if not self.is_model_loaded:
            self.append_to_chat("Please load a model first.", "error")
            return
            
        # Clear the input field
        self.input_field.delete("1.0", tk.END)
        
        # Display user message in chat
        self.append_to_chat(f"You: {user_input}", "user")
        
        # Disable input during processing
        self.input_field.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        
        # Add to chat history
        self.chat_history.append({"role": "user", "content": user_input})
        
        # Process the message in a separate thread to keep UI responsive
        threading.Thread(
            target=self.process_user_input,
            args=(user_input,),
            daemon=True
        ).start()
    
    def process_user_input(self, user_input):
        """Process user input and generate response"""
        try:
            self.update_status("Generating response...")
            
            # Check if model is loaded
            if not self.is_model_loaded or self.model is None:
                self.append_to_chat("Error: Model not loaded properly.", "error")
                self.enable_input_controls()
                return
            
            # For now, we'll use a simple prompt without database integration
            # In future versions, we'll add the database searching capability
            
            # Construct the prompt from chat history
            full_prompt = "You are LOKI (Localized Offline Knowledge Interface), an AI assistant specializing in survival and emergency information. "
            full_prompt += "You have access to the Survivor Library, a comprehensive collection of books and manuals on survival, medicine, construction, and other practical skills.\n\n"
            
            # Add relevant chat history (last 5 exchanges at most)
            for entry in self.chat_history[-10:]:
                if entry["role"] == "user":
                    full_prompt += f"Human: {entry['content']}\n"
                else:
                    full_prompt += f"LOKI: {entry['content']}\n"
            
            # Add the current question if it's not already the last one
            if self.chat_history[-1]["content"] != user_input:
                full_prompt += f"Human: {user_input}\n"
            
            full_prompt += "LOKI: "
            
            # Start response streaming by updating status
            self.append_to_chat("LOKI is thinking...", "system")
            
            # Generate response with the LLM
            response = self.model(
                full_prompt,
                max_tokens=1024,
                stop=["Human:", "\nHuman:", "LOKI:"],
                echo=False
            )
            
            # Extract the generated text
            if isinstance(response, dict) and "choices" in response and len(response["choices"]) > 0:
                generated_text = response["choices"][0]["text"].strip()
            else:
                generated_text = "I'm having difficulty generating a response."
                
            # Add to chat history
            self.chat_history.append({"role": "assistant", "content": generated_text})
                
            # Mock finding PDFs in the database (for demonstration)
            sources = []
            try:
                # Look for PDF files in the database that might be relevant
                keywords = user_input.lower().split()
                for root, dirs, files in os.walk(self.database_path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            # Simple keyword matching for demo purposes
                            file_lower = file.lower()
                            if any(keyword in file_lower for keyword in keywords):
                                sources.append({
                                    "title": file,
                                    "path": os.path.join(root, file),
                                    "page": 1  # Default to first page
                                })
                                if len(sources) >= 3:  # Limit to 3 sources
                                    break
                    if len(sources) >= 3:
                        break
            except Exception as e:
                self.append_to_chat(f"Error searching for sources: {str(e)}", "error")
                
            # Format response with sources
            response_with_sources = generated_text
            if sources:
                source_text = "\n\nSources:\n"
                for i, source in enumerate(sources, 1):
                    source_text += f"[{i}] {source['title']}\n"
                response_with_sources += source_text
            
            # Display the response in the chat
            self.display_loki_response(response_with_sources, sources)
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            self.append_to_chat(f"Error generating response: {str(e)}\n{error_traceback}", "error")
        finally:
            # Re-enable input controls
            self.enable_input_controls()
            self.update_status("Ready")
    
    def enable_input_controls(self):
        """Re-enable input field and send button"""
        self.root.after(0, lambda: self.input_field.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.input_field.focus_set())
    
    def display_loki_response(self, response, sources=None):
        """Display LOKI's response with optional source citations"""
        # Split the response to extract the main content and sources section
        if "Sources:" in response:
            main_content, sources_text = response.split("Sources:", 1)
            response_text = f"LOKI: {main_content.strip()}\n\nSources:{sources_text}"
        else:
            response_text = f"LOKI: {response.strip()}"
        
        # Display the response
        self.append_to_chat(response_text, "ai")
        
        # Add clickable source citations if available
        if sources:
            self.append_to_chat("\nClick on sources to view original documents:", "system")
            for i, source in enumerate(sources, 1):
                source_text = f"[{i}] {source['title']}"
                
                # Add the source with a tag that can be clicked
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.insert(tk.END, source_text + "\n", f"source_{i}")
                
                # Bind click event to this specific source
                self.chat_display.tag_bind(
                    f"source_{i}", 
                    "<Button-1>", 
                    lambda e, src=source: self.open_source_document(src)
                )
                self.chat_display.config(state=tk.DISABLED)
    
    def open_source_document(self, source):
        """Open the source document in a separate window"""
        # Check if the source file exists
        if 'path' in source and os.path.exists(source['path']):
            try:
                # Try to open the PDF with the default system PDF viewer
                if sys.platform == 'linux':
                    subprocess.Popen(['xdg-open', source['path']])
                    self.append_to_chat(f"Opening {source['title']} with system PDF viewer.", "system")
                    return
            except Exception as e:
                pass  # Fall back to our built-in viewer
        
        # If system viewer fails or file doesn't exist, show our own viewer
        
        # Close any existing source window
        if self.source_window and self.source_window.winfo_exists():
            self.source_window.destroy()
            
        # Create new window for the source
        self.source_window = tk.Toplevel(self.root)
        self.source_window.title(f"Source: {source['title']}")
        self.source_window.geometry("800x600")
        
        # Add a frame for the content
        frame = tk.Frame(self.source_window, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Show document path
        path_label = tk.Label(frame, text=f"Document: {source.get('path', 'Unknown')}", anchor="w", justify="left")
        path_label.pack(fill=tk.X, pady=(0, 10))
        
        # For now, just show a placeholder
        # In the future, this will display the actual PDF content
        info_text = f"Document: {source['title']}\n"
        if 'page' in source:
            info_text += f"Page: {source['page']}\n"
        
        if 'path' in source and os.path.exists(source['path']):
            info_text += f"\nFile exists at: {source['path']}\n"
        else:
            info_text += f"\nFile not found at: {source.get('path', 'Unknown')}\n"
        
        info_text += "\nThis is a placeholder for the actual document viewer.\n"
        info_text += "Currently, we're trying to open the document with your system's PDF viewer.\n"
        info_text += "In the future implementation, the PDF will be displayed directly here."
        
        # Display the information
        info_label = tk.Label(frame, text=info_text, justify=tk.LEFT, padx=20, pady=20)
        info_label.pack(fill=tk.BOTH, expand=True)
        
        # Add open with system viewer button if file exists
        if 'path' in source and os.path.exists(source['path']):
            open_button = tk.Button(
                frame, 
                text="Open with System Viewer", 
                command=lambda: subprocess.Popen(['xdg-open', source['path']])
            )
            open_button.pack(pady=5)
        
        # Add a close button
        close_button = tk.Button(frame, text="Close", command=self.source_window.destroy)
        close_button.pack(pady=5)
    
    def append_to_chat(self, message, tag=None):
        """Add a message to the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        # Add timestamp if it's a new message (not a continuation)
        if not message.startswith("\n"):
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            self.chat_display.insert(tk.END, timestamp, "system")
        
        # Add the message with appropriate tag
        self.chat_display.insert(tk.END, message + "\n", tag)
        
        # Scroll to the end
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def update_status(self, status_text):
        """Update the status bar with current system status"""
        self.status_label.config(text=f"Status: {status_text}")
        self.root.update_idletasks()
    
    def initialize_system(self):
        """Initialize system components"""
        try:
            # Step 1: Detect hardware
            self.update_status("Detecting hardware...")
            time.sleep(0.5)
            
            # Detect CPU cores and RAM
            cpu_cores = os.cpu_count() or 2
            ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
            self.hardware_label.config(text=f"Hardware: {cpu_cores} cores, {ram_gb}GB RAM")
            
            # Step 2: Check database
            self.update_status("Checking knowledge database...")
            time.sleep(0.5)
            
            if not os.path.exists(self.database_path):
                self.append_to_chat(f"Warning: Database path not found at {self.database_path}", "error")
                self.update_status("Warning: Database not found")
            else:
                # Count files in database (just for display)
                file_count = 0
                for _, _, files in os.walk(self.database_path):
                    for file in files:
                        if file.lower().endswith(('.pdf', '.txt')):
                            file_count += 1
                            if file_count >= 100:  # Limit counting for performance
                                break
                    if file_count >= 100:
                        break
                        
                if file_count >= 100:
                    file_count = f"{file_count}+"
                self.append_to_chat(f"Database found with approximately {file_count} documents", "system")
            
            # Step 3: Check LLM
            self.update_status("Checking language models...")
            time.sleep(0.5)
            
            llm_files = []
            if os.path.exists(self.llm_path):
                llm_files = [f for f in os.listdir(self.llm_path) if f.endswith('.gguf')]
            
            if not llm_files:
                self.append_to_chat(f"Warning: No language models found at {self.llm_path}", "error")
                self.update_status("Warning: LLM not found")
            else:
                self.append_to_chat(f"Found language models: {', '.join(llm_files)}", "system")
                
                # Populate model dropdown
                model_options = self.find_model_files()
                self.model_dropdown['values'] = model_options
                if model_options:
                    self.model_dropdown.current(0)  # Select first model by default
            
            # System ready
            self.update_status("Ready")
            self.append_to_chat("System initialized. Please load a model to begin.", "system")
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            self.update_status("Initialization error")
            self.append_to_chat(f"Error during initialization: {str(e)}\n{error_traceback}", "error")


def main():
    """Main entry point for the application"""
    root = tk.Tk()
    app = LokiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
