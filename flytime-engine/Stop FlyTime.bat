@echo off
title FlyTime - Stopping...
cd /d "%~dp0"

echo.
echo  Local Fly Intelligence Platform is disabled.
echo  It runs on Oracle Cloud — see oracle-cloud\README.md
echo.
echo  Cleaning up any leftover local processes...
echo.

if exist "data\monitor.pid" (
    for /f %%i in (data\monitor.pid) do (
        taskkill /PID %%i /F >nul 2>&1
    )
    del "data\monitor.pid" >nul 2>&1
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8787.*LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)

taskkill /FI "WINDOWTITLE eq FlyTime Platform*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FlyTime Monitor*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FlyTime Dashboard*" /F >nul 2>&1

echo  Done.
echo.
pause
