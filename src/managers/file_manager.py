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
from ..utils.constants import DEFAULT_ENCODING, MAX_FILE_SIZE_FOR_FULL_LOAD


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

    def open(self, start_at_end=True):
        """
        Open the file for reading.
        
        Args:
            start_at_end: If True, start reading from end of file
            
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

        # Auto-detect encoding (BOM first)
        if self.encoding == "auto":
            enc = self._encoding_from_bom(self._fh)
            self.encoding = enc or "utf-8"

        if start_at_end:
            # Start reading from end of file (for tailing)
            self._fh.seek(0, io.SEEK_END)
            self._pos = self._fh.tell()
        else:
            # Start reading from beginning of file
            self._fh.seek(0)
            self._pos = 0
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

    def _check_rotation_or_truncate(self):
        """
        Check for file rotation or truncation and reopen if needed.
        
        Detects when the file has been rotated (new inode) or truncated
        (file size smaller than last position) and handles accordingly.
        """
        try:
            st_path = os.stat(self.path)
            inode = (st_path.st_dev, st_path.st_ino)
        except OSError:
            return  # Possibly temporarily missing during rotation
            
        if self._inode and inode != self._inode:
            # File rotated/recreated - reopen from beginning
            self.open(start_at_end=False)
            return
            
        if self._fh:
            try:
                size = os.fstat(self._fh.fileno()).st_size
                if size < self._pos:
                    # File truncated - reset to beginning
                    self._fh.seek(0)
                    self._pos = 0
            except OSError:
                pass

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
                self.open(start_at_end=False)
            except OSError:
                return ""

        self._check_rotation_or_truncate()
        self._fh.seek(self._pos)
        data = self._fh.read()
        if not data:
            return ""

        self._pos = self._fh.tell()

        # Heuristic: if we don't have a BOM and see lots of NULs, switch to utf-16-le
        if self.encoding in ("utf-8", "utf-8-sig") and data and data.count(b"\x00") > len(data) // 4:
            self.encoding = "utf-16-le"

        try:
            return data.decode(self.encoding, errors="replace")
        except LookupError:
            # Fallback to UTF-8 if encoding not supported
            return data.decode("utf-8", errors="replace")
    
    def should_start_at_end(self) -> bool:
        """
        Determine if file should start reading from end.
        
        Returns:
            True if file is large enough to start tailing from end
        """
        try:
            return os.path.getsize(self.path) > MAX_FILE_SIZE_FOR_FULL_LOAD
        except OSError:
            return False
