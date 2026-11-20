@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

if not exist "output" mkdir output
if not exist "logs" mkdir logs

set "PY_CMD="
py -3 --version >nul 2>&1 && set "PY_CMD=py -3"
if not defined PY_CMD (
    python --version >nul 2>&1 && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python was not found in PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment using %PY_CMD%...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv
        pause
        exit /b 1
    )
)

set "VENV_PY=.venv\Scripts\python.exe"

REM Ensure requirements are installed if pandas is missing
"%VENV_PY%" -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo Installing project dependencies from requirements.txt...
    "%VENV_PY%" -m pip install --upgrade pip
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Check your internet connection.
        pause
        exit /b 1
    )
)

echo Starting RoastTrack Kenya Simulation Engine...
start "RoastTrack_Sim" /B "%VENV_PY%" realtime_simulation.py > logs\realtime-simulation.log 2>&1

timeout /t 2 /nobreak >nul

echo Starting Scenario Terminal...
start "RoastTrack_Term" /B "%VENV_PY%" realtime_terminal.py > logs\scenario-terminal.log 2>&1

echo Starting Desktop Dashboard...
"%VENV_PY%" scientific_ui.py > logs\ui-error.log 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] scientific_ui.py exited with an error. Check logs\ui-error.log:
    type logs\ui-error.log
    pause
)

echo Stopping background workers...
taskkill /F /FI "WINDOWTITLE eq RoastTrack_*" >nul 2>&1
for /f "tokens=2" %%i in ('wmic process where "name='python.exe' and commandline like '%%realtime_%%'" get processid 2^>nul ^| findstr [0-9]') do taskkill /F /PID %%i >nul 2>&1

endlocal