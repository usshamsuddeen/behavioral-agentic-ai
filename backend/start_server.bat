@echo off
title Behavioral Agentic AI - Backend Server
color 0A

echo.
echo ========================================================
echo    BEHAVIORAL AGENTIC AI - Backend Setup & Run
echo    Sentiment-Aware Escalation System
echo ========================================================
echo.

cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo [1/5] Python found!
python --version
echo.

:: Check if virtual environment exists
if not exist "venv" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully!
) else (
    echo [2/5] Virtual environment already exists.
)
echo.

:: Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo       Virtual environment activated!
echo.

:: Install requirements
echo [4/5] Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)
echo       Dependencies installed successfully!
echo.

:: Create data directory if not exists
if not exist "data" (
    mkdir data
)

:: Seed database if empty
echo [5/5] Checking database...
if not exist "data\app.db" (
    echo       Seeding database with demo data...
    python seed_data.py
) else (
    echo       Database already exists.
)
echo.

echo ========================================================
echo    STARTING SERVER
echo ========================================================
echo.
echo    API Documentation: http://localhost:8000/docs
echo    Health Check:      http://localhost:8000/api/health
echo.
echo    Press Ctrl+C to stop the server
echo ========================================================
echo.

:: Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

:: Keep window open if server stops
pause
