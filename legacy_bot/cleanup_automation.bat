@echo off
echo ========================================
echo Cleaning up Kumoh Bot Automations
echo ========================================
echo.

echo 1. Removing Morning Scrape Task...
schtasks /delete /tn "KumohPorkFreeBot_MorningScrape" /f 2>nul
if %errorlevel% == 0 (
    echo    ✅ Removed Morning Scrape task
) else (
    echo    ⚠️ Task not found (already removed)
)

echo.
echo 2. Removing Auto-Start Task...
schtasks /delete /tn "KumohPorkFreeBot_AutoStart" /f 2>nul
if %errorlevel% == 0 (
    echo    ✅ Removed Auto-Start task
) else (
    echo    ⚠️ Task not found (already removed)
)

echo.
echo ========================================
echo Cleanup Complete!
echo The bot will no longer run automatically on this PC.
echo ========================================
echo.
pause
