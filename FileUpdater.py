#!/usr/bin/env python3
"""
Log Viewer (auto-refresh) — Windows-friendly, 3.6+ compatible

Features
- Choose a log file via File → Open… or pass --file /path/to/file
- Auto-refresh (500 ms by default), adjustable in the UI
- Pause/Resume
- Auto-scroll to bottom when new lines arrive
- Word wrap toggle
- Clear view
- Handles file rotation/truncation
- Auto-detects common encodings (UTF-16 LE/BE, UTF-8 BOM), with heuristic for NUL-byte "spaced" text
- Multiple color themes (Dark, Light, Sunset)
- Keeps memory in check by trimming to last N lines (default 10,000)
- NEW: Live filter box (substring match) with case-sensitive toggle

Run
    python log_viewer.py --file /path/to/your/log.txt

Requires only the Python standard library.
"""

import argparse
import io
import os
import sys
import time
import tkinter as tk
import collections
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Any

MAX_LINES_DEFAULT = 10_000
DEFAULT_REFRESH_MS = 500
DEFAULT_ENCODING = "auto"  # auto | utf-8 | utf-16 | utf-16-le | utf-16-be | etc.
DEFAULT_THEME = "dark"     # dark | light | sunset


class ThemeManager:
    """Manages color themes for the Log Viewer application."""
    
    # Theme color definitions
    THEMES = {
        "dark": {
            "name": "Dark",
            "bg": "#1e1e1e",           # Main background
            "fg": "#d4d4d4",           # Main text
            "text_bg": "#1e1e1e",      # Text area background
            "text_fg": "#d4d4d4",      # Text area text
            "insert_bg": "#ffffff",    # Caret color
            "toolbar_bg": "#2d2d2d",   # Toolbar background
            "toolbar_fg": "#d4d4d4",   # Toolbar text
            "status_bg": "#2d2d2d",    # Status bar background
            "status_fg": "#d4d4d4",    # Status bar text
            "menu_bg": "#2d2d2d",      # Menu background
            "menu_fg": "#d4d4d4",      # Menu text
            "menu_select_bg": "#404040", # Menu selection background
            "button_bg": "#404040",     # Button background
            "button_fg": "#d4d4d4",    # Button text
            "entry_bg": "#3c3c3c",     # Entry field background
            "entry_fg": "#d4d4d4",     # Entry field text
            "entry_insert_bg": "#ffffff", # Entry caret color
        },
        "light": {
            "name": "Light",
            "bg": "#ffffff",           # Main background
            "fg": "#000000",           # Main text
            "text_bg": "#ffffff",      # Text area background
            "text_fg": "#000000",      # Text area text
            "insert_bg": "#000000",    # Caret color
            "toolbar_bg": "#f0f0f0",   # Toolbar background
            "toolbar_fg": "#000000",   # Toolbar text
            "status_bg": "#f0f0f0",    # Status bar background
            "status_fg": "#000000",    # Status bar text
            "menu_bg": "#f0f0f0",      # Menu background
            "menu_fg": "#000000",      # Menu text
            "menu_select_bg": "#e0e0e0", # Menu selection background
            "button_bg": "#e0e0e0",     # Button background
            "button_fg": "#000000",    # Button text
            "entry_bg": "#ffffff",     # Entry field background
            "entry_fg": "#000000",     # Entry field text
            "entry_insert_bg": "#000000", # Entry caret color
        },
        "sunset": {
            "name": "Sunset",
            "bg": "#2d1b3d",           # Main background (deep purple)
            "fg": "#f4e4bc",           # Main text (warm cream)
            "text_bg": "#2d1b3d",      # Text area background
            "text_fg": "#f4e4bc",      # Text area text
            "insert_bg": "#ff6b35",    # Caret color (orange)
            "toolbar_bg": "#3d2b4d",   # Toolbar background
            "toolbar_fg": "#f4e4bc",   # Toolbar text
            "status_bg": "#3d2b4d",    # Status bar background
            "status_fg": "#f4e4bc",    # Status bar text
            "menu_bg": "#3d2b4d",      # Menu background
            "menu_fg": "#f4e4bc",      # Menu text
            "menu_select_bg": "#4d3b5d", # Menu selection background
            "button_bg": "#4d3b5d",     # Button background
            "button_fg": "#f4e4bc",    # Button text
            "entry_bg": "#3d2b4d",     # Entry field background
            "entry_fg": "#f4e4bc",     # Entry field text
            "entry_insert_bg": "#ff6b35", # Entry caret color
        }
    }
    
    def __init__(self, theme_name: str = DEFAULT_THEME):
        self.current_theme = theme_name
        if theme_name not in self.THEMES:
            self.current_theme = DEFAULT_THEME
    
    def get_theme(self, theme_name: str = None) -> Dict[str, Any]:
        """Get theme colors by name."""
        if theme_name is None:
            theme_name = self.current_theme
        return self.THEMES.get(theme_name, self.THEMES[DEFAULT_THEME])
    
    def get_current_theme(self) -> Dict[str, Any]:
        """Get current theme colors."""
        return self.get_theme(self.current_theme)
    
    def set_theme(self, theme_name: str) -> bool:
        """Set current theme. Returns True if theme changed."""
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            return True
        return False
    
    def get_theme_names(self) -> list:
        """Get list of available theme names."""
        return list(self.THEMES.keys())
    
    def get_theme_display_names(self) -> list:
        """Get list of theme display names."""
        return [self.THEMES[name]["name"] for name in self.THEMES]


class TailReader:
    """Efficiently read new bytes from a growing (append-only) text file.
    Detects truncation and rotation and reopens as needed.
    Includes BOM detection and heuristic for UTF-16 logs without BOM.
    """
    def __init__(self, path: str, encoding: str = DEFAULT_ENCODING):
        self.path = path
        self.encoding = encoding
        self._fh = None  # type: Optional[io.BufferedReader]
        self._inode = None  # type: Optional[tuple]
        self._pos = 0

    def _encoding_from_bom(self, fh) -> Optional[str]:
        pos = fh.tell()
        try:
            fh.seek(0)
            head = fh.read(4)
        finally:
            fh.seek(pos)
        if not head:
            return None
        if head.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if head.startswith(b"\xfe\xff"):
            return "utf-16-be"
        if head.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        return None

    def open(self, start_at_end=True):
        self.close()
        self._fh = open(self.path, "rb")
        try:
            st = os.fstat(self._fh.fileno())
            self._inode = (st.st_dev, st.st_ino)
        except Exception:
            self._inode = None

        # Auto-detect encoding (BOM first)
        if self.encoding == "auto":
            enc = self._encoding_from_bom(self._fh)
            self.encoding = enc or "utf-8"

        if start_at_end:
            self._fh.seek(0, io.SEEK_END)
            self._pos = self._fh.tell()
        else:
            self._fh.seek(0)
            self._pos = 0
        return True

    def close(self):
        try:
            if self._fh:
                self._fh.close()
        finally:
            self._fh = None
            self._inode = None
            self._pos = 0

    def _check_rotation_or_truncate(self):
        """Reopen file if inode changed (rotation) or size < pos (truncation)."""
        try:
            st_path = os.stat(self.path)
            inode = (st_path.st_dev, st_path.st_ino)
        except OSError:
            return  # Possibly temporarily missing during rotation
        if self._inode and inode != self._inode:
            # rotated/recreated
            self.open(start_at_end=False)
            return
        if self._fh:
            try:
                size = os.fstat(self._fh.fileno()).st_size
                if size < self._pos:
                    # truncated
                    self._fh.seek(0)
                    self._pos = 0
            except OSError:
                pass

    def read_new_text(self) -> str:
        if not self._fh:
            try:
                self.open(start_at_end=False)
            except OSError:
                return ""

        self._check_rotation_or_truncate()
        self._fh.seek(self._pos)
        data = self._fh.read()
        if not data:
            return ""

        self._pos = self._fh.tell()

        # Heuristic: if we don’t have a BOM and see lots of NULs, switch to utf-16-le
        if self.encoding in ("utf-8", "utf-8-sig") and data and data.count(b"\x00") > len(data) // 4:
            self.encoding = "utf-16-le"

        try:
            return data.decode(self.encoding, errors="replace")
        except LookupError:
            return data.decode("utf-8", errors="replace")


class LogViewerApp(tk.Tk):
    def __init__(self, path: Optional[str], refresh_ms: int = DEFAULT_REFRESH_MS, encoding: str = DEFAULT_ENCODING, theme: str = DEFAULT_THEME):
        super().__init__()
        self.title("Log Viewer")
        self.geometry("1000x640")
        self.minsize(640, 360)

        # Initialize theme manager with saved preference or command line argument
        self.theme_manager = ThemeManager(theme)  # Will be updated after UI is built
        
        self.path = path
        self.tail = TailReader(path, encoding=encoding) if path else None
        self.refresh_ms = tk.IntVar(value=refresh_ms)
        self.autoscroll = tk.BooleanVar(value=True)
        self.wrap = tk.BooleanVar(value=False)
        self.paused = tk.BooleanVar(value=False)
        self.max_lines = tk.IntVar(value=MAX_LINES_DEFAULT)

        # Filtering
        self.filter_text = tk.StringVar(value="")
        self.case_sensitive = tk.BooleanVar(value=False)
        self._filter_job = None  # debounce handle

        # Store raw lines so we can rebuild view when filter changes
        self._line_buffer = collections.deque(maxlen=MAX_LINES_DEFAULT)

        self._build_ui()
        
        # Load saved theme preference if using default theme
        if theme == DEFAULT_THEME:
            saved_theme = self._load_theme_preference()
            if saved_theme != DEFAULT_THEME:
                self.theme_manager.set_theme(saved_theme)
                # Update menu checkmarks
                for name, var in self.theme_vars.items():
                    var.set(name == saved_theme)
        
        self._apply_theme()  # Apply initial theme
        if self.path:
            self._open_path(self.path, first_open=True)
        self.after(self.refresh_ms.get(), self._poll)

    # UI
    def _build_ui(self):
        # Menu
        menubar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open…", command=self._choose_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu with theme selection
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Word Wrap", command=self._toggle_wrap)
        view_menu.add_separator()
        
        # Theme submenu
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
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Theme Info", command=self._show_theme_info)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_keyboard_shortcuts)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)
        
        # Bind keyboard shortcuts
        self.bind('<Control-t>', lambda e: self._cycle_theme())
        self.bind('<Control-T>', lambda e: self._cycle_theme())
        self.bind('<Control-f>', lambda e: self._focus_filter())
        self.bind('<Control-F>', lambda e: self._focus_filter())
        self.bind('<Control-w>', lambda e: self._toggle_wrap())
        self.bind('<Control-W>', lambda e: self._toggle_wrap())
        self.bind('<Control-p>', lambda e: self._toggle_pause())
        self.bind('<Control-P>', lambda e: self._toggle_pause())

        # Controls / toolbar
        toolbar = ttk.Frame(self, padding=(8, 4))
        toolbar.pack(fill=tk.X)

        self.path_label = ttk.Label(toolbar, text="No file selected", width=80)
        self.path_label.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(toolbar, text="Refresh (ms)").pack(side=tk.LEFT)
        refresh_entry = ttk.Spinbox(toolbar, from_=100, to=5000, textvariable=self.refresh_ms, width=6)
        refresh_entry.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Checkbutton(toolbar, text="Auto-scroll", variable=self.autoscroll).pack(side=tk.LEFT)
        ttk.Checkbutton(toolbar, text="Wrap", variable=self.wrap, command=self._apply_wrap).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Label(toolbar, text="Max lines").pack(side=tk.LEFT)
        ttk.Spinbox(toolbar, from_=1000, to=200000, increment=1000, textvariable=self.max_lines, width=7).pack(side=tk.LEFT, padx=(4, 8))

        self.pause_btn = ttk.Button(toolbar, text="Pause", command=self._toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=(8, 4))
        ttk.Button(toolbar, text="Clear", command=self._clear).pack(side=tk.LEFT)

        # Filter controls
        ttk.Label(toolbar, text="Filter").pack(side=tk.LEFT, padx=(12, 4))
        filt_entry = ttk.Entry(toolbar, textvariable=self.filter_text, width=24)
        filt_entry.pack(side=tk.LEFT)
        ttk.Checkbutton(toolbar, text="Case-sensitive", variable=self.case_sensitive, command=self._on_filter_change).pack(side=tk.LEFT, padx=(6, 0))
        
        # Theme indicator (right side)
        theme_frame = ttk.Frame(toolbar)
        theme_frame.pack(side=tk.RIGHT, padx=(8, 0))
        
        self.theme_label = ttk.Label(theme_frame, text="", width=15)
        self.theme_label.pack(side=tk.LEFT)
        
        # Theme preview button
        self.theme_preview_btn = ttk.Button(theme_frame, text="🎨", width=3, command=self._show_theme_preview)
        self.theme_preview_btn.pack(side=tk.LEFT, padx=(4, 0))
        
        # Rebuild when user types
        self.filter_text.trace_add('write', lambda *args: self._on_filter_change())

        # Text area
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Choose a monospaced font per platform
        font_family = "Consolas" if sys.platform.startswith("win") else "Menlo"

        self.text = tk.Text(
            text_frame,
            wrap=tk.WORD if self.wrap.get() else tk.NONE,
            undo=False,
            font=(font_family, 11)
        )

        yscroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=yscroll.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar
        self.status = ttk.Label(self, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X)

    # Filtering
    def _on_filter_change(self):
        # Debounce rapid typing; rebuild shortly after user stops
        if self._filter_job is not None:
            try:
                self.after_cancel(self._filter_job)
            except Exception:
                pass
        self._filter_job = self.after(150, self._rebuild_view)

    def _matches(self, line: str) -> bool:
        needle = self.filter_text.get()
        if not needle:
            return True
        if self.case_sensitive.get():
            return needle in line
        return needle.lower() in line.lower()

    def _rebuild_view(self):
        # Re-render the text widget from the buffered lines using the current filter
        try:
            self.text.delete('1.0', tk.END)
            at_end = True
            for line in self._line_buffer:
                if self._matches(line):
                    self.text.insert(tk.END, line)
            if self.autoscroll.get() and at_end:
                self.text.see(tk.END)
            self._set_status("Filtered")
        except Exception as e:
            self._set_status("Filter error: {}".format(e))

    def _buffer_trim(self):
        # Ensure buffer keeps approximately the last N lines (N = max_lines)
        try:
            target = max(1000, int(self.max_lines.get() or MAX_LINES_DEFAULT))
        except Exception:
            target = MAX_LINES_DEFAULT
        # collections.deque with maxlen handles trimming automatically if maxlen is set.
        # Update maxlen dynamically to follow user control.
        if self._line_buffer.maxlen != target:
            tmp = collections.deque(self._line_buffer, maxlen=target)
            self._line_buffer = tmp

    # Actions
    def _choose_file(self):
        path = filedialog.askopenfilename(title="Choose log file")
        if path:
            self._open_path(path, first_open=True)

    def _open_path(self, path: str, first_open=False):
        self.path = path
        self.path_label.config(text=path)
        try:
            if not self.tail:
                self.tail = TailReader(path)
            self.tail.path = path

            # If small file (<2MB), show existing contents; else start tailing from end
            start_at_end = False
            try:
                if os.path.getsize(path) > 2 * 1024 * 1024:
                    start_at_end = True
            except OSError:
                pass
            self.tail.open(start_at_end=start_at_end)
            if not start_at_end:
                # Load initial chunk
                text = self.tail.read_new_text()
                if text:
                    self._append(text)
            self._set_status("Opened")
        except Exception as e:
            messagebox.showerror("Error", "Failed to open file:\n{}".format(e))
            self._set_status("Open failed")

    def _toggle_pause(self):
        self.paused.set(not self.paused.get())
        self.pause_btn.config(text="Resume" if self.paused.get() else "Pause")
        self._set_status("Paused" if self.paused.get() else "Running")

    def _clear(self):
        self.text.delete('1.0', tk.END)

    def _toggle_wrap(self):
        """Toggle word wrap and update menu checkmark."""
        self.wrap.set(not self.wrap.get())
        self._apply_wrap()
        # Update menu checkmark
        if hasattr(self, 'view_menu'):
            # Find the word wrap menu item and update it
            pass  # Menu update will be handled by the menu system
    
    def _apply_wrap(self):
        self.text.config(wrap=tk.WORD if self.wrap.get() else tk.NONE)
    
    def _change_theme(self, theme_name: str):
        """Change the application theme."""
        if self.theme_manager.set_theme(theme_name):
            self._apply_theme()
            # Update theme menu checkmarks
            for name, var in self.theme_vars.items():
                var.set(name == theme_name)
            # Show theme change confirmation in status
            self._set_status(f"Theme changed to {self.theme_manager.get_theme(theme_name)['name']}")
    
    def _apply_theme(self):
        """Apply the current theme to all UI elements."""
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
        
        # Save theme preference
        self._save_theme_preference()
    
    def _save_theme_preference(self):
        """Save current theme preference to a simple config file."""
        try:
            config_dir = os.path.expanduser("~/.logviewer")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "theme.txt")
            with open(config_file, 'w') as f:
                f.write(self.theme_manager.current_theme)
        except Exception:
            pass  # Silently fail if we can't save preferences
    
    def _load_theme_preference(self) -> str:
        """Load saved theme preference. Returns default if none saved."""
        try:
            config_file = os.path.join(os.path.expanduser("~/.logviewer"), "theme.txt")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    theme = f.read().strip()
                    if theme in self.theme_manager.get_theme_names():
                        return theme
        except Exception:
            pass
        return DEFAULT_THEME
    
    def _cycle_theme(self):
        """Cycle through available themes with keyboard shortcut."""
        themes = self.theme_manager.get_theme_names()
        current_index = themes.index(self.theme_manager.current_theme)
        next_index = (current_index + 1) % len(themes)
        next_theme = themes[next_index]
        self._change_theme(next_theme)
    
    def _show_theme_info(self):
        """Show information about available themes."""
        info = "Available Themes:\n\n"
        for theme_name in self.theme_manager.get_theme_names():
            theme = self.theme_manager.get_theme(theme_name)
            current = " (Current)" if theme_name == self.theme_manager.current_theme else ""
            info += f"• {theme['name']}{current}\n"
        info += "\nUse Ctrl+T to cycle through themes\n"
        info += "Or use View → Theme menu"
        
        messagebox.showinfo("Theme Information", info)
    
    def _show_keyboard_shortcuts(self):
        """Show available keyboard shortcuts."""
        shortcuts = "Keyboard Shortcuts:\n\n"
        shortcuts += "Ctrl+O    - Open file\n"
        shortcuts += "Ctrl+T    - Cycle themes\n"
        shortcuts += "Ctrl+F    - Focus filter box\n"
        shortcuts += "Ctrl+W    - Toggle word wrap\n"
        shortcuts += "Ctrl+P    - Toggle pause/resume\n"
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def _show_theme_preview(self):
        """Show a preview of all available themes."""
        preview_window = tk.Toplevel(self)
        preview_window.title("Theme Preview")
        preview_window.geometry("400x300")
        preview_window.resizable(False, False)
        preview_window.transient(self)
        preview_window.grab_set()
        
        # Center the window
        preview_window.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))
        
        # Create preview for each theme
        for i, theme_name in enumerate(self.theme_manager.get_theme_names()):
            theme = self.theme_manager.get_theme(theme_name)
            current = " (Current)" if theme_name == self.theme_manager.current_theme else ""
            
            # Theme frame
            theme_frame = ttk.Frame(preview_window)
            theme_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Theme name and current indicator
            name_label = ttk.Label(theme_frame, text=f"{theme['name']}{current}")
            name_label.pack(anchor=tk.W)
            
            # Color preview
            preview_frame = tk.Frame(theme_frame, height=40)
            preview_frame.pack(fill=tk.X, pady=2)
            preview_frame.pack_propagate(False)
            
            # Background color
            bg_label = tk.Label(preview_frame, text="  Background  ", 
                               bg=theme["bg"], fg=theme["fg"], relief=tk.RAISED)
            bg_label.pack(side=tk.LEFT, padx=2)
            
            # Text color
            text_label = tk.Label(preview_frame, text="  Text  ", 
                                 bg=theme["text_bg"], fg=theme["text_fg"], relief=tk.RAISED)
            text_label.pack(side=tk.LEFT, padx=2)
            
            # Button color
            btn_label = tk.Label(preview_frame, text="  Button  ", 
                                bg=theme["button_bg"], fg=theme["button_fg"], relief=tk.RAISED)
            btn_label.pack(side=tk.LEFT, padx=2)
            
            # Apply button
            apply_btn = ttk.Button(theme_frame, text="Apply", 
                                  command=lambda t=theme_name: self._apply_theme_from_preview(t, preview_window))
            apply_btn.pack(anchor=tk.E, pady=2)
        
        # Close button
        close_btn = ttk.Button(preview_window, text="Close", command=preview_window.destroy)
        close_btn.pack(pady=10)
    
    def _apply_theme_from_preview(self, theme_name: str, preview_window):
        """Apply theme from preview window and close it."""
        self._change_theme(theme_name)
        preview_window.destroy()
    
    def _focus_filter(self):
        """Focus the filter entry box."""
        # Find the filter entry widget and focus it
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):  # Toolbar
                for toolbar_child in child.winfo_children():
                    if isinstance(toolbar_child, ttk.Entry):
                        toolbar_child.focus_set()
                        toolbar_child.select_range(0, tk.END)
                        break
                break

    def _set_status(self, msg: str):
        now = time.strftime("%H:%M:%S")
        base = "[{}] {}".format(now, msg)
        if self.path:
            try:
                size = os.path.getsize(self.path)
                base += "  •  size: {:,} bytes".format(size)
            except OSError:
                pass
        self.status.config(text=base)

    def _trim_if_needed(self):
        # Keep last N lines for memory safety
        try:
            max_lines = max(1000, int(self.max_lines.get() or MAX_LINES_DEFAULT))
        except Exception:
            max_lines = MAX_LINES_DEFAULT
        total = int(self.text.index('end-1c').split('.')[0])
        if total > max_lines:
            cutoff = total - max_lines
            self.text.delete('1.0', "{}.0".format(cutoff))

    def _append(self, s: str):
        # Break incoming chunk into lines, store, and append only matching ones
        lines = s.splitlines(True)  # keep line endings
        if not lines:
            return
        at_end = (self.text.yview()[1] == 1.0)
        self._line_buffer.extend(lines)
        # Dynamic buffer size based on Max lines control
        self._buffer_trim()
        for line in lines:
            if self._matches(line):
                self.text.insert(tk.END, line)
        self._trim_if_needed()
        if self.autoscroll.get() and (at_end or self.paused.get() is False):
            self.text.see(tk.END)

    def _poll(self):
        try:
            if not self.paused.get() and self.tail and self.path:
                new_text = self.tail.read_new_text()
                if new_text:
                    self._append(new_text)
                    self._set_status("Updated")
        except Exception as e:
            # Non-fatal: show in status bar, keep polling
            self._set_status("Error: {}".format(e))
        finally:
            # Reschedule
            try:
                interval = max(100, int(self.refresh_ms.get()))
            except Exception:
                interval = DEFAULT_REFRESH_MS
            self.after(interval, self._poll)


def main():
    parser = argparse.ArgumentParser(description="Simple GUI log viewer that tails a file.")
    parser.add_argument('--file', '-f', help='Path to the log file to open on launch')
    parser.add_argument('--refresh', '-r', type=int, default=DEFAULT_REFRESH_MS, help='Refresh interval in milliseconds (default 500)')
    parser.add_argument('--encoding', '-e', default=DEFAULT_ENCODING, help='File encoding (default auto; try utf-16 on Windows logs)')
    parser.add_argument('--theme', '-t', default=DEFAULT_THEME, choices=['dark', 'light', 'sunset'], help='Color theme (default dark)')
    args = parser.parse_args()

    app = LogViewerApp(args.file, refresh_ms=args.refresh, encoding=args.encoding, theme=args.theme)
    if app.tail:
        app.tail.encoding = args.encoding
    app.mainloop()


if __name__ == '__main__':
    main()
