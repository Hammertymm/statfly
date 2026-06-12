@echo off
title FlyTime - Stopping...
cd /d "%~dp0"

echo.
echo  Stopping FlyTime...
echo.

REM Stop via saved process ID (cleanest method)
if exist "data\monitor.pid" (
    for /f %%i in (data\monitor.pid) do (
        taskkill /PID %%i /F >nul 2>&1
        if not errorlevel 1 echo  Monitor stopped.
    )
    del "data\monitor.pid" >nul 2>&1
) else (
    echo  No monitor PID file found - may already be stopped.
)

REM Close the named background windows if still open
taskkill /FI "WINDOWTITLE eq FlyTime Monitor*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FlyTime Dashboard*" /F >nul 2>&1

echo.
echo  FlyTime stopped. You can close this window.
echo.
pause
