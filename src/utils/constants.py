#!/usr/bin/env python3
"""
Constants for the Log Viewer application.

This module contains all global constants used throughout the application
including default values, configuration keys, and application settings.
"""

# Application metadata
APP_NAME = "Log Viewer"
APP_VERSION = "v0.2"
APP_DESCRIPTION = "Real-time log file monitor with advanced filtering"
APP_AUTHOR = "Log Viewer Team"

# Application defaults
MAX_LINES_DEFAULT = 10_000      # Maximum lines to keep in memory
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

# Configuration file paths
CONFIG_DIR_WINDOWS = "AppData\\Local\\LogViewer"
CONFIG_DIR_UNIX = "~/.logviewer"
CONFIG_FILENAME = "config.json"
FILTER_PREFS_FILENAME = "filter_prefs.txt"

# Icon paths
ICON_DIR = "icons"
ICON_EXTENSION = ".ico"
