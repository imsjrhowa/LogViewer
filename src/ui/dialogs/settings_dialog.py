#!/usr/bin/env python3
"""
Settings Dialog for the Log Viewer application.

Provides a comprehensive settings interface for configuring all aspects
of the application including display options, themes, filtering, and
file handling preferences.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any

from src.managers import ConfigManager, ThemeManager
from src.utils.constants import DEFAULT_THEME


class SettingsDialog(tk.Toplevel):
    """
    Comprehensive settings dialog for the Log Viewer application.
    
    Provides tabs for different categories of settings including:
    - Display: Text appearance, line numbers, word wrap
    - Performance: Refresh rate, max lines, auto-scroll
    - Themes: Color scheme selection and preview
    - Filtering: Default filter mode and case sensitivity
    - File: Encoding preferences and file handling
    """
    
    def __init__(self, parent, config_manager: ConfigManager, theme_manager: ThemeManager):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent window
            config_manager: Configuration manager instance
            theme_manager: Theme manager instance
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        
        # Dialog setup
        self.title("Log Viewer Settings")
        self.geometry("600x500")
        self.resizable(True, True)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Center dialog on parent
        self._center_on_parent(parent)
        
        # Build the interface
        self._build_ui()
        
        # Load current settings
        self._load_current_settings()
        
        # Focus on dialog
        self.focus_set()
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _center_on_parent(self, parent):
        """Center the dialog on its parent window."""
        parent.update_idletasks()
        
        # Get parent position and size
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Get dialog size
        dialog_width = 600
        dialog_height = 500
        
        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # Ensure dialog is on screen
        x = max(0, x)
        y = max(0, y)
        
        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _build_ui(self):
        """Build the complete settings interface."""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create tabs
        self._create_display_tab()
        self._create_performance_tab()
        self._create_theme_tab()
        self._create_filter_tab()
        self._create_file_tab()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buttons
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self._reset_to_defaults).pack(side=tk.LEFT)
        
        # Spacer
        ttk.Frame(button_frame).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Action buttons
        ttk.Button(button_frame, text="Cancel", 
                  command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Apply", 
                  command=self._apply_settings).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="OK", 
                  command=self._on_ok).pack(side=tk.RIGHT, padx=(5, 0))
    
    def _create_display_tab(self):
        """Create the display settings tab."""
        display_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(display_frame, text="Display")
        
        # Font settings
        font_frame = ttk.LabelFrame(display_frame, text="Font Settings", padding="5")
        font_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(font_frame, text="Font Size:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.font_size_var = tk.IntVar()
        font_size_spin = ttk.Spinbox(font_frame, from_=8, to=24, textvariable=self.font_size_var, width=10)
        font_size_spin.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(font_frame, text="Font Family:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.font_family_var = tk.StringVar()
        font_family_combo = ttk.Combobox(font_frame, textvariable=self.font_family_var, 
                                        values=["Consolas", "Courier New", "Monaco", "DejaVu Sans Mono"], 
                                        width=15, state="readonly")
        font_family_combo.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Display options
        options_frame = ttk.LabelFrame(display_frame, text="Display Options", padding="5")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.show_line_numbers_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Show Line Numbers", 
                       variable=self.show_line_numbers_var).pack(anchor=tk.W)
        
        self.word_wrap_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Word Wrap", 
                       variable=self.word_wrap_var).pack(anchor=tk.W)
        
        self.auto_scroll_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Auto-scroll to End", 
                       variable=self.auto_scroll_var).pack(anchor=tk.W)
        
        # Icon settings
        icon_frame = ttk.LabelFrame(display_frame, text="Application Icon", padding="5")
        icon_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(icon_frame, text="Icon:").pack(anchor=tk.W)
        self.icon_var = tk.StringVar()
        icon_combo = ttk.Combobox(icon_frame, textvariable=self.icon_var, 
                                 values=["default.ico", "dark.ico", "light.ico", "sunset.ico"], 
                                 width=20, state="readonly")
        icon_combo.pack(anchor=tk.W, pady=(5, 0))
    
    def _create_performance_tab(self):
        """Create the performance settings tab."""
        perf_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(perf_frame, text="Performance")
        
        # Refresh settings
        refresh_frame = ttk.LabelFrame(perf_frame, text="Refresh Settings", padding="5")
        refresh_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(refresh_frame, text="Refresh Rate (ms):").pack(anchor=tk.W)
        self.refresh_rate_var = tk.IntVar()
        refresh_spin = ttk.Spinbox(refresh_frame, from_=100, to=5000, increment=100, 
                                 textvariable=self.refresh_rate_var, width=10)
        refresh_spin.pack(anchor=tk.W, pady=(5, 0))
        
        # Memory settings
        memory_frame = ttk.LabelFrame(perf_frame, text="Memory Management", padding="5")
        memory_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(memory_frame, text="Maximum Lines to Keep:").pack(anchor=tk.W)
        self.max_lines_var = tk.IntVar()
        max_lines_spin = ttk.Spinbox(memory_frame, from_=1000, to=200000, increment=1000, 
                                   textvariable=self.max_lines_var, width=10)
        max_lines_spin.pack(anchor=tk.W, pady=(5, 0))
        

    
    def _create_theme_tab(self):
        """Create the theme settings tab."""
        theme_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(theme_frame, text="Themes")
        
        # Theme selection
        selection_frame = ttk.LabelFrame(theme_frame, text="Theme Selection", padding="5")
        selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(selection_frame, text="Current Theme:").pack(anchor=tk.W)
        self.theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(selection_frame, textvariable=self.theme_var, 
                                  values=self.theme_manager.get_theme_display_names(), 
                                  width=20, state="readonly")
        theme_combo.pack(anchor=tk.W, pady=(5, 0))
        
        # Theme preview
        preview_frame = ttk.LabelFrame(theme_frame, text="Theme Preview", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_text = tk.Text(preview_frame, height=8, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Bind theme change to preview update
        theme_combo.bind('<<ComboboxSelected>>', self._update_theme_preview)
    
    def _create_filter_tab(self):
        """Create the filter settings tab."""
        filter_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(filter_frame, text="Filtering")
        
        # Default filter settings
        default_frame = ttk.LabelFrame(filter_frame, text="Default Filter Settings", padding="5")
        default_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(default_frame, text="Default Filter Mode:").pack(anchor=tk.W)
        self.default_filter_mode_var = tk.StringVar()
        filter_mode_combo = ttk.Combobox(default_frame, textvariable=self.default_filter_mode_var, 
                                        values=["Contains", "Starts With", "Ends With", "Regular Expression", "Exact Match", "Not Contains"], 
                                        width=20, state="readonly")
        filter_mode_combo.pack(anchor=tk.W, pady=(5, 0))
        
        # Filter options
        options_frame = ttk.LabelFrame(filter_frame, text="Filter Options", padding="5")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Case Sensitive by Default", 
                       variable=self.case_sensitive_var).pack(anchor=tk.W)
        
        self.remember_history_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Remember Filter History", 
                       variable=self.remember_history_var).pack(anchor=tk.W)
        
        ttk.Label(options_frame, text="Maximum History Items:").pack(anchor=tk.W, pady=(10, 0))
        self.max_history_var = tk.IntVar()
        history_spin = ttk.Spinbox(options_frame, from_=5, to=100, textvariable=self.max_history_var, width=10)
        history_spin.pack(anchor=tk.W, pady=(5, 0))
    
    def _create_file_tab(self):
        """Create the file handling settings tab."""
        file_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(file_frame, text="File Handling")
        
        # Encoding settings
        encoding_frame = ttk.LabelFrame(file_frame, text="File Encoding", padding="5")
        encoding_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_detect_encoding_var = tk.BooleanVar()
        ttk.Checkbutton(encoding_frame, text="Auto-detect File Encoding", 
                       variable=self.auto_detect_encoding_var).pack(anchor=tk.W)
        
        self.remember_encoding_var = tk.BooleanVar()
        ttk.Checkbutton(encoding_frame, text="Remember Encoding for Files", 
                       variable=self.remember_encoding_var).pack(anchor=tk.W)
        
        ttk.Label(encoding_frame, text="Default Encoding:").pack(anchor=tk.W, pady=(10, 0))
        self.default_encoding_var = tk.StringVar()
        encoding_combo = ttk.Combobox(encoding_frame, textvariable=self.default_encoding_var, 
                                     values=["auto", "utf-8", "utf-16-le", "utf-16-be", "latin-1"], 
                                     width=15, state="readonly")
        encoding_combo.pack(anchor=tk.W, pady=(5, 0))
        
        # File options
        file_options_frame = ttk.LabelFrame(file_frame, text="File Options", padding="5")
        file_options_frame.pack(fill=tk.X)
        
        self.remember_last_file_var = tk.BooleanVar()
        ttk.Checkbutton(file_options_frame, text="Remember Last Opened File", 
                       variable=self.remember_last_file_var).pack(anchor=tk.W)
        
        self.remember_last_directory_var = tk.BooleanVar()
        ttk.Checkbutton(file_options_frame, text="Remember Last Directory", 
                       variable=self.remember_last_directory_var).pack(anchor=tk.W)
    
    def _load_current_settings(self):
        """Load current settings from configuration manager."""
        # Display settings
        self.font_size_var.set(self.config_manager.get('display.font_size', 11))
        self.font_family_var.set(self.config_manager.get('display.font_family', 'Consolas'))
        self.show_line_numbers_var.set(self.config_manager.get('display.show_line_numbers', True))
        self.word_wrap_var.set(self.config_manager.get('display.word_wrap', False))
        self.auto_scroll_var.set(self.config_manager.get('display.auto_scroll', True))
        
        # Performance settings
        self.refresh_rate_var.set(self.config_manager.get('display.refresh_rate', 500))
        self.max_lines_var.set(self.config_manager.get('display.max_lines', 10000))
        
        # Theme settings
        current_theme = self.config_manager.get('theme.current', DEFAULT_THEME)
        theme_names = self.theme_manager.get_theme_names()
        if current_theme in theme_names:
            theme_index = theme_names.index(current_theme)
            self.theme_var.set(self.theme_manager.get_theme_display_names()[theme_index])
        
        # Filter settings
        self.default_filter_mode_var.set(self.config_manager.get('filter.default_mode', 'Contains'))
        self.case_sensitive_var.set(self.config_manager.get('filter.case_sensitive', False))
        self.remember_history_var.set(self.config_manager.get('filter.remember_history', True))
        self.max_history_var.set(self.config_manager.get('filter.max_history', 20))
        
        # File settings
        self.auto_detect_encoding_var.set(self.config_manager.get('file.auto_detect_encoding', True))
        self.remember_encoding_var.set(self.config_manager.get('file.remember_encoding', True))
        self.default_encoding_var.set(self.config_manager.get('file.default_encoding', 'auto'))
        self.remember_last_file_var.set(self.config_manager.get('file.remember_last_file', True))
        self.remember_last_directory_var.set(self.config_manager.get('file.remember_last_directory', True))
        
        # Update theme preview
        self._update_theme_preview()
        
        # Icon settings
        self.icon_var.set(self.config_manager.get('display.icon', 'default.ico'))
    
    def _update_theme_preview(self, event=None):
        """Update the theme preview text."""
        try:
            # Get selected theme
            theme_display_name = self.theme_var.get()
            theme_names = self.theme_manager.get_theme_display_names()
            
            if theme_display_name in theme_names:
                theme_index = theme_names.index(theme_display_name)
                theme_name = self.theme_manager.get_theme_names()[theme_index]
                theme = self.theme_manager.get_theme(theme_name)
                
                # Apply theme to preview
                self.preview_text.configure(
                    bg=theme["text_bg"],
                    fg=theme["text_fg"],
                    insertbackground=theme["insert_bg"]
                )
                
                # Sample text
                sample_text = f"""Theme Preview: {theme['name']}

This is a sample of how text will appear with the {theme['name']} theme.

Features:
• Background: {theme['text_bg']}
• Text: {theme['text_fg']}
• Cursor: {theme['insert_bg']}

The theme will be applied to the entire application when you click OK or Apply."""
                
                self.preview_text.delete('1.0', tk.END)
                self.preview_text.insert('1.0', sample_text)
        except Exception:
            pass
    

    
    def _reset_to_defaults(self):
        """Reset all settings to default values."""
        if messagebox.askyesno("Reset Settings", 
                              "Are you sure you want to reset all settings to default values?\n\n"
                              "This action cannot be undone."):
            self.config_manager.reset_to_defaults()
            self._load_current_settings()
            messagebox.showinfo("Settings Reset", "All settings have been reset to default values.")
    
    def _apply_settings(self):
        """Apply current settings to configuration."""
        try:
            # Save display settings
            self.config_manager.set('display.font_size', self.font_size_var.get())
            self.config_manager.set('display.font_family', self.font_family_var.get())
            self.config_manager.set('display.show_line_numbers', self.show_line_numbers_var.get())
            self.config_manager.set('display.word_wrap', self.word_wrap_var.get())
            self.config_manager.set('display.auto_scroll', self.auto_scroll_var.get())
            self.config_manager.set('display.icon', self.icon_var.get())
            
            # Save performance settings
            self.config_manager.set('display.refresh_rate', self.refresh_rate_var.get())
            self.config_manager.set('display.max_lines', self.max_lines_var.get())
            
            # Save theme settings
            theme_display_name = self.theme_var.get()
            theme_names = self.theme_manager.get_theme_display_names()
            if theme_display_name in theme_names:
                theme_index = theme_names.index(theme_display_name)
                theme_name = self.theme_manager.get_theme_names()[theme_index]
                self.config_manager.set('theme.current', theme_name)
            
            # Save filter settings
            self.config_manager.set('filter.default_mode', self.default_filter_mode_var.get())
            self.config_manager.set('filter.case_sensitive', self.case_sensitive_var.get())
            self.config_manager.set('filter.remember_history', self.remember_history_var.get())
            self.config_manager.set('filter.max_history', self.max_history_var.get())
            
            # Save file settings
            self.config_manager.set('file.auto_detect_encoding', self.auto_detect_encoding_var.get())
            self.config_manager.set('file.remember_encoding', self.remember_encoding_var.get())
            self.config_manager.set('file.default_encoding', self.default_encoding_var.get())
            self.config_manager.set('file.remember_last_file', self.remember_last_file_var.get())
            self.config_manager.set('file.remember_last_directory', self.remember_last_directory_var.get())
            
            # Save configuration
            self.config_manager.save_config()
            
            # Refresh the main window's UI to reflect the new settings immediately
            if hasattr(self.master, '_refresh_ui_from_config'):
                self.master._refresh_ui_from_config()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")
    
    def _on_ok(self):
        """Handle OK button click."""
        self._apply_settings()
        self.destroy()
    
    def _on_cancel(self):
        """Handle Cancel button click."""
        self.destroy()
