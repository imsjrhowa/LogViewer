@echo off
echo 🚀 Log Viewer Executable Builder
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.6+ and try again.
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ Failed to install PyInstaller
        pause
        exit /b 1
    )
    echo ✅ PyInstaller installed
) else (
    echo ✅ PyInstaller already installed
)

echo.
echo 🔨 Building executable...
python build_exe.py

if errorlevel 1 (
    echo.
    echo ❌ Build failed! Check the error messages above.
    pause
    exit /b 1
)

echo.
echo 🎉 Build completed successfully!
echo 📁 Executable location: dist\LogViewer.exe
echo.
echo You can now distribute LogViewer.exe to users who don't have Python installed!
echo.
pause
