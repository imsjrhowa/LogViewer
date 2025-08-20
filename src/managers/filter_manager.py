#!/usr/bin/env python3
"""
Filter Manager for the Log Viewer application.

Advanced filtering system for log entries with multiple modes and history.
Supports various filtering modes including substring matching, regex patterns,
exact matching, and negation. Maintains filter history and provides
comprehensive error handling for invalid patterns.
"""

import re
from typing import Dict, Any, List
from ..utils.constants import DEFAULT_FILTER_MODE, MAX_FILTER_HISTORY


class FilterManager:
    """
    Advanced filtering system for log entries with multiple modes and history.
    
    Supports various filtering modes including substring matching, regex patterns,
    exact matching, and negation. Maintains filter history and provides
    comprehensive error handling for invalid patterns.
    """
    
    # Available filter modes with human-readable descriptions
    MODES = {
        "contains": "Contains",           # Text appears anywhere in line
        "starts_with": "Starts With",     # Line begins with text
        "ends_with": "Ends With",         # Line ends with text
        "regex": "Regular Expression",    # Use regex patterns
        "exact": "Exact Match",           # Line exactly matches text
        "not_contains": "Not Contains"    # Line does NOT contain text
    }
    
    def __init__(self):
        """Initialize filter manager with default settings."""
        self.current_filter = ""          # Current filter text
        self.current_mode = DEFAULT_FILTER_MODE    # Current filter mode
        self.case_sensitive = False       # Case sensitivity flag
        self.filter_history = []          # List of previous filters
        self.max_history = MAX_FILTER_HISTORY            # Maximum history items to keep
        self.compiled_regex = None        # Compiled regex pattern (if applicable)
        self.last_error = None            # Last regex compilation error
        
    def set_filter(self, text: str, mode: str = None, case_sensitive: bool = None) -> bool:
        """
        Set the current filter with optional mode and case sensitivity.
        
        Args:
            text: Filter text to apply
            mode: Filter mode (None to keep current)
            case_sensitive: Case sensitivity flag (None to keep current)
            
        Returns:
            True if filter changed, False if no change
        """
        if mode is not None:
            self.current_mode = mode
        if case_sensitive is not None:
            self.case_sensitive = case_sensitive
            
        if text != self.current_filter:
            self.current_filter = text
            self._add_to_history(text)
            self._compile_regex()
            return True
        return False
    
    def _add_to_history(self, text: str):
        """
        Add filter text to history if it's not empty and not already there.
        
        Args:
            text: Filter text to add to history
        """
        if text and text not in self.filter_history:
            self.filter_history.insert(0, text)
            # Maintain maximum history size
            if len(self.filter_history) > self.max_history:
                self.filter_history.pop()
    
    def _compile_regex(self):
        """
        Compile regex pattern if mode is regex.
        
        Handles regex compilation errors gracefully and stores error messages
        for user feedback.
        """
        self.compiled_regex = None
        self.last_error = None
        
        if self.current_mode == "regex" and self.current_filter:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self.compiled_regex = re.compile(self.current_filter, flags)
            except re.error as e:
                self.last_error = str(e)
    
    def matches(self, line: str) -> bool:
        """
        Check if a line matches the current filter.
        
        Args:
            line: Text line to check against filter
            
        Returns:
            True if line matches filter, False otherwise
        """
        if not self.current_filter:
            return True
            
        if self.last_error:
            return False
            
        try:
            # Route to appropriate matching method based on mode
            if self.current_mode == "contains":
                return self._contains_match(line)
            elif self.current_mode == "starts_with":
                return self._starts_with_match(line)
            elif self.current_mode == "ends_with":
                return self._ends_with_match(line)
            elif self.current_mode == "regex":
                return self._regex_match(line)
            elif self.current_mode == "exact":
                return self._exact_match(line)
            elif self.current_mode == "not_contains":
                return self._not_contains_match(line)
            else:
                return self._contains_match(line)
        except Exception:
            return False
    
    def _contains_match(self, line: str) -> bool:
        """
        Check if line contains the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if filter text is found in line
        """
        if self.case_sensitive:
            return self.current_filter in line
        return self.current_filter.lower() in line.lower()
    
    def _starts_with_match(self, line: str) -> bool:
        """
        Check if line starts with the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line begins with filter text
        """
        if self.case_sensitive:
            return line.startswith(self.current_filter)
        return line.lower().startswith(self.current_filter.lower())
    
    def _ends_with_match(self, line: str) -> bool:
        """
        Check if line ends with the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line ends with filter text
        """
        if self.case_sensitive:
            return line.endswith(self.current_filter)
        return line.lower().endswith(self.current_filter.lower())
    
    def _regex_match(self, line: str) -> bool:
        """
        Check if line matches the regex pattern.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line matches regex pattern
        """
        if self.compiled_regex:
            return bool(self.compiled_regex.search(line))
        return False
    
    def _exact_match(self, line: str) -> bool:
        """
        Check if line exactly matches the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line exactly matches filter text
        """
        if self.case_sensitive:
            return line == self.current_filter
        return line.lower() == self.current_filter.lower()
    
    def _not_contains_match(self, line: str) -> bool:
        """
        Check if line does NOT contain the filter text.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line does NOT contain filter text
        """
        return not self._contains_match(line)
    
    def get_filter_info(self) -> Dict[str, Any]:
        """
        Get current filter information for display and status updates.
        
        Returns:
            Dictionary containing filter state information
        """
        return {
            "text": self.current_filter,
            "mode": self.current_mode,
            "mode_display": self.MODES.get(self.current_mode, "Unknown"),
            "case_sensitive": self.case_sensitive,
            "has_error": bool(self.last_error),
            "error": self.last_error,
            "is_active": bool(self.current_filter)
        }
    
    def get_mode_names(self) -> List[str]:
        """
        Get list of available filter mode names.
        
        Returns:
            List of filter mode identifier strings
        """
        return list(self.MODES.keys())
    
    def get_mode_display_names(self) -> List[str]:
        """
        Get list of filter mode display names for UI.
        
        Returns:
            List of human-readable filter mode names
        """
        return list(self.MODES.values())
    
    def clear_filter(self):
        """Clear the current filter and reset related state."""
        self.current_filter = ""
        self.compiled_regex = None
        self.last_error = None
