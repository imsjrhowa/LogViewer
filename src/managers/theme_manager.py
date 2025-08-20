#!/usr/bin/env python3
"""
Theme Manager for the Log Viewer application.

Manages color themes for the Log Viewer application.
Provides three built-in themes (Dark, Light, Sunset) with consistent
color schemes across all UI elements. Supports dynamic theme switching
and theme preference persistence.
"""

from typing import Dict, Any, List
from ..utils.constants import DEFAULT_THEME


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
    
    def get_theme_names(self) -> List[str]:
        """
        Get list of available theme names.
        
        Returns:
            List of theme identifier strings
        """
        return list(self.THEMES.keys())
    
    def get_theme_display_names(self) -> List[str]:
        """
        Get list of theme display names for UI.
        
        Returns:
            List of human-readable theme names
        """
        return [self.THEMES[name]["name"] for name in self.THEMES]
