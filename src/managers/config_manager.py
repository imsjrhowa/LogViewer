#!/usr/bin/env python3
"""
Configuration Manager for the Log Viewer application.

Manages application configuration and user preferences.
Handles saving and loading of user settings including window geometry,
theme preferences, filter settings, and display options. Provides
import/export functionality and maintains backward compatibility.
"""

import os
import sys
import json
from typing import Dict, Any
from ..utils.constants import (
    CONFIG_DIR_WINDOWS, CONFIG_DIR_UNIX, CONFIG_FILENAME,
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, MAX_WINDOW_WIDTH, MAX_WINDOW_HEIGHT
)


class ConfigManager:
    """
    Manages application configuration and user preferences.
    
    Handles saving and loading of user settings including window geometry,
    theme preferences, filter settings, and display options. Provides
    import/export functionality and maintains backward compatibility.
    """
    
    # Default configuration values for all application settings
    DEFAULT_CONFIG = {
        "window": {
            "width": 1000,        # Default window width
            "height": 1000,       # Default window height
            "x": None,            # Window X position (None = center)
            "y": None,            # Window Y position (None = center)
            "maximized": False    # Whether window starts maximized
        },
        "theme": {
            "current": "dark",           # Default theme
            "auto_switch": False,        # Auto-switch themes based on time
            "auto_switch_time": "18:00"  # Time to switch themes (HH:MM)
        },
        "filter": {
            "default_mode": "contains",  # Default filter mode
            "case_sensitive": False,     # Default case sensitivity
            "remember_history": True,    # Remember filter history
            "max_history": 20           # Maximum history items
        },
        "display": {
            "refresh_rate": 500,         # Default refresh rate (ms)
            "max_lines": 10000,          # Maximum lines to display
            "auto_scroll": True,         # Auto-scroll by default
            "word_wrap": False,          # Word wrap by default
            "font_size": 11,             # Default font size
            "font_family": None,         # Default font family (None = system default)
            "show_line_numbers": True    # Show line numbers by default
        },
        "file": {
            "last_directory": "",        # Last directory used in file dialog
            "last_file_path": "",       # Last file opened
            "remember_encoding": True,   # Remember file encoding
            "auto_detect_encoding": True # Auto-detect file encoding
        },
        "ui": {
            "show_toolbar": True,        # Show toolbar by default
            "show_status_bar": True,     # Show status bar by default
            "toolbar_position": "top",   # Toolbar position
            "status_bar_position": "bottom" # Status bar position
        }
    }
    
    def __init__(self, config_dir: str = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory to store configuration files (None = auto-detect)
        """
        if config_dir is None:
            # Use platform-appropriate configuration directory
            if sys.platform.startswith("win"):
                # Windows: Use AppData\Local\LogViewer
                config_dir = os.path.join(os.path.expanduser("~"), CONFIG_DIR_WINDOWS)
            else:
                # Unix/Linux: Use ~/.logviewer
                config_dir = os.path.expanduser(CONFIG_DIR_UNIX)
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, CONFIG_FILENAME)
        print(f"Debug: Config directory: {self.config_dir}")
        print(f"Debug: Config file: {self.config_file}")
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """
        Load configuration from file.
        
        Attempts to load user configuration, falling back to defaults
        if the file doesn't exist or is corrupted.
        """
        try:
            print(f"Debug: Checking if config file exists: {self.config_file}")
            if os.path.exists(self.config_file):
                print(f"Debug: Loading config from: {self.config_file}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    print(f"Debug: Loaded config keys: {list(loaded_config.keys())}")
                    # Merge with defaults to handle missing keys
                    self._merge_config(loaded_config)
                    print(f"Debug: Config merged successfully")
            else:
                print(f"Debug: Config file does not exist, using defaults")
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            print(f"Debug: Error details: {type(e).__name__}: {e}")
            # Keep default config on error
    
    def save_config(self):
        """
        Save current configuration to file.
        
        Creates configuration directory if it doesn't exist and writes
        the current configuration in JSON format.
        """
        try:
            print(f"Debug: Creating config directory: {self.config_dir}")
            os.makedirs(self.config_dir, exist_ok=True)
            print(f"Debug: Writing config to: {self.config_file}")
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"Debug: Config saved successfully to: {self.config_file}")
            print(f"Debug: Config content preview: {list(self.config.keys())}")
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
            print(f"Debug: Error details: {type(e).__name__}: {e}")
    
    def _merge_config(self, loaded_config: Dict[str, Any]):
        """
        Recursively merge loaded config with defaults.
        
        This ensures that new configuration options are automatically
        added to existing config files without losing user settings.
        
        Args:
            loaded_config: Configuration loaded from file
        """
        def _merge_dict(target: Dict[str, Any], source: Dict[str, Any]):
            """
            Helper function to merge source into target recursively.
            
            Args:
                target: Target dictionary to merge into
                source: Source dictionary to merge from
            """
            for key, value in source.items():
                if key in target and isinstance(value, dict) and isinstance(target[key], dict):
                    # Recursively merge nested dictionaries
                    _merge_dict(target[key], value)
                else:
                    # Direct value assignment (overwrites existing)
                    target[key] = value
        
        # Start merging from the root level
        _merge_dict(self.config, loaded_config)
    
    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., 'window.width')
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
            
        Example:
            config.get('window.width', 800)  # Gets window.width or returns 800
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value):
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., 'window.width')
            value: Value to set
            
        Example:
            config.set('window.width', 1200)  # Sets window.width to 1200
        """
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
    
    def get_window_geometry(self) -> str:
        """
        Get window geometry string for Tkinter.
        
        Constructs a geometry string from saved window dimensions and position.
        Validates dimensions and handles invalid positions gracefully.
        
        Returns:
            Tkinter geometry string (e.g., "1000x800+100+100")
        """
        width = self.get('window.width', 1000)
        height = self.get('window.height', 1000)
        x = self.get('window.x')
        y = self.get('window.y')
        
        # Validate dimensions within reasonable bounds
        width = max(MIN_WINDOW_WIDTH, min(width, MAX_WINDOW_WIDTH))
        height = max(MIN_WINDOW_HEIGHT, min(height, MAX_WINDOW_HEIGHT))
        
        # On Windows, position might not work reliably, so validate coordinates
        if x is not None and y is not None and sys.platform.startswith("win"):
            # Try to center the window if position seems invalid
            if x < 0 or y < 0 or x > MAX_WINDOW_WIDTH or y > MAX_WINDOW_HEIGHT:
                x = None
                y = None
        
        if x is not None and y is not None:
            return f"{width}x{height}+{x}+{y}"
        else:
            return f"{width}x{height}"
    
    def save_window_state(self, window):
        """
        Save current window state and position.
        
        Extracts window geometry and state information from the Tkinter window
        and saves it to configuration for restoration on next launch.
        
        Args:
            window: Tkinter window to save state from
        """
        try:
            # Get window geometry
            geometry = window.geometry()
            print(f"Debug: Parsing geometry string: '{geometry}'")
            
            # Parse geometry string - can be "WxH" or "WxH+X+Y"
            if '+' in geometry:
                # Format: "WxH+X+Y" (with position)
                size_part, pos_part = geometry.split('+', 1)
                width, height = size_part.split('x')
                x, y = pos_part.split('+')
                
                print(f"Debug: Parsed - Width: {width}, Height: {height}, X: {x}, Y: {y}")
                
                self.set('window.width', int(width))
                self.set('window.height', int(height))
                self.set('window.x', int(x))
                self.set('window.y', int(y))
            else:
                # Format: "WxH" (size only)
                width, height = geometry.split('x')
                print(f"Debug: Parsed - Width: {width}, Height: {height} (no position)")
                
                self.set('window.width', int(width))
                self.set('window.height', int(height))
                # Clear saved position
                self.set('window.x', None)
                self.set('window.y', None)
            
            # Check if maximized
            try:
                window_state = window.state()
                print(f"Debug: Window state: {window_state}")
                self.set('window.maximized', window_state == 'zoomed')
            except Exception as e:
                # Some platforms may not support state() method
                print(f"Debug: Could not get window state: {e}")
                self.set('window.maximized', False)
            
            print("Debug: Window state saved successfully")
            
        except Exception as e:
            print(f"Warning: Could not save window state: {e}")
            # Set safe defaults on error
            self.set('window.width', 1000)
            self.set('window.height', 1000)
            self.set('window.x', None)
            self.set('window.y', None)
            self.set('window.maximized', False)
    
    def reset_to_defaults(self):
        """Reset configuration to default values and save to file."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
    
    def export_config(self, filepath: str):
        """
        Export configuration to a file.
        
        Args:
            filepath: Path to export configuration to
            
        Raises:
            Exception: If export fails
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Could not export config: {e}")
    
    def import_config(self, filepath: str):
        """
        Import configuration from a file.
        
        Args:
            filepath: Path to import configuration from
            
        Raises:
            Exception: If import fails
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                self._merge_config(loaded_config)
                self.save_config()
        except Exception as e:
            raise Exception(f"Could not import config: {e}")
