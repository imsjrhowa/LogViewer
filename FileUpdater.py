#!/usr/bin/env python3
"""
Log Viewer (auto-refresh) — Windows-friendly, 3.6+ compatible

Features
- Choose a log file via File → Open… or pass --file /path/to/file
- Auto-refresh (500 ms by default), adjustable in the UI
- Pause/Resume
- Auto-scroll to bottom when new lines arrive
- Word wrap toggle
- Clear view
- Handles file rotation/truncation
- Auto-detects common encodings (UTF-16 LE/BE, UTF-8 BOM), with heuristic for NUL-byte "spaced" text
- Multiple color themes (Dark, Light, Sunset)
- Keeps memory in check by trimming to last N lines (default 10,000)
- NEW: Live filter box (substring match) with case-sensitive toggle

Run
    python log_viewer.py --file /path/to/your/log.txt

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

MAX_LINES_DEFAULT = 10_000
DEFAULT_REFRESH_MS = 500
DEFAULT_ENCODING = "auto"  # auto | utf-8 | utf-16 | utf-16-le | utf-16-be | etc.
DEFAULT_THEME = "dark"     # dark | light | sunset


class ThemeManager:
    """Manages color themes for the Log Viewer application."""
    
    # Theme color definitions
    THEMES = {
        "dark": {
            "name": "Dark",
            "bg": "#1e1e1e",           # Main background
            "fg": "#d4d4d4",           # Main text
            "text_bg": "#1e1e1e",      # Text area background
            "text_fg": "#d4d4d4",      # Text area text
            "insert_bg": "#ffffff",    # Caret color
            "toolbar_bg": "#2d2d2d",   # Toolbar background
            "toolbar_fg": "#d4d4d4",   # Toolbar text
            "status_bg": "#2d2d2d",    # Status bar background
            "status_fg": "#d4d4d4",    # Status bar text
            "menu_bg": "#2d2d2d",      # Menu background
            "menu_fg": "#d4d4d4",      # Menu text
            "menu_select_bg": "#404040", # Menu selection background
            "button_bg": "#404040",     # Button background
            "button_fg": "#d4d4d4",    # Button text
            "entry_bg": "#3c3c3c",     # Entry field background
            "entry_fg": "#d4d4d4",     # Entry field text
            "entry_insert_bg": "#ffffff", # Entry caret color
        },
        "light": {
            "name": "Light",
            "bg": "#ffffff",           # Main background
            "fg": "#000000",           # Main text
            "text_bg": "#ffffff",      # Text area background
            "text_fg": "#000000",      # Text area text
            "insert_bg": "#000000",    # Caret color
            "toolbar_bg": "#f0f0f0",   # Toolbar background
            "toolbar_fg": "#000000",   # Toolbar text
            "status_bg": "#f0f0f0",    # Status bar background
            "status_fg": "#000000",    # Status bar text
            "menu_bg": "#f0f0f0",      # Menu background
            "menu_fg": "#000000",      # Menu text
            "menu_select_bg": "#e0e0e0", # Menu selection background
            "button_bg": "#e0e0e0",     # Button background
            "button_fg": "#000000",    # Button text
            "entry_bg": "#ffffff",     # Entry field background
            "entry_fg": "#000000",     # Entry field text
            "entry_insert_bg": "#000000", # Entry caret color
        },
        "sunset": {
            "name": "Sunset",
            "bg": "#2d1b3d",           # Main background (deep purple)
            "fg": "#f4e4bc",           # Main text (warm cream)
            "text_bg": "#2d1b3d",      # Text area background
            "text_fg": "#f4e4bc",      # Text area text
            "insert_bg": "#ff6b35",    # Caret color (orange)
            "toolbar_bg": "#3d2b4d",   # Toolbar background
            "toolbar_fg": "#f4e4bc",   # Toolbar text
            "status_bg": "#3d2b4d",    # Status bar background
            "status_fg": "#f4e4bc",    # Status bar text
            "menu_bg": "#3d2b4d",      # Menu background
            "menu_fg": "#f4e4bc",      # Menu text
            "menu_select_bg": "#4d3b5d", # Menu selection background
            "button_bg": "#4d3b5d",     # Button background
            "button_fg": "#f4e4bc",    # Button text
            "entry_bg": "#3d2b4d",     # Entry field background
            "entry_fg": "#f4e4bc",     # Entry field text
            "entry_insert_bg": "#ff6b35", # Entry caret color
        }
    }
    
    def __init__(self, theme_name: str = DEFAULT_THEME):
        self.current_theme = theme_name
        if theme_name not in self.THEMES:
            self.current_theme = DEFAULT_THEME
    
    def get_theme(self, theme_name: str = None) -> Dict[str, Any]:
        """Get theme colors by name."""
        if theme_name is None:
            theme_name = self.current_theme
        return self.THEMES.get(theme_name, self.THEMES[DEFAULT_THEME])
    
    def get_current_theme(self) -> Dict[str, Any]:
        """Get current theme colors."""
        return self.get_theme(self.current_theme)
    
    def set_theme(self, theme_name: str) -> bool:
        """Set current theme. Returns True if theme changed."""
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            return True
        return False
    
    def get_theme_names(self) -> list:
        """Get list of available theme names."""
        return list(self.THEMES.keys())
    
    def get_theme_display_names(self) -> list:
        """Get list of theme display names."""
        return [self.THEMES[name]["name"] for name in self.THEMES]


class FilterManager:
    """Advanced filtering system for log entries with multiple modes and history."""
    
    # Filter modes
    MODES = {
        "contains": "Contains",
        "starts_with": "Starts With", 
        "ends_with": "Ends With",
        "regex": "Regular Expression",
        "exact": "Exact Match",
        "not_contains": "Not Contains"
    }
    
    def __init__(self):
        self.current_filter = ""
        self.current_mode = "contains"
        self.case_sensitive = False
        self.filter_history = []
        self.max_history = 20
        self.compiled_regex = None
        self.last_error = None
        
    def set_filter(self, text: str, mode: str = None, case_sensitive: bool = None) -> bool:
        """Set the current filter. Returns True if filter changed."""
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
        """Add filter text to history if it's not empty and not already there."""
        if text and text not in self.filter_history:
            self.filter_history.insert(0, text)
            if len(self.filter_history) > self.max_history:
                self.filter_history.pop()
    
    def _compile_regex(self):
        """Compile regex pattern if mode is regex."""
        self.compiled_regex = None
        self.last_error = None
        
        if self.current_mode == "regex" and self.current_filter:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self.compiled_regex = re.compile(self.current_filter, flags)
            except re.error as e:
                self.last_error = str(e)
    
    def matches(self, line: str) -> bool:
        """Check if a line matches the current filter."""
        if not self.current_filter:
            return True
            
        if self.last_error:
            return False
            
        try:
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
        """Check if line contains the filter text."""
        if self.case_sensitive:
            return self.current_filter in line
        return self.current_filter.lower() in line.lower()
    
    def _starts_with_match(self, line: str) -> bool:
        """Check if line starts with the filter text."""
        if self.case_sensitive:
            return line.startswith(self.current_filter)
        return line.lower().startswith(self.current_filter.lower())
    
    def _ends_with_match(self, line: str) -> bool:
        """Check if line ends with the filter text."""
        if self.case_sensitive:
            return line.endswith(self.current_filter)
        return line.lower().endswith(self.current_filter.lower())
    
    def _regex_match(self, line: str) -> bool:
        """Check if line matches the regex pattern."""
        if self.compiled_regex:
            return bool(self.compiled_regex.search(line))
        return False
    
    def _exact_match(self, line: str) -> bool:
        """Check if line exactly matches the filter text."""
        if self.case_sensitive:
            return line == self.current_filter
        return line.lower() == self.current_filter.lower()
    
    def _not_contains_match(self, line: str) -> bool:
        """Check if line does NOT contain the filter text."""
        return not self._contains_match(line)
    
    def get_filter_info(self) -> Dict[str, Any]:
        """Get current filter information for display."""
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
        """Get list of available filter mode names."""
        return list(self.MODES.keys())
    
    def get_mode_display_names(self) -> List[str]:
        """Get list of filter mode display names."""
        return list(self.MODES.values())
    
    def clear_filter(self):
        """Clear the current filter."""
        self.current_filter = ""
        self.compiled_regex = None
        self.last_error = None


class ConfigManager:
    """Manages application configuration and user preferences."""
    
    DEFAULT_CONFIG = {
        "window": {
            "width": 1000,
            "height": 1000,
            "x": None,
            "y": None,
            "maximized": False
        },
        "theme": {
            "current": "dark",
            "auto_switch": False,
            "auto_switch_time": "18:00"
        },
        "filter": {
            "default_mode": "contains",
            "case_sensitive": False,
            "remember_history": True,
            "max_history": 20
        },
        "display": {
            "refresh_rate": 500,
            "max_lines": 10000,
            "auto_scroll": True,
            "word_wrap": False,
            "font_size": 11,
            "font_family": None,
            "show_line_numbers": True
        },
        "file": {
            "last_directory": "",
            "remember_encoding": True,
            "auto_detect_encoding": True
        },
        "ui": {
            "show_toolbar": True,
            "show_status_bar": True,
            "toolbar_position": "top",
            "status_bar_position": "bottom"
        }
    }
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Use proper Windows path handling
            if sys.platform.startswith("win"):
                config_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "LogViewer")
            else:
                config_dir = os.path.expanduser("~/.logviewer")
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
        print(f"Debug: Config directory: {self.config_dir}")
        print(f"Debug: Config file: {self.config_file}")
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
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
            # Keep default config
    
    def save_config(self):
        """Save current configuration to file."""
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
        """Recursively merge loaded config with defaults."""
        def _merge_dict(target: Dict[str, Any], source: Dict[str, Any]):
            """Helper function to merge source into target recursively."""
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
        """Get configuration value using dot notation (e.g., 'window.width')."""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value):
        """Set configuration value using dot notation."""
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
        """Get window geometry string for Tkinter."""
        width = self.get('window.width', 1000)
        height = self.get('window.height', 1000)
        x = self.get('window.x')
        y = self.get('window.y')
        
        # Validate dimensions
        width = max(800, min(width, 3000))  # Reasonable bounds
        height = max(600, min(height, 2000))
        
        # On Windows, position might not work reliably, so we'll try both approaches
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
        """Save current window state and position."""
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
            # Set safe defaults
            self.set('window.width', 1000)
            self.set('window.height', 1000)
            self.set('window.x', None)
            self.set('window.y', None)
            self.set('window.maximized', False)
    
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
    
    def export_config(self, filepath: str):
        """Export configuration to a file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Could not export config: {e}")
    
    def import_config(self, filepath: str):
        """Import configuration from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                self._merge_config(loaded_config)
                self.save_config()
        except Exception as e:
            raise Exception(f"Could not import config: {e}")


class TailReader:
    """Efficiently read new bytes from a growing (append-only) text file.
    Detects truncation and rotation and reopens as needed.
    Includes BOM detection and heuristic for UTF-16 logs without BOM.
    """
    def __init__(self, path: str, encoding: str = DEFAULT_ENCODING):
        self.path = path
        self.encoding = encoding
        self._fh = None  # type: Optional[io.BufferedReader]
        self._inode = None  # type: Optional[tuple]
        self._pos = 0

    def _encoding_from_bom(self, fh) -> Optional[str]:
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
        self.close()
        self._fh = open(self.path, "rb")
        try:
            st = os.fstat(self._fh.fileno())
            self._inode = (st.st_dev, st.st_ino)
        except Exception:
            self._inode = None

        # Auto-detect encoding (BOM first)
        if self.encoding == "auto":
            enc = self._encoding_from_bom(self._fh)
            self.encoding = enc or "utf-8"

        if start_at_end:
            self._fh.seek(0, io.SEEK_END)
            self._pos = self._fh.tell()
        else:
            self._fh.seek(0)
            self._pos = 0
        return True

    def close(self):
        try:
            if self._fh:
                self._fh.close()
        finally:
            self._fh = None
            self._inode = None
            self._pos = 0

    def _check_rotation_or_truncate(self):
        """Reopen file if inode changed (rotation) or size < pos (truncation)."""
        try:
            st_path = os.stat(self.path)
            inode = (st_path.st_dev, st_path.st_ino)
        except OSError:
            return  # Possibly temporarily missing during rotation
        if self._inode and inode != self._inode:
            # rotated/recreated
            self.open(start_at_end=False)
            return
        if self._fh:
            try:
                size = os.fstat(self._fh.fileno()).st_size
                if size < self._pos:
                    # truncated
                    self._fh.seek(0)
                    self._pos = 0
            except OSError:
                pass

    def read_new_text(self) -> str:
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
            return data.decode("utf-8", errors="replace")


class LogViewerApp(tk.Tk):
    def __init__(self, path: Optional[str], refresh_ms: int = DEFAULT_REFRESH_MS, encoding: str = DEFAULT_ENCODING, theme: str = DEFAULT_THEME):
        super().__init__()
        
        # Initialize configuration manager first
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
        
        # Initialize filter manager
        self.filter_manager = FilterManager()
        
        self.path = path
        self.tail = TailReader(path, encoding=encoding) if path else None
        
        # Load settings from config
        self.refresh_ms = tk.IntVar(value=self.config_manager.get('display.refresh_rate', refresh_ms))
        self.autoscroll = tk.BooleanVar(value=self.config_manager.get('display.auto_scroll', True))
        self.wrap = tk.BooleanVar(value=self.config_manager.get('display.word_wrap', False))
        self.show_line_numbers = tk.BooleanVar(value=self.config_manager.get('display.show_line_numbers', True))
        self.paused = tk.BooleanVar(value=False)
        self.max_lines = tk.IntVar(value=self.config_manager.get('display.max_lines', MAX_LINES_DEFAULT))

        # Filtering
        self.filter_text = tk.StringVar(value="")
        self.case_sensitive = tk.BooleanVar(value=False)
        self.filter_mode = tk.StringVar(value="contains")
        self._filter_job = None  # debounce handle

        # Store raw lines so we can rebuild view when filter changes
        self._line_buffer = collections.deque(maxlen=MAX_LINES_DEFAULT)

        self._build_ui()
        
        # Load saved theme preference if using default theme
        if theme == DEFAULT_THEME:
            saved_theme = self._load_theme_preference()
            if saved_theme != DEFAULT_THEME:
                self.theme_manager.set_theme(saved_theme)
                # Update menu checkmarks
                for name, var in self.theme_vars.items():
                    var.set(name == saved_theme)
        
        # Ensure the icon is set for the current theme (command line or saved)
        self._set_app_icon()
        
        # Load saved filter preferences
        self._load_filter_preferences()
        
        self._apply_theme()  # Apply initial theme
        if self.path:
            self._open_path(self.path, first_open=True)
        self.after(self.refresh_ms.get(), self._poll)
        
        # Bind window close event to save configuration
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # UI
    def _build_ui(self):
        # Menu
        menubar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open…", command=self._choose_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu with theme selection
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Word Wrap", command=self._toggle_wrap)
        view_menu.add_separator()
        
        # Theme submenu
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
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Preferences...", command=self._show_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Save Current Settings as Default", command=self._save_as_default)
        settings_menu.add_command(label="Reset to Defaults", command=self._reset_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Export Settings...", command=self._export_settings)
        settings_menu.add_command(label="Import Settings...", command=self._import_settings)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Filter Help", command=self._show_filter_help)
        help_menu.add_command(label="Theme Info", command=self._show_theme_info)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_keyboard_shortcuts)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)
        
        # Bind keyboard shortcuts
        self.bind('<Control-t>', lambda e: self._cycle_theme())
        self.bind('<Control-T>', lambda e: self._cycle_theme())
        self.bind('<Control-f>', lambda e: self._focus_filter())
        self.bind('<Control-F>', lambda e: self._focus_filter())
        self.bind('<Control-w>', lambda e: self._toggle_wrap())
        self.bind('<Control-W>', lambda e: self._toggle_wrap())
        self.bind('<Control-p>', lambda e: self._toggle_pause())
        self.bind('<Control-P>', lambda e: self._toggle_pause())
        
        # Filter-specific shortcuts
        self.bind('<Escape>', lambda e: self._clear_filter())
        self.bind('<Control-r>', lambda e: self._focus_filter())
        self.bind('<Control-R>', lambda e: self._focus_filter())

        # Controls / toolbar
        toolbar = ttk.Frame(self, padding=(8, 4))
        toolbar.pack(fill=tk.X)

        self.path_label = ttk.Label(toolbar, text="No file selected", width=80)
        self.path_label.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(toolbar, text="Refresh (ms)").pack(side=tk.LEFT)
        refresh_entry = ttk.Spinbox(toolbar, from_=100, to=5000, textvariable=self.refresh_ms, width=6)
        refresh_entry.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Checkbutton(toolbar, text="Auto-scroll", variable=self.autoscroll).pack(side=tk.LEFT)
        ttk.Checkbutton(toolbar, text="Wrap", variable=self.wrap, command=self._apply_wrap).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Checkbutton(toolbar, text="Line Numbers", variable=self.show_line_numbers, command=self._toggle_line_numbers).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Label(toolbar, text="Max lines").pack(side=tk.LEFT)
        ttk.Spinbox(toolbar, from_=1000, to=200000, increment=1000, textvariable=self.max_lines, width=7).pack(side=tk.LEFT, padx=(4, 8))

        self.pause_btn = ttk.Button(toolbar, text="Pause", command=self._toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=(8, 4))
        ttk.Button(toolbar, text="Clear", command=self._clear).pack(side=tk.LEFT)

        # Enhanced Filter controls
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.LEFT, padx=(12, 4))
        
        # Filter mode dropdown
        ttk.Label(filter_frame, text="Mode:").pack(side=tk.LEFT)
        self.filter_mode_combo = ttk.Combobox(filter_frame, textvariable=self.filter_mode, 
                                             values=self.filter_manager.get_mode_display_names(),
                                             width=12, state="readonly")
        self.filter_mode_combo.pack(side=tk.LEFT, padx=(4, 0))
        
        # Filter entry with history
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(8, 4))
        
        # Filter entry frame for dropdown
        filter_entry_frame = ttk.Frame(filter_frame)
        filter_entry_frame.pack(side=tk.LEFT)
        
        self.filter_entry = ttk.Entry(filter_entry_frame, textvariable=self.filter_text, width=30)
        self.filter_entry.pack(side=tk.LEFT)
        
        # Filter history dropdown
        self.filter_history_btn = ttk.Button(filter_entry_frame, text="▼", width=2,
                                           command=self._show_filter_history)
        self.filter_history_btn.pack(side=tk.LEFT)
        
        # Filter controls
        filter_controls_frame = ttk.Frame(filter_frame)
        filter_controls_frame.pack(side=tk.LEFT, padx=(4, 0))
        
        # Case sensitive checkbox
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
        
        # Theme indicator (right side)
        theme_frame = ttk.Frame(toolbar)
        theme_frame.pack(side=tk.RIGHT, padx=(8, 0))
        
        self.theme_label = ttk.Label(theme_frame, text="", width=15)
        self.theme_label.pack(side=tk.LEFT)
        
        # Theme preview button
        self.theme_preview_btn = ttk.Button(theme_frame, text="🎨", width=3, command=self._show_theme_preview)
        self.theme_preview_btn.pack(side=tk.LEFT, padx=(4, 0))
        
        # Bind filter events
        self.filter_text.trace_add('write', lambda *args: self._on_filter_change())
        self.filter_mode_combo.bind('<<ComboboxSelected>>', self._on_filter_mode_change)
        self.case_sensitive.trace_add('write', lambda *args: self._on_filter_change())
        
        # Set initial filter mode
        self.filter_mode_combo.set(self.filter_manager.get_mode_display_names()[0])

        # Text area with line numbers support
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Create a frame for text and line numbers
        text_content_frame = ttk.Frame(text_frame)
        text_content_frame.pack(fill=tk.BOTH, expand=True)

        # Line numbers widget
        self.line_numbers = tk.Text(
            text_content_frame,
            width=8,
            padx=3,
            pady=2,
            relief=tk.FLAT,
            borderwidth=0,
            state=tk.DISABLED,
            font=("Consolas", 11),
            background="#f0f0f0",
            foreground="#666666"
        )
        
        # Main text widget
        self.text = tk.Text(
            text_content_frame,
            wrap=tk.WORD if self.wrap.get() else tk.NONE,
            undo=False,
            font=("Consolas", 11)
        )

        # Scrollbars
        yscroll = ttk.Scrollbar(text_content_frame, orient=tk.VERTICAL, command=self.text.yview)
        xscroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # Pack widgets
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar should span the full width of the application
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Store references for layout management
        self.text_content_frame = text_content_frame
        self.yscroll = yscroll
        self.xscroll = xscroll
        
        # Bind events for line numbers
        self.text.bind('<KeyRelease>', self._update_line_numbers)
        self.text.bind('<ButtonRelease-1>', self._update_line_numbers)
        self.show_line_numbers.trace_add('write', lambda *args: self._toggle_line_numbers())
        
        # Bind scrollbar to update line numbers
        yscroll.config(command=lambda *args: self._on_yscroll(*args))

        # Status bar
        self.status = ttk.Label(self, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X)

    # Enhanced Filtering
    def _on_filter_change(self):
        """Handle filter text or case sensitivity changes."""
        # Update filter manager
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
        """Update the filter status indicator."""
        info = self.filter_manager.get_filter_info()
        
        if info["is_active"]:
            if info["has_error"]:
                self.filter_status_label.config(text="❌ Error", foreground="red")
            else:
                self.filter_status_label.config(text="✅ Active", foreground="green")
        else:
            self.filter_status_label.config(text="", foreground="black")
    
    def _on_filter_mode_change(self, event=None):
        """Handle filter mode changes."""
        self._on_filter_change()
    
    def _clear_filter(self):
        """Clear the current filter."""
        self.filter_text.set("")
        self.filter_manager.clear_filter()
        self._rebuild_view()
        self._set_status("Filter cleared")
    
    def _show_settings(self):
        """Show the settings/preferences dialog."""
        settings_window = tk.Toplevel(self)
        settings_window.title("Log Viewer Settings")
        settings_window.geometry("600x700")
        settings_window.resizable(True, True)
        settings_window.transient(self)
        settings_window.grab_set()
        
        # Center the window
        settings_window.geometry("+%d+%d" % (self.winfo_rootx() + 100, self.winfo_rooty() + 100))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        self._create_general_settings_tab(general_frame)
        
        # Display tab
        display_frame = ttk.Frame(notebook)
        notebook.add(display_frame, text="Display")
        self._create_display_settings_tab(display_frame)
        
        # Filter tab
        filter_frame = ttk.Frame(notebook)
        notebook.add(filter_frame, text="Filtering")
        self._create_filter_settings_tab(filter_frame)
        
        # Theme tab
        theme_frame = ttk.Frame(notebook)
        notebook.add(theme_frame, text="Theme")
        self._create_theme_settings_tab(theme_frame)
        
        # Buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=lambda: self._save_settings_and_close(settings_window)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Apply", command=self._apply_settings).pack(side=tk.RIGHT, padx=5)
    
    def _create_general_settings_tab(self, parent):
        """Create the general settings tab."""
        # Window settings
        window_frame = ttk.LabelFrame(parent, text="Window", padding=10)
        window_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Window size
        ttk.Label(window_frame, text="Default Window Size:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        size_frame = ttk.Frame(window_frame)
        size_frame.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        self.settings_width = tk.StringVar(value=str(self.config_manager.get('window.width', 1000)))
        self.settings_height = tk.StringVar(value=str(self.config_manager.get('window.height', 1000)))
        
        ttk.Label(size_frame, text="Width:").pack(side=tk.LEFT)
        ttk.Entry(size_frame, textvariable=self.settings_width, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_frame, text="Height:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(size_frame, textvariable=self.settings_height, width=8).pack(side=tk.LEFT, padx=5)
        
        # Remember window position
        self.settings_remember_pos = tk.BooleanVar(value=self.config_manager.get('window.x') is not None)
        ttk.Checkbutton(window_frame, text="Remember window position", variable=self.settings_remember_pos).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # File settings
        file_frame = ttk.LabelFrame(parent, text="File Handling", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.settings_remember_dir = tk.BooleanVar(value=self.config_manager.get('file.remember_encoding', True))
        ttk.Checkbutton(file_frame, text="Remember last directory", variable=self.settings_remember_dir).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.settings_auto_encoding = tk.BooleanVar(value=self.config_manager.get('file.auto_detect_encoding', True))
        ttk.Checkbutton(file_frame, text="Auto-detect file encoding", variable=self.settings_auto_encoding).grid(row=1, column=0, sticky=tk.W, pady=2)
    
    def _create_display_settings_tab(self, parent):
        """Create the display settings tab."""
        # Refresh settings
        refresh_frame = ttk.LabelFrame(parent, text="Refresh & Performance", padding=10)
        refresh_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(refresh_frame, text="Default Refresh Rate (ms):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_refresh_rate = tk.StringVar(value=str(self.config_manager.get('display.refresh_rate', 500)))
        ttk.Entry(refresh_frame, textvariable=self.settings_refresh_rate, width=10).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(refresh_frame, text="Default Max Lines:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.settings_max_lines = tk.StringVar(value=str(self.config_manager.get('display.max_lines', 10000)))
        ttk.Entry(refresh_frame, textvariable=self.settings_max_lines, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Display options
        display_frame = ttk.LabelFrame(parent, text="Display Options", padding=10)
        display_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.settings_auto_scroll = tk.BooleanVar(value=self.config_manager.get('display.auto_scroll', True))
        ttk.Checkbutton(display_frame, text="Auto-scroll by default", variable=self.settings_auto_scroll).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.settings_word_wrap = tk.BooleanVar(value=self.config_manager.get('display.word_wrap', False))
        ttk.Checkbutton(display_frame, text="Word wrap by default", variable=self.settings_word_wrap).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Font settings
        font_frame = ttk.LabelFrame(parent, text="Font", padding=10)
        font_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(font_frame, text="Font Size:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_font_size = tk.StringVar(value=str(self.config_manager.get('display.font_size', 11)))
        ttk.Entry(font_frame, textvariable=self.settings_font_size, width=8).grid(row=0, column=1, sticky=tk.W, pady=2)
    
    def _create_filter_settings_tab(self, parent):
        """Create the filter settings tab."""
        filter_frame = ttk.LabelFrame(parent, text="Filter Preferences", padding=10)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Default filter mode
        ttk.Label(filter_frame, text="Default Filter Mode:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_filter_mode = tk.StringVar(value=self.config_manager.get('filter.default_mode', 'contains'))
        filter_mode_combo = ttk.Combobox(filter_frame, textvariable=self.settings_filter_mode, 
                                        values=self.filter_manager.get_mode_display_names(), state="readonly")
        filter_mode_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Filter options
        self.settings_case_sensitive = tk.BooleanVar(value=self.config_manager.get('filter.case_sensitive', False))
        ttk.Checkbutton(filter_frame, text="Case sensitive by default", variable=self.settings_case_sensitive).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.settings_remember_history = tk.BooleanVar(value=self.config_manager.get('filter.remember_history', True))
        ttk.Checkbutton(filter_frame, text="Remember filter history", variable=self.settings_remember_history).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Label(filter_frame, text="Max History Items:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.settings_max_history = tk.StringVar(value=str(self.config_manager.get('filter.max_history', 20)))
        ttk.Entry(filter_frame, textvariable=self.settings_max_history, width=8).grid(row=3, column=1, sticky=tk.W, pady=2)
    
    def _create_theme_settings_tab(self, parent):
        """Create the theme settings tab."""
        theme_frame = ttk.LabelFrame(parent, text="Theme Preferences", padding=10)
        theme_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Default theme
        ttk.Label(theme_frame, text="Default Theme:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.settings_default_theme = tk.StringVar(value=self.config_manager.get('theme.current', 'dark'))
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.settings_default_theme, 
                                  values=self.theme_manager.get_theme_names(), state="readonly")
        theme_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Auto-switch theme
        self.settings_auto_switch_theme = tk.BooleanVar(value=self.config_manager.get('theme.auto_switch', False))
        ttk.Checkbutton(theme_frame, text="Auto-switch theme based on time", variable=self.settings_auto_switch_theme).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Label(theme_frame, text="Switch Time (HH:MM):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.settings_switch_time = tk.StringVar(value=self.config_manager.get('theme.auto_switch_time', '18:00'))
        ttk.Entry(theme_frame, textvariable=self.settings_switch_time, width=10).grid(row=2, column=1, sticky=tk.W, pady=2)
    
    def _apply_settings(self):
        """Apply current settings without closing the dialog."""
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
        """Save settings and close the dialog."""
        self._apply_settings()
        window.destroy()
    
    def _apply_current_settings(self):
        """Apply current configuration to the running application."""
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
        """Save current application state as default settings."""
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
            
            # Save to file
            self.config_manager.save_config()
            
            self._set_status("Current settings saved as default")
            messagebox.showinfo("Success", "Current settings have been saved as your new defaults!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def _reset_settings(self):
        """Reset all settings to default values."""
        if messagebox.askyesno("Reset Settings", 
                              "Are you sure you want to reset all settings to default values?\n\nThis cannot be undone."):
            self.config_manager.reset_to_defaults()
            self._set_status("Settings reset to defaults")
            messagebox.showinfo("Reset Complete", "All settings have been reset to default values.\n\nRestart the application to apply the changes.")
    
    def _export_settings(self):
        """Export current settings to a file."""
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
        """Import settings from a file."""
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
        """Handle application closing - save configuration."""
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
        """Re-render the text widget from the buffered lines using the current filter."""
        try:
            self.text.delete('1.0', tk.END)
            at_end = True
            matched_count = 0
            total_count = len(self._line_buffer)
            
            for line in self._line_buffer:
                if self.filter_manager.matches(line):
                    self.text.insert(tk.END, line)
                    matched_count += 1
            
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
        path = filedialog.askopenfilename(title="Choose log file")
        if path:
            self._open_path(path, first_open=True)

    def _open_path(self, path: str, first_open=False):
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
                # Load initial chunk
                text = self.tail.read_new_text()
                if text:
                    self._append(text)
            self._set_status("Opened")
        except Exception as e:
            messagebox.showerror("Error", "Failed to open file:\n{}".format(e))
            self._set_status("Open failed")

    def _toggle_pause(self):
        self.paused.set(not self.paused.get())
        self.pause_btn.config(text="Resume" if self.paused.get() else "Pause")
        self._set_status("Paused" if self.paused.get() else "Running")

    def _clear(self):
        self.text.delete('1.0', tk.END)
        self._update_line_numbers()

    def _toggle_wrap(self):
        """Toggle word wrap and update menu checkmark."""
        self.wrap.set(not self.wrap.get())
        self._apply_wrap()
        # Update menu checkmark
        if hasattr(self, 'view_menu'):
            # Find the word wrap menu item and update it
            pass  # Menu update will be handled by the menu system
    
    def _apply_wrap(self):
        self.text.config(wrap=tk.WORD if self.wrap.get() else tk.NONE)
    
    def _change_theme(self, theme_name: str):
        """Change the application theme."""
        if self.theme_manager.set_theme(theme_name):
            self._apply_theme()
            # Update theme menu checkmarks
            for name, var in self.theme_vars.items():
                var.set(name == theme_name)
            # Show theme change confirmation in status
            self._set_status(f"Theme changed to {self.theme_manager.get_theme(theme_name)['name']}")
    
    def _apply_theme(self):
        """Apply the current theme to all UI elements."""
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
        """Save current filter preferences to config file."""
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
        """Load saved filter preferences. Returns default if none saved."""
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
        """Save current theme preference to the configuration system."""
        try:
            self.config_manager.set('theme.current', self.theme_manager.current_theme)
            self.config_manager.save_config()
        except Exception:
            pass  # Silently fail if we can't save preferences
    
    def _load_theme_preference(self) -> str:
        """Load saved theme preference from the configuration system."""
        try:
            saved_theme = self.config_manager.get('theme.current', DEFAULT_THEME)
            if saved_theme in self.theme_manager.get_theme_names():
                return saved_theme
        except Exception:
            pass
        return DEFAULT_THEME
    
    def _cycle_theme(self):
        """Cycle through available themes with keyboard shortcut."""
        themes = self.theme_manager.get_theme_names()
        current_index = themes.index(self.theme_manager.current_theme)
        next_index = (current_index + 1) % len(themes)
        next_theme = themes[next_index]
        self._change_theme(next_theme)
    
    def _show_theme_info(self):
        """Show information about available themes."""
        info = "Available Themes:\n\n"
        for theme_name in self.theme_manager.get_theme_names():
            theme = self.theme_manager.get_theme(theme_name)
            current = " (Current)" if theme_name == self.theme_manager.current_theme else ""
            info += f"• {theme['name']}{current}\n"
        info += "\nUse Ctrl+T to cycle through themes\n"
        info += "Or use View → Theme menu"
        
        messagebox.showinfo("Theme Information", info)
    
    def _show_keyboard_shortcuts(self):
        """Show available keyboard shortcuts."""
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
        """Show help information for the filtering system."""
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
        """Show a preview of all available themes."""
        preview_window = tk.Toplevel(self)
        preview_window.title("Theme Preview")
        preview_window.geometry("400x300")
        preview_window.resizable(False, False)
        preview_window.transient(self)
        preview_window.grab_set()
        
        # Center the window
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
            
            # Color preview
            preview_frame = tk.Frame(theme_frame, height=40)
            preview_frame.pack(fill=tk.X, pady=2)
            preview_frame.pack_propagate(False)
            
            # Background color
            bg_label = tk.Label(preview_frame, text="  Background  ", 
                               bg=theme["bg"], fg=theme["fg"], relief=tk.RAISED)
            bg_label.pack(side=tk.LEFT, padx=2)
            
            # Text color
            text_label = tk.Label(preview_frame, text="  Text  ", 
                                 bg=theme["text_bg"], fg=theme["text_fg"], relief=tk.RAISED)
            text_label.pack(side=tk.LEFT, padx=2)
            
            # Button color
            btn_label = tk.Label(preview_frame, text="  Button  ", 
                                bg=theme["button_bg"], fg=theme["button_fg"], relief=tk.RAISED)
            btn_label.pack(side=tk.LEFT, padx=2)
            
            # Apply button
            apply_btn = ttk.Button(theme_frame, text="Apply", 
                                  command=lambda t=theme_name: self._apply_theme_from_preview(t, preview_window))
            apply_btn.pack(anchor=tk.E, pady=2)
        
        # Close button
        close_btn = ttk.Button(preview_window, text="Close", command=preview_window.destroy)
        close_btn.pack(pady=10)
    
    def _apply_theme_from_preview(self, theme_name: str, preview_window):
        """Apply theme from preview window and close it."""
        self._change_theme(theme_name)
        preview_window.destroy()
    
    def _focus_filter(self):
        """Focus the filter entry box."""
        self.filter_entry.focus_set()
        self.filter_entry.select_range(0, tk.END)

    def _set_status(self, msg: str):
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
        """Append new text to the display, applying current filter."""
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
            # Reschedule
            try:
                interval = max(100, int(self.refresh_ms.get()))
            except Exception:
                interval = DEFAULT_REFRESH_MS
            self.after(interval, self._poll)

    def _center_window(self):
        """Centers the window on the screen."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = self.winfo_reqwidth()
        window_height = self.winfo_reqheight()
        
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _set_app_icon(self):
        """Sets the application icon based on the current theme."""
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
        """Handle scrollbar events for the text widget."""
        # Only call yview if args are valid scrollbar commands
        if args and args[0] in ['moveto', 'scroll']:
            self.text.yview(*args)
            self._sync_scroll()
    
    def _on_yscroll(self, *args):
        """Handle vertical scrollbar events and update line numbers."""
        self.text.yview(*args)
        self._sync_scroll()

    def _update_line_numbers(self, event=None):
        """Update the line numbers display."""
        if not self.show_line_numbers.get():
            return
            
        try:
            # Get the current number of lines
            lines = self.text.get('1.0', tk.END).count('\n')
            
            # Update line numbers widget
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
        """Toggle line numbers display."""
        if self.show_line_numbers.get():
            # Make line numbers visible and update them
            self.line_numbers.pack(side=tk.LEFT, fill=tk.Y, before=self.text)
            self._update_line_numbers()
        else:
            # Hide line numbers
            self.line_numbers.pack_forget()
    
    def _sync_scroll(self):
        """Synchronize scroll position between text and line numbers."""
        try:
            # Get current scroll position
            first, last = self.text.yview()
            
            # Apply same scroll position to line numbers
            self.line_numbers.yview_moveto(first)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Simple GUI log viewer that tails a file.")
    parser.add_argument('--file', '-f', help='Path to the log file to open on launch')
    parser.add_argument('--refresh', '-r', type=int, default=DEFAULT_REFRESH_MS, help='Refresh interval in milliseconds (default 500)')
    parser.add_argument('--encoding', '-e', default=DEFAULT_ENCODING, help='File encoding (default auto; try utf-16 on Windows logs)')
    parser.add_argument('--theme', '-t', default=DEFAULT_THEME, choices=['dark', 'light', 'sunset'], help='Color theme (default dark)')
    args = parser.parse_args()

    app = LogViewerApp(args.file, refresh_ms=args.refresh, encoding=args.encoding, theme=args.theme)
    if app.tail:
        app.tail.encoding = args.encoding
    app.mainloop()


if __name__ == '__main__':
    main()
