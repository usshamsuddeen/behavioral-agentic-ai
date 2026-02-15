@echo off
title Behavioral Agentic AI v3.0
color 0A

echo.
echo  ============================================================
echo       BEHAVIORAL AGENTIC AI v3.0 - ONE-CLICK LAUNCHER
echo  ============================================================
echo.

REM Go to the folder where this .bat file lives
cd /d "%~dp0"

REM ------------------------------------------------------------
REM  STEP 1: Check Python
REM ------------------------------------------------------------
echo  [1/5] Checking Python...
python --version
if errorlevel 1 (
    echo  ERROR: Python not found. Install from python.org
    pause
    exit /b 1
)
echo.

REM ------------------------------------------------------------
REM  STEP 2: Create venv if needed
REM ------------------------------------------------------------
echo  [2/5] Setting up virtual environment...
cd backend
if not exist "venv\Scripts\activate.bat" (
    echo         Creating new venv...
    python -m venv venv
)
echo         OK
echo.

REM ------------------------------------------------------------
REM  STEP 3: Install dependencies
REM ------------------------------------------------------------
echo  [3/5] Installing dependencies (this may take a minute)...
call venv\Scripts\activate.bat
pip install --upgrade pip -q >nul 2>&1
pip install -r requirements.txt -q
echo         OK - Dependencies installed
echo.

REM ------------------------------------------------------------
REM  STEP 4: Create data folders
REM ------------------------------------------------------------
echo  [4/5] Creating data directories...
if not exist "data" mkdir data
if not exist "data\vector_store" mkdir data\vector_store
if not exist "data\chroma_db" mkdir data\chroma_db
if not exist "logs" mkdir logs
echo         OK
echo.

REM ------------------------------------------------------------
REM  STEP 5: Launch everything
REM ------------------------------------------------------------
echo  [5/5] Starting servers...

REM Start Backend in a new minimized window
start "BAI-Backend" /min cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
echo         Backend starting on port 8000...

REM Start Frontend in a new minimized window
start "BAI-Frontend" /min cmd /k "cd /d %~dp0frontend && python -m http.server 5500"
echo         Frontend starting on port 5500...

echo.
echo  Waiting 10 seconds for servers to start...
timeout /t 10 /nobreak >nul

REM Open landing page
start http://localhost:5500/index.html
echo         Browser opened!

echo.
echo  ============================================================
echo.
echo    SYSTEM IS RUNNING!
echo.
echo    Landing Page : http://localhost:5500
echo    Login        : http://localhost:5500/pages/login.html
echo    Dashboard    : http://localhost:5500/pages/dashboard.html
echo    API Docs     : http://localhost:8000/docs
echo.
echo    Two minimized windows are running in background.
echo    Close this window or press Ctrl+C to exit.
echo    (Backend and Frontend will keep running in their windows)
echo.
echo  ============================================================
echo.
pause
