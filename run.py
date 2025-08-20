#!/usr/bin/env python3
"""
Launcher script for the Log Viewer application.

This script provides a simple way to run the application from the root directory
while maintaining the modular structure.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function
from main import main

if __name__ == '__main__':
    main()
