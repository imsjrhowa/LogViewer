#!/usr/bin/env python3
"""
Log Viewer (auto-refresh) — Windows-friendly, 3.6+ compatible

A comprehensive log file viewer with real-time monitoring, advanced filtering,
multiple themes, and extensive customization options.

Features:
- Real-time log file monitoring with auto-refresh
- Advanced filtering system with multiple modes (contains, regex, exact match, etc.)
- Multiple color themes (Dark, Light, Sunset) with dynamic switching
- Line numbers display with scroll synchronization
- Word wrap and auto-scroll options
- File encoding auto-detection (UTF-8, UTF-16, BOM detection)
- Comprehensive settings management with import/export
- Keyboard shortcuts for common operations
- Filter history and preferences persistence
- Professional UI with toolbar and status bar

Usage:
    python log_viewer.py --file /path/to/your/log.txt
    python log_viewer.py --theme light --refresh 1000

Requires only the Python standard library.
"""

import argparse
import io
import os
import sys
import time
import tkinter as tk
import collections
import re
import json
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Any, List, Tuple

# Global constants for application defaults
MAX_LINES_DEFAULT = 10_000      # Maximum lines to keep in memory
DEFAULT_REFRESH_MS = 500        # Default refresh interval in milliseconds
DEFAULT_ENCODING = "auto"       # Default encoding (auto-detection enabled)
DEFAULT_THEME = "dark"          # Default color theme


class ThemeManager:
    """
    Manages color themes for the Log Viewer application.
    
    Provides three built-in themes (Dark, Light, Sunset) with consistent
    color schemes across all UI elements. Supports dynamic theme switching
    and theme preference persistence.
    """
    
    # Comprehensive theme color definitions for consistent UI appearance
    THEMES = {
        "dark": {
            "name": "Dark",
            "bg": "#1e1e1e",           # Main application background
            "fg": "#d4d4d4",           # Main text color
            "text_bg": "#1e1e1e",      # Text area background
            "text_fg": "#d4d4d4",      # Text area text color
            "insert_bg": "#ffffff",    # Text cursor/caret color
            "toolbar_bg": "#2d2d2d",   # Toolbar background
            "toolbar_fg": "#d4d4d4",   # Toolbar text color
            "status_bg": "#2d2d2d",    # Status bar background
            "status_fg": "#d4d4d4",    # Status bar text color
            "menu_bg": "#2d2d2d",      # Menu background
            "menu_fg": "#d4d4d4",      # Menu text color
            "menu_select_bg": "#404040", # Menu selection highlight
            "button_bg": "#404040",     # Button background
            "button_fg": "#d4d4d4",    # Button text color
            "entry_bg": "#3c3c3c",     # Entry field background
            "entry_fg": "#d4d4d4",     # Entry field text color
            "entry_insert_bg": "#ffffff", # Entry field cursor color
        },
        "light": {
            "name": "Light",
            "bg": "#ffffff",           # Main application background
            "fg": "#000000",           # Main text color
            "text_bg": "#ffffff",      # Text area background
            "text_fg": "#000000",      # Text area text color
            "insert_bg": "#000000",    # Text cursor/caret color
            "toolbar_bg": "#f0f0f0",   # Toolbar background
            "toolbar_fg": "#000000",   # Toolbar text color
            "status_bg": "#f0f0f0",    # Status bar background
            "status_fg": "#000000",    # Status bar text color
            "menu_bg": "#f0f0f0",      # Menu background
            "menu_fg": "#000000",      # Menu text color
            "menu_select_bg": "#e0e0e0", # Menu selection highlight
            "button_bg": "#e0e0e0",     # Button background
            "button_fg": "#000000",    # Button text color
            "entry_bg": "#ffffff",     # Entry field background
            "entry_fg": "#000000",     # Entry field text color
            "entry_insert_bg": "#000000", # Entry field cursor color
        },
        "sunset": {
            "name": "Sunset",
            "bg": "#2d1b3d",           # Main background (deep purple)
            "fg": "#f4e4bc",           # Main text (warm cream)
            "text_bg": "#2d1b3d",      # Text area background
            "text_fg": "#f4e4bc",      # Text area text color
            "insert_bg": "#ff6b35",    # Text cursor/caret color (orange)
            "toolbar_bg": "#3d2b4d",   # Toolbar background
            "toolbar_fg": "#f4e4bc",   # Toolbar text color
            "status_bg": "#3d2b4d",    # Status bar background
            "status_fg": "#f4e4bc",    # Status bar text color
            "menu_bg": "#3d2b4d",      # Menu background
            "menu_fg": "#f4e4bc",      # Menu text color
            "menu_select_bg": "#4d3b5d", # Menu selection highlight
            "button_bg": "#4d3b5d",     # Button background
            "button_fg": "#f4e4bc",    # Button text color
            "entry_bg": "#3d2b4d",     # Entry field background
            "entry_fg": "#f4e4bc",     # Entry field text color
            "entry_insert_bg": "#ff6b35", # Entry field cursor color
        }
    }
    
    def __init__(self, theme_name: str = DEFAULT_THEME):
        """
        Initialize theme manager with specified theme.
        
        Args:
            theme_name: Name of the initial theme to use
        """
        self.current_theme = theme_name
        # Fallback to default theme if specified theme doesn't exist
        if theme_name not in self.THEMES:
            self.current_theme = DEFAULT_THEME
    
    def get_theme(self, theme_name: str = None) -> Dict[str, Any]:
        """
        Get theme colors by name.
        
        Args:
            theme_name: Name of theme to retrieve (None for current)
            
        Returns:
            Dictionary containing theme color definitions
        """
        if theme_name is None:
            theme_name = self.current_theme
        return self.THEMES.get(theme_name, self.THEMES[DEFAULT_THEME])
    
    def get_current_theme(self) -> Dict[str, Any]:
        """
        Get current theme colors.
        
        Returns:
            Dictionary containing current theme color definitions
        """
        return self.get_theme(self.current_theme)
    
    def set_theme(self, theme_name: str) -> bool:
        """
        Set current theme.
        
        Args:
            theme_name: Name of theme to set
            
        Returns:
            True if theme changed, False if theme doesn't exist
        """
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            return True
        return False
    
    def get_theme_names(self) -> list:
        """
        Get list of available theme names.
        
        Returns:
            List of theme identifier strings
        """
        return list(self.THEMES.keys())
    
    def get_theme_display_names(self) -> list:
        """
        Get list of theme display names for UI.
        
        Returns:
            List of human-readable theme names
        """
        return [self.THEMES[name]["name"] for name in self.THEMES]


class FilterManager:
    """
    Advanced filtering system for log entries with multiple modes and history.
    
    Supports various filtering modes including substring matching, regex patterns,
    exact matching, and negation. Maintains filter history and provides
    comprehensive error handling for invalid patterns.
    """
    
    # Available filter modes with human-readable descriptions
    MODES = {
        "contains": "Contains",           # Text appears anywhere in line
        "starts_with": "Starts With",     # Line begins with text
        "ends_with": "Ends With",         # Line ends with text
        "regex": "Regular Expression",    # Use regex patterns
        "exact": "Exact Match",           # Line exactly matches text
        "not_contains": "Not Contains"    # Line does NOT contain text
    }
    
    def __init__(self):
        """Initialize filter manager with default settings."""
        self.current_filter = ""          # Current filter text
        self.current_mode = "contains"    # Current filter mode
        self.case_sensitive = False       # Case sensitivity flag
        self.filter_history = []          # List of previous filters
        self.max_history = 20            # Maximum history items to keep
        self.compiled_regex = None        # Compiled regex pattern (if applicable)
        self.last_error = None            # Last regex compilation error
        
    def set_filter(self, text: str, mode: str = None, case_sensitive: bool = None) -> bool:
        """
        Set the current filter with optional mode and case sensitivity.
        
        Args:
            text: Filter text to apply
            mode: Filter mode (None to keep current)
            case_sensitive: Case sensitivity flag (None to keep current)
            
        Returns:
            True if filter changed, False if no change
        """
        if mode is not None:
            self.current_mode = mode
        if case_sensitive is not None:
            self.case_sensitive = case_sensitive
            
        if text != self.current_filter:
            self.current_filter = text
            self._add_to_history(text)
            self._compile_regex()
            return True
        return False
    
    def _add_to_history(self, text: str):
        """
        Add filter text to history if it's not empty and not already there.
        
        Args:
            text: Filter text to add to history
        """
        if text and text not in self.filter_history:
            self.filter_history.insert(0, text)
            # Maintain maximum history size
            if len(self.filter_history) > self.max_history:
                self.filter_history.pop()
    
    def _compile_regex(self):
        """
        Compile regex pattern if mode is regex.
        
        Handles regex compilation errors gracefully and stores error messages
        for user feedback.
        """
        self.compiled_regex = None
        self.last_error = None
        
        if self.current_mode == "regex" and self.current_filter:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self.compiled_regex = re.compile(self.current_filter, flags)
            except re.error as e:
                self.last_error = str(e)
    
    def matches(self, line: str) -> bool:
        """
        Check if a line matches the current filter.
        
        Args:
            line: Text line to check against filter
            
        Returns:
            True if line matches filter, False otherwise
        """
        if not self.current_filter:
            return True
            
        if self.last_error:
            return False
            
        try:
            # Route to appropriate matching method based on mode
            if self.current_mode == "contains":
                return self._contains_match(line)
            elif self.current_mode == "starts_with":
                return self._starts_with_match(line)
            elif self.current_mode == "ends_with":
                return self._ends_with_match(line)
            elif self.current_mode == "regex":
                return self._regex_match(line)
            elif self.current_mode == "exact":
                return self._exact_match(line)
            elif self.current_mode == "not_contains":
                return self._not_contains_match(line)
            else:
                return self._contains_match(line)
        except Exception:
            return False
    
    def _contains_match(self, line: str) -> bool:
        """
        Check if line contains the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if filter text is found in line
        """
        if self.case_sensitive:
            return self.current_filter in line
        return self.current_filter.lower() in line.lower()
    
    def _starts_with_match(self, line: str) -> bool:
        """
        Check if line starts with the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line begins with filter text
        """
        if self.case_sensitive:
            return line.startswith(self.current_filter)
        return line.lower().startswith(self.current_filter.lower())
    
    def _ends_with_match(self, line: str) -> bool:
        """
        Check if line ends with the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line ends with filter text
        """
        if self.case_sensitive:
            return line.endswith(self.current_filter)
        return line.lower().endswith(self.current_filter.lower())
    
    def _regex_match(self, line: str) -> bool:
        """
        Check if line matches the regex pattern.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line matches regex pattern
        """
        if self.compiled_regex:
            return bool(self.compiled_regex.search(line))
        return False
    
    def _exact_match(self, line: str) -> bool:
        """
        Check if line exactly matches the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line exactly matches filter text
        """
        if self.case_sensitive:
            return line == self.current_filter
        return line.lower() == self.current_filter.lower()
    
    def _not_contains_match(self, line: str) -> bool:
        """
        Check if line does NOT contain the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line does NOT contain filter text
        """
        return not self._contains_match(line)
    
    def get_filter_info(self) -> Dict[str, Any]:
        """
        Get current filter information for display and status updates.
        
        Returns:
            Dictionary containing filter state information
        """
        return {
            "text": self.current_filter,
            "mode": self.current_mode,
            "mode_display": self.MODES.get(self.current_mode, "Unknown"),
            "case_sensitive": self.case_sensitive,
            "has_error": bool(self.last_error),
            "error": self.last_error,
            "is_active": bool(self.current_filter)
        }
    
    def get_mode_names(self) -> List[str]:
        """
        Get list of available filter mode names.
        
        Returns:
            List of filter mode identifier strings
        """
        return list(self.MODES.keys())
    
    def get_mode_display_names(self) -> List[str]:
        """
        Get list of filter mode display names for UI.
        
        Returns:
            List of human-readable filter mode names
        """
        return list(self.MODES.values())
    
    def clear_filter(self):
        """Clear the current filter and reset related state."""
        self.current_filter = ""
        self.compiled_regex = None
        self.last_error = None


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
                config_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "LogViewer")
            else:
                # Unix/Linux: Use ~/.logviewer
                config_dir = os.path.expanduser("~/.logviewer")
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
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
        width = max(800, min(width, 3000))   # Min 800, Max 3000
        height = max(600, min(height, 2000)) # Min 600, Max 2000
        
        # On Windows, position might not work reliably, so validate coordinates
        if x is not None and y is not None and sys.platform.startswith("win"):
            # Try to center the window if position seems invalid
            if x < 0 or y < 0 or x > 3000 or y > 2000:
                x = None
                y = None
        
        if x is not None and y is not None:
            return f"{width}x{height}+{x}+{y}"
        else:
            return f"{width}x{height}"
    
    def save_window_state(self, window: tk.Tk):
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


class TailReader:
    """
    Efficiently read new bytes from a growing (append-only) text file.
    
    Detects file truncation and rotation and reopens as needed. Includes
    BOM detection and heuristic for UTF-16 logs without BOM. Optimized
    for real-time log monitoring with minimal resource usage.
    """
    
    def __init__(self, path: str, encoding: str = DEFAULT_ENCODING):
        """
        Initialize tail reader.
        
        Args:
            path: Path to the file to monitor
            encoding: File encoding (use "auto" for auto-detection)
        """
        self.path = path
        self.encoding = encoding
        self._fh = None  # File handle for reading
        self._inode = None  # File inode for detecting rotation
        self._pos = 0  # Current file position

    def _encoding_from_bom(self, fh) -> Optional[str]:
        """
        Detect encoding from Byte Order Mark (BOM).
        
        Examines the first few bytes of the file to detect common
        encoding signatures like UTF-16 LE/BE and UTF-8 BOM.
        
        Args:
            fh: File handle to examine
            
        Returns:
            Detected encoding string or None if no BOM found
        """
        pos = fh.tell()
        try:
            fh.seek(0)
            head = fh.read(4)
        finally:
            fh.seek(pos)
        if not head:
            return None
        if head.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if head.startswith(b"\xfe\xff"):
            return "utf-16-be"
        if head.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        return None

    def open(self, start_at_end=True):
        """
        Open the file for reading.
        
        Args:
            start_at_end: If True, start reading from end of file
            
        Returns:
            True if file opened successfully
        """
        self.close()
        self._fh = open(self.path, "rb")
        try:
            # Get file inode for rotation detection
            st = os.fstat(self._fh.fileno())
            self._inode = (st.st_dev, st.st_ino)
        except Exception:
            self._inode = None

        # Auto-detect encoding (BOM first)
        if self.encoding == "auto":
            enc = self._encoding_from_bom(self._fh)
            self.encoding = enc or "utf-8"

        if start_at_end:
            # Start reading from end of file (for tailing)
            self._fh.seek(0, io.SEEK_END)
            self._pos = self._fh.tell()
        else:
            # Start reading from beginning of file
            self._fh.seek(0)
            self._pos = 0
        return True

    def close(self):
        """Close the file handle and reset state."""
        try:
            if self._fh:
                self._fh.close()
        finally:
            self._fh = None
            self._inode = None
            self._pos = 0

    def _check_rotation_or_truncate(self):
        """
        Check for file rotation or truncation and reopen if needed.
        
        Detects when the file has been rotated (new inode) or truncated
        (file size smaller than last position) and handles accordingly.
        """
        try:
            st_path = os.stat(self.path)
            inode = (st_path.st_dev, st_path.st_ino)
        except OSError:
            return  # Possibly temporarily missing during rotation
            
        if self._inode and inode != self._inode:
            # File rotated/recreated - reopen from beginning
            self.open(start_at_end=False)
            return
            
        if self._fh:
            try:
                size = os.fstat(self._fh.fileno()).st_size
                if size < self._pos:
                    # File truncated - reset to beginning
                    self._fh.seek(0)
                    self._pos = 0
            except OSError:
                pass

    def read_new_text(self) -> str:
        """
        Read new text from the file since last read.
        
        Handles file rotation, truncation, and encoding issues gracefully.
        Uses heuristics to detect UTF-16 files without BOM.
        
        Returns:
            New text content as string
        """
        if not self._fh:
            try:
                self.open(start_at_end=False)
            except OSError:
                return ""

        self._check_rotation_or_truncate()
        self._fh.seek(self._pos)
        data = self._fh.read()
        if not data:
            return ""

        self._pos = self._fh.tell()

        # Heuristic: if we don't have a BOM and see lots of NULs, switch to utf-16-le
        if self.encoding in ("utf-8", "utf-8-sig") and data and data.count(b"\x00") > len(data) // 4:
            self.encoding = "utf-16-le"

        try:
            return data.decode(self.encoding, errors="replace")
        except LookupError:
            # Fallback to UTF-8 if encoding not supported
            return data.decode("utf-8", errors="replace")


class LogViewerApp(tk.Tk):
    """
    Main Log Viewer application class.
    
    Provides a comprehensive GUI for monitoring log files in real-time with
    advanced filtering, multiple themes, and extensive customization options.
    Built on Tkinter for cross-platform compatibility.
    """
    
    def __init__(self, path: Optional[str], refresh_ms: int = DEFAULT_REFRESH_MS, 
                 encoding: str = DEFAULT_ENCODING, theme: str = DEFAULT_THEME):
        """
        Initialize the Log Viewer application.
        
        Args:
            path: Path to log file to open on startup (None = no file)
            refresh_ms: Refresh interval in milliseconds
            encoding: File encoding to use
            theme: Initial color theme
        """
        super().__init__()
        
        # Initialize configuration manager first (needed for window setup)
        self.config_manager = ConfigManager()
        
        self.title("Log Viewer")
        
        # Get saved window geometry and apply it
        saved_geometry = self.config_manager.get_window_geometry()
        print(f"Debug: Applying saved geometry: '{saved_geometry}'")
        self.geometry(saved_geometry)
        
        # Set minimum size after applying geometry
        self.minsize(800, 600)
        
        # Restore maximized state if saved
        if self.config_manager.get('window.maximized', False):
            print(f"Debug: Restoring maximized state")
            self.state('zoomed')
        
        # Force update to ensure geometry is applied
        self.update_idletasks()
        print(f"Debug: Final window geometry: '{self.geometry()}'")
        
        # Center window if no position was saved or if position is invalid
        if not self.config_manager.get('window.x') or not self.config_manager.get('window.y'):
            self._center_window()
            print(f"Debug: Window centered on screen")
        
        # Initialize theme manager with saved preference or command line argument
        self.theme_manager = ThemeManager(theme)  # Will be updated after UI is built
        
        # Initialize filter manager for advanced filtering capabilities
        self.filter_manager = FilterManager()
        
        # File handling
        self.path = path
        self.tail = TailReader(path, encoding=encoding) if path else None
        
        # Load settings from configuration with fallbacks to defaults
        self.refresh_ms = tk.IntVar(value=self.config_manager.get('display.refresh_rate', refresh_ms))
        self.autoscroll = tk.BooleanVar(value=self.config_manager.get('display.auto_scroll', True))
        self.wrap = tk.BooleanVar(value=self.config_manager.get('display.word_wrap', False))
        self.show_line_numbers = tk.BooleanVar(value=self.config_manager.get('display.show_line_numbers', True))
        self.paused = tk.BooleanVar(value=False)
        self.max_lines = tk.IntVar(value=self.config_manager.get('display.max_lines', MAX_LINES_DEFAULT))

        # Filtering variables
        self.filter_text = tk.StringVar(value="")
        self.case_sensitive = tk.BooleanVar(value=False)
        self.filter_mode = tk.StringVar(value="contains")
        self._filter_job = None  # Debounce handle for filter updates

        # Data storage for efficient filtering and display
        self._line_buffer = collections.deque(maxlen=MAX_LINES_DEFAULT)  # Raw lines storage
        self._filtered_lines = []  # Store filtered lines with original line numbers

        # Build the user interface
        self._build_ui()
        
        # Load saved theme preference if using default theme
        if theme == DEFAULT_THEME:
            saved_theme = self._load_theme_preference()
            if saved_theme != DEFAULT_THEME:
                self.theme_manager.set_theme(saved_theme)
                # Update menu checkmarks to reflect saved theme
                for name, var in self.theme_vars.items():
                    var.set(name == saved_theme)
        
        # Set application icon based on current theme
        self._set_app_icon()
        
        # Load saved filter preferences
        self._load_filter_preferences()
        
        # Apply initial theme to all UI elements
        self._apply_theme()
        
        # Check if we should open the last file from configuration
        if not self.path:  # Only if no file was passed via command line
            last_file_path = self.config_manager.get('file.last_file_path', '')
            if last_file_path and os.path.exists(last_file_path):
                self.path = last_file_path
                self._set_status(f"Opening last file: {os.path.basename(last_file_path)}")
        
        # Open file if specified and start monitoring
        if self.path:
            self._open_path(self.path, first_open=True)
            
        # Start the polling loop for file updates
        self.after(self.refresh_ms.get(), self._poll)
        
        # Bind window close event to save configuration
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # UI
    def _build_ui(self):
        """
        Build the complete user interface.
        
        Creates menus, toolbar, text area with line numbers, scrollbars,
        and status bar. Sets up keyboard shortcuts and event bindings.
        """
        # Create main menu bar
        menubar = tk.Menu(self)
        
        # File menu for file operations
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open…", command=self._choose_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu for display options and theme selection
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Word Wrap", command=self._toggle_wrap)
        view_menu.add_separator()
        
        # Theme submenu with checkmarks for current selection
        theme_menu = tk.Menu(view_menu, tearoff=0)
        self.theme_vars = {}
        for theme_name in self.theme_manager.get_theme_names():
            var = tk.BooleanVar(value=(theme_name == self.theme_manager.current_theme))
            self.theme_vars[theme_name] = var
            theme_menu.add_checkbutton(
                label=self.theme_manager.get_theme(theme_name)["name"],
                variable=var,
                command=lambda t=theme_name: self._change_theme(t)
            )
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Settings menu for application preferences
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Preferences...", command=self._show_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Save Current Settings as Default", command=self._save_as_default)
        settings_menu.add_command(label="Reset to Defaults", command=self._reset_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Export Settings...", command=self._export_settings)
        settings_menu.add_command(label="Import Settings...", command=self._import_settings)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        # Help menu for user assistance
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Filter Help", command=self._show_filter_help)
        help_menu.add_command(label="Theme Info", command=self._show_theme_info)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_keyboard_shortcuts)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)
        
        # Bind keyboard shortcuts for common operations
        self.bind('<Control-t>', lambda e: self._cycle_theme())      # Cycle themes
        self.bind('<Control-T>', lambda e: self._cycle_theme())      # Cycle themes (Shift)
        self.bind('<Control-f>', lambda e: self._focus_filter())     # Focus filter
        self.bind('<Control-F>', lambda e: self._focus_filter())     # Focus filter (Shift)
        self.bind('<Control-w>', lambda e: self._toggle_wrap())      # Toggle word wrap
        self.bind('<Control-W>', lambda e: self._toggle_wrap())      # Toggle word wrap (Shift)
        self.bind('<Control-p>', lambda e: self._toggle_pause())     # Toggle pause
        self.bind('<Control-P>', lambda e: self._toggle_pause())     # Toggle pause (Shift)
        
        # Filter-specific shortcuts
        self.bind('<Escape>', lambda e: self._clear_filter())        # Clear filter
        self.bind('<Control-r>', lambda e: self._focus_filter())     # Focus filter (alternative)
        self.bind('<Control-R>', lambda e: self._focus_filter())     # Focus filter (alternative, Shift)

        # Create main toolbar with controls
        toolbar = ttk.Frame(self, padding=(8, 4))
        toolbar.pack(fill=tk.X)

        # File path display
        self.path_label = ttk.Label(toolbar, text="No file selected", width=80)
        self.path_label.pack(side=tk.LEFT, padx=(0, 8))

        # Refresh rate control
        ttk.Label(toolbar, text="Refresh (ms)").pack(side=tk.LEFT)
        refresh_entry = ttk.Spinbox(toolbar, from_=100, to=5000, textvariable=self.refresh_ms, width=6)
        refresh_entry.pack(side=tk.LEFT, padx=(4, 10))

        # Display options
        ttk.Checkbutton(toolbar, text="Auto-scroll", variable=self.autoscroll).pack(side=tk.LEFT)
        ttk.Checkbutton(toolbar, text="Wrap", variable=self.wrap, command=self._apply_wrap).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Checkbutton(toolbar, text="Line Numbers", variable=self.show_line_numbers, command=self._toggle_line_numbers).pack(side=tk.LEFT, padx=(8, 8))
        
        # Performance settings
        ttk.Label(toolbar, text="Max lines").pack(side=tk.LEFT)
        ttk.Spinbox(toolbar, from_=1000, to=200000, increment=1000, textvariable=self.max_lines, width=7).pack(side=tk.LEFT, padx=(4, 8))

        # Control buttons
        self.pause_btn = ttk.Button(toolbar, text="Pause", command=self._toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=(8, 4))
        ttk.Button(toolbar, text="Clear", command=self._clear).pack(side=tk.LEFT)

        # Enhanced Filter controls section
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.LEFT, padx=(12, 4))
        
        # Filter mode dropdown
        ttk.Label(filter_frame, text="Mode:").pack(side=tk.LEFT)
        self.filter_mode_combo = ttk.Combobox(filter_frame, textvariable=self.filter_mode, 
                                             values=self.filter_manager.get_mode_display_names(),
                                             width=12, state="readonly")
        self.filter_mode_combo.pack(side=tk.LEFT, padx=(4, 0))
        
        # Filter entry with history dropdown
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(8, 4))
        
        # Filter entry frame for dropdown integration
        filter_entry_frame = ttk.Frame(filter_frame)
        filter_entry_frame.pack(side=tk.LEFT)
        
        self.filter_entry = ttk.Entry(filter_entry_frame, textvariable=self.filter_text, width=30)
        self.filter_entry.pack(side=tk.LEFT)
        
        # Filter history dropdown button
        self.filter_history_btn = ttk.Button(filter_entry_frame, text="▼", width=2,
                                           command=self._show_filter_history)
        self.filter_history_btn.pack(side=tk.LEFT)
        
        # Filter control buttons
        filter_controls_frame = ttk.Frame(filter_frame)
        filter_controls_frame.pack(side=tk.LEFT, padx=(4, 0))
        
        # Case sensitivity checkbox
        self.case_sensitive_cb = ttk.Checkbutton(filter_controls_frame, text="Case", 
                                                variable=self.case_sensitive, 
                                                command=self._on_filter_change)
        self.case_sensitive_cb.pack(side=tk.LEFT)
        
        # Clear filter button
        self.clear_filter_btn = ttk.Button(filter_controls_frame, text="✕", width=3,
                                         command=self._clear_filter)
        self.clear_filter_btn.pack(side=tk.LEFT, padx=(4, 0))
        
        # Filter info button
        self.filter_info_btn = ttk.Button(filter_controls_frame, text="ℹ", width=3,
                                        command=self._show_filter_info)
        self.filter_info_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Filter status indicator
        self.filter_status_label = ttk.Label(filter_controls_frame, text="", width=8)
        self.filter_status_label.pack(side=tk.LEFT, padx=(4, 0))
        
        # Theme indicator and controls (right side of toolbar)
        theme_frame = ttk.Frame(toolbar)
        theme_frame.pack(side=tk.RIGHT, padx=(8, 0))
        
        self.theme_label = ttk.Label(theme_frame, text="", width=15)
        self.theme_label.pack(side=tk.LEFT)
        
        # Theme preview button
        self.theme_preview_btn = ttk.Button(theme_frame, text="🎨", width=3, command=self._show_theme_preview)
        self.theme_preview_btn.pack(side=tk.LEFT, padx=(4, 0))
        
        # Bind filter events for real-time updates
        self.filter_text.trace_add('write', lambda *args: self._on_filter_change())
        self.filter_mode_combo.bind('<<ComboboxSelected>>', self._on_filter_mode_change)
        self.case_sensitive.trace_add('write', lambda *args: self._on_filter_change())
        
        # Set initial filter mode
        self.filter_mode_combo.set(self.filter_manager.get_mode_display_names()[0])

        # Create main text area with line numbers support
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Create a frame for text and line numbers
        text_content_frame = ttk.Frame(text_frame)
        text_content_frame.pack(fill=tk.BOTH, expand=True)

        # Line numbers widget (left side)
        self.line_numbers = tk.Text(
            text_content_frame,
            width=8,                    # Fixed width for line numbers
            padx=3,                     # Horizontal padding
            pady=2,                     # Vertical padding
            relief=tk.FLAT,             # No border
            borderwidth=0,              # No border width
            state=tk.DISABLED,          # Read-only
            font=("Consolas", 11)       # Monospace font for alignment
        )
        
        # Main text widget for log content
        self.text = tk.Text(
            text_content_frame,
            wrap=tk.WORD if self.wrap.get() else tk.NONE,  # Word wrap based on setting
            undo=False,                  # Disable undo for performance
            font=("Consolas", 11)       # Monospace font for log readability
        )

        # Scrollbars for navigation
        yscroll = ttk.Scrollbar(text_content_frame, orient=tk.VERTICAL, command=self.text.yview)
        xscroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # Pack widgets - only show line numbers if configured to do so
        if self.show_line_numbers.get():
            self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar spans the full width of the application
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Store references for layout management
        self.text_content_frame = text_content_frame
        self.yscroll = yscroll
        self.xscroll = xscroll
        
        # Bind events for line numbers synchronization
        self.text.bind('<KeyRelease>', self._update_line_numbers)
        self.text.bind('<ButtonRelease-1>', self._update_line_numbers)
        self.text.bind('<MouseWheel>', self._on_mouse_wheel)  # Windows mouse wheel
        self.text.bind('<Button-4>', self._on_mouse_wheel)    # Linux scroll up
        self.text.bind('<Button-5>', self._on_mouse_wheel)    # Linux scroll down
        self.show_line_numbers.trace_add('write', lambda *args: self._toggle_line_numbers())
        
        # Bind scrollbar to update line numbers
        yscroll.config(command=lambda *args: self._on_yscroll(*args))

        # Status bar for information display
        self.status = ttk.Label(self, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X)

    # Enhanced Filtering
    def _on_filter_change(self):
        """
        Handle filter text or case sensitivity changes.
        
        Updates the filter manager with new settings and triggers a
        debounced view rebuild to avoid excessive updates during typing.
        """
        # Update filter manager with current UI state
        mode_index = self.filter_mode_combo.current()
        mode_name = self.filter_manager.get_mode_names()[mode_index]
        
        if self.filter_manager.set_filter(
            self.filter_text.get(), 
            mode_name, 
            self.case_sensitive.get()
        ):
            # Update filter status indicator
            self._update_filter_status()
            
            # Debounce rapid typing; rebuild shortly after user stops
            if self._filter_job is not None:
                try:
                    self.after_cancel(self._filter_job)
                except Exception:
                    pass
            self._filter_job = self.after(150, self._rebuild_view)
    
    def _update_filter_status(self):
        """
        Update the filter status indicator.
        
        Shows visual feedback about filter state including errors
        and active status.
        """
        info = self.filter_manager.get_filter_info()
        
        if info["is_active"]:
            if info["has_error"]:
                self.filter_status_label.config(text="❌ Error", foreground="red")
            else:
                self.filter_status_label.config(text="✅ Active", foreground="green")
        else:
            self.filter_status_label.config(text="", foreground="black")
    
    def _on_filter_mode_change(self, event=None):
        """
        Handle filter mode changes.
        
        Triggered when user selects a different filter mode from
        the dropdown menu.
        
        Args:
            event: Tkinter event (unused)
        """
        self._on_filter_change()
    
    def _clear_filter(self):
        """
        Clear the current filter.
        
        Resets filter text, clears filtered lines cache, and
        rebuilds the view to show all content.
        """
        self.filter_text.set("")
        self.filter_manager.clear_filter()
        self._filtered_lines = []  # Clear filtered lines when filter is cleared
        self._rebuild_view()
        self._set_status("Filter cleared")
    
    def _show_settings(self):
        """
        Show the settings/preferences dialog.
        
        Creates a comprehensive settings dialog with multiple tabs for
        organizing different categories of preferences.
        """
        settings_window = tk.Toplevel(self)
        settings_window.title("Log Viewer Settings")
        settings_window.geometry("600x700")
        settings_window.resizable(True, True)
        settings_window.transient(self)
        settings_window.grab_set()
        
        # Center the window relative to main application
        settings_window.geometry("+%d+%d" % (self.winfo_rootx() + 100, self.winfo_rooty() + 100))
        
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General settings tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        self._create_general_settings_tab(general_frame)
        
        # Display settings tab
        display_frame = ttk.Frame(notebook)
        notebook.add(display_frame, text="Display")
        self._create_display_settings_tab(display_frame)
        
        # Filter settings tab
        filter_frame = ttk.Frame(notebook)
        notebook.add(filter_frame, text="Filtering")
        self._create_filter_settings_tab(filter_frame)
        
        # Theme settings tab
        theme_frame = ttk.Frame(notebook)
        notebook.add(theme_frame, text="Theme")
        self._create_theme_settings_tab(theme_frame)
        
        # Action buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=lambda: self._save_settings_and_close(settings_window)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Apply", command=self._apply_settings).pack(side=tk.RIGHT, padx=5)
    
    def _create_general_settings_tab(self, parent):
        """
        Create the general settings tab.
        
        Contains window settings and file handling preferences.
        
        Args:
            parent: Parent frame for the tab
        """
        # Window settings section
        window_frame = ttk.LabelFrame(parent, text="Window", padding=10)
        window_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Window size controls
        ttk.Label(window_frame, text="Default Window Size:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        size_frame = ttk.Frame(window_frame)
        size_frame.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        self.settings_width = tk.StringVar(value=str(self.config_manager.get('window.width', 1000)))
        self.settings_height = tk.StringVar(value=str(self.config_manager.get('window.height', 1000)))
        
        ttk.Label(size_frame, text="Width:").pack(side=tk.LEFT)
        ttk.Entry(size_frame, textvariable=self.settings_width, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_frame, text="Height:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(size_frame, textvariable=self.settings_height, width=8).pack(side=tk.LEFT, padx=5)
        
        # Remember window position option
        self.settings_remember_pos = tk.BooleanVar(value=self.config_manager.get('window.x') is not None)
        ttk.Checkbutton(window_frame, text="Remember window position", variable=self.settings_remember_pos).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # File handling settings section
        file_frame = ttk.LabelFrame(parent, text="File Handling", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.settings_remember_dir = tk.BooleanVar(value=self.config_manager.get('file.remember_encoding', True))
        ttk.Checkbutton(file_frame, text="Remember last directory", variable=self.settings_remember_dir).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.settings_auto_encoding = tk.BooleanVar(value=self.config_manager.get('file.auto_detect_encoding', True))
        ttk.Checkbutton(file_frame, text="Auto-detect file encoding", variable=self.settings_auto_encoding).grid(row=1, column=0, sticky=tk.W, pady=2)
    
    def _create_display_settings_tab(self, parent):
        """
        Create the display settings tab.
        
        Contains refresh settings, display options, and font preferences.
        
        Args:
            parent: Parent frame for the tab
        """
        # Refresh and performance settings section
        refresh_frame = ttk.LabelFrame(parent, text="Refresh & Performance", padding=10)
        refresh_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(refresh_frame, text="Default Refresh Rate (ms):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_refresh_rate = tk.StringVar(value=str(self.config_manager.get('display.refresh_rate', 500)))
        ttk.Entry(refresh_frame, textvariable=self.settings_refresh_rate, width=10).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(refresh_frame, text="Default Max Lines:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.settings_max_lines = tk.StringVar(value=str(self.config_manager.get('display.max_lines', 10000)))
        ttk.Entry(refresh_frame, textvariable=self.settings_max_lines, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Display options section
        display_frame = ttk.LabelFrame(parent, text="Display Options", padding=10)
        display_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.settings_auto_scroll = tk.BooleanVar(value=self.config_manager.get('display.auto_scroll', True))
        ttk.Checkbutton(display_frame, text="Auto-scroll by default", variable=self.settings_auto_scroll).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.settings_word_wrap = tk.BooleanVar(value=self.config_manager.get('display.word_wrap', False))
        ttk.Checkbutton(display_frame, text="Word wrap by default", variable=self.settings_word_wrap).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Font settings section
        font_frame = ttk.LabelFrame(parent, text="Font", padding=10)
        font_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(font_frame, text="Font Size:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_font_size = tk.StringVar(value=str(self.config_manager.get('display.font_size', 11)))
        ttk.Entry(font_frame, textvariable=self.settings_font_size, width=8).grid(row=0, column=1, sticky=tk.W, pady=2)
    
    def _create_filter_settings_tab(self, parent):
        """
        Create the filter settings tab.
        
        Contains filter preferences and history settings.
        
        Args:
            parent: Parent frame for the tab
        """
        filter_frame = ttk.LabelFrame(parent, text="Filter Preferences", padding=10)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Default filter mode selection
        ttk.Label(filter_frame, text="Default Filter Mode:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_filter_mode = tk.StringVar(value=self.config_manager.get('filter.default_mode', 'contains'))
        filter_mode_combo = ttk.Combobox(filter_frame, textvariable=self.settings_filter_mode, 
                                        values=self.filter_manager.get_mode_display_names(), state="readonly")
        filter_mode_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Filter behavior options
        self.settings_case_sensitive = tk.BooleanVar(value=self.config_manager.get('filter.case_sensitive', False))
        ttk.Checkbutton(filter_frame, text="Case sensitive by default", variable=self.settings_case_sensitive).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.settings_remember_history = tk.BooleanVar(value=self.config_manager.get('filter.remember_history', True))
        ttk.Checkbutton(filter_frame, text="Remember filter history", variable=self.settings_remember_history).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Label(filter_frame, text="Max History Items:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.settings_max_history = tk.StringVar(value=str(self.config_manager.get('filter.max_history', 20)))
        ttk.Entry(filter_frame, textvariable=self.settings_max_history, width=8).grid(row=3, column=1, sticky=tk.W, pady=2)
    
    def _create_theme_settings_tab(self, parent):
        """
        Create the theme settings tab.
        
        Contains theme preferences and auto-switching options.
        
        Args:
            parent: Parent frame for the tab
        """
        theme_frame = ttk.LabelFrame(parent, text="Theme Preferences", padding=10)
        theme_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Default theme selection
        ttk.Label(theme_frame, text="Default Theme:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_default_theme = tk.StringVar(value=self.config_manager.get('theme.current', 'dark'))
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.settings_default_theme, 
                                  values=self.theme_manager.get_theme_names(), state="readonly")
        theme_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Auto-switch theme options
        self.settings_auto_switch_theme = tk.BooleanVar(value=self.config_manager.get('theme.auto_switch', False))
        ttk.Checkbutton(theme_frame, text="Auto-switch theme based on time", variable=self.settings_auto_switch_theme).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Label(theme_frame, text="Switch Time (HH:MM):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.settings_switch_time = tk.StringVar(value=self.config_manager.get('theme.auto_switch_time', '18:00'))
        ttk.Entry(theme_frame, textvariable=self.settings_switch_time, width=10).grid(row=2, column=1, sticky=tk.W, pady=2)
    
    def _apply_settings(self):
        """
        Apply current settings without closing the dialog.
        
        Saves all current settings values to the configuration system
        and applies some settings immediately to the running application.
        """
        try:
            # Save window settings
            self.config_manager.set('window.width', int(self.settings_width.get()))
            self.config_manager.set('window.height', int(self.settings_height.get()))
            
            if self.settings_remember_pos.get():
                # Keep current position
                pass
            else:
                # Clear saved position
                self.config_manager.set('window.x', None)
                self.config_manager.set('window.y', None)
            
            # Save file settings
            self.config_manager.set('file.remember_encoding', self.settings_remember_dir.get())
            self.config_manager.set('file.auto_detect_encoding', self.settings_auto_encoding.get())
            
            # Save display settings
            self.config_manager.set('display.refresh_rate', int(self.settings_refresh_rate.get()))
            self.config_manager.set('display.max_lines', int(self.settings_max_lines.get()))
            self.config_manager.set('display.auto_scroll', self.settings_auto_scroll.get())
            self.config_manager.set('display.word_wrap', self.settings_word_wrap.get())
            self.config_manager.set('display.font_size', int(self.settings_font_size.get()))
            
            # Save filter settings
            mode_index = self.filter_manager.get_mode_names().index(self.settings_filter_mode.get())
            self.config_manager.set('filter.default_mode', self.filter_manager.get_mode_names()[mode_index])
            self.config_manager.set('filter.case_sensitive', self.settings_case_sensitive.get())
            self.config_manager.set('filter.remember_history', self.settings_remember_history.get())
            self.config_manager.set('filter.max_history', int(self.settings_max_history.get()))
            
            # Save theme settings
            self.config_manager.set('theme.current', self.settings_default_theme.get())
            self.config_manager.set('theme.auto_switch', self.settings_auto_switch_theme.get())
            self.config_manager.set('theme.auto_switch_time', self.settings_switch_time.get())
            
            # Save to file
            self.config_manager.save_config()
            
            # Apply some settings immediately
            self._apply_current_settings()
            
            self._set_status("Settings applied successfully")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings: {e}")
    
    def _save_settings_and_close(self, window):
        """
        Save settings and close the dialog.
        
        Args:
            window: Settings window to close
        """
        self._apply_settings()
        window.destroy()
    
    def _apply_current_settings(self):
        """
        Apply current configuration to the running application.
        
        Updates font settings and other runtime-configurable options
        without requiring a restart.
        """
        # Update font size if changed
        font_size = self.config_manager.get('display.font_size', 11)
        font_family = self.config_manager.get('display.font_family')
        if font_family:
            self.text.configure(font=(font_family, font_size))
        else:
            # Use platform default font
            font_family = "Consolas" if sys.platform.startswith("win") else "Menlo"
            self.text.configure(font=(font_family, font_size))
    
    def _save_as_default(self):
        """
        Save current application state as default settings.
        
        Captures the current state of all configurable options and
        saves them as the new default values for future sessions.
        """
        try:
            # Save current window state
            self.config_manager.save_window_state(self)
            
            # Save current display settings
            self.config_manager.set('display.refresh_rate', self.refresh_ms.get())
            self.config_manager.set('display.max_lines', self.max_lines.get())
            self.config_manager.set('display.auto_scroll', self.autoscroll.get())
            self.config_manager.set('display.word_wrap', self.wrap.get())
            self.config_manager.set('display.show_line_numbers', self.show_line_numbers.get())
            
            # Save current filter settings
            mode_index = self.filter_mode_combo.current()
            if mode_index >= 0:
                mode_name = self.filter_manager.get_mode_names()[mode_index]
                self.config_manager.set('filter.default_mode', mode_name)
            self.config_manager.set('filter.case_sensitive', self.case_sensitive.get())
            
            # Save current theme
            self.config_manager.set('theme.current', self.theme_manager.current_theme)
            
            # Save current file path if one is open
            if hasattr(self, 'path') and self.path:
                self.config_manager.set('file.last_file_path', self.path)
                # Also save the directory for the file dialog
                last_dir = os.path.dirname(self.path)
                if last_dir:
                    self.config_manager.set('file.last_directory', last_dir)
            
            # Save configuration
            self.config_manager.save_config()
            
            self._set_status("Current settings saved as default")
            messagebox.showinfo("Success", "Current settings have been saved as your new defaults!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def _reset_settings(self):
        """
        Reset all settings to default values.
        
        Prompts user for confirmation before resetting all configuration
        to factory defaults. Cannot be undone.
        """
        if messagebox.askyesno("Reset Settings", 
                              "Are you sure you want to reset all settings to default values?\n\nThis cannot be undone."):
            self.config_manager.reset_to_defaults()
            self._set_status("Settings reset to defaults")
            messagebox.showinfo("Reset Complete", "All settings have been reset to default values.\n\nRestart the application to apply the changes.")
    
    def _export_settings(self):
        """
        Export current settings to a file.
        
        Allows users to backup their configuration or share it
        with other installations.
        """
        filepath = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            try:
                self.config_manager.export_config(filepath)
                self._set_status(f"Settings exported to {os.path.basename(filepath)}")
                messagebox.showinfo("Export Success", f"Settings exported successfully to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export settings: {e}")
    
    def _import_settings(self):
        """
        Import settings from a file.
        
        Allows users to restore settings from a backup or
        import settings from another installation.
        """
        filepath = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            try:
                self.config_manager.import_config(filepath)
                self._set_status(f"Settings imported from {os.path.basename(filepath)}")
                messagebox.showinfo("Import Success", f"Settings imported successfully from:\n{filepath}\n\nRestart the application to apply the changes.")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import settings: {e}")
    
    def _on_closing(self):
        """
        Handle application closing - save configuration.
        
        Called when the user closes the application window.
        Saves all current settings and window state before exit.
        """
        try:
            # Save current window state
            self.config_manager.save_window_state(self)
            
            # Save current settings
            self.config_manager.set('display.refresh_rate', self.refresh_ms.get())
            self.config_manager.set('display.max_lines', self.max_lines.get())
            self.config_manager.set('display.auto_scroll', self.autoscroll.get())
            self.config_manager.set('display.word_wrap', self.wrap.get())
            self.config_manager.set('display.show_line_numbers', self.show_line_numbers.get())
            
            # Save current filter settings
            mode_index = self.filter_mode_combo.current()
            if mode_index >= 0:
                mode_name = self.filter_manager.get_mode_names()[mode_index]
                self.config_manager.set('filter.default_mode', mode_name)
            self.config_manager.set('filter.case_sensitive', self.case_sensitive.get())
            
            # Save current theme
            self.config_manager.set('theme.current', self.theme_manager.current_theme)
            
            # Save current file path if one is open
            if hasattr(self, 'path') and self.path:
                self.config_manager.set('file.last_file_path', self.path)
                # Also save the directory for the file dialog
                last_dir = os.path.dirname(self.path)
                if last_dir:
                    self.config_manager.set('file.last_directory', last_dir)
            
            # Save configuration
            self.config_manager.save_config()
            
        except Exception as e:
            print(f"Warning: Could not save configuration: {e}")
        
        # Destroy the window
        self.destroy()
    
    def _show_filter_info(self):
        """Show detailed information about the current filter."""
        info = self.filter_manager.get_filter_info()
        
        if info["is_active"]:
            status_text = f"Active Filter: {info['mode_display']}"
            if info["has_error"]:
                status_text += f" (Error: {info['error']})"
            self._set_status(status_text)
        else:
            self._set_status("No active filter")
    
    def _show_filter_history(self):
        """Show filter history in a popup menu."""
        if not self.filter_manager.filter_history:
            self._set_status("No filter history")
            return
        
        # Create popup menu
        history_menu = tk.Menu(self, tearoff=0)
        
        for i, filter_text in enumerate(self.filter_manager.filter_history):
            # Truncate long filter text for display
            display_text = filter_text[:50] + "..." if len(filter_text) > 50 else filter_text
            history_menu.add_command(
                label=f"{i+1}. {display_text}",
                command=lambda text=filter_text: self._use_filter_from_history(text)
            )
        
        # Show menu below the history button
        x = self.filter_history_btn.winfo_rootx()
        y = self.filter_history_btn.winfo_rooty() + self.filter_history_btn.winfo_height()
        history_menu.post(x, y)
    
    def _use_filter_from_history(self, filter_text: str):
        """Use a filter from history."""
        self.filter_text.set(filter_text)
        self._on_filter_change()
        self._set_status(f"Using filter from history: {filter_text[:30]}...")
    
    def _rebuild_view(self):
        """
        Re-render the text widget from the buffered lines using the current filter.
        
        This method efficiently rebuilds the display by applying the current
        filter to all stored lines, maintaining original line numbers for
        accurate reference.
        """
        try:
            # Clear current display
            self.text.delete('1.0', tk.END)
            at_end = True
            matched_count = 0
            total_count = len(self._line_buffer)
            
            # Store filtered lines with their original line numbers
            self._filtered_lines = []
            
            # Apply filter to all stored lines
            for i, line in enumerate(self._line_buffer, 1):
                if self.filter_manager.matches(line):
                    self.text.insert(tk.END, line)
                    self._filtered_lines.append((i, line))  # Store (original_line_number, line_content)
                    matched_count += 1
            
            # Auto-scroll if configured and we were at the end
            if self.autoscroll.get() and at_end:
                self.text.see(tk.END)
            
            # Update status with filter information
            if self.filter_manager.current_filter:
                if self.filter_manager.last_error:
                    self._set_status(f"Filter error: {self.filter_manager.last_error}")
                else:
                    self._set_status(f"Filtered: {matched_count}/{total_count} lines")
            else:
                self._set_status(f"Showing all {total_count} lines")
            
            # Update line numbers after rebuilding view
            self._update_line_numbers()
                
        except Exception as e:
            self._set_status("Filter error: {}".format(e))

    def _buffer_trim(self):
        # Ensure buffer keeps approximately the last N lines (N = max_lines)
        try:
            target = max(1000, int(self.max_lines.get() or MAX_LINES_DEFAULT))
        except Exception:
            target = MAX_LINES_DEFAULT
        # collections.deque with maxlen handles trimming automatically if maxlen is set.
        # Update maxlen dynamically to follow user control.
        if self._line_buffer.maxlen != target:
            tmp = collections.deque(self._line_buffer, maxlen=target)
            self._line_buffer = tmp

    # Actions
    def _choose_file(self):
        """
        Open file dialog to choose a log file.
        
        Shows a file selection dialog and opens the selected file
        if the user makes a selection.
        """
        path = filedialog.askopenfilename(title="Choose log file")
        if path:
            self._open_path(path, first_open=True)

    def _open_path(self, path: str, first_open=False):
        """
        Open a log file for monitoring.
        
        Initializes the tail reader and loads initial content if the file
        is small enough. Handles file opening errors gracefully.
        
        Args:
            path: Path to the log file to open
            first_open: Whether this is the first file opened in this session
        """
        self.path = path
        self.path_label.config(text=path)
        try:
            if not self.tail:
                self.tail = TailReader(path)
            self.tail.path = path

            # If small file (<2MB), show existing contents; else start tailing from end
            start_at_end = False
            try:
                if os.path.getsize(path) > 2 * 1024 * 1024:
                    start_at_end = True
            except OSError:
                pass
            self.tail.open(start_at_end=start_at_end)
            if not start_at_end:
                # Load initial chunk for small files
                text = self.tail.read_new_text()
                if text:
                    self._append(text)
            self._set_status("Opened")
        except Exception as e:
            messagebox.showerror("Error", "Failed to open file:\n{}".format(e))
            self._set_status("Open failed")

    def _toggle_pause(self):
        """
        Toggle pause/resume state of log monitoring.
        
        Updates button text and status to reflect current state.
        """
        self.paused.set(not self.paused.get())
        self.pause_btn.config(text="Resume" if self.paused.get() else "Pause")
        self._set_status("Paused" if self.paused.get() else "Running")

    def _clear(self):
        """
        Clear the text display.
        
        Removes all content from the text widget and updates line numbers.
        """
        self.text.delete('1.0', tk.END)
        self._update_line_numbers()

    def _toggle_wrap(self):
        """
        Toggle word wrap setting.
        
        Switches between word wrap and no wrap modes and applies
        the change immediately to the text widget.
        """
        self.wrap.set(not self.wrap.get())
        self._apply_wrap()
    
    def _apply_wrap(self):
        """
        Apply word wrap setting to text widget.
        
        Configures the text widget to use word wrap or no wrap
        based on the current setting.
        """
        self.text.config(wrap=tk.WORD if self.wrap.get() else tk.NONE)
    
    def _change_theme(self, theme_name: str):
        """
        Change the application theme.
        
        Updates the theme manager and applies the new theme to all
        UI elements. Updates menu checkmarks to reflect the change.
        
        Args:
            theme_name: Name of the theme to apply
        """
        if self.theme_manager.set_theme(theme_name):
            self._apply_theme()
            # Update theme menu checkmarks
            for name, var in self.theme_vars.items():
                var.set(name == theme_name)
            # Show theme change confirmation in status
            self._set_status(f"Theme changed to {self.theme_manager.get_theme(theme_name)['name']}")
    
    def _apply_theme(self):
        """
        Apply the current theme to all UI elements.
        
        Updates colors and styling for all interface components
        including text widgets, toolbar, status bar, and menus.
        """
        theme = self.theme_manager.get_current_theme()
        
        # Configure main window
        self.configure(bg=theme["bg"])
        
        # Configure text widget
        self.text.configure(
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            insertbackground=theme["insert_bg"],
            selectbackground=theme["menu_select_bg"],
            selectforeground=theme["text_fg"]
        )
        
        # Configure line numbers widget
        if hasattr(self, 'line_numbers'):
            self.line_numbers.configure(
                bg=theme["text_bg"],
                fg=theme["text_fg"],
                insertbackground=theme["insert_bg"],
                selectbackground=theme["menu_select_bg"],
                selectforeground=theme["text_fg"]
            )
        
        # Configure toolbar (if using ttk, this may have limited effect)
        try:
            style = ttk.Style()
            style.configure("Toolbar.TFrame", background=theme["toolbar_bg"])
            style.configure("Toolbar.TLabel", background=theme["toolbar_bg"], foreground=theme["toolbar_fg"])
            style.configure("Toolbar.TButton", background=theme["button_bg"], foreground=theme["button_fg"])
            style.configure("Toolbar.TEntry", fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])
            style.configure("Toolbar.TCheckbutton", background=theme["toolbar_bg"], foreground=theme["toolbar_fg"])
            style.configure("Toolbar.TSpinbox", fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])
        except Exception:
            pass  # ttk styling may not work on all platforms
        
        # Configure status bar
        self.status.configure(
            background=theme["status_bg"],
            foreground=theme["status_fg"]
        )
        
        # Configure menu colors (limited support on some platforms)
        try:
            self.option_add('*Menu.background', theme["menu_bg"])
            self.option_add('*Menu.foreground', theme["menu_fg"])
            self.option_add('*Menu.selectBackground', theme["menu_select_bg"])
        except Exception:
            pass
        
        # Update theme indicator
        if hasattr(self, 'theme_label'):
            self.theme_label.configure(text=f"🎨 {theme['name']}")
        
        # Update application icon to match theme
        self._set_app_icon()
        
        # Save theme preference
        self._save_theme_preference()
        
        # Save filter preferences
        self._save_filter_preferences()
    
    def _save_filter_preferences(self):
        """
        Save current filter preferences to config file.
        
        Stores filter mode, case sensitivity, and other filter-related
        settings for restoration on next launch.
        """
        try:
            config_dir = os.path.expanduser("~/.logviewer")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "filter_prefs.txt")
            
            with open(config_file, 'w') as f:
                f.write(f"mode:{self.filter_mode.get()}\n")
                f.write(f"case_sensitive:{self.case_sensitive.get()}\n")
                f.write(f"filter_text:{self.filter_text.get()}\n")
        except Exception:
            pass  # Silently fail if we can't save preferences
    
    def _load_filter_preferences(self):
        """
        Load saved filter preferences.
        
        Restores previously saved filter settings including mode,
        case sensitivity, and filter text.
        
        Returns:
            Default values if no preferences are saved
        """
        try:
            config_file = os.path.join(os.path.expanduser("~/.logviewer"), "filter_prefs.txt")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.strip().split(':', 1)
                            if key == 'mode' and value in self.filter_manager.get_mode_names():
                                self.filter_mode.set(value)
                            elif key == 'case_sensitive':
                                self.case_sensitive.set(value.lower() == 'true')
                            elif key == 'filter_text':
                                self.filter_text.set(value)
        except Exception:
            pass
    
    def _save_theme_preference(self):
        """
        Save current theme preference to the configuration system.
        
        Stores the user's theme choice for restoration on next launch.
        """
        try:
            self.config_manager.set('theme.current', self.theme_manager.current_theme)
            self.config_manager.save_config()
        except Exception:
            pass  # Silently fail if we can't save preferences
    
    def _load_theme_preference(self) -> str:
        """
        Load saved theme preference from the configuration system.
        
        Returns:
            Saved theme name or default theme if none saved
        """
        try:
            saved_theme = self.config_manager.get('theme.current', DEFAULT_THEME)
            if saved_theme in self.theme_manager.get_theme_names():
                return saved_theme
        except Exception:
            pass
        return DEFAULT_THEME
    
    def _cycle_theme(self):
        """
        Cycle through available themes with keyboard shortcut.
        
        Allows users to quickly switch between themes using
        Ctrl+T keyboard shortcut.
        """
        themes = self.theme_manager.get_theme_names()
        current_index = themes.index(self.theme_manager.current_theme)
        next_index = (current_index + 1) % len(themes)
        next_theme = themes[next_index]
        self._change_theme(next_theme)
    
    def _show_theme_info(self):
        """
        Show information about available themes.
        
        Displays a dialog with list of available themes and
        keyboard shortcuts for theme switching.
        """
        info = "Available Themes:\n\n"
        for theme_name in self.theme_manager.get_theme_names():
            theme = self.theme_manager.get_theme(theme_name)
            current = " (Current)" if theme_name == self.theme_manager.current_theme else ""
            info += f"• {theme['name']}{current}\n"
        info += "\nUse Ctrl+T to cycle through themes\n"
        info += "Or use View → Theme menu"
        
        messagebox.showinfo("Theme Information", info)
    
    def _show_keyboard_shortcuts(self):
        """
        Show available keyboard shortcuts.
        
        Displays a dialog listing all available keyboard shortcuts
        for quick reference.
        """
        shortcuts = "Keyboard Shortcuts:\n\n"
        shortcuts += "Ctrl+O    - Open file\n"
        shortcuts += "Ctrl+T    - Cycle themes\n"
        shortcuts += "Ctrl+F    - Focus filter box\n"
        shortcuts += "Ctrl+R    - Focus filter box\n"
        shortcuts += "Ctrl+W    - Toggle word wrap\n"
        shortcuts += "Ctrl+P    - Toggle pause/resume\n"
        shortcuts += "Escape     - Clear filter\n"
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def _show_filter_help(self):
        """
        Show help information for the filtering system.
        
        Displays comprehensive help for all filter modes including
        regex examples and usage tips.
        """
        help_text = """Advanced Filtering System

Filter Modes:
• Contains: Text appears anywhere in the line
• Starts With: Line begins with the text
• Ends With: Line ends with the text
• Regular Expression: Use regex patterns
• Exact Match: Line exactly matches the text
• Not Contains: Line does NOT contain the text

Regular Expression Examples:
• ^ERROR - Lines starting with "ERROR"
• \\d{4}-\\d{2}-\\d{2} - Date pattern (YYYY-MM-DD)
• (ERROR|WARN) - Lines with ERROR or WARN
• .*exception.* - Lines containing "exception"

Keyboard Shortcuts:
• Ctrl+F - Focus filter box
• Ctrl+R - Focus filter box
• Escape - Clear filter
• Enter - Apply filter

Tips:
• Use regex mode for complex patterns
• Filter history remembers your searches
• Case sensitivity affects all modes
• Invalid regex shows error indicator"""
        
        messagebox.showinfo("Filter Help", help_text)
    
    def _show_theme_preview(self):
        """
        Show a preview of all available themes.
        
        Creates a preview window showing color samples for each
        theme with the ability to apply themes directly.
        """
        preview_window = tk.Toplevel(self)
        preview_window.title("Theme Preview")
        preview_window.geometry("400x360")
        preview_window.resizable(False, False)
        preview_window.transient(self)
        preview_window.grab_set()
        
        # Center the window relative to main application
        preview_window.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))
        
        # Create preview for each theme
        for i, theme_name in enumerate(self.theme_manager.get_theme_names()):
            theme = self.theme_manager.get_theme(theme_name)
            current = " (Current)" if theme_name == self.theme_manager.current_theme else ""
            
            # Theme frame
            theme_frame = ttk.Frame(preview_window)
            theme_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Theme name and current indicator
            name_label = ttk.Label(theme_frame, text=f"{theme['name']}{current}")
            name_label.pack(anchor=tk.W)
            
            # Color preview section
            preview_frame = tk.Frame(theme_frame, height=40)
            preview_frame.pack(fill=tk.X, pady=2)
            preview_frame.pack_propagate(False)
            
            # Background color sample
            bg_label = tk.Label(preview_frame, text="  Background  ", 
                               bg=theme["bg"], fg=theme["fg"], relief=tk.RAISED)
            bg_label.pack(side=tk.LEFT, padx=2)
            
            # Text color sample
            text_label = tk.Label(preview_frame, text="  Text  ", 
                                 bg=theme["text_bg"], fg=theme["text_fg"], relief=tk.RAISED)
            text_label.pack(side=tk.LEFT, padx=2)
            
            # Button color sample
            btn_label = tk.Label(preview_frame, text="  Button  ", 
                                bg=theme["button_bg"], fg=theme["button_fg"], relief=tk.RAISED)
            btn_label.pack(side=tk.LEFT, padx=2)
            
            # Apply button for this theme
            apply_btn = ttk.Button(theme_frame, text="Apply", 
                                  command=lambda t=theme_name: self._apply_theme_from_preview(t, preview_window))
            apply_btn.pack(anchor=tk.E, pady=2)
        
        # Close button
        close_btn = ttk.Button(preview_window, text="Close", command=preview_window.destroy)
        close_btn.pack(pady=10)
    
    def _apply_theme_from_preview(self, theme_name: str, preview_window):
        """
        Apply theme from preview window and close it.
        
        Args:
            theme_name: Name of theme to apply
            preview_window: Preview window to close
        """
        self._change_theme(theme_name)
        preview_window.destroy()
    
    def _focus_filter(self):
        """
        Focus the filter entry box.
        
        Moves keyboard focus to the filter entry field and selects
        all text for easy replacement.
        """
        self.filter_entry.focus_set()
        self.filter_entry.select_range(0, tk.END)

    def _set_status(self, msg: str):
        """
        Update the status bar with a message.
        
        Displays the current time, status message, and file size
        information in the status bar at the bottom of the window.
        
        Args:
            msg: Status message to display
        """
        now = time.strftime("%H:%M:%S")
        base = "[{}] {}".format(now, msg)
        if self.path:
            try:
                size = os.path.getsize(self.path)
                base += "  •  size: {:,} bytes".format(size)
            except OSError:
                pass
        self.status.config(text=base)

    def _trim_if_needed(self):
        """
        Trim text widget content if it exceeds maximum lines.
        
        Removes older lines from the beginning of the text widget
        to maintain performance and memory usage within limits.
        """
        # Keep last N lines for memory safety
        try:
            max_lines = max(1000, int(self.max_lines.get() or MAX_LINES_DEFAULT))
        except Exception:
            max_lines = MAX_LINES_DEFAULT
        total = int(self.text.index('end-1c').split('.')[0])
        if total > max_lines:
            cutoff = total - max_lines
            self.text.delete('1.0', "{}.0".format(cutoff))

    def _append(self, s: str):
        """
        Append new text to the display, applying current filter.
        
        Processes incoming text chunk by chunk, stores lines in buffer,
        and displays only lines that match the current filter.
        
        Args:
            s: New text content to append
        """
        # Break incoming chunk into lines, store, and append only matching ones
        lines = s.splitlines(True)  # keep line endings
        if not lines:
            return
        at_end = (self.text.yview()[1] == 1.0)
        self._line_buffer.extend(lines)
        # Dynamic buffer size based on Max lines control
        self._buffer_trim()
        
        # Apply current filter to new lines
        for line in lines:
            if self.filter_manager.matches(line):
                self.text.insert(tk.END, line)
        
        self._trim_if_needed()
        if self.autoscroll.get() and (at_end or self.paused.get() is False):
            self.text.see(tk.END)
        
        # Update line numbers after appending new text
        self._update_line_numbers()

    def _poll(self):
        """
        Main polling loop for file updates.
        
        Checks for new content in the monitored file at regular intervals.
        Handles errors gracefully and reschedules itself for continuous monitoring.
        """
        try:
            if not self.paused.get() and self.tail and self.path:
                new_text = self.tail.read_new_text()
                if new_text:
                    self._append(new_text)
                    self._set_status("Updated")
        except Exception as e:
            # Non-fatal: show in status bar, keep polling
            self._set_status("Error: {}".format(e))
        finally:
            # Reschedule polling
            try:
                interval = max(100, int(self.refresh_ms.get()))
            except Exception:
                interval = DEFAULT_REFRESH_MS
            self.after(interval, self._poll)

    def _center_window(self):
        """
        Center the window on the screen.
        
        Calculates the center position based on screen dimensions
        and current window size, then moves the window to that position.
        """
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = self.winfo_reqwidth()
        window_height = self.winfo_reqheight()
        
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _set_app_icon(self):
        """
        Set the application icon based on the current theme.
        
        Attempts to load a theme-specific icon file and falls back
        to a default icon if the theme-specific one doesn't exist.
        """
        try:
            current_theme = self.theme_manager.current_theme
            icon_path = os.path.join(os.path.dirname(__file__), "icons", f"{current_theme}.ico")
            
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
            else:
                # Fallback to a generic icon if theme-specific one doesn't exist
                fallback_path = os.path.join(os.path.dirname(__file__), "icons", "default.ico")
                if os.path.exists(fallback_path):
                    self.iconbitmap(fallback_path)
        except Exception:
            # Silently fail if icon setting fails
            pass

    def _on_scroll(self, *args):
        """
        Handle scrollbar events for the text widget.
        
        Processes scrollbar commands and synchronizes scroll position
        with line numbers display.
        
        Args:
            *args: Scrollbar command arguments
        """
        # Only call yview if args are valid scrollbar commands
        if args and args[0] in ['moveto', 'scroll']:
            self.text.yview(*args)
            self._sync_scroll()
    
    def _on_yscroll(self, *args):
        """
        Handle vertical scrollbar events and update line numbers.
        
        Processes vertical scrollbar movement and ensures line numbers
        stay synchronized with the main text content.
        
        Args:
            *args: Scrollbar command arguments
        """
        self.text.yview(*args)
        self._sync_scroll()

    def _update_line_numbers(self, event=None):
        """
        Update the line numbers display.
        
        Refreshes the line numbers widget to show current line numbers.
        Handles both filtered and unfiltered content appropriately.
        
        Args:
            event: Tkinter event that triggered the update (optional)
        """
        if not self.show_line_numbers.get():
            return
            
        try:
            # Check if we're showing filtered content
            if hasattr(self, '_filtered_lines') and self._filtered_lines and self.filter_manager.current_filter:
                # Show original line numbers for filtered content
                self.line_numbers.config(state=tk.NORMAL)
                self.line_numbers.delete('1.0', tk.END)
                
                for original_line_num, _ in self._filtered_lines:
                    self.line_numbers.insert(tk.END, f"{original_line_num}\n")
                
                self.line_numbers.config(state=tk.DISABLED)
            else:
                # Show sequential line numbers for unfiltered content
                lines = self.text.get('1.0', tk.END).count('\n')
                
                self.line_numbers.config(state=tk.NORMAL)
                self.line_numbers.delete('1.0', tk.END)
                
                for i in range(1, lines + 1):
                    self.line_numbers.insert(tk.END, f"{i}\n")
                
                self.line_numbers.config(state=tk.DISABLED)
            
            # Sync scroll position
            self._sync_scroll()
        except Exception:
            pass
    
    def _toggle_line_numbers(self):
        """
        Toggle line numbers display.
        
        Shows or hides the line numbers widget based on user preference
        and updates the display accordingly.
        """
        if self.show_line_numbers.get():
            # Make line numbers visible and update them
            self.line_numbers.pack(side=tk.LEFT, fill=tk.Y, before=self.text)
            self._update_line_numbers()
        else:
            # Hide line numbers
            self.line_numbers.pack_forget()
    
    def _sync_scroll(self):
        """
        Synchronize scroll position between text and line numbers.
        
        Ensures that the line numbers widget scrolls in sync with the
        main text widget for consistent visual alignment.
        """
        try:
            # Only sync if line numbers are visible
            if not self.show_line_numbers.get():
                return
                
            # Get current scroll position
            first, last = self.text.yview()
            
            # Validate scroll values
            if first is None or last is None or first < 0 or last > 1:
                return
                
            # Apply same scroll position to line numbers
            self.line_numbers.yview_moveto(first)
            
        except Exception:
            pass

    def _on_mouse_wheel(self, event):
        """
        Handle mouse wheel events to scroll the text widget.
        
        Processes mouse wheel scrolling on different platforms and
        schedules line number updates with debouncing for smooth performance.
        
        Args:
            event: Mouse wheel event
        """
        # Cancel any pending scroll sync
        if hasattr(self, '_wheel_sync_job'):
            try:
                self.after_cancel(self._wheel_sync_job)
            except Exception:
                pass
        
        # Handle different mouse wheel events
        if event.num == 4:  # Linux scroll up
            self.text.yview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll down
            self.text.yview_scroll(1, "units")
        else:  # Windows mouse wheel
            self.text.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Schedule line number update after a short delay to ensure scroll completes
        # Use debouncing to prevent rapid updates during fast scrolling
        self._wheel_sync_job = self.after(20, self._sync_scroll)


def main():
    """
    Main entry point for the Log Viewer application.
    
    Parses command line arguments and launches the main application
    with specified configuration options.
    """
    parser = argparse.ArgumentParser(description="Simple GUI log viewer that tails a file.")
    parser.add_argument('--file', '-f', help='Path to the log file to open on launch')
    parser.add_argument('--refresh', '-r', type=int, default=DEFAULT_REFRESH_MS, 
                       help='Refresh interval in milliseconds (default 500)')
    parser.add_argument('--encoding', '-e', default=DEFAULT_ENCODING, 
                       help='File encoding (default auto; try utf-16 on Windows logs)')
    parser.add_argument('--theme', '-t', default=DEFAULT_THEME, 
                       choices=['dark', 'light', 'sunset'], 
                       help='Color theme (default dark)')
    args = parser.parse_args()

    # Create and launch the main application
    app = LogViewerApp(args.file, refresh_ms=args.refresh, encoding=args.encoding, theme=args.theme)
    if app.tail:
        app.tail.encoding = args.encoding
    app.mainloop()


if __name__ == '__main__':
    main()
