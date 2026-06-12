@echo off
title FlyTime - Status
cd /d "%~dp0"

echo.
echo  ============================================
echo   FlyTime Status Check
echo  ============================================
echo.

if exist "data\monitor.pid" (
    echo  Monitor: RUNNING
) else (
    echo  Monitor: NOT RUNNING  ^(double-click Start FlyTime.bat^)
)
echo.

python main.py report

echo.
echo  --------------------------------------------
if exist "logs\monitor.log" (
    echo  Last few log lines:
    echo.
    powershell -Command "Get-Content 'logs\monitor.log' -Tail 5"
) else (
    echo  No log file yet - start the monitor first.
)
echo.
echo  --------------------------------------------
echo  Dashboard: http://127.0.0.1:8787/
echo.
pause
