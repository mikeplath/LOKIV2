#!/usr/bin/env python3
"""
LOKI Configuration Management
Handles all configuration settings for the LOKI system
"""

import os
import json
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional

class LokiConfig:
    """Configuration manager for LOKI"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.loki_dir = Path("/home/mike/LOKI")
        self.config_file = Path(config_file) if config_file else self.loki_dir / "config" / "loki_config.json"
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Default configuration
        self.defaults = {
            "paths": {
                "loki_dir": str(self.loki_dir),
                "vector_db_dir": str(self.loki_dir / "vector_db"),
                "database_dir": str(self.loki_dir / "DATABASE"),
                "logs_dir": str(self.loki_dir / "logs"),
                "models_dir": str(self.loki_dir / "LLM" / "models")
            },
            "gui": {
                "theme": "system",
                "window_geometry": "1200x800+100+100",
                "font_size": 11,
                "search_mode": "vector_llm"
            },
            "llm": {
                "default_model": "",
                "context_size": 8192,
                "temperature": 0.7,
                "max_tokens": 2048
            },
            "search": {
                "max_results": 5,
                "min_similarity": 0.0
            },
            "emergency": {
                "stop_command_word": "STOP"
            }
        }
        
        # Load existing config or create default
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_configs(self.defaults, config)
            else:
                # Create default config file
                self._save_config(self.defaults)
                return self.defaults.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.defaults.copy()
    
    def _merge_configs(self, defaults: Dict, config: Dict) -> Dict:
        """Recursively merge configurations"""
        merged = defaults.copy()
        for key, value in config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        # Save the updated configuration
        self._save_config(self._config)
    
    def list_available_models(self) -> List[str]:
        """Find available LLM models in standard directories"""
        model_dirs = [
            self.get("paths.models_dir"),
            str(self.loki_dir / "models"),
            str(Path.home() / "models"),
            str(Path.home() / ".cache" / "lm-studio" / "models")
        ]
        
        extensions = [".gguf", ".bin"]
        models = []
        
        for directory in model_dirs:
            if not Path(directory).exists():
                continue
            
            for ext in extensions:
                for model_file in Path(directory).glob(f"**/*{ext}"):
                    model_path = str(model_file)
                    if model_path not in models:
                        models.append(model_path)
        
        return models
    
    def save(self) -> None:
        """Manually save configuration"""
        self._save_config(self._config)


# Global config instance
_config_instance = None


def get_config() -> LokiConfig:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = LokiConfig()
    return _config_instance


def reload_config() -> LokiConfig:
    """Reload the configuration from file"""
    global _config_instance
    _config_instance = LokiConfig()
    return _config_instance
