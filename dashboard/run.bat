@echo off
setlocal EnableDelayedExpansion
title CampusOps - Launcher

cd /d "%~dp0"

echo ===============================================================================
echo            CAMPUSOPS: INTELLIGENT CAMPUS OPERATIONS PLATFORM
echo            Target: SRM Easwari Engineering College (Autonomous)
echo ===============================================================================
echo.

REM -----------------------------------------------------------------------------
REM 1. Check or generate .env file
REM -----------------------------------------------------------------------------
if not exist ".env" (
    echo [INFO] .env file not found. Creating from .env.example...
    copy ".env.example" ".env" >nul
    if errorlevel 1 (
        echo [ERROR] Failed to copy .env.example to .env.
        pause
        exit /b 1
    )
    echo [OK] Created .env configuration file.
) else (
    echo [OK] .env configuration file found.
)

REM -----------------------------------------------------------------------------
REM 2. Locate or create Python virtual environment
REM -----------------------------------------------------------------------------
set "PYTHON_EXE="

if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0venv\bin\python.exe" (
    set "PYTHON_EXE=%~dp0venv\bin\python.exe"
)

if not defined PYTHON_EXE (
    call :FIND_SYSTEM_PYTHON
)

if not defined PYTHON_EXE (
    echo.
    echo ===============================================================================
    echo [ERROR] Python 3.11+ was not found on your system!
    echo.
    echo Please install Python 3.11 or higher from https://www.python.org/downloads/
    echo Make sure to check the box: "Add python.exe to PATH"
    echo ===============================================================================
    echo.
    pause
    exit /b 1
)

echo [OK] Using Python: %PYTHON_EXE%

REM -----------------------------------------------------------------------------
REM 3. Check / Install Backend Dependencies
REM -----------------------------------------------------------------------------
"%PYTHON_EXE%" -c "import fastapi, uvicorn, asyncpg, pydantic" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing backend dependencies from backend\requirements.txt...
    "%PYTHON_EXE%" -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install backend requirements.
        pause
        exit /b 1
    )
)
echo [OK] Backend Python dependencies ready.

REM -----------------------------------------------------------------------------
REM 4. Verify Node.js & Frontend Dependencies
REM -----------------------------------------------------------------------------
set "NPM_CMD="
where npm.cmd >nul 2>&1
if !errorlevel! equ 0 (
    set "NPM_CMD=npm.cmd"
) else (
    where npm >nul 2>&1
    if !errorlevel! equ 0 (
        set "NPM_CMD=npm"
    )
)

if not defined NPM_CMD (
    echo [ERROR] Node.js or npm was not found. Please install Node.js 18+.
    pause
    exit /b 1
)

if not exist "%~dp0frontend\node_modules" (
    echo [INFO] Installing frontend dependencies: node_modules...
    pushd "%~dp0frontend"
    call !NPM_CMD! install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend packages.
        popd
        pause
        exit /b 1
    )
    popd
)
echo [OK] Frontend dependencies ready.

REM -----------------------------------------------------------------------------
REM 5. Check PostgreSQL Service / Port 5432
REM -----------------------------------------------------------------------------
echo [INFO] Checking PostgreSQL on port 5432...

REM Attempt to start local Windows service if stopped (ignores if already running)
net start postgresql-x64-18 >nul 2>&1
net start postgresql-x64-16 >nul 2>&1
net start postgresql >nul 2>&1

REM Test port 5432 via Python socket check
"%PYTHON_EXE%" -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 5432)); s.close()" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PostgreSQL is not yet responding on localhost:5432.
    echo If your database is not running, you can start it via:
    echo   - Windows Service: net start postgresql-x64-18
    echo   - Or with Docker:  docker compose up -d postgres
    echo Continuing launch...
) else (
    echo [OK] PostgreSQL is reachable on localhost:5432.
)

REM -----------------------------------------------------------------------------
REM 6. Launch Backend and Frontend in separate windows
REM -----------------------------------------------------------------------------
echo.
echo ===============================================================================
echo Starting CampusOps Servers...
echo   * Backend:  http://localhost:8000 (Docs: http://localhost:8000/docs)
echo   * Frontend: http://localhost:5173
echo ===============================================================================
echo.

REM Launch FastAPI backend in a new console window
start "CampusOps Backend" cmd /k "cd /d %~dp0backend && \"%PYTHON_EXE%\" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Launch Vite frontend in a new console window
start "CampusOps Frontend" cmd /k "cd /d %~dp0frontend && %NPM_CMD% run dev"

REM Wait 3 seconds and open the browser
ping 127.0.0.1 -n 4 >nul
start http://localhost:5173

echo.
echo ===============================================================================
echo Servers launched successfully in separate windows!
echo If this is your first time running CampusOps, initialize and seed the database
echo by running: setup_database.bat
echo ===============================================================================
echo.
ping 127.0.0.1 -n 4 >nul
exit /b 0

REM =============================================================================
REM SUBROUTINE: Find or create Python virtual environment
REM =============================================================================
:FIND_SYSTEM_PYTHON
echo [INFO] Virtual environment not found. Searching for system Python 3...
set "SYSTEM_PY="

py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "SYSTEM_PY=py -3"
    goto :CREATE_VENV
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "SYSTEM_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :CREATE_VENV
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "SYSTEM_PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :CREATE_VENV
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "SYSTEM_PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :CREATE_VENV
)
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "SYSTEM_PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    goto :CREATE_VENV
)
if exist "C:\Program Files\Python312\python.exe" (
    set "SYSTEM_PY=C:\Program Files\Python312\python.exe"
    goto :CREATE_VENV
)
if exist "C:\Program Files\Python311\python.exe" (
    set "SYSTEM_PY=C:\Program Files\Python311\python.exe"
    goto :CREATE_VENV
)
if exist "C:\Program Files\Python313\python.exe" (
    set "SYSTEM_PY=C:\Program Files\Python313\python.exe"
    goto :CREATE_VENV
)

python -c "import sys; sys.exit(0)" >nul 2>&1
if !errorlevel! equ 0 (
    set "SYSTEM_PY=python"
    goto :CREATE_VENV
)

exit /b 1

:CREATE_VENV
echo [INFO] Creating Python virtual environment using !SYSTEM_PY!...
!SYSTEM_PY! -m venv "%~dp0venv"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    exit /b 1
)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0venv\bin\python.exe" (
    set "PYTHON_EXE=%~dp0venv\bin\python.exe"
)
exit /b 0
