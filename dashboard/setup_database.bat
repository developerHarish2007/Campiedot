@echo off
setlocal EnableDelayedExpansion
title CampusOps - Database Initializer and Seeder

cd /d "%~dp0"

echo ===============================================================================
echo            CAMPUSOPS: DATABASE SETUP & SEED SCRIPT
echo ===============================================================================
echo.

:: Locate Python
set "PYTHON_EXE="
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [1/3] Applying PostgreSQL DDL & Invariant Triggers...
"%PYTHON_EXE%" scripts\setup_db.py
if errorlevel 1 (
    echo [ERROR] setup_db.py failed. Please verify PostgreSQL is running and .env has correct credentials.
    pause
    exit /b 1
)

echo.
echo [2/3] Seeding SRM Easwari Campus digital twin topology and fixtures...
"%PYTHON_EXE%" scripts\seed_demo.py
if errorlevel 1 (
    echo [ERROR] seed_demo.py failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Running Invariant Verification Suite (Phase 1)...
"%PYTHON_EXE%" scripts\verify_phase1.py

echo.
echo ===============================================================================
echo Database initialization and seeding complete!
echo ===============================================================================
pause
