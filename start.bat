@echo off

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python 3.6 or higher first.
    pause
    exit /b 1
)

REM Start Video Auto Splitter Tool
echo Starting Video Auto Splitter Tool...
python video_splitter.py

REM Show error message if program exits abnormally
if %errorlevel% neq 0 (
    echo Program error occurred.
    pause
)