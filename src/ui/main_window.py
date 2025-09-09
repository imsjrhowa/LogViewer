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

from src.managers import ThemeManager, FilterManager, ConfigManager, FileManager
from src.utils.constants import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_AUTHOR,
    DEFAULT_REFRESH_MS, DEFAULT_ENCODING, DEFAULT_THEME,
    FILTER_DEBOUNCE_MS, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    LINE_NUMBER_WIDTH, BUILD_NUMBER
)
from .dialogs import SettingsDialog, FileLoadingDialog


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
        
        self.title(f"{APP_NAME} {APP_VERSION} - Build {BUILD_NUMBER}")
        
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

        # Filtering variables
        self.filter_text = tk.StringVar(value="")
        self.case_sensitive = tk.BooleanVar(value=False)
        self.filter_mode = tk.StringVar(value="contains")
        self._filter_job = None  # Debounce handle for filter updates

        # Data storage for efficient filtering and display
        self._line_buffer = collections.deque()  # Raw lines storage - no size limit
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
        
        # Filter preferences are not loaded on startup - filter field starts empty
        
        # Apply initial theme to all UI elements
        self._apply_theme()
        
        # Force a theme refresh after window is fully initialized to ensure proper colors
        self.after(100, self._force_theme_refresh)
        
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
        
        # Start the heartbeat
        self._start_heartbeat()
        

        
        # Bind window close event to save configuration
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Bind window resize events to ensure toolbar remains visible
        self.bind('<Configure>', self._on_window_resize)

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
        # Only show themes that are fully available (have icon files)
        for theme_name in self.theme_manager.get_available_themes():
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
        settings_menu.add_command(label="Reset to Defaults", command=self._reset_settings)
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
        
        # Text selection and copy shortcuts
        self.bind('<Control-c>', lambda e: self._copy_selected_text())  # Copy selected text
        self.bind('<Control-C>', lambda e: self._copy_selected_text())  # Copy selected text (Shift)
        self.bind('<Control-a>', lambda e: self._select_all_text())     # Select all text
        self.bind('<Control-A>', lambda e: self._select_all_text())     # Select all text (Shift)

        # Create a multi-row toolbar container
        toolbar = ttk.Frame(self, padding=(8, 4))
        toolbar.pack(fill=tk.X)

        # Row 1: File path (left, expands) + Theme and Build (right)
        row1 = ttk.Frame(toolbar)
        row1.pack(fill=tk.X)

        left_section = ttk.Frame(row1)
        left_section.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File path display - make it expandable and responsive
        self.path_label = ttk.Label(left_section, text="No file selected")
        self.path_label.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)

        right_section = ttk.Frame(row1)
        right_section.pack(side=tk.RIGHT, padx=(8, 0))

        self.theme_label = ttk.Label(right_section, text="", width=15)
        self.theme_label.pack(side=tk.LEFT)

        # Theme preview button
        self.theme_preview_btn = ttk.Button(right_section, text="🎨", width=3, command=self._show_theme_preview)
        self.theme_preview_btn.pack(side=tk.LEFT, padx=(4, 0))


        # Row 2: Main controls (refresh, options, max lines, pause/clear)
        controls_row = ttk.Frame(toolbar)
        controls_row.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(controls_row, text="Refresh (ms)").pack(side=tk.LEFT)
        refresh_entry = ttk.Spinbox(controls_row, from_=100, to=5000, textvariable=self.refresh_ms, width=6)
        refresh_entry.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Checkbutton(controls_row, text="Auto-scroll", variable=self.autoscroll).pack(side=tk.LEFT)
        ttk.Checkbutton(controls_row, text="Wrap", variable=self.wrap, command=self._apply_wrap).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Checkbutton(controls_row, text="Line Numbers", variable=self.show_line_numbers, command=self._toggle_line_numbers).pack(side=tk.LEFT, padx=(8, 8))



        self.pause_btn = ttk.Button(controls_row, text="Pause", command=self._toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=(8, 4))

        # Row 3: Enhanced Filter controls
        filter_row = ttk.Frame(toolbar)
        filter_row.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(filter_row, text="Mode:").pack(side=tk.LEFT)
        self.filter_mode_combo = ttk.Combobox(filter_row, textvariable=self.filter_mode,
                                             values=self.filter_manager.get_mode_display_names(),
                                             width=10, state="readonly")
        self.filter_mode_combo.pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(filter_row, text="Filter:").pack(side=tk.LEFT, padx=(8, 4))

        filter_entry_frame = ttk.Frame(filter_row)
        filter_entry_frame.pack(side=tk.LEFT)

        self.filter_entry = ttk.Entry(filter_entry_frame, textvariable=self.filter_text, width=20)
        self.filter_entry.pack(side=tk.LEFT)

        self.filter_history_btn = ttk.Button(filter_entry_frame, text="▼", width=2,
                                           command=self._show_filter_history)
        self.filter_history_btn.pack(side=tk.LEFT)

        filter_controls_frame = ttk.Frame(filter_row)
        filter_controls_frame.pack(side=tk.LEFT, padx=(4, 0))

        self.case_sensitive_cb = ttk.Checkbutton(filter_controls_frame, text="Case",
                                                variable=self.case_sensitive,
                                                command=self._on_filter_change)
        self.case_sensitive_cb.pack(side=tk.LEFT)

        self.clear_filter_btn = ttk.Button(filter_controls_frame, text="✕", width=3,
                                         command=self._clear_filter)
        self.clear_filter_btn.pack(side=tk.LEFT, padx=(4, 0))

        self.filter_info_btn = ttk.Button(filter_controls_frame, text="ℹ", width=3,
                                        command=self._show_filter_info)
        self.filter_info_btn.pack(side=tk.LEFT, padx=(2, 0))

        self.filter_status_label = ttk.Label(filter_controls_frame, text="", width=8)
        self.filter_status_label.pack(side=tk.LEFT, padx=(4, 0))
        
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
            width=LINE_NUMBER_WIDTH,    # Fixed width for line numbers
            padx=3,                     # Left and right padding for better spacing
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
            font=("Consolas", 11),      # Monospace font for log readability
            selectbackground="#0078d4",  # Blue selection background
            selectforeground="white",    # White selection text
            exportselection=True,        # Enable text selection and copying
            state=tk.NORMAL              # Allow text selection (not DISABLED)
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
        
        # Bind right-click context menu for text operations
        self.text.bind('<Button-3>', self._show_text_context_menu)  # Right-click context menu
        self.text.bind('<Control-Button-1>', self._show_text_context_menu)  # Ctrl+click context menu
        
        # Bind scrollbar to update line numbers
        yscroll.config(command=lambda *args: self._on_yscroll(*args))

        # Status bar for information display
        self.status = ttk.Label(self, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X)
        
        # Apply initial theme colors to status bar immediately
        self._apply_initial_theme_colors()
        
        # Heartbeat variables
        self._heartbeat_active = True
        self._heartbeat_state = "active"  # active, paused, error
        self._heartbeat_chars = {
            "active": ["💓", "💗", "💓", "💗"],
            "paused": ["⏸️", "⏸️", "⏸️", "⏸️"],
            "error": ["⚠️", "⚠️", "⚠️", "⚠️"]
        }
        self._heartbeat_index = 0
        self._heartbeat_interval = 1000  # 1 second
        
        # Initialize base status text
        self._base_status_text = "Ready"
    
    def _apply_initial_theme_colors(self):
        """Apply initial theme colors to status bar and other critical UI elements."""
        try:
            # Get the current theme from theme manager
            theme = self.theme_manager.get_current_theme()
            
            # Apply theme colors to status bar immediately
            self.status.configure(
                background=theme["status_bg"],
                foreground=theme["status_fg"]
            )
            
            # Also apply to main window background
            self.configure(bg=theme["bg"])
            
        except Exception:
            # Silently fail if theme colors can't be applied initially
            pass
    
    def _force_theme_refresh(self):
        """Force a theme refresh to ensure all colors are properly applied."""
        try:
            # Get current theme and reapply critical colors
            theme = self.theme_manager.get_current_theme()
            
            # Ensure status bar has correct colors
            self.status.configure(
                background=theme["status_bg"],
                foreground=theme["status_fg"]
            )
            
            # Ensure main window background is correct
            self.configure(bg=theme["bg"])
            
            # Force update to ensure colors are applied
            self.update_idletasks()
            
        except Exception:
            # Silently fail if theme refresh can't be applied
            pass
    
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
    
    def _on_window_resize(self, event):
        """
        Handle window resize events to ensure toolbar remains visible.
        
        Args:
            event: Tkinter configure event
        """
        # Only handle main window resize events (not child widget events)
        if event.widget == self:
            # Force update of toolbar layout
            self.update_idletasks()
            
            # Ensure minimum window width to keep toolbar visible
            min_width = 800  # Minimum width to show essential controls
            if event.width < min_width:
                # Don't allow window to be smaller than minimum
                self.geometry(f"{min_width}x{event.height}")
    
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
        Set the application icon based on user preference.
        
        Uses the icon selected in settings, with fallback to default icon.
        """
        try:
            # Get user's preferred icon from configuration
            preferred_icon = self.config_manager.get('display.icon', 'default.ico')
            
            # Build path to the preferred icon
            icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", preferred_icon)
            
            # Try to use preferred icon
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                return
            
            # Fallback to default icon if preferred doesn't exist
            fallback_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "default.ico")
            if os.path.exists(fallback_path):
                self.iconbitmap(fallback_path)
        except Exception:
            # Silently fail if icon setting fails
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
        
        # Ensure status bar colors are properly set and not overridden
        self.update_idletasks()
        
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
        
        # Reconfigure highlight tags for new theme
        if hasattr(self, '_highlight_tag_configured'):
            self._configure_highlight_tags()
        
        # Save theme preference
        self._save_theme_preference()
    
    def _open_path(self, path, first_open=False):
        """
        Open a log file for monitoring.
        
        Always reads the entire file initially, then starts monitoring for updates.
        Uses chunked reading for large files to manage memory efficiently.
        
        Args:
            path: Path to log file to open
            first_open: Whether this is the first file opened in this session
        """
        self.path = path
        self.path_label.config(text=path)
        
        # Check file size to determine if we need a loading dialog
        try:
            file_size = os.path.getsize(path)
            show_loading = file_size > 1024 * 1024  # Show loading for files > 1MB
        except OSError:
            show_loading = False
            file_size = 0
        
        loading_dialog = None
        if show_loading:
            filename = os.path.basename(path)
            loading_dialog = FileLoadingDialog(self, filename)
            loading_dialog.set_file_size(file_size)
            loading_dialog.update_message(f"Opening {filename}...")
            self.update_idletasks()
        
        try:
            if not self.file_manager:
                self.file_manager = FileManager(path)
                # Set up truncation callback for automatic file reloading
                self.file_manager.set_truncation_callback(self._handle_file_truncation)
            else:
                # Force re-detection of encoding for the file (even if same path)
                self.file_manager.force_encoding_detection()
            self.file_manager.path = path

            # Always read the entire file initially
            self._set_status("Loading file...")
            self.update()  # Force UI update to show loading status
            
            # Clear existing content and line buffer when opening a new file
            if not first_open:
                self._clear_current_view()
            
            # Read entire file with chunked reading for large files
            if loading_dialog:
                # Create progress callback for the loading dialog
                def progress_callback(progress, message):
                    loading_dialog.update_progress(progress, message)
                    self.update_idletasks()
                
                text = self.file_manager.read_entire_file(progress_callback=progress_callback)
            else:
                text = self.file_manager.read_entire_file()
            
            if text:
                # For new files, use _load_file_content instead of _append
                if not first_open:
                    self._load_file_content(text)
                else:
                    self._append(text)
                                
                self._set_heartbeat_state("active")
                self._set_status(f"File loaded ({len(text.splitlines()):,} lines)")
            else:
                self._set_heartbeat_state("active")
                self._set_status("File opened (empty)")
                
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            messagebox.showerror("Error", "Failed to open file:\n{}".format(e))
            self._set_heartbeat_state("error")
            self._set_status("Open failed")
        finally:
            # Always close the loading dialog
            if loading_dialog:
                loading_dialog.close()
    
    def _handle_file_truncation(self):
        """
        Handle file truncation events.
        
        Called when the monitored file becomes significantly smaller,
        indicating it was cleared or rotated. Automatically reloads the file.
        """
        try:
            if self.path and self.file_manager:
                self._set_status("File truncated - reloading...")
                self._set_heartbeat_state("active")
                
                # Clear current view and reload file
                self._clear_current_view()
                
                # Read entire file again
                text = self.file_manager.read_entire_file()
                if text:
                    self._load_file_content(text)
                    self._set_status(f"File reloaded after truncation ({len(text.splitlines()):,} lines)")
                else:
                    self._set_status("File reloaded (empty after truncation)")
                    
        except Exception as e:
            self._set_heartbeat_state("error")
            self._set_status(f"Error reloading truncated file: {e}")
    
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
                    self._set_heartbeat_state("active")
                    self._set_status("Updated")
        except Exception as e:
            # Non-fatal: show in status bar, keep polling
            self._set_heartbeat_state("error")
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
        
        # Store the base status text for heartbeat to use
        self._base_status_text = base
        
        # Update status (heartbeat will add its indicator)
        self.status.config(text=base)
    
    def _start_heartbeat(self):
        """Start the heartbeat animation to show application activity."""
        if self._heartbeat_active:
            self._update_heartbeat()
    
    def _update_heartbeat(self):
        """Update the heartbeat indicator in the status bar."""
        if not self._heartbeat_active:
            return
            
        try:
            # Get appropriate heartbeat character for current state
            heartbeat_chars = self._heartbeat_chars[self._heartbeat_state]
            heartbeat_char = heartbeat_chars[self._heartbeat_index]
            
            # Get the base status text (without heartbeat)
            base_status = self._get_base_status_text()
            
            # Create status with heartbeat at fixed position (right side)
            # Limit base status length to prevent overflow
            max_base_length = 80  # Leave room for heartbeat indicator
            if len(base_status) > max_base_length:
                base_status = base_status[:max_base_length-3] + "..."
            
            # Format: [Time] Status | State Heartbeat
            status_text = f"{base_status} | {self._heartbeat_state.title()} {heartbeat_char}"
            
            # Update status with heartbeat
            self.status.config(text=status_text)
            
            # Cycle to next heartbeat character
            self._heartbeat_index = (self._heartbeat_index + 1) % len(heartbeat_chars)
            
            # Schedule next heartbeat update
            self.after(self._heartbeat_interval, self._update_heartbeat)
            
        except Exception:
            # Silently fail to avoid breaking the main functionality
            pass
    
    def _get_base_status_text(self):
        """Get the base status text without heartbeat indicators."""
        try:
            # Use stored base status text if available
            if hasattr(self, '_base_status_text'):
                return self._base_status_text
            
            # Fallback: get current status text and clean it
            current_text = self.status.cget("text")
            
            # Remove any existing heartbeat indicators and separator
            for indicator in ["💓", "💗", "⏸️", "⚠️"]:
                current_text = current_text.replace(indicator, "")
            
            # Remove the separator and state text
            if " | " in current_text:
                current_text = current_text.split(" | ")[0]
            
            return current_text.strip()
        except Exception:
            return ""
    
    def _stop_heartbeat(self):
        """Stop the heartbeat animation."""
        self._heartbeat_active = False
    
    def _set_heartbeat_state(self, state: str):
        """
        Set the heartbeat state to show different application statuses.
        
        Args:
            state: One of "active", "paused", or "error"
        """
        if state in self._heartbeat_chars:
            self._heartbeat_state = state
            # Reset index for smooth transition
            self._heartbeat_index = 0
            
            # Update status bar color based on state (if supported)
            try:
                if state == "error":
                    self.status.configure(foreground="red")
                elif state == "paused":
                    self.status.configure(foreground="orange")
                else:  # active - restore theme foreground color
                    theme = self.theme_manager.get_current_theme()
                    self.status.configure(foreground=theme["status_fg"])
            except Exception:
                # Silently fail if color change is not supported
                pass
    
    # File operations
    def _choose_file(self):
        """
        Open file dialog to choose a log file.
        
        Shows a file selection dialog and opens the selected file
        if the user makes a selection.
        """
        path = filedialog.askopenfilename(title="Choose log file")
        if path:
            self._open_path(path, first_open=False)
    
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
        
        filter_text = self.filter_text.get()
        
        if self.filter_manager.set_filter(
            filter_text, 
            mode_name, 
            self.case_sensitive.get()
        ):
            # Update filter status indicator
            self._update_filter_status()
            
            # Clear old highlighting when filter changes
            self._clear_highlighting()
            
            # Debounce rapid typing; rebuild shortly after user stops
            if self._filter_job is not None:
                try:
                    self.after_cancel(self._filter_job)
                except Exception:
                    pass
            self._filter_job = self.after(FILTER_DEBOUNCE_MS, self._rebuild_view)
            
            # If there's no filter text, clear highlighting immediately
            if not filter_text:
                self._clear_highlighting()
            else:
                # For immediate feedback, apply highlighting to current content
                self.after(50, self._refresh_highlighting)
    
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
        restores the original unfiltered view.
        """
        self.filter_text.set("")
        self.filter_manager.clear_filter()
        self._filtered_lines = []  # Clear filtered lines when filter is cleared
        
        # Clear all highlighting tags
        self._clear_highlighting()
        
        # Restore original unfiltered view
        self._restore_original_view()
        self._set_status("Filter cleared")
    
    def _clear_current_view(self):
        """
        Clear the current view and reset all buffers.
        
        Used when opening a new file to ensure clean state.
        """
        # Clear text widget
        self.text.delete('1.0', tk.END)
        
        # Clear all buffers
        self._line_buffer.clear()
        self._filtered_lines = []
        
        # Clear any active filters
        self.filter_text.set("")
        self.filter_manager.clear_filter()
        
        # Clear highlighting
        self._clear_highlighting()
        
        # Update line numbers
        self._update_line_numbers()
    
    def _rebuild_view(self):
        """
        Re-render the text widget from the buffered lines using the current filter.
        
        This method efficiently rebuilds the display by applying the current
        filter to all stored lines, maintaining original line numbers for
        accurate reference.
        """
        try:
            # If no active filter, restore original view
            if not self.filter_manager.current_filter:
                self._restore_original_view()
                return
            
            # Ensure text widget is in normal state for editing
            self.text.config(state=tk.NORMAL)
            
            # Clear current display
            self.text.delete('1.0', tk.END)
            at_end = True
            matched_count = 0
            total_count = len(self._line_buffer)
            
            # Store filtered lines with their original line numbers
            self._filtered_lines = []
            
            # First, collect all matching lines
            matching_lines = []
            for i, line in enumerate(self._line_buffer, 1):
                if self.filter_manager.matches(line):
                    matching_lines.append((i, line))
                    matched_count += 1
            
            # Then insert all matching lines at once
            for i, line in matching_lines:
                self.text.insert(tk.END, line)
                self._filtered_lines.append((i, line))
            
            # Now apply highlighting to the complete filtered content
            if matching_lines:
                self._highlight_all_filter_matches()
                
            # Force update to ensure highlighting is applied
            self.text.update_idletasks()
            
            # Ensure highlighting is applied even if the above didn't work
            if matching_lines:
                self.after(100, self._refresh_highlighting)
            
            # Auto-scroll if configured and we were at the end
            if self.autoscroll.get() and at_end:
                self.text.see(tk.END)
            
            # Update status with filter information
            if self.filter_manager.last_error:
                self._set_status(f"Filter error: {self.filter_manager.last_error}")
            else:
                self._set_status(f"Filtered: {matched_count}/{total_count} lines")
            
            # Update line numbers after rebuilding view
            self._update_line_numbers()
                
        except Exception as e:
            self._set_status("Filter error: {}".format(e))
    
    def _restore_original_view(self):
        """
        Restore the original unfiltered view with all content.
        
        This method properly restores the original log view when filters are cleared,
        ensuring line numbers and content are correctly aligned.
        """
        try:
            # Ensure text widget is in normal state for editing
            self.text.config(state=tk.NORMAL)
            
            # Clear current display
            self.text.delete('1.0', tk.END)
            
            # Clear filtered lines tracking
            self._filtered_lines = []
            
            # Insert all original lines from buffer
            for line in self._line_buffer:
                self.text.insert(tk.END, line)
            
            # Force update to ensure content is displayed
            self.text.update_idletasks()
            
            # Auto-scroll if configured
            if self.autoscroll.get():
                self.text.see(tk.END)
            
            # Update line numbers for unfiltered content
            self._update_line_numbers()
            
            # Update status
            total_count = len(self._line_buffer)
            self._set_status(f"Showing all {total_count} lines")
            
        except Exception as e:
            self._set_status(f"Error restoring view: {e}")
    
    def _highlight_filter_matches(self, start_pos, end_pos, line_content):
        """
        Highlight text that matches the current filter in the specified range.
        
        Args:
            start_pos: Starting position in the text widget
            end_pos: Ending position in the text widget
            line_content: The content of the line to highlight
        """
        try:
            if not self.filter_manager.current_filter:
                return
                
            filter_text = self.filter_manager.current_filter
            filter_mode = self.filter_manager.current_mode
            case_sensitive = self.filter_manager.case_sensitive
            
            # Configure highlight tag if not already configured
            if not hasattr(self, '_highlight_tag_configured'):
                self._configure_highlight_tags()
                self._highlight_tag_configured = True
            
            # Find and highlight matches based on filter mode
            if filter_mode == "contains":
                self._highlight_contains_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
            elif filter_mode == "starts_with":
                self._highlight_starts_with_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
            elif filter_mode == "ends_with":
                self._highlight_ends_with_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
            elif filter_mode == "exact":
                self._highlight_exact_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
            elif filter_mode == "regex":
                self._highlight_regex_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
            # Note: "not_contains" mode doesn't need highlighting since it shows non-matching lines
            
        except Exception:
            # Silently fail highlighting to avoid breaking the main functionality
            pass
    
    def _highlight_all_filter_matches(self):
        """
        Highlight all filter matches in the currently displayed filtered content.
        This method is called after all filtered lines have been inserted.
        """
        try:
            if not self.filter_manager.current_filter:
                return
                
            filter_text = self.filter_manager.current_filter
            filter_mode = self.filter_manager.current_mode
            case_sensitive = self.filter_manager.case_sensitive
            
            # Configure highlight tag if not already configured
            if not hasattr(self, '_highlight_tag_configured'):
                self._configure_highlight_tags()
                self._highlight_tag_configured = True
            
            # Get the complete text content that's currently displayed
            displayed_text = self.text.get('1.0', 'end-1c')
            if not displayed_text:
                return
            
            # Find and highlight matches based on filter mode
            if filter_mode == "contains":
                self._highlight_contains_matches_in_text(displayed_text, filter_text, case_sensitive)
            elif filter_mode == "starts_with":
                self._highlight_starts_with_matches_in_text(displayed_text, filter_text, case_sensitive)
            elif filter_mode == "ends_with":
                self._highlight_ends_with_matches_in_text(displayed_text, filter_text, case_sensitive)
            elif filter_mode == "exact":
                self._highlight_exact_matches_in_text(displayed_text, filter_text, case_sensitive)
            elif filter_mode == "regex":
                self._highlight_regex_matches_in_text(displayed_text, filter_text, case_sensitive)
            # Note: "not_contains" mode doesn't need highlighting since it shows non-matching lines
            
        except Exception:
            # Silently fail highlighting to avoid breaking the main functionality
            pass
    
    def _configure_highlight_tags(self):
        """Configure text highlighting tags with theme-appropriate colors."""
        # Remove existing tags to avoid conflicts
        for tag in self.text.tag_names():
            if tag.startswith('filter_highlight'):
                self.text.tag_delete(tag)
        
        # Get current theme's highlight colors
        theme = self.theme_manager.get_current_theme()
        highlight_bg = theme.get('highlight_bg', '#ffeb3b')  # Fallback to yellow
        highlight_fg = theme.get('highlight_fg', '#000000')  # Fallback to black
        
        # Create single highlight tag with theme colors
        self.text.tag_configure('filter_highlight', 
                               background=highlight_bg, 
                               foreground=highlight_fg,
                               relief='raised',
                               borderwidth=1)
        # Raise the tag priority to ensure it's visible over other tags
        self.text.tag_raise('filter_highlight')


    
    def _highlight_contains_matches_in_text(self, displayed_text, filter_text, case_sensitive):
        """Highlight all occurrences of the filter text in the displayed text."""
        if not filter_text:
            return
        
        # Use the text widget's search to find all occurrences
        search_start = "1.0"
        tag_index = 0
        
        while True:
            # Search for the filter text in the entire text widget
            found_pos = self.text.search(filter_text, search_start, "end", nocase=not case_sensitive)
            if not found_pos:
                break
                
            # Calculate end position
            found_end = self.text.index(f"{found_pos}+{len(filter_text)}c")
            
            # Apply highlighting tag
            self.text.tag_add('filter_highlight', found_pos, found_end)
            
            # Move to next position to avoid infinite loop
            search_start = self.text.index(f"{found_pos}+1c")
            tag_index += 1
            
            # Safety break to avoid infinite loops
            if tag_index > 100:
                break
    
    def _highlight_starts_with_matches_in_text(self, displayed_text, filter_text, case_sensitive):
        """Highlight lines that start with the filter text."""
        if not filter_text:
            return
        
        # Split displayed text into lines and find matches
        lines = displayed_text.splitlines()
        tag_index = 0
        
        for i, line in enumerate(lines):
            if case_sensitive:
                if line.startswith(filter_text):
                    line_start = f"{i+1}.0"
                    line_end = f"{i+1}.{len(filter_text)}"
                    tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
                    self.text.tag_add(tag_name, line_start, line_end)
                    tag_index += 1
            else:
                if line.lower().startswith(filter_text.lower()):
                    line_start = f"{i+1}.0"
                    line_end = f"{i+1}.{len(filter_text)}"
                    tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
                    self.text.tag_add(tag_name, line_start, line_end)
                    tag_index += 1
    
    def _highlight_ends_with_matches_in_text(self, displayed_text, filter_text, case_sensitive):
        """Highlight lines that end with the filter text."""
        if not filter_text:
            return
        
        # Split displayed text into lines and find matches
        lines = displayed_text.splitlines()
        tag_index = 0
        
        for i, line in enumerate(lines):
            if case_sensitive:
                if line.endswith(filter_text):
                    line_start = f"{i+1}.{len(line) - len(filter_text)}"
                    line_end = f"{i+1}.end"
                    tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
                    self.text.tag_add(tag_name, line_start, line_end)
                    tag_index += 1
            else:
                if line.lower().endswith(filter_text.lower()):
                    line_start = f"{i+1}.{len(line) - len(filter_text)}"
                    line_end = f"{i+1}.end"
                    tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
                    self.text.tag_add(tag_name, line_start, line_end)
                    tag_index += 1
    
    def _highlight_exact_matches_in_text(self, displayed_text, filter_text, case_sensitive):
        """Highlight lines that exactly match the filter text."""
        if not filter_text:
            return
        
        # Split displayed text into lines and find matches
        lines = displayed_text.splitlines()
        tag_index = 0
        
        for i, line in enumerate(lines):
            if case_sensitive:
                if line.rstrip() == filter_text:
                    line_start = f"{i+1}.0"
                    line_end = f"{i+1}.end"
                    tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
                    self.text.tag_add(tag_name, line_start, line_end)
                    tag_index += 1
            else:
                if line.rstrip().lower() == filter_text.lower():
                    line_start = f"{i+1}.0"
                    line_end = f"{i+1}.end"
                    tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
                    self.text.tag_add(tag_name, line_start, line_end)
                    tag_index += 1
    
    def _highlight_regex_matches_in_text(self, displayed_text, filter_text, case_sensitive):
        """Highlight regex pattern matches in the displayed text."""
        if not filter_text:
            return
        
        try:
            import re
            flags = 0 if case_sensitive else re.IGNORECASE
            
            # Split displayed text into lines and find matches
            lines = displayed_text.splitlines()
            tag_index = 0
            
            for i, line in enumerate(lines):
                pattern = re.compile(filter_text, flags)
                matches = list(pattern.finditer(line))
                
                for match in matches:
                    line_start = f"{i+1}.{match.start()}"
                    line_end = f"{i+1}.{match.end()}"
                    tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
                    self.text.tag_add(tag_name, line_start, line_end)
                    tag_index += 1
                    
        except Exception:
            # If regex compilation fails, fall back to contains highlighting
            self._highlight_contains_matches_in_text(displayed_text, filter_text, case_sensitive)
    
    def _highlight_contains_matches(self, start_pos, end_pos, line_content, filter_text, case_sensitive):
        """Highlight all occurrences of the filter text in the line."""
        if not filter_text:
            return
        
        # Use the text widget's search to find all occurrences
        search_start = "1.0"
        tag_index = 0
        
        while True:
            # Search for the filter text in the entire text widget
            found_pos = self.text.search(filter_text, search_start, "end", nocase=not case_sensitive)
            if not found_pos:
                break
                
            # Calculate end position
            found_end = self.text.index(f"{found_pos}+{len(filter_text)}c")
            
            # Apply highlighting tag
            tag_name = f'filter_highlight_{(tag_index % 5) + 1}'
            self.text.tag_add(tag_name, found_pos, found_end)
            
            # Move to next position to avoid infinite loop
            search_start = self.text.index(f"{found_end}+1c")
            tag_index += 1
            
            # Safety break to avoid infinite loops
            if tag_index > 100:
                break
    
    def _highlight_starts_with_matches(self, start_pos, end_pos, line_content, filter_text, case_sensitive):
        """Highlight the beginning of the line if it starts with the filter text."""
        if not filter_text:
            return
            
        if case_sensitive:
            if line_content.startswith(filter_text):
                line_start = start_pos
                line_end = self.text.index(f"{start_pos}+{len(filter_text)}c")
                self.text.tag_add('filter_highlight', line_start, line_end)
        else:
            if line_content.lower().startswith(filter_text.lower()):
                line_start = start_pos
                line_end = self.text.index(f"{start_pos}+{len(filter_text)}c")
                self.text.tag_add('filter_highlight', line_start, line_end)
    
    def _highlight_ends_with_matches(self, start_pos, end_pos, line_content, filter_text, case_sensitive):
        """Highlight the end of the line if it ends with the filter text."""
        if not filter_text:
            return
            
        if case_sensitive:
            if line_content.endswith(filter_text):
                line_start = self.text.index(f"{end_pos}-{len(filter_text)}c")
                line_end = end_pos
                self.text.tag_add('filter_highlight', line_start, line_end)
        else:
            if line_content.lower().endswith(filter_text.lower()):
                line_start = self.text.index(f"{end_pos}-{len(filter_text)}c")
                line_end = end_pos
                self.text.tag_add('filter_highlight', line_start, line_end)
    
    def _highlight_exact_matches(self, start_pos, end_pos, line_content, filter_text, case_sensitive):
        """Highlight the entire line if it exactly matches the filter text."""
        if not filter_text:
            return
            
        if case_sensitive:
            if line_content.rstrip() == filter_text:
                self.text.tag_add('filter_highlight', start_pos, end_pos)
        else:
            if line_content.rstrip().lower() == filter_text.lower():
                self.text.tag_add('filter_highlight', start_pos, end_pos)
    
    def _highlight_regex_matches(self, start_pos, end_pos, line_content, filter_text, case_sensitive):
        """Highlight regex pattern matches in the line."""
        if not filter_text:
            return
            
        try:
            import re
            flags = 0 if case_sensitive else re.IGNORECASE
            
            # Find all matches of the regex pattern
            pattern = re.compile(filter_text, flags)
            matches = list(pattern.finditer(line_content))
            
            tag_index = 0
            for match in matches:
                # Calculate positions in the text widget
                line_start = self.text.index(f"{start_pos}+{match.start()}c")
                line_end = self.text.index(f"{line_start}+{match.end() - match.start()}c")
                
                # Apply highlighting tag
                self.text.tag_add('filter_highlight', line_start, line_end)
                tag_index += 1
                
        except Exception:
            # If regex compilation fails, fall back to contains highlighting
            self._highlight_contains_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
    
    def _clear_highlighting(self):
        """Clear all highlighting tags from the text widget."""
        try:
            # Remove the single highlight tag from all ranges but keep the configuration
            self.text.tag_remove('filter_highlight', '1.0', 'end')
        except Exception:
            pass  # Silently fail to avoid breaking functionality
    
    def _refresh_highlighting(self):
        """Refresh highlighting for the current filter on the displayed content."""
        try:
            if self.filter_manager.current_filter:
                # Clear existing highlighting first
                self._clear_highlighting()
                # Reapply highlighting to current content
                self._highlight_all_filter_matches()
                # Force update to ensure highlighting is visible
                self.text.update_idletasks()
        except Exception:
            pass  # Silently fail to avoid breaking functionality
    
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
        
        # Update heartbeat state based on pause status
        if self.paused.get():
            self._set_heartbeat_state("paused")
            self._set_status("Paused")
        else:
            self._set_heartbeat_state("active")
            self._set_status("Running")
    

    
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
                    # Right-justify line numbers with proper formatting
                    # Use LINE_NUMBER_WIDTH - 1 to account for the newline character
                    formatted_line = f"{original_line_num:>{LINE_NUMBER_WIDTH - 1}}\n"
                    self.line_numbers.insert(tk.END, formatted_line)
                
                self.line_numbers.config(state=tk.DISABLED)
            else:
                # Show sequential line numbers for unfiltered content
                lines = self.text.get('1.0', tk.END).count('\n')
                
                self.line_numbers.config(state=tk.NORMAL)
                self.line_numbers.delete('1.0', tk.END)
                
                for i in range(1, lines + 1):
                    # Right-justify line numbers with proper formatting
                    # Use LINE_NUMBER_WIDTH - 1 to account for the newline character
                    formatted_line = f"{i:>{LINE_NUMBER_WIDTH - 1}}\n"
                    self.line_numbers.insert(tk.END, formatted_line)
                
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
        Ctrl+T keyboard shortcut. Only cycles through fully supported themes.
        """
        themes = self.theme_manager.get_available_themes()
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
        # Show all available themes
        available_themes = self.theme_manager.get_available_themes()
        for theme_name in available_themes:
            theme = self.theme_manager.get_theme(theme_name)
            current = " (Current)" if theme_name == self.theme_manager.current_theme else ""
            info += f"• {theme['name']}{current}\n"
        
        info += "\nNote: Icon can be customized in Settings → Display → Application Icon.\n"
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
    
    def _copy_selected_text(self):
        """
        Copy selected text to clipboard.
        
        Copies the currently selected text in the log viewer to the system clipboard.
        If no text is selected, shows a status message.
        """
        try:
            # Check if there's any text selected
            if self.text.tag_ranges(tk.SEL):
                # Get the selected text
                selected_text = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
                
                # Copy to clipboard
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                
                # Show confirmation in status bar
                char_count = len(selected_text)
                line_count = selected_text.count('\n') + 1
                self._set_status(f"Copied {char_count} characters ({line_count} lines) to clipboard")
            else:
                self._set_status("No text selected")
        except Exception as e:
            self._set_status(f"Copy failed: {e}")
    
    def _select_all_text(self):
        """
        Select all text in the log viewer.
        
        Selects all visible text in the main text widget for easy copying.
        """
        try:
            # Focus the text widget first
            self.text.focus_set()
            
            # Select all text
            self.text.tag_add(tk.SEL, "1.0", tk.END)
            self.text.mark_set(tk.INSERT, tk.END)
            self.text.see(tk.INSERT)
            
            # Show confirmation in status bar
            total_chars = len(self.text.get("1.0", tk.END))
            total_lines = int(self.text.index('end-1c').split('.')[0])
            self._set_status(f"Selected all text ({total_chars} characters, {total_lines} lines)")
        except Exception as e:
            self._set_status(f"Select all failed: {e}")
    
    def _show_text_context_menu(self, event):
        """
        Show context menu for text operations.
        
        Displays a right-click context menu with copy, select all, and other text operations.
        
        Args:
            event: Mouse event that triggered the context menu
        """
        try:
            # Create context menu
            context_menu = tk.Menu(self, tearoff=0)
            
            # Add menu items
            context_menu.add_command(label="Copy", command=self._copy_selected_text)
            context_menu.add_separator()
            context_menu.add_command(label="Select All", command=self._select_all_text)
            context_menu.add_separator()
            context_menu.add_command(label="Clear Selection", command=self._clear_selection)
            
            # Show menu at cursor position
            context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            self._set_status(f"Context menu failed: {e}")
    
    def _clear_selection(self):
        """
        Clear current text selection.
        
        Removes any current text selection in the main text widget.
        """
        try:
            # Clear selection by moving cursor to current position
            self.text.tag_remove(tk.SEL, "1.0", tk.END)
            self.text.mark_set(tk.INSERT, tk.INSERT)
            self._set_status("Selection cleared")
        except Exception as e:
            self._set_status(f"Clear selection failed: {e}")
    
    def _load_file_content(self, s: str):
        """
        Load file content into the display, bypassing filters.
        
        Used when opening a new file to load all content without filtering.
        
        Args:
            s: File content to load
        """
        # Ensure text widget is in normal state for editing
        self.text.config(state=tk.NORMAL)
        
        # Clear existing content first
        self.text.delete('1.0', tk.END)
        self._line_buffer.clear()
        self._filtered_lines = []
        
        # Insert the entire content at once to preserve formatting
        self.text.insert('1.0', s)
        
        # Make text widget read-only but allow selection
        self.text.config(state=tk.NORMAL)
        
        # Break content into lines and store in buffer (for filtering later)
        lines = s.splitlines(True)  # keep line endings
        if lines:
            self._line_buffer.extend(lines)
        
        # Auto-scroll to end if configured
        if self.autoscroll.get():
            self.text.see(tk.END)
        
        # Update line numbers
        self._update_line_numbers()
    
    def _append(self, s: str):
        """
        Append new text to the display, applying current filter.
        
        Processes incoming text chunk by chunk, stores lines in buffer,
        and displays only lines that match the current filter.
        
        Args:
            s: New text content to append
        """
        # Ensure text widget is in normal state for editing
        self.text.config(state=tk.NORMAL)
        
        # Break incoming chunk into lines, store, and append only matching ones
        lines = s.splitlines(True)  # keep line endings
        if not lines:
            return
        at_end = (self.text.yview()[1] == 1.0)
        self._line_buffer.extend(lines)
        
        # Apply current filter to new lines
        matching_lines = []
        for line in lines:
            if self.filter_manager.matches(line):
                matching_lines.append(line)
        
        # Insert all matching lines at once
        for line in matching_lines:
            self.text.insert(tk.END, line)
        
        # Apply highlighting to all newly added content if there's an active filter
        if self.filter_manager.current_filter and matching_lines:
            self._highlight_all_filter_matches()
            # Force update to ensure highlighting is applied
            self.text.update_idletasks()
        
        if self.autoscroll.get() and (at_end or self.paused.get() is False):
            self.text.see(tk.END)
        
        # Update line numbers after appending new text
        self._update_line_numbers()
    

    

    
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
    
    def _refresh_ui_from_config(self):
        """
        Refresh UI state from configuration to sync checkboxes and other settings.
        
        Called after settings dialog is closed to ensure UI reflects current configuration.
        """
        try:
            # Refresh display settings
            self.wrap.set(self.config_manager.get('display.word_wrap', False))
            self.autoscroll.set(self.config_manager.get('display.auto_scroll', True))
            self.show_line_numbers.set(self.config_manager.get('display.show_line_numbers', True))
            self.refresh_ms.set(self.config_manager.get('display.refresh_rate', DEFAULT_REFRESH_MS))
            
            # Apply any changed settings immediately
            self._apply_wrap()
            self._toggle_line_numbers()
            
        except Exception as e:
            print(f"Warning: Could not refresh UI from configuration: {e}")
    

    
    def _show_settings(self):
        """Show the settings/preferences dialog."""
        dialog = SettingsDialog(self, self.config_manager, self.theme_manager)
        
        # Wait for dialog to close, then refresh UI state
        self.wait_window(dialog)
        
        # Refresh icon in case it was changed in settings
        self._set_app_icon()
        
        # Refresh UI state from configuration to sync checkboxes and other settings
        self._refresh_ui_from_config()
    
    def _reset_settings(self):
        """Reset all settings to default values."""
        messagebox.showinfo("Reset Settings", "Reset settings will be implemented in the next phase.")
    
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

Text Selection & Copy:
• Ctrl+C - Copy selected text
• Ctrl+A - Select all text
• Mouse drag - Select text range
• Double-click - Select word
• Triple-click - Select line

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
