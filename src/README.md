# Log Viewer - Modular Source Code

This directory contains the modular source code for the Log Viewer application, organized into logical packages for better maintainability and extensibility.

## Directory Structure

```
src/
├── __init__.py              # Main package initialization
├── main.py                  # Application entry point
├── managers/                # Business logic managers
│   ├── __init__.py         # Managers package
│   ├── theme_manager.py    # Theme management
│   ├── filter_manager.py   # Filtering system
│   ├── config_manager.py   # Configuration management
│   └── file_manager.py     # File handling and monitoring
├── ui/                     # User interface components
│   ├── __init__.py         # UI package
│   ├── main_window.py      # Main application window
│   ├── dialogs/            # Dialog windows
│   └── widgets/            # Custom UI widgets
└── utils/                  # Utility modules
    ├── __init__.py         # Utils package
    └── constants.py        # Application constants
```

## Package Descriptions

### Managers Package (`src/managers/`)
Contains the core business logic classes that handle different aspects of the application:

- **ThemeManager**: Manages color themes and theme switching
- **FilterManager**: Handles advanced filtering with multiple modes
- **ConfigManager**: Manages application configuration and user preferences
- **FileManager**: Handles file reading, monitoring, and encoding detection

### UI Package (`src/ui/`)
Contains all user interface components:

- **main_window.py**: The main LogViewerApp class with the complete GUI
- **dialogs/**: Settings dialogs, theme preview, and help windows
- **widgets/**: Custom UI components like enhanced text widgets

### Utils Package (`src/utils/`)
Contains utility modules and constants:

- **constants.py**: All application constants and default values

## Running the Application

### Option 1: From the root directory
```bash
python run.py
```

### Option 2: From the src directory
```bash
cd src
python main.py
```

### Option 3: Direct module execution
```bash
python -m src.main
```

## Adding New Features

### Adding a New Manager
1. Create a new file in `src/managers/`
2. Implement your manager class
3. Add it to `src/managers/__init__.py`
4. Import and use it in the main window

### Adding a New UI Component
1. Create a new file in `src/ui/` or appropriate subdirectory
2. Implement your UI component
3. Add it to the appropriate `__init__.py` file
4. Import and use it in the main window

### Adding New Constants
1. Add constants to `src/utils/constants.py`
2. Update `src/utils/__init__.py` to export them
3. Import and use them throughout the application

## Benefits of This Structure

1. **Separation of Concerns**: Each class has a single responsibility
2. **Maintainability**: Easier to find and modify specific functionality
3. **Testability**: Individual components can be unit tested
4. **Reusability**: Managers can be imported and used independently
5. **Collaboration**: Multiple developers can work on different components
6. **Documentation**: Each module can have focused documentation

## Import Patterns

```python
# Import managers
from src.managers import ThemeManager, FilterManager

# Import UI components
from src.ui import LogViewerApp

# Import utilities
from src.utils.constants import DEFAULT_THEME

# Import specific modules
from src.managers.theme_manager import ThemeManager
from src.ui.main_window import LogViewerApp
```

## Testing

Each module can be tested independently:

```bash
# Test a specific manager
python -m pytest tests/test_theme_manager.py

# Test all managers
python -m pytest tests/managers/

# Test the entire application
python -m pytest tests/
```

## Contributing

When contributing to this project:

1. Follow the existing import patterns
2. Add new constants to the constants module
3. Update appropriate `__init__.py` files
4. Add comprehensive docstrings
5. Include type hints for all public methods
6. Write tests for new functionality
