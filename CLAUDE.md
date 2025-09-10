# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Log Viewer** application - a real-time log file monitoring GUI application built with Python and Tkinter. It features advanced filtering, theme management, and intelligent file handling with encoding detection.

## Running the Application

```bash
# Recommended way to run (from project root)
python run.py

# Alternative methods
python src/main.py
python -m src.main

# With command line options
python run.py --file /path/to/log.txt --theme light --refresh 1000
```

Command line options:
- `--file, -f`: Path to log file to open
- `--refresh, -r`: Refresh interval in milliseconds (default 500)
- `--encoding, -e`: File encoding (default auto-detection)
- `--theme, -t`: Color theme (dark, light, sunset, ocean, forest, midnight, sepia, high_contrast)

## Build System

### Creating Executable
```bash
# Windows (automated)
build_exe.bat

# Cross-platform Python script
python build_exe.py
```

The build process uses PyInstaller with a custom spec file (`LogViewer.spec`) and automatically bumps the build number in `src/utils/constants.py`.

## Architecture

The application follows a modular architecture with clear separation of concerns:

### Core Managers (`src/managers/`)
- **ThemeManager**: Manages color themes and visual appearance
- **FilterManager**: Handles advanced filtering with 6 modes (Contains, Starts With, Ends With, Regex, Exact Match, Not Contains)
- **ConfigManager**: Manages persistent configuration and user preferences
- **FileManager**: Handles file reading, monitoring, encoding detection, and file rotation/truncation

### UI Layer (`src/ui/`)
- **main_window.py**: Main LogViewerApp class with complete GUI implementation
- **dialogs/settings_dialog.py**: Comprehensive settings interface with 5 tabs
- **dialogs/loading_dialog.py**: Loading dialog for file operations

### Utilities (`src/utils/`)
- **constants.py**: All application constants, defaults, and theme definitions

## Key Technical Features

### Memory Management
- Uses `collections.deque` with dynamic `maxlen` for efficient line buffering
- Configurable maximum lines displayed (default from `MAX_LINES_DEFAULT`)
- Automatic buffer trimming based on user preferences

### File Handling Intelligence
- **Encoding Detection**: Automatic BOM detection and UTF-16 heuristics
- **File Rotation**: Detects when log files are rotated or truncated
- **Smart Tailing**: Only reads new content, handles growing files efficiently
- **Mixed Encoding**: Can detect and handle files with mixed encodings

### Filtering System
- **Debounced Updates**: 150ms delay to prevent UI lag during typing
- **Multiple Modes**: Contains, Starts With, Ends With, Regex, Exact Match, Not Contains
- **History Management**: Maintains last 20 filter patterns
- **Case Sensitivity**: Toggle for all filter modes

### Configuration System
- **JSON-based**: Stored in platform-appropriate config directories
- **Persistent State**: Window geometry, theme, filter preferences
- **Import/Export**: Configuration can be saved/loaded as JSON files

## Development Patterns

### Import Structure
```python
# From root directory or when using run.py
from src.managers import ThemeManager, FilterManager, ConfigManager, FileManager
from src.ui.main_window import LogViewerApp
from src.utils.constants import APP_NAME, DEFAULT_THEME

# From within src/ directory
from managers import ThemeManager
from ui.main_window import LogViewerApp
from utils.constants import APP_NAME
```

### Manager Pattern
Each manager class follows a consistent pattern:
- Constructor initializes state
- Public methods for external interaction
- Private methods (prefixed with `_`) for internal logic
- Clear separation of concerns

### Error Handling
- Graceful degradation when files are inaccessible
- Exception handling in file I/O operations  
- User-friendly error messages in status bar
- Fallback behaviors for missing configurations

## Testing

No formal test suite exists currently. Testing is done through:
- Manual verification of modular imports
- Application launch testing with various command line options
- File handling verification with different log types
- Cross-platform compatibility testing

## Configuration Locations

- **Windows**: `%LOCALAPPDATA%\LogViewer\`
- **Unix/Linux/macOS**: `~/.logviewer/`
- **Files**: `config.json`, `filter_prefs.txt`

## Performance Considerations

- **Refresh Rate**: Configurable from 100ms to 5000ms
- **File Size Limits**: Files >2MB start tailing from end
- **Line Limits**: Configurable maximum displayed lines
- **Memory Efficient**: Bounded buffers prevent memory leaks
- **Debounced UI**: Prevents excessive redraws during rapid changes

## Key Files to Understand

1. `src/main.py` - Application entry point and CLI parsing
2. `src/ui/main_window.py` - Main GUI class (~2500+ lines, core functionality)
3. `src/managers/file_manager.py` - File handling and monitoring logic
4. `src/managers/filter_manager.py` - Advanced filtering implementation
5. `src/utils/constants.py` - All configuration constants and defaults