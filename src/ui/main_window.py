#!/usr/bin/env python3
"""
Main Window for the Log Viewer application.

Provides a comprehensive GUI for monitoring log files in real-time with
advanced filtering, multiple themes, and extensive customization options.
Built on Tkinter for cross-platform compatibility.
"""

import os
import sys
import time
import tkinter as tk
import collections
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from ..managers import ThemeManager, FilterManager, ConfigManager, FileManager
from ..utils.constants import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_AUTHOR,
    MAX_LINES_DEFAULT, DEFAULT_REFRESH_MS, DEFAULT_ENCODING, DEFAULT_THEME,
    FILTER_DEBOUNCE_MS, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
)
from .dialogs import SettingsDialog


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
        
        self.title(f"{APP_NAME} {APP_VERSION}")
        
        # Get saved window geometry and apply it
        saved_geometry = self.config_manager.get_window_geometry()
        print(f"Debug: Applying saved geometry: '{saved_geometry}'")
        self.geometry(saved_geometry)
        
        # Set minimum size after applying geometry
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
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
        self.file_manager = FileManager(path, encoding=encoding) if path else None
        
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
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
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
    
    def _load_theme_preference(self):
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
    
    def _set_app_icon(self):
        """
        Set the application icon based on the current theme.
        
        Attempts to load a theme-specific icon file and falls back
        to a default icon if the theme-specific one doesn't exist.
        """
        try:
            current_theme = self.theme_manager.current_theme
            icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", f"{current_theme}.ico")
            
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
            else:
                # Fallback to a generic icon if theme-specific one doesn't exist
                fallback_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "default.ico")
                if os.path.exists(fallback_path):
                    self.iconbitmap(fallback_path)
        except Exception:
            # Silently fail if icon setting fails
            pass
    
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
    
    def _open_path(self, path, first_open=False):
        """
        Open a log file for monitoring.
        
        Initializes the file manager and loads initial content if the file
        is small enough. Handles file opening errors gracefully.
        
        Args:
            path: Path to the log file to open
            first_open: Whether this is the first file opened in this session
        """
        self.path = path
        self.path_label.config(text=path)
        try:
            if not self.file_manager:
                self.file_manager = FileManager(path)
            self.file_manager.path = path

            # If small file (<2MB), show existing contents; else start tailing from end
            start_at_end = self.file_manager.should_start_at_end()
            self.file_manager.open(start_at_end=start_at_end)
            if not start_at_end:
                # Load initial chunk for small files
                text = self.file_manager.read_new_text()
                if text:
                    self._append(text)
            self._set_status("Opened")
        except Exception as e:
            messagebox.showerror("Error", "Failed to open file:\n{}".format(e))
            self._set_status("Open failed")
    
    def _poll(self):
        """
        Main polling loop for file updates.
        
        Checks for new content in the monitored file at regular intervals.
        Handles errors gracefully and reschedules itself for continuous monitoring.
        """
        try:
            if not self.paused.get() and self.file_manager and self.path:
                new_text = self.file_manager.read_new_text()
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
    
    def _set_status(self, msg):
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
    
    # File operations
    def _choose_file(self):
        """
        Open file dialog to choose a log file.
        
        Shows a file selection dialog and opens the selected file
        if the user makes a selection.
        """
        path = filedialog.askopenfilename(title="Choose log file")
        if path:
            self._open_path(path, first_open=True)
    
    # Filtering methods
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
            self._filter_job = self.after(FILTER_DEBOUNCE_MS, self._rebuild_view)
    
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
    
    # Display and UI methods
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
    
    # Theme methods
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
    
    def _show_theme_preview(self):
        """
        Show a preview of all available themes.
        
        Creates a preview window showing color samples for each
        theme with the ability to apply themes directly.
        """
        # For now, just show theme info - full preview will be implemented in dialogs
        self._show_theme_info()
    
    # Utility methods
    def _focus_filter(self):
        """
        Focus the filter entry box.
        
        Moves keyboard focus to the filter entry field and selects
        all text for easy replacement.
        """
        self.filter_entry.focus_set()
        self.filter_entry.select_range(0, tk.END)
    
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
    
    def _buffer_trim(self):
        """Ensure buffer keeps approximately the last N lines (N = max_lines)."""
        try:
            target = max(1000, int(self.max_lines.get() or MAX_LINES_DEFAULT))
        except Exception:
            target = MAX_LINES_DEFAULT
        # collections.deque with maxlen handles trimming automatically if maxlen is set.
        # Update maxlen dynamically to follow user control.
        if self._line_buffer.maxlen != target:
            tmp = collections.deque(self._line_buffer, maxlen=target)
            self._line_buffer = tmp
    
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
    
    # Settings and preferences methods
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
    
    def _show_settings(self):
        """Show the settings/preferences dialog."""
        SettingsDialog(self, self.config_manager, self.theme_manager)
    
    def _save_as_default(self):
        """Save current application state as default settings."""
        messagebox.showinfo("Save Defaults", "Save as default will be implemented in the next phase.")
    
    def _reset_settings(self):
        """Reset all settings to default values."""
        messagebox.showinfo("Reset Settings", "Reset settings will be implemented in the next phase.")
    
    def _export_settings(self):
        """Export current settings to a file."""
        messagebox.showinfo("Export Settings", "Export settings will be implemented in the next phase.")
    
    def _import_settings(self):
        """Import settings from a file."""
        messagebox.showinfo("Import Settings", "Import settings will be implemented in the next phase.")
    
    def _show_filter_help(self):
        """Show help information for the filtering system."""
        messagebox.showinfo("Filter Help", "Filter help will be implemented in the next phase.")
    
    def _show_keyboard_shortcuts(self):
        """Show available keyboard shortcuts."""
        shortcuts = """Keyboard Shortcuts:

File Operations:
• Ctrl+O - Open file
• Ctrl+Q - Quit application

View Controls:
• Ctrl+W - Toggle word wrap
• Ctrl+P - Pause/Resume monitoring
• Ctrl+L - Toggle line numbers

Filtering:
• Ctrl+F - Focus filter box
• Ctrl+R - Focus filter box (alternative)
• Escape - Clear current filter

Themes:
• Ctrl+T - Cycle through themes

Navigation:
• Mouse wheel - Scroll text
• Page Up/Down - Navigate content
• Home/End - Go to start/end"""
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def _show_about(self):
        """Show application information and version."""
        about_text = f"""{APP_NAME} {APP_VERSION}

{APP_DESCRIPTION}

Author: {APP_AUTHOR}

Features:
• Real-time log file monitoring
• Advanced filtering with 6 modes
• Multiple color themes
• Cross-platform compatibility
• No external dependencies

Built with Python and Tkinter
© 2024 Log Viewer Team"""
        
        messagebox.showinfo("About", about_text)
