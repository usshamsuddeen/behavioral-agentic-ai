@echo off
title Behavioral Agentic AI - Frontend Server
color 0B

echo.
echo ========================================================
echo    BEHAVIORAL AGENTIC AI - Frontend Server
echo    Opens Landing Page in Browser
echo ========================================================
echo.

cd /d "%~dp0"

:: Open the landing page in default browser
start "" "index.html"

echo    Frontend opened in your default browser!
echo.
echo    Pages available:
echo    - index.html      (Landing Page)
echo    - pages/dashboard.html
echo    - pages/chat.html
echo    - pages/analytics.html
echo    - pages/escalations.html
echo    - pages/settings.html
echo.

:: Optional: Start a simple HTTP server if Python is available
python --version >nul 2>&1
if not errorlevel 1 (
    echo    Starting local HTTP server on port 5500...
    echo    Open: http://localhost:5500
    echo.
    python -m http.server 5500
)

pause
