#!/usr/bin/env python3
"""
Build script for creating the Log Viewer executable.

This script automates the process of building a standalone executable
using PyInstaller with optimized settings.
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

def clean_build_dirs():
    """Clean up previous build artifacts."""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            try:
                shutil.rmtree(dir_name)
                print(f"✅ Cleaned {dir_name}")
            except PermissionError:
                print(f"⚠️  Could not clean {dir_name} (files may be in use)")
                print("   Continuing with build...")
            except Exception as e:
                print(f"⚠️  Warning: Could not clean {dir_name}: {e}")
                print("   Continuing with build...")
    
    # Clean up spec file
    spec_file = 'LogViewer.spec'
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"✅ Removed {spec_file}")
        except Exception as e:
            print(f"⚠️  Warning: Could not remove {spec_file}: {e}")

def bump_build_number():
    """Increment the build number in constants.py."""
    constants_file = 'src/utils/constants.py'
    
    try:
        # Read the current constants file
        with open(constants_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and increment the build number
        import re
        build_pattern = r'BUILD_NUMBER\s*=\s*(\d+)'
        match = re.search(build_pattern, content)
        
        if match:
            current_build = int(match.group(1))
            new_build = current_build + 1
            print(f"📈 Bumping build number: {current_build} → {new_build}")
            
            # Replace the build number
            new_content = re.sub(build_pattern, f'BUILD_NUMBER = {new_build}', content)
            
            # Write back to file
            with open(constants_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ Build number updated to {new_build}")
            return new_build
        else:
            print("⚠️  Could not find BUILD_NUMBER in constants.py")
            return None
            
    except Exception as e:
        print(f"⚠️  Warning: Could not bump build number: {e}")
        return None

def build_executable():
    """Build the executable using PyInstaller."""
    print("Building Log Viewer executable...")
    
    # Bump build number first
    new_build = bump_build_number()
    
    # Get version info for the executable
    try:
        # Import version constants (after bumping)
        sys.path.insert(0, 'src')
        from utils.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION, BUILD_NUMBER
        version_string = f"{APP_NAME} {APP_VERSION} - Build {BUILD_NUMBER}"
    except ImportError:
        version_string = "LogViewer v0.1"
        print("⚠️  Could not import version info, using default")
    
    # PyInstaller command with optimized settings
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                    # Single executable file
        '--windowed',                   # No console window
        '--name', 'LogViewer',          # Executable name
        '--icon', 'icons/default.ico',  # Application icon
        '--add-data', 'icons;icons',    # Include icon files
        '--add-data', 'src;src',        # Include src directory
        '--hidden-import', 'tkinter',   # Ensure tkinter is included
        '--hidden-import', 'tkinter.ttk',
        '--hidden-import', 'tkinter.messagebox',
        '--hidden-import', 'tkinter.filedialog',
        '--hidden-import', 'src.main',
        '--hidden-import', 'src.managers',
        '--hidden-import', 'src.ui',
        '--hidden-import', 'src.utils',
        '--clean',                      # Clean cache
        'run.py'                        # Entry point
    ]
    
    print(f"Building {version_string}...")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return False

def verify_executable():
    """Verify the executable was created and works."""
    exe_path = Path('dist/LogViewer.exe')
    
    if not exe_path.exists():
        print("❌ Executable not found!")
        return False
    
    print(f"✅ Executable created: {exe_path}")
    print(f"📁 Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
    
    # Test the executable
    try:
        result = subprocess.run([str(exe_path), '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Executable test passed!")
            return True
        else:
            print(f"❌ Executable test failed with code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Executable test timed out")
        return False
    except Exception as e:
        print(f"❌ Executable test error: {e}")
        return False

def main():
    """Main build process."""
    print("🚀 Log Viewer Executable Builder")
    print("=" * 40)
    
    # Clean previous builds
    clean_build_dirs()
    
    # Build executable
    if build_executable():
        # Wait a moment for files to be fully written
        print("Waiting for build to complete...")
        time.sleep(2)
        
        # Verify the result
        if verify_executable():
            print("\n🎉 Build completed successfully!")
            print(f"📁 Executable location: {Path('dist/LogViewer.exe').absolute()}")
            print("\nYou can now distribute LogViewer.exe to users who don't have Python installed!")
        else:
            print("\n❌ Build verification failed!")
            sys.exit(1)
    else:
        print("\n❌ Build failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
