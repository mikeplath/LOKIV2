#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path

class LLMSettings:
    """Class to handle LLM settings and instructions."""
    
    def __init__(self, base_dir=None):
        """Initialize the LLM settings."""
        if base_dir is None:
            self.base_dir = os.path.expanduser("~/LOKI")
        else:
            self.base_dir = base_dir
        
        # Set paths
        self.settings_path = os.path.join(self.base_dir, "LLM", "settings.json")
        self.instructions_dir = os.path.join(self.base_dir, "LLM", "instructions")
        self.default_instructions_path = os.path.join(self.instructions_dir, "default_instructions.txt")
        self.user_instructions_path = os.path.join(self.instructions_dir, "user_instructions.txt")
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        os.makedirs(self.instructions_dir, exist_ok=True)
        
        # Default settings
        self.default_settings = {
            "context_size": 8192,
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "use_custom_instructions": True
        }
        
        # Load settings
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from the settings file."""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                return self.default_settings.copy()
        except Exception as e:
            print(f"Error loading LLM settings: {str(e)}")
            return self.default_settings.copy()
    
    def save_settings(self):
        """Save settings to the settings file."""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving LLM settings: {str(e)}")
            return False
    
    def reset_settings(self):
        """Reset settings to default."""
        self.settings = self.default_settings.copy()
        return self.save_settings()
    
    def update_settings(self, new_settings):
        """Update settings with new values."""
        self.settings.update(new_settings)
        return self.save_settings()
    
    def get_setting(self, key, default=None):
        """Get a specific setting."""
        return self.settings.get(key, default)
    
    def get_instructions(self):
        """Get the instructions for the LLM."""
        # Determine which instructions to use
        if self.get_setting("use_custom_instructions", True) and os.path.exists(self.user_instructions_path):
            instructions_path = self.user_instructions_path
        else:
            instructions_path = self.default_instructions_path
        
        # Load instructions
        try:
            if os.path.exists(instructions_path):
                with open(instructions_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                return ""
        except Exception as e:
            print(f"Error loading LLM instructions: {str(e)}")
            return ""
    
    def save_instructions(self, instructions, is_default=False):
        """Save instructions to the instructions file."""
        try:
            if is_default:
                path = self.default_instructions_path
            else:
                path = self.user_instructions_path
            
            # Make sure the directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Write instructions to file
            with open(path, "w", encoding="utf-8") as f:
                f.write(instructions)
            
            return True
        except Exception as e:
            print(f"Error saving LLM instructions: {str(e)}")
            return False
    
    def copy_default_to_user(self):
        """Copy default instructions to user instructions."""
        try:
            if os.path.exists(self.default_instructions_path):
                with open(self.default_instructions_path, "r", encoding="utf-8") as f:
                    default_instructions = f.read()
                
                with open(self.user_instructions_path, "w", encoding="utf-8") as f:
                    f.write(default_instructions)
                
                return True
            else:
                return False
        except Exception as e:
            print(f"Error copying instructions: {str(e)}")
            return False


# For testing
if __name__ == "__main__":
    settings = LLMSettings()
    print("Current settings:", settings.settings)
    print("Instructions:", settings.get_instructions())
