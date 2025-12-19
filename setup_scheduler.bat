@echo off
echo ========================================
echo Setting up automatic morning scrape
echo ========================================
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0

echo This will create a Windows Task to run every weekday at 6:50 AM
echo The menu will be scraped and analyzed before 7 AM
echo.
echo Script directory: %SCRIPT_DIR%
echo.

REM Create the task
schtasks /create /tn "KumohPorkFreeBot_MorningScrape" /tr "python %SCRIPT_DIR%morning_scrape.py" /sc weekly /d MON,TUE,WED,THU,FRI /st 06:50 /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Task created successfully!
    echo.
    echo The bot will now automatically scrape menus every weekday at 6:50 AM
    echo Cache will be ready before users wake up!
    echo.
    echo To verify: Open Task Scheduler and look for "KumohPorkFreeBot_MorningScrape"
    echo To delete: schtasks /delete /tn "KumohPorkFreeBot_MorningScrape" /f
) else (
    echo.
    echo ❌ Failed to create task
    echo Make sure you run this as Administrator!
)

echo.
pause
