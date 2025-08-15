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

The Log Viewer follows a **Model-View-Controller (MVC)** pattern with these main components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GUI Layer     │    │  File Handler   │    │  Polling Engine │
│  (Tkinter)     │◄──►│  (TailReader)   │◄──►│  (Timer-based)  │
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
- **Separation of Concerns:** UI, file handling, and polling are separate
- **Memory Efficiency:** Bounded buffers prevent memory leaks
- **Error Resilience:** Graceful handling of file system issues
- **Cross-Platform:** Uses only standard library components

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

# Install development dependencies (if any)
pip install -r requirements-dev.txt  # Future: when we add dev deps

# Run the application
python FileUpdater.py
```

### IDE Configuration
- **VS Code:** Use the provided `.code-workspace` file
- **PyCharm:** Mark the project root as source root
- **Vim/Emacs:** Standard Python development setup

## 🏛️ Code Structure

### File Organization
```
FileUpdater.py          # Main application file
├── Imports & Constants
├── TailReader Class    # File handling logic
├── LogViewerApp Class  # Main GUI application
└── Main Function       # Entry point & CLI parsing
```

### Key Constants
```python
MAX_LINES_DEFAULT = 10_000      # Default line limit
DEFAULT_REFRESH_MS = 500        # Default refresh rate
DEFAULT_ENCODING = "auto"       # Default encoding detection
```

## 🔧 Key Classes

### TailReader Class
**Purpose:** Efficiently reads growing text files with smart encoding detection.

**Key Methods:**
- `open(start_at_end=True)`: Opens file and positions cursor
- `read_new_text()`: Reads only new content since last read
- `_check_rotation_or_truncate()`: Detects file changes

**Encoding Detection Logic:**
1. **BOM Detection:** Check for UTF-16/UTF-8 byte order marks
2. **Heuristic Fallback:** Detect UTF-16 by NUL byte frequency
3. **Safe Fallback:** Use UTF-8 with error replacement

**File Rotation Handling:**
- **Inode Tracking:** Monitor device/inode changes
- **Size Checking:** Detect truncation events
- **Automatic Recovery:** Reopen file when needed

### LogViewerApp Class
**Purpose:** Main GUI application managing the user interface and coordination.

**Key Components:**
- **Toolbar:** Control panel with all user settings
- **Text Widget:** Main display area for log content
- **Status Bar:** Real-time status and file information
- **Menu System:** File operations and application control

**State Management:**
- **File State:** Current file path and reader
- **UI State:** Pause, filter, wrap, scroll settings
- **Buffer State:** Line storage and filtering

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
# Debounced filtering with 150ms delay
def _on_filter_change(self):
    if self._filter_job is not None:
        try:
            self.after_cancel(self._filter_job)
        except Exception:
            pass
    self._filter_job = self.after(150, self._rebuild_view)
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
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_tail_reader.py

# Run with coverage
python -m pytest --cov=FileUpdater tests/
```

### Test Structure
```
tests/
├── test_tail_reader.py      # File handling tests
├── test_log_viewer_app.py   # GUI application tests
├── test_integration.py      # End-to-end tests
└── fixtures/                # Test data and files
```

### Test Categories
- **Unit Tests:** Individual class/method testing
- **Integration Tests:** Component interaction testing
- **Performance Tests:** Large file handling
- **Platform Tests:** Cross-platform compatibility

## 🚀 Future Improvements

### High Priority
1. **Syntax Highlighting:** Support for common log formats
2. **Multiple File Tabs:** Monitor multiple logs simultaneously
3. **Search & Replace:** Advanced text search functionality
4. **Custom Themes:** Light/dark mode toggle

### Medium Priority
1. **Plugin System:** Extensible log format support
2. **Remote File Support:** SSH, FTP, HTTP log monitoring
3. **Statistics Dashboard:** Log analysis and metrics
4. **Export Functionality:** Save filtered results

### Low Priority
1. **CustomTkinter UI:** Modern-looking interface
2. **Database Backend:** For extremely large logs
3. **Alert System:** Pattern-based notifications
4. **Log Parsing:** Structured log format support

### Implementation Roadmap
```
Phase 1: Core Improvements (1-2 months)
├── Syntax highlighting
├── Multiple file tabs
└── Search functionality

Phase 2: Advanced Features (2-3 months)
├── Plugin system
├── Remote file support
└── Statistics dashboard

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
