@echo off
REM ═══════════════════════════════════════════════════════════════
REM  BEHAVIORAL AGENTIC AI — STOP ALL SERVERS
REM ═══════════════════════════════════════════════════════════════

title Stopping Behavioral Agentic AI...
color 0C

echo.
echo  Stopping all Behavioral AI servers...
echo.

REM Kill backend (uvicorn on 8000)
echo  [1/3] Stopping Backend (port 8000)...
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8000.*LISTEN" 2^>nul') do (
    taskkill /PID %%p /F >nul 2>&1
    echo        [OK] Killed PID %%p
)

REM Kill frontend (http.server on 5500)
echo  [2/3] Stopping Frontend (port 5500)...
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":5500.*LISTEN" 2^>nul') do (
    taskkill /PID %%p /F >nul 2>&1
    echo        [OK] Killed PID %%p
)

REM Close background windows
echo  [3/3] Closing background windows...
taskkill /fi "windowtitle eq Behavioral AI*" /F >nul 2>&1

echo.
echo  [OK] All servers stopped.
echo.
timeout /t 3 >nul
