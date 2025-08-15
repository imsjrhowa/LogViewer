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
1. **Run the application:**
   ```bash
   python FileUpdater.py
   ```

2. **Open a log file:**
   - Use **File → Open…** from the menu
   - Or drag and drop a log file onto the application
   - Or use command line: `python FileUpdater.py --file log.txt`

3. **The interface will show:**
   - **Toolbar** with controls and file path
   - **Text area** displaying log content
   - **Status bar** showing current status and file size

## 🔧 Basic Operations

### Opening Files
- **Menu method:** File → Open… → Navigate to your log file
- **Command line:** `python FileUpdater.py --file /path/to/log.txt`
- **Supported formats:** Any text-based log file (`.txt`, `.log`, `.out`, etc.)

### Viewing Controls
- **Pause/Resume:** Click the Pause button to stop auto-refresh
- **Clear:** Remove all displayed content (doesn't affect the file)
- **Auto-scroll:** Keep checked to automatically scroll to new content
- **Word Wrap:** Toggle between wrapped and unwrapped text display

### Theme Selection
- **View → Theme** menu to choose from available themes
- **Dark theme** (default) - Easy on the eyes for long viewing sessions
- **Light theme** - Classic light background for bright environments
- **Sunset theme** - Warm purple and cream colors for a unique look
- **Theme persistence** - Your choice is remembered between sessions

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

### Live Filtering
1. **Enter text** in the Filter box
2. **Results update automatically** as you type
3. **Toggle case sensitivity** with the checkbox
4. **Filter is applied** to all displayed content

**Filter Tips:**
- Use partial words or phrases
- Combine with case sensitivity for precise matching
- Filter updates in real-time with 150ms debouncing

### Encoding Detection
The application automatically detects common encodings:
- **UTF-8** (with or without BOM)
- **UTF-16** (Little Endian and Big Endian)
- **Fallback** to UTF-8 if detection fails

**Manual encoding override:**
```bash
python FileUpdater.py --file log.txt --encoding utf-16
```

### File Rotation Handling
- **Automatic detection** of file rotation/truncation
- **Seamless reopening** when files are rotated
- **No manual intervention** required

### Theme System
The Log Viewer includes three beautiful color themes:

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
- **Wait for debouncing** (150ms delay)

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
- **Ctrl+W:** Toggle word wrap
- **Ctrl+P:** Toggle pause/resume
- **Ctrl+T:** Cycle through themes

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
