# Log Viewer - Developer Guide

Technical documentation for developers who want to understand, modify, or contribute to the Log Viewer application.

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Code Structure](#code-structure)
4. [Key Classes](#key-classes)
5. [Contributing Guidelines](#contributing-guidelines)
6. [Testing](#testing)
7. [Future Improvements](#future-improvements)

## 🏗️ Architecture Overview

The Log Viewer now follows a **modular architecture** with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI Layer      │    │  Managers       │    │  Utils          │
│  (Tkinter)     │◄──►│  (Business      │◄──►│  (Constants,    │
│                 │    │   Logic)        │    │   Helpers)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  File System    │
                    │  (OS Interface) │
                    └─────────────────┘
```

### Design Principles
- **Separation of Concerns:** UI, business logic, and utilities are separate
- **Modular Design:** Each component has a single responsibility
- **Memory Efficiency:** Bounded buffers prevent memory leaks
- **Error Resilience:** Graceful handling of file system issues
- **Cross-Platform:** Uses only standard library components
- **Maintainability:** Clean, organized code structure

## 🛠️ Development Setup

### Prerequisites
- **Python 3.6+** (tested on 3.6, 3.8, 3.9, 3.10, 3.11)
- **Git** for version control
- **VS Code** (recommended) with Python extension

### Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd FileUpdater

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the application (Recommended)
python run.py

# Or run from source
python src/main.py

# Or direct module execution
python -m src.main
```

### IDE Configuration
- **VS Code:** Use the provided `.code-workspace` file
- **PyCharm:** Mark the project root as source root
- **Vim/Emacs:** Standard Python development setup

## 🏛️ Code Structure

### New Modular Organization
```
src/                           # Main package
├── __init__.py               # Package metadata
├── main.py                   # Application entry point & CLI parsing
├── managers/                 # Business logic managers
│   ├── __init__.py          # Manager exports
│   ├── theme_manager.py     # Theme management & color schemes
│   ├── filter_manager.py    # Advanced filtering system
│   ├── config_manager.py    # Configuration & preferences
│   └── file_manager.py      # File handling & monitoring
├── ui/                      # User interface components
│   ├── __init__.py          # UI exports
│   ├── main_window.py       # Main application window
│   └── dialogs/             # Dialog windows
│       ├── __init__.py      # Dialog exports
│       └── settings_dialog.py # Comprehensive settings dialog
└── utils/                   # Utility modules
    ├── __init__.py          # Utility exports
    └── constants.py         # Application constants & defaults
```

### Legacy File
- **`FileUpdater.py`** - Original monolithic file (preserved for reference)

## 🔧 Key Classes

### ThemeManager Class
**Purpose:** Manages application color themes and visual appearance.

**Key Methods:**
- `get_theme_names()`: Returns available theme names
- `get_theme(theme_name)`: Retrieves theme color scheme
- `set_theme(theme_name)`: Applies a specific theme

**Features:**
- Three built-in themes: Dark, Light, Sunset
- Theme persistence across sessions
- Consistent color scheme management

### FilterManager Class
**Purpose:** Handles advanced log filtering with multiple modes and regex support.

**Key Methods:**
- `set_filter(pattern, mode, case_sensitive)`: Sets filter criteria
- `match_line(line)`: Checks if line matches current filter
- `get_mode_names()`: Returns available filter modes
- `add_to_history(pattern)`: Manages filter history

**Features:**
- Six filter modes: Contains, Starts With, Ends With, Regex, Exact Match, Not Contains
- Regular expression support with validation
- Case sensitivity control
- Filter history management (last 20 filters)

### ConfigManager Class
**Purpose:** Manages application configuration and user preferences.

**Key Methods:**
- `load_config()`: Loads configuration from file
- `save_config()`: Saves current configuration
- `get_setting(key)`: Retrieves specific setting
- `set_setting(key, value)`: Updates specific setting
- `export_config()`: Exports configuration to file
- `import_config()`: Imports configuration from file

**Features:**
- Window geometry and state persistence
- Theme preferences
- Filter settings and history
- Display options (line numbers, word wrap, auto-scroll)
- Performance settings (refresh rate, max lines)

### FileManager Class
**Purpose:** Handles file reading, monitoring, and encoding detection.

**Key Methods:**
- `open_file(path, encoding)`: Opens and monitors a file
- `read_new_text()`: Reads only new content since last read
- `_check_rotation_or_truncate()`: Detects file changes

**Features:**
- Automatic encoding detection (BOM, UTF-16 heuristics)
- File rotation and truncation handling
- Efficient tailing of growing files
- Cross-platform file handling

### LogViewerApp Class
**Purpose:** Main GUI application managing the user interface and coordination.

**Key Components:**
- **Toolbar:** Control panel with all user settings
- **Text Widget:** Main display area for log content
- **Status Bar:** Real-time status and file information
- **Menu System:** File operations and application control
- **Line Numbers:** Synchronized line number display

**State Management:**
- **File State:** Current file path and reader
- **UI State:** Pause, filter, wrap, scroll settings
- **Buffer State:** Line storage and filtering

### SettingsDialog Class
**Purpose:** Comprehensive settings interface for application configuration.

**Features:**
- Five-tab interface: Display, Performance, Themes, Filtering, File Handling
- Live previews for theme changes
- Real-time configuration updates
- Import/export functionality

## 🔍 Advanced Implementation Details

### Memory Management
```python
# Dynamic buffer sizing
self._line_buffer = collections.deque(maxlen=MAX_LINES_DEFAULT)

# Automatic trimming
def _buffer_trim(self):
    target = max(1000, int(self.max_lines.get() or MAX_LINES_DEFAULT))
    if self._line_buffer.maxlen != target:
        tmp = collections.deque(self._line_buffer, maxlen=target)
        self._line_buffer = tmp
```

### Filtering System
```python
# Debounced filtering with 300ms delay
def _on_filter_change(self):
    if self._filter_job is not None:
        try:
            self.after_cancel(self._filter_job)
        except Exception:
            pass
    self._filter_job = self.after(300, self._rebuild_view)
```

### Text Highlighting System
```python
# Highlight configuration with 5 color schemes
def _configure_highlight_tags(self):
    highlight_colors = [
        ('filter_highlight_1', '#ffeb3b', '#000000'),  # Yellow
        ('filter_highlight_2', '#4caf50', '#ffffff'),  # Green
        ('filter_highlight_3', '#2196f3', '#ffffff'),  # Blue
        ('filter_highlight_4', '#ff9800', '#000000'),  # Orange
        ('filter_highlight_5', '#9c27b0', '#ffffff'),  # Purple
    ]
    
    for tag_name, bg_color, fg_color in highlight_colors:
        self.text.tag_configure(tag_name, 
                               background=bg_color, 
                               foreground=fg_color)

# Mode-specific highlighting
def _highlight_filter_matches(self, start_pos, end_pos, line_content):
    filter_mode = self.filter_manager.current_mode
    if filter_mode == "contains":
        self._highlight_contains_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
    elif filter_mode == "regex":
        self._highlight_regex_matches(start_pos, end_pos, line_content, filter_text, case_sensitive)
    # ... other modes
```

### Polling Engine
```python
def _poll(self):
    try:
        if not self.paused.get() and self.tail and self.path:
            new_text = self.tail.read_new_text()
            if new_text:
                self._append(new_text)
                self._set_status("Updated")
    except Exception as e:
        self._set_status("Error: {}".format(e))
    finally:
        # Reschedule with current refresh rate
        interval = max(100, int(self.refresh_ms.get()))
        self.after(interval, self._poll)
```

## 🤝 Contributing Guidelines

### Code Style
- **PEP 8** compliance for Python code
- **Type hints** for all function parameters and returns
- **Docstrings** for all classes and public methods
- **Meaningful variable names** and clear comments

### Pull Request Process
1. **Fork** the repository
2. **Create feature branch:** `git checkout -b feature/amazing-feature`
3. **Make changes** following the style guide
4. **Test thoroughly** on multiple platforms
5. **Commit changes:** `git commit -m 'Add amazing feature'`
6. **Push to branch:** `git push origin feature/amazing-feature`
7. **Open Pull Request** with detailed description

### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Testing Requirements
- **Unit tests** for new functionality
- **Integration tests** for file handling
- **Cross-platform testing** (Windows, macOS, Linux)
- **Performance testing** for large files

## 🧪 Testing

### Running Tests
```bash
# Test the modular structure
python test_modular.py  # (if you recreate the test file)

# Run specific modules
python -c "from src.managers import ThemeManager; print('Import successful')"

# Test the application
python run.py --help
```

### Test Structure
```
# Current testing approach
- Manual testing of the modular structure
- Import verification for all modules
- Basic functionality testing of managers
- Application launch testing
```

### Test Categories
- **Import Tests:** Verify all modules can be imported
- **Functionality Tests:** Basic manager operations
- **Integration Tests:** Component interaction
- **Application Tests:** End-to-end functionality

## 🚀 Future Improvements

### High Priority
1. **Comprehensive Testing Suite:** Unit tests, integration tests, performance tests
2. **Performance Optimization:** Large file handling, memory management
3. **Enhanced Filtering:** Advanced regex, filter combinations
4. **Plugin System:** Extensible architecture for custom features

### Medium Priority
1. **Multiple File Tabs:** Monitor multiple logs simultaneously
2. **Search & Replace:** Advanced text search functionality
3. **Custom Themes:** User-defined color schemes
4. **Remote File Support:** SSH, FTP, HTTP log monitoring

### Low Priority
1. **CustomTkinter UI:** Modern-looking interface
2. **Database Backend:** For extremely large logs
3. **Alert System:** Pattern-based notifications
4. **Log Parsing:** Structured log format support

### Implementation Roadmap
```
Phase 1: Testing & Optimization (1-2 months)
├── Comprehensive testing suite
├── Performance optimization
└── Bug fixes and stability

Phase 2: Advanced Features (2-3 months)
├── Multiple file tabs
├── Enhanced search functionality
└── Plugin system architecture

Phase 3: Modern UI (3-4 months)
├── CustomTkinter migration
├── Custom themes
└── Enhanced UX
```

## 📚 Additional Resources

### Documentation
- **[User Guide](USER_GUIDE.md)** - End-user documentation
- **[Features](FEATURES.md)** - Complete feature list
- **[Changelog](CHANGELOG.md)** - Version history

### External References
- **Tkinter Documentation:** [Python.org](https://docs.python.org/3/library/tkinter.html)
- **Python File I/O:** [Python.org](https://docs.python.org/3/tutorial/inputoutput.html)
- **PEP 8 Style Guide:** [Python.org](https://www.python.org/dev/peps/pep-0008/)

### Community
- **GitHub Issues:** Report bugs and request features
- **Discussions:** General questions and ideas
- **Contributions:** Pull requests and code reviews

---

**Ready to contribute?** Start with the [Future Improvements](#future-improvements) section and pick a feature that interests you!
