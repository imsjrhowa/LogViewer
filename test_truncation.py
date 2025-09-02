#!/usr/bin/env python3
"""
Test script to demonstrate file truncation detection.
"""

import time
import os

def test_file_truncation():
    """Test file truncation by creating a file and then clearing it."""
    
    test_file = "test_truncation.log"
    
    print("Creating test file with content...")
    
    # Create a file with some content
    with open(test_file, 'w') as f:
        for i in range(1000):
            f.write(f"Line {i+1}: This is test content for line {i+1}\n")
    
    # Get initial file size
    initial_size = os.path.getsize(test_file)
    print(f"Initial file size: {initial_size:,} bytes")
    
    print("\nFile created. Now open this file in your Log Viewer application.")
    print("Then run this script again to truncate the file.")
    print("\nPress Enter when ready to truncate the file...")
    input()
    
    # Truncate the file (clear it)
    print("Truncating file...")
    with open(test_file, 'w') as f:
        f.write("File was cleared\n")
    
    # Get new file size
    new_size = os.path.getsize(test_file)
    print(f"New file size: {new_size:,} bytes")
    print(f"Size reduction: {((initial_size - new_size) / initial_size * 100):.1f}%")
    
    print("\n✅ File truncated! Your Log Viewer should now automatically reload the file.")
    print("Check the status bar for 'File truncated - reloading...' message.")
    
    # Clean up
    print("\nCleaning up test file...")
    os.remove(test_file)
    print("Test complete!")

if __name__ == "__main__":
    test_file_truncation()

