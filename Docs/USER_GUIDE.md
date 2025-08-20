# Log Viewer - User Guide

Complete guide to using the Log Viewer application for monitoring log files in real-time.

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Operations](#basic-operations)
3. [Advanced Features](#advanced-features)
4. [Troubleshooting](#troubleshooting)
5. [Tips & Tricks](#tips--tricks)

## 🚀 Getting Started

### First Launch
1. **Run the application (Recommended):**
   ```bash
   python run.py
   ```

2. **Alternative launch methods:**
   ```bash
   # From source directory
   python src/main.py
   
   # Direct module execution
   python -m src.main
   ```

3. **Open a log file:**
   - Use **File → Open…** from the menu
   - Or drag and drop a log file onto the application
   - Or use command line: `python run.py --file log.txt`

4. **The interface will show:**
   - **Toolbar** with controls and file path
   - **Text area** displaying log content
   - **Status bar** showing current status and file size
   - **Line numbers** (toggleable) for easy navigation

## 🔧 Basic Operations

### Opening Files
- **Menu method:** File → Open… → Navigate to your log file
- **Command line:** `python run.py --file /path/to/log.txt`
- **Supported formats:** Any text-based log file (`.txt`, `.log`, `.out`, etc.)

### Viewing Controls
- **Pause/Resume:** Click the Pause button to stop auto-refresh
- **Clear:** Remove all displayed content (doesn't affect the file)
- **Auto-scroll:** Keep checked to automatically scroll to new content
- **Word Wrap:** Toggle between wrapped and unwrapped text display
- **Line Numbers:** Toggle line number display for easy reference

### Theme Selection
- **View → Theme** menu to choose from available themes
- **Dark theme** (default) - Easy on the eyes for long viewing sessions
- **Light theme** - Classic light background for bright environments
- **Sunset theme** - Warm purple and cream colors for a unique look
- **Ocean theme** - Deep blue interface with light blue text
- **Forest theme** - Dark green interface with light green text
- **Midnight theme** - Pure black with matrix green text
- **Sepia theme** - Warm cream background with brown text
- **High Contrast theme** - Maximum contrast white/black interface
- **Theme persistence** - Your choice is remembered between sessions
- **Quick switching** - Use Ctrl+T to cycle through themes

### Configuration & Settings
- **Settings → Preferences...** for comprehensive configuration dialog
- **Settings → Save Current Settings as Default** to make current setup permanent
- **Settings → Export/Import Settings** for backup and sharing configurations
- **Automatic saving** of window size, position, and preferences

### Refresh Settings
- **Refresh Rate:** Adjust from 100ms (fast) to 5000ms (slow)
  - Lower values = more responsive but higher CPU usage
  - Higher values = less CPU usage but slower updates
- **Default:** 500ms (good balance for most use cases)

### Memory Management
- **Max Lines:** Control how many lines to keep in memory
  - Range: 1,000 to 200,000 lines
  - Default: 10,000 lines
  - Higher values use more memory but show more history

## 🔍 Advanced Features

### Advanced Filtering
The Log Viewer includes a powerful filtering system with multiple modes:

#### Filter Modes
- **Contains** - Text appears anywhere in the line (default)
- **Starts With** - Line begins with the specified text
- **Ends With** - Line ends with the specified text
- **Regular Expression** - Use regex patterns for complex matching
- **Exact Match** - Line exactly matches the filter text
- **Not Contains** - Line does NOT contain the specified text

#### Using Filters
1. **Select mode** from the Mode dropdown
2. **Enter text** in the Filter box
3. **Toggle case sensitivity** with the Case checkbox
4. **Results update automatically** as you type (with debouncing)
5. **Use filter history** with the ▼ button (last 20 filters)

#### Regular Expression Examples
- `^ERROR` - Lines starting with "ERROR"
- `\d{4}-\d{2}-\d{2}` - Date pattern (YYYY-MM-DD)
- `(ERROR|WARN)` - Lines with ERROR or WARN
- `.*exception.*` - Lines containing "exception"

**Filter Tips:**
- Use regex mode for complex patterns
- Filter history remembers your searches
- Case sensitivity affects all modes
- Invalid regex shows error indicator
- Filter updates in real-time with 300ms debouncing

### Encoding Detection
The application automatically detects common encodings:
- **UTF-8** (with or without BOM)
- **UTF-16** (Little Endian and Big Endian)
- **Fallback** to UTF-8 if detection fails

**Manual encoding override:**
```bash
python run.py --file log.txt --encoding utf-16
```

### File Rotation Handling
- **Automatic detection** of file rotation/truncation
- **Seamless reopening** when files are rotated
- **No manual intervention** required

### Theme System
The Log Viewer includes eight beautiful color themes:

#### Dark Theme (Default)
- **Background:** Deep gray (#1e1e1e)
- **Text:** Light gray (#d4d4d4)
- **Best for:** Low-light environments, long viewing sessions

#### Light Theme
- **Background:** Pure white (#ffffff)
- **Text:** Black (#000000)
- **Best for:** Bright environments, classic text editor feel

#### Sunset Theme
- **Background:** Deep purple (#2d1b3d)
- **Text:** Warm cream (#f4e4bc)
- **Best for:** Unique aesthetic, reduced eye strain

#### Ocean Theme
- **Background:** Deep blue (#0a1929)
- **Text:** Light blue (#b8d4e3)
- **Best for:** Calming blue tones, professional environments

#### Forest Theme
- **Background:** Dark green (#1a2f1a)
- **Text:** Light green (#c8e6c9)
- **Best for:** Nature-inspired interface, easy on the eyes

#### Midnight Theme
- **Background:** Pure black (#000000)
- **Text:** Matrix green (#00ff00)
- **Best for:** Classic terminal look, maximum contrast

#### Sepia Theme
- **Background:** Warm cream (#f4f1e8)
- **Text:** Dark brown (#5d4037)
- **Best for:** Vintage aesthetic, reduced blue light

#### High Contrast Theme
- **Background:** Pure white (#ffffff)
- **Text:** Pure black (#000000)
- **Best for:** Accessibility, maximum readability

**Theme Features:**
- **Live preview** with the 🎨 button in the toolbar
- **Automatic saving** of your preference
- **Quick switching** with Ctrl+T keyboard shortcut
- **Menu access** via View → Theme

## 🛠️ Troubleshooting

### Common Issues

#### File Won't Open
- **Check file permissions** - ensure you have read access
- **Verify file exists** - check the path is correct
- **Check file size** - extremely large files may take time to open

#### Encoding Problems
- **Garbled text:** Try specifying encoding manually
- **Missing characters:** Check if file uses special encoding
- **Command line:** `--encoding utf-16` for Windows logs

#### Performance Issues
- **High CPU usage:** Increase refresh rate (e.g., 1000ms)
- **Slow updates:** Decrease refresh rate (e.g., 100ms)
- **Memory issues:** Reduce max lines setting

#### Filter Not Working
- **Check case sensitivity** setting
- **Verify filter text** is correct
- **Wait for debouncing** (300ms delay)

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Failed to open file" | File doesn't exist or no permission | Check path and permissions |
| "Filter error" | Filter processing failed | Clear filter and try again |
| "Open failed" | File system error | Check if file is locked by another process |

## 💡 Tips & Tricks

### Performance Optimization
- **Large log files:** Start with higher refresh rates (1000ms+)
- **Real-time monitoring:** Use lower refresh rates (100-500ms)
- **Memory management:** Adjust max lines based on available RAM

### Efficient Filtering
- **Start broad:** Use short filter terms first
- **Refine gradually:** Add more specific terms
- **Case sensitivity:** Use for exact matches

### File Management
- **Multiple instances:** Run separate instances for different logs
- **File watching:** Monitor system logs, application logs, etc.
- **Backup logs:** Keep original files safe

### Keyboard Shortcuts
- **Ctrl+O:** Open file dialog
- **Ctrl+F:** Focus filter box
- **Ctrl+R:** Focus filter box (alternative)
- **Ctrl+W:** Toggle word wrap
- **Ctrl+P:** Toggle pause/resume
- **Ctrl+T:** Cycle through themes
- **Escape:** Clear current filter

### Settings Management
- **Settings → Preferences...** - Open comprehensive configuration dialog
- **Settings → Save Current Settings as Default** - Save current state
- **Settings → Reset to Defaults** - Restore factory settings
- **Settings → Export/Import Settings** - Backup and restore configurations

## 📱 Platform-Specific Notes

### Windows
- **Default font:** Consolas (monospaced)
- **File paths:** Use backslashes or forward slashes
- **Encoding:** UTF-16 logs are common

### macOS
- **Default font:** Menlo (monospaced)
- **File paths:** Forward slashes
- **Permissions:** May need to grant accessibility permissions

### Linux
- **Default font:** System monospace font
- **File paths:** Forward slashes
- **Permissions:** Check read permissions on log files

## 🔗 Related Documentation

- **[Features](FEATURES.md)** - Complete feature list
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Technical details
- **[README](README.md)** - Quick start and overview

---

**Need more help?** Check the troubleshooting section above or refer to the [Developer Guide](DEVELOPER_GUIDE.md) for technical details.
