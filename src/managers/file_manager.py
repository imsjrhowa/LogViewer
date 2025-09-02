#!/usr/bin/env python3
"""
File Manager for the Log Viewer application.

Efficiently read new bytes from a growing (append-only) text file.
Detects file truncation and rotation and reopens as needed. Includes
BOM detection and heuristic for UTF-16 logs without BOM. Optimized
for real-time log monitoring with minimal resource usage.
"""

import os
import io
from typing import Optional
from src.utils.constants import DEFAULT_ENCODING


class FileManager:
    """
    Efficiently read new bytes from a growing (append-only) text file.
    
    Detects file truncation and rotation and reopens as needed. Includes
    BOM detection and heuristic for UTF-16 logs without BOM. Optimized
    for real-time log monitoring with minimal resource usage.
    """
    
    def __init__(self, path: str, encoding: str = DEFAULT_ENCODING):
        """
        Initialize file manager.
        
        Args:
            path: Path to the file to monitor
            encoding: File encoding (use "auto" for auto-detection)
        """
        self.path = path
        self.encoding = encoding
        self._fh = None  # File handle for reading
        self._inode = None  # File inode for detecting rotation
        self._pos = 0  # Current file position
        self._detected_encoding = None  # Store detected encoding to avoid re-detection
        self._last_file_size = 0  # Track last known file size
        self._truncation_callback = None  # Callback for file truncation events

    def _encoding_from_bom(self, fh) -> Optional[str]:
        """
        Detect encoding from Byte Order Mark (BOM).
        
        Examines the first few bytes of the file to detect common
        encoding signatures like UTF-16 LE/BE and UTF-8 BOM.
        
        Args:
            fh: File handle to examine
            
        Returns:
            Detected encoding string or None if no BOM found
        """
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

    def open(self, start_at_end=False):
        """
        Open the file for reading.
        
        Args:
            start_at_end: If True, start reading from end of file (legacy, not used)
            
        Returns:
            True if file opened successfully
        """
        self.close()
        self._fh = open(self.path, "rb")
        try:
            # Get file inode for rotation detection
            st = os.fstat(self._fh.fileno())
            self._inode = (st.st_dev, st.st_ino)
        except Exception:
            self._inode = None

        # Auto-detect encoding (BOM first) - only if not already detected
        if self.encoding == "auto" and self._detected_encoding is None:
            enc = self._encoding_from_bom(self._fh)
            self._detected_encoding = enc or "utf-8"
            self.encoding = self._detected_encoding

        # Always start from beginning for initial load
        self._fh.seek(0)
        self._pos = 0
        
        # Initialize file size tracking
        try:
            self._last_file_size = os.path.getsize(self.path)
        except OSError:
            self._last_file_size = 0
        
        return True

    def close(self):
        """Close the file handle and reset state."""
        try:
            if self._fh:
                self._fh.close()
        finally:
            self._fh = None
            self._inode = None
            self._pos = 0
    
    def reset_encoding(self):
        """Reset detected encoding - useful when opening a new file."""
        self._detected_encoding = None
        if self.encoding == "auto":
            self.encoding = DEFAULT_ENCODING
    
    def force_encoding_detection(self):
        """Force re-detection of encoding from file content."""
        self._detected_encoding = None
        # Close and reopen to ensure fresh encoding detection
        if self._fh:
            self.close()
    
    def set_truncation_callback(self, callback):
        """
        Set callback function to be called when file truncation is detected.
        
        Args:
            callback: Function to call when truncation detected (should take no arguments)
        """
        self._truncation_callback = callback
    
    def _analyze_content_encoding(self, data: bytes) -> str:
        """
        Analyze content to determine the most likely encoding.
        
        Args:
            data: Raw bytes to analyze
            
        Returns:
            Suggested encoding string
        """
        if not data:
            return self.encoding
            
        # Check for BOM first
        if data.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if data.startswith(b"\xfe\xff"):
            return "utf-16-be"
        if data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
            
        # Heuristic: analyze NUL byte patterns
        nul_ratio = data.count(b"\x00") / len(data) if data else 0
        
        if nul_ratio > 0.25:  # More than 25% NULs suggests UTF-16
            return "utf-16-le"
        elif nul_ratio < 0.05:  # Less than 5% NULs suggests UTF-8
            return "utf-8"
        else:
            # Middle ground - keep current encoding
            return self.encoding
    
    def _detect_mixed_encoding(self, data: bytes) -> bool:
        """
        Detect if content appears to have mixed encoding.
        
        Args:
            data: Raw bytes to analyze
            
        Returns:
            True if mixed encoding is detected
        """
        if not data or len(data) < 10:
            return False
            
        # Check for mixed patterns that suggest encoding issues
        # Look for sequences that are neither valid UTF-8 nor UTF-16
        
        # Count valid UTF-8 sequences vs invalid ones
        try:
            data.decode('utf-8')
            utf8_valid = True
        except UnicodeDecodeError:
            utf8_valid = False
            
        # Count valid UTF-16 sequences vs invalid ones  
        try:
            data.decode('utf-16-le')
            utf16_valid = True
        except UnicodeDecodeError:
            utf16_valid = False
            
        # If neither encoding is valid, we likely have mixed content
        return not (utf8_valid or utf16_valid)

    def _check_rotation_or_truncate(self):
        """
        Check for file rotation or truncation and reopen if needed.
        
        Detects when the file has been rotated (new inode) or truncated
        (file size smaller than last position) and handles accordingly.
        """
        try:
            st_path = os.stat(self.path)
            inode = (st_path.st_dev, st_path.st_ino)
            current_size = st_path.st_size
        except OSError:
            return  # Possibly temporarily missing during rotation
            
        if self._inode and inode != self._inode:
            # File rotated/recreated - reopen from beginning
            self.open(start_at_end=False)
            self._last_file_size = current_size
            return
            
        if self._fh:
            try:
                size = os.fstat(self._fh.fileno()).st_size
                if size < self._pos:
                    # File truncated - reset to beginning
                    self._fh.seek(0)
                    self._pos = 0
                    
                    # Check if file size has significantly decreased (more than 50% reduction)
                    if (self._last_file_size > 0 and 
                        current_size < self._last_file_size * 0.5 and 
                        self._truncation_callback):
                        # Call the truncation callback to notify main window
                        self._truncation_callback()
                    
                    self._last_file_size = current_size
            except OSError:
                pass
        
        # Update last known file size
        self._last_file_size = current_size

    def read_entire_file(self, chunk_size: int = 1024 * 1024, progress_callback=None) -> str:
        """
        Read the entire file with chunked reading for large files.
        
        Args:
            chunk_size: Size of chunks to read (default 1MB)
            progress_callback: Optional callback function(progress, message) for progress updates
            
        Returns:
            Entire file content as string
        """
        if not self._fh:
            try:
                self.open()
            except OSError:
                return ""

        # Get file size for progress calculation
        try:
            file_size = os.path.getsize(self.path)
        except OSError:
            file_size = 0

        self._fh.seek(0)
        content = []
        total_read = 0
        
        if progress_callback:
            progress_callback(0, "")
        
        while True:
            chunk = self._fh.read(chunk_size)
            if not chunk:
                break
            content.append(chunk)
            total_read += len(chunk)
            
            # Update progress if callback provided
            if progress_callback and file_size > 0:
                progress = (total_read / file_size) * 100.0
                progress_callback(progress, f"{self._format_size(total_read)} / {self._format_size(file_size)}")
                
        
        if progress_callback:
            progress_callback(80, "")
        
        # Combine all chunks
        data = b''.join(content)
        
        # Heuristic: if we don't have a BOM and see lots of NULs, switch to utf-16-le
        # Only apply this heuristic once per file to avoid changing encoding mid-stream
        if (self.encoding in ("utf-8", "utf-8-sig") and 
            self._detected_encoding is None and 
            data and data.count(b"\x00") > len(data) // 4):
            self._detected_encoding = "utf-16-le"
            self.encoding = self._detected_encoding

        if progress_callback:
            progress_callback(90, "")

        try:
            decoded_content = data.decode(self.encoding, errors="replace")
            
            # IMPORTANT: Set position to end for future tailing AFTER reading
            # This ensures we start monitoring from the current end of file
            self._pos = self._fh.tell()
            
            if progress_callback:
                progress_callback(99, "                                              ")
                progress_callback(100, "Reading!")
            
            return decoded_content
        except LookupError:
            # Fallback to UTF-8 if encoding not supported
            if self._detected_encoding is None:
                self._detected_encoding = "utf-8"
                self.encoding = self._detected_encoding
            decoded_content = data.decode("utf-8", errors="replace")
            
            # Set position to end for future tailing
            self._pos = self._fh.tell()
            
            if progress_callback:
                progress_callback(100, "File read complete (UTF-8 fallback)")
            
            return decoded_content
    
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

    def read_new_text(self) -> str:
        """
        Read new text from the file since last read.
        
        Handles file rotation, truncation, and encoding issues gracefully.
        Uses heuristics to detect UTF-16 files without BOM.
        
        Returns:
            New text content as string
        """
        if not self._fh:
            try:
                self.open()
            except OSError:
                return ""

        self._check_rotation_or_truncate()
        
        # Get current file size to check if there's new content
        try:
            current_size = os.path.getsize(self.path)
            if current_size <= self._pos:
                # No new content since last read
                return ""
        except OSError:
            return ""
        
        # Seek to our last position and read new content
        self._fh.seek(self._pos)
        data = self._fh.read()
        if not data:
            return ""

        # Update position to current end of file
        self._pos = self._fh.tell()

        # Continuous encoding detection for new content
        # This helps catch cases where new content has different encoding characteristics
        if data:
            suggested_encoding = self._analyze_content_encoding(data)
            if suggested_encoding != self.encoding:
                print(f"Debug: Encoding changed from {self.encoding} to {suggested_encoding} for new content")
                self._detected_encoding = suggested_encoding
                self.encoding = suggested_encoding

        try:
            return data.decode(self.encoding, errors="replace")
        except LookupError:
            # Fallback to UTF-8 if encoding not supported
            if self._detected_encoding != "utf-8":
                self._detected_encoding = "utf-8"
                self.encoding = self._detected_encoding
                print(f"Debug: Fallback to UTF-8 encoding for new content")
            return data.decode("utf-8", errors="replace")
    

