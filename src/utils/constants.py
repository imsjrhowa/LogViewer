#!/usr/bin/env python3
"""
Constants for the Log Viewer application.

This module contains all global constants used throughout the application
including default values, configuration keys, and application settings.
"""

# Application metadata
APP_NAME = "Log Viewer"
APP_VERSION = "v0.3"
APP_DESCRIPTION = "Real-time log file monitor with advanced filtering"
APP_AUTHOR = "Log Viewer Team"
BUILD_NUMBER = 15

# Application defaults

DEFAULT_REFRESH_MS = 500        # Default refresh interval in milliseconds
DEFAULT_ENCODING = "auto"       # Default encoding (auto-detection enabled)
DEFAULT_THEME = "dark"          # Default color theme

# File handling constants
MAX_FILE_SIZE_FOR_FULL_LOAD = 2 * 1024 * 1024  # 2MB - files larger than this start tailing from end

# UI constants
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600
MAX_WINDOW_WIDTH = 3000
MAX_WINDOW_HEIGHT = 2000
LINE_NUMBER_WIDTH = 8              # Width of line numbers panel

# Filter constants
DEFAULT_FILTER_MODE = "contains"
MAX_FILTER_HISTORY = 20
FILTER_DEBOUNCE_MS = 150

# Theme constants
# All available themes - using single icon for all
THEME_NAMES = {
    "dark": "Dark",
    "light": "Light", 
    "sunset": "Sunset",
    "ocean": "Ocean",
    "forest": "Forest",
    "midnight": "Midnight",
    "sepia": "Sepia",
    "high_contrast": "High Contrast"
}

# All themes are now available (using single icon)
AVAILABLE_THEMES = ["dark", "light", "sunset", "ocean", "forest", "midnight", "sepia", "high_contrast"]

# Configuration file paths
CONFIG_DIR_WINDOWS = "AppData\\Local\\LogViewer"
CONFIG_DIR_UNIX = "~/.logviewer"
CONFIG_FILENAME = "config.json"
FILTER_PREFS_FILENAME = "filter_prefs.txt"

# Icon paths
ICON_DIR = "icons"
ICON_EXTENSION = ".ico"

# Theme validation utilities
def get_available_themes() -> list[str]:
    """
    Get list of available themes that are fully supported.
    
    Returns:
        List of theme identifier strings
    """
    return AVAILABLE_THEMES.copy()

def is_theme_available(theme_name: str) -> bool:
    """
    Check if a theme is fully available.
    
    Args:
        theme_name: Name of theme to check
        
    Returns:
        True if theme is fully available, False otherwise
    """
    return theme_name in AVAILABLE_THEMES

def validate_theme_name(theme_name: str) -> str:
    """
    Validate theme name and return a valid theme name.
    
    Args:
        theme_name: Name of theme to validate
        
    Returns:
        Valid theme name (falls back to default if invalid)
    """
    if theme_name in AVAILABLE_THEMES:
        return theme_name
    else:
        print(f"Warning: Unknown theme '{theme_name}'. Falling back to default theme.")
        return DEFAULT_THEME
