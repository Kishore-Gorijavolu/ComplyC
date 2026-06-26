@echo off
setlocal

echo ==========================================
echo Building ComplyC GUI EXE
echo ==========================================

C:\Python311\python.exe -m pip install --upgrade pyinstaller pycparser pyyaml

if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

C:\Python311\python.exe -m PyInstaller ^
--onefile ^
--windowed ^
--name ComplyC-GUI ^
--add-data "fake_libc_include;fake_libc_include" ^
--add-data "rules;rules" ^
complyc_gui.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo Build complete.
echo EXE location: dist\ComplyC-GUI.exe
pause
