@echo off
echo ========================================
echo Fixing Kumoh Pork-Free Bot Scheduler
echo ========================================
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo Script directory: %SCRIPT_DIR%
echo.

REM Delete old task if exists
echo Removing old task...
schtasks /delete /tn "KumohPorkFreeBot_MorningScrape" /f 2>nul

REM Create new task with WORKING DIRECTORY
echo Creating new task with correct settings...
schtasks /create ^
    /tn "KumohPorkFreeBot_MorningScrape" ^
    /tr "cmd /c cd /d \"%SCRIPT_DIR%\" && python morning_scrape.py" ^
    /sc weekly ^
    /d MON,TUE,WED,THU,FRI ^
    /st 06:50 ^
    /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Task created successfully!
    echo.
    echo The bot will now automatically scrape menus every weekday at 6:50 AM
    echo Working directory is correctly set to: %SCRIPT_DIR%
    echo.
    echo To verify: Open Task Scheduler and look for "KumohPorkFreeBot_MorningScrape"
    echo To test now: python morning_scrape.py
) else (
    echo.
    echo ❌ Failed to create task
    echo Make sure you run this as Administrator!
)

echo.
pause
