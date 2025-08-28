#!/usr/bin/env python3
"""
Loading Dialog for the Log Viewer application.

Shows a loading dialog with progress bar when opening large files
to prevent the UI from appearing frozen during long operations.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time


class LoadingDialog(tk.Toplevel):
    """
    Loading dialog with progress bar and status updates.
    
    Shows a modal dialog that displays loading progress and can be
    updated from background threads to show file loading status.
    """
    
    def __init__(self, parent, title="Loading", message="Please wait..."):
        """
        Initialize the loading dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Initial status message
        """
        super().__init__(parent)
        
        # Configure dialog properties
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self._center_on_parent(parent)
        
        # Initialize variables
        self._progress = tk.DoubleVar(value=0.0)
        self._message = tk.StringVar(value=message)
        self._is_cancelled = False
        self._cancelled_event = threading.Event()
        
        # Build the UI
        self._build_ui()
        
        # Prevent closing with X button
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Focus and center
        self.focus_set()
        
    def _build_ui(self):
        """Build the loading dialog UI."""
        # Main container
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(main_frame, text="Loading File", 
                               font=("TkDefaultFont", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Status message
        self.status_label = ttk.Label(main_frame, textvariable=self._message,
                                     wraplength=350, justify=tk.CENTER)
        self.status_label.pack(pady=(0, 20))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, variable=self._progress,
                                           maximum=100, length=300, mode='determinate')
        self.progress_bar.pack(pady=(0, 20))
        
        # Progress percentage
        self.progress_label = ttk.Label(main_frame, text="0%")
        self.progress_label.pack(pady=(0, 20))
        
        # Cancel button
        self.cancel_button = ttk.Button(main_frame, text="Cancel", 
                                       command=self._cancel_loading)
        self.cancel_button.pack()
        
        # Update progress label when progress changes
        self._progress.trace_add('write', self._update_progress_label)
        
    def _center_on_parent(self, parent):
        """Center the dialog on its parent window."""
        try:
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            
            dialog_width = 400
            dialog_height = 150
            
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            # Fallback to screen center - just use default position
            pass
    
    def _update_progress_label(self, *args):
        """Update the progress percentage label."""
        try:
            progress = int(self._progress.get())
            self.progress_label.config(text=f"{progress}%")
        except Exception:
            pass
    
    def _cancel_loading(self):
        """Cancel the loading operation."""
        self._is_cancelled = True
        self._cancelled_event.set()
        self._message.set("Cancelling...")
        self.cancel_button.config(state=tk.DISABLED)
    
    def _on_closing(self):
        """Handle dialog closing - treat as cancel."""
        self._cancel_loading()
    
    def update_progress(self, progress: float, message: str = None):
        """
        Update the progress bar and optionally the message.
        
        Args:
            progress: Progress value (0.0 to 100.0)
            message: Optional status message to update
        """
        try:
            # Ensure progress is within bounds
            progress = max(0.0, min(100.0, progress))
            
            # Update progress bar
            self._progress.set(progress)
            
            # Update message if provided
            if message:
                self._message.set(message)
                
            # Force update
            self.update_idletasks()
            
        except Exception:
            pass
    
    def update_message(self, message: str):
        """
        Update only the status message.
        
        Args:
            message: New status message
        """
        try:
            self._message.set(message)
            self.update_idletasks()
        except Exception:
            pass
    
    def set_progress_mode(self, mode: str):
        """
        Set the progress bar mode.
        
        Args:
            mode: Either 'determinate' (shows progress) or 'indeterminate' (animated)
        """
        try:
            if mode == 'indeterminate':
                self.progress_bar.config(mode='indeterminate')
                self.progress_bar.start(10)
            else:
                self.progress_bar.stop()
                self.progress_bar.config(mode='determinate')
        except Exception:
            pass
    
    def is_cancelled(self) -> bool:
        """Check if loading was cancelled."""
        return self._is_cancelled
    
    def wait_for_cancellation(self, timeout: float = None) -> bool:
        """
        Wait for cancellation event.
        
        Args:
            timeout: Timeout in seconds (None for no timeout)
            
        Returns:
            True if cancelled, False if timeout
        """
        return self._cancelled_event.wait(timeout)
    
    def close(self):
        """Close the loading dialog."""
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass


class FileLoadingDialog(LoadingDialog):
    """
    Specialized loading dialog for file operations.
    
    Provides file-specific loading messages and progress updates.
    """
    
    def __init__(self, parent, filename: str):
        """
        Initialize file loading dialog.
        
        Args:
            parent: Parent window
            filename: Name of the file being loaded
        """
        super().__init__(parent, title="Loading File", 
                        message=f"Loading {filename}...")
        
        self.filename = filename
        self._file_size = 0
        self._bytes_read = 0
        
    def set_file_size(self, size_bytes: int):
        """
        Set the total file size for progress calculation.
        
        Args:
            size_bytes: Total file size in bytes
        """
        self._file_size = size_bytes
        if size_bytes > 0:
            self.update_message(f"Loading {self.filename} ({self._format_size(size_bytes)})")
    
    def update_bytes_read(self, bytes_read: int, message: str = None):
        """
        Update progress based on bytes read.
        
        Args:
            bytes_read: Number of bytes read so far
            message: Optional custom message
        """
        self._bytes_read = bytes_read
        
        if self._file_size > 0:
            # Calculate percentage
            progress = (bytes_read / self._file_size) * 100.0
            self.update_progress(progress, message)
        else:
            # Indeterminate mode for unknown file sizes
            self.set_progress_mode('indeterminate')
            if message:
                self.update_message(message)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        try:
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        except Exception:
            return f"{size_bytes} bytes"
