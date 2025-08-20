# Log Viewer - Real-Time Log File Monitor

A powerful, cross-platform GUI application for monitoring log files in real-time with advanced filtering and viewing capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.6 or higher
- No external dependencies required (uses only Python standard library)

### Installation & Run
```bash
# Clone or download the project
cd FileUpdater

# Run the application (Recommended)
python run.py

# Or run from the source directory
python src/main.py

# Or open a specific log file
python run.py --file /path/to/your/log.txt

# Customize refresh rate (in milliseconds)
python run.py --file log.txt --refresh 1000

# Specify encoding
python run.py --file log.txt --encoding utf-16

# Choose a theme
python run.py --theme light
python run.py --theme sunset
```

## ✨ Key Features

- **Real-time monitoring** with configurable refresh rates (100ms - 5000ms)
- **Smart file handling** - automatically detects file rotation and truncation
- **Advanced filtering** with 6 modes (Contains, Starts With, Ends With, Regex, Exact Match, Not Contains)
- **Auto-encoding detection** for UTF-8, UTF-16, and other formats
- **Memory efficient** - limits displayed lines to prevent memory issues
- **Multiple color themes** (Dark, Light, Sunset) with easy switching
- **Comprehensive configuration system** with persistent user preferences
- **Cross-platform** support (Windows, macOS, Linux)
- **Modular architecture** for easy maintenance and extension

## 📁 File Structure

```
FileUpdater/
├── src/                      # ✅ Modular source code
│   ├── __init__.py          # Main package
│   ├── main.py              # ✅ Application entry point
│   ├── managers/            # ✅ Business logic managers
│   │   ├── __init__.py
│   │   ├── theme_manager.py
│   │   ├── filter_manager.py
│   │   ├── config_manager.py
│   │   └── file_manager.py
│   ├── ui/                  # ✅ User interface components
│   │   ├── __init__.py
│   │   ├── main_window.py   # ✅ Complete main application
│   │   └── dialogs/         # ✅ Dialog windows
│   │       ├── __init__.py
│   │       └── settings_dialog.py
│   └── utils/               # ✅ Utility modules
│       ├── __init__.py
│       └── constants.py
├── run.py                   # ✅ Launcher script (recommended)
├── FileUpdater.py          # Original monolithic file (preserved)
├── FileUpdater.code-workspace  # VS Code workspace
├── icons/                   # Theme-specific icons
└── Docs/                    # Documentation folder
    ├── README.md            # This file
    ├── USER_GUIDE.md        # Detailed user instructions
    ├── DEVELOPER_GUIDE.md   # Development and contribution guide
    ├── FEATURES.md          # Complete feature documentation
    └── CHANGELOG.md         # Version history and changes
```

## 🔧 Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--file` | `-f` | Path to log file to open | None |
| `--refresh` | `-r` | Refresh interval in milliseconds | 500 |
| `--encoding` | `-e` | File encoding (auto/utf-8/utf-16/etc.) | auto |
| `--theme` | `-t` | Color theme (dark/light/sunset) | dark |

## 🏗️ Architecture

The application now uses a **modular architecture** with clear separation of concerns:

- **`managers/`** - Business logic (themes, filtering, configuration, file handling)
- **`ui/`** - User interface components and dialogs
- **`utils/`** - Shared constants and utilities
- **`main.py`** - Application entry point and CLI parsing

## 📖 Documentation

- **[User Guide](USER_GUIDE.md)** - Complete user instructions and tips
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Development setup and contribution
- **[Features](FEATURES.md)** - Detailed feature documentation
- **[Changelog](CHANGELOG.md)** - Version history and updates

## 🤝 Contributing

See [Developer Guide](DEVELOPER_GUIDE.md) for information on contributing to this project.

## 📄 License

This project is open source. Free to use, modify, and distribute.

---

**Need help?** Check the [User Guide](USER_GUIDE.md) for detailed instructions or the [Developer Guide](DEVELOPER_GUIDE.md) for technical details.
