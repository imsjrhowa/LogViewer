#!/usr/bin/env python3
"""
Launcher script for the Log Viewer application.

This script provides a simple way to run the application from the root directory
while maintaining the modular structure.
"""

import sys
import os

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import and run the main function
try:
    # Try the direct import first (for PyInstaller)
    from src.main import main
except ImportError:
    # Fallback for development (when src is in path)
    from main import main

if __name__ == '__main__':
    main()
