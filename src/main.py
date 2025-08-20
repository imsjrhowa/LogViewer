#!/usr/bin/env python3
"""
Main entry point for the Log Viewer application.

Parses command line arguments and launches the main application
with specified configuration options.
"""

import argparse
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.managers import ThemeManager, FilterManager, ConfigManager, FileManager
from src.ui.main_window import LogViewerApp
from src.utils.constants import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION,
    DEFAULT_REFRESH_MS, DEFAULT_ENCODING, DEFAULT_THEME
)


def main():
    """
    Main entry point for the Log Viewer application.
    
    Parses command line arguments and launches the main application
    with specified configuration options.
    """
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=f"{APP_DESCRIPTION} ({APP_VERSION})"
    )
    parser.add_argument('--version', action='version', version=f'{APP_NAME} {APP_VERSION}')
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
    if app.file_manager:
        app.file_manager.encoding = args.encoding
    app.mainloop()


if __name__ == '__main__':
    main()
