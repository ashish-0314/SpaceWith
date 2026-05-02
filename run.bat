@echo off
echo ============================================
echo  Gemini Screen Assistant - Launcher
echo ============================================

:: Try different Python launchers
set PYTHON=

where python 2>nul | findstr /v "WindowsApps" > temp_py.txt 2>&1
if %ERRORLEVEL% == 0 (
    set /p PYTHON=<temp_py.txt
    del temp_py.txt
    goto :found
)
del temp_py.txt 2>nul

if exist "C:\Program Files\Python313\python.exe" (
    set PYTHON=C:\Program Files\Python313\python.exe
    goto :found
)
if exist "C:\Program Files\Python312\python.exe" (
    set PYTHON=C:\Program Files\Python312\python.exe
    goto :found
)
if exist "C:\Program Files\Python311\python.exe" (
    set PYTHON=C:\Program Files\Python311\python.exe
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
    goto :found
)

echo [ERROR] Python not found. Please install from https://python.org
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:found
echo Using Python: %PYTHON%
echo.
echo Installing dependencies...
"%PYTHON%" -m pip install -r requirements.txt --quiet

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo Starting Gemini Screen Assistant...
"%PYTHON%" main.py
pause
