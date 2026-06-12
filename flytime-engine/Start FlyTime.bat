@echo off
title FlyTime - Starting...
cd /d "%~dp0"

echo.
echo  ============================================
echo   FlyTime Live Monitor
echo  ============================================
echo.
echo  Starting in 3 seconds...
echo  - A monitor window will open (minimize it, don't close it)
echo  - Your web browser will open to the dashboard
echo.
echo  IMPORTANT: Keep your laptop awake and plugged in.
echo  It stops collecting when the laptop sleeps.
echo.
timeout /t 3 /nobreak >nul

REM Start the data collector in its own minimized window
start "FlyTime Monitor" /MIN cmd /c "cd /d "%~dp0" && python run_service.py"

REM Give the collector a moment to start
timeout /t 4 /nobreak >nul

REM Start the dashboard in its own minimized window
start "FlyTime Dashboard" /MIN cmd /c "cd /d "%~dp0" && python main.py dashboard"

REM Open the dashboard in the default browser
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8787/"

echo.
echo  Done! FlyTime is now running.
echo.
echo  What's open:
echo    - Browser tab at http://127.0.0.1:8787/  (your dashboard)
echo    - Two minimized windows in the taskbar (Monitor + Dashboard)
echo.
echo  To check it's working: double-click "Check Status.bat"
echo  To stop everything:    double-click "Stop FlyTime.bat"
echo.
pause
