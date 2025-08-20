#!/usr/bin/env python3
"""
Utilities package for the Log Viewer application.

This package contains utility modules including constants and helper functions.
"""

from .constants import *

__all__ = [
    'MAX_LINES_DEFAULT',
    'DEFAULT_REFRESH_MS',
    'DEFAULT_ENCODING',
    'DEFAULT_THEME',
    'MAX_FILE_SIZE_FOR_FULL_LOAD',
    'MIN_WINDOW_WIDTH',
    'MIN_WINDOW_HEIGHT',
    'MAX_WINDOW_WIDTH',
    'MAX_WINDOW_HEIGHT',
    'DEFAULT_FILTER_MODE',
    'MAX_FILTER_HISTORY',
    'FILTER_DEBOUNCE_MS',
    'THEME_NAMES',
    'CONFIG_DIR_WINDOWS',
    'CONFIG_DIR_UNIX',
    'CONFIG_FILENAME',
    'FILTER_PREFS_FILENAME',
    'ICON_DIR',
    'ICON_EXTENSION'
]
