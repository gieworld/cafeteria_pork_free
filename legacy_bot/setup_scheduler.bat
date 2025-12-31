@echo off
echo ========================================
echo Kumoh Pork-Free Bot - Morning Scrape Setup
echo ========================================
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo Script directory: %SCRIPT_DIR%
echo.

:MENU
echo What would you like to do?
echo.
echo 1. Enable morning scrape (runs at 6:50 AM every weekday)
echo 2. Disable morning scrape (remove scheduled task)
echo 3. Check status (see if morning scrape is enabled)
echo 4. Test now (run morning scrape immediately)
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto ENABLE
if "%choice%"=="2" goto DISABLE
if "%choice%"=="3" goto STATUS
if "%choice%"=="4" goto TEST
if "%choice%"=="5" goto EXIT
echo Invalid choice! Please try again.
echo.
goto MENU

:ENABLE
echo.
echo Enabling morning scrape...
schtasks /create ^
    /tn "KumohPorkFreeBot_MorningScrape" ^
    /tr "cmd /c cd /d \"%SCRIPT_DIR%\" && python morning_scrape.py" ^
    /sc weekly ^
    /d MON,TUE,WED,THU,FRI ^
    /st 06:50 ^
    /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Morning scrape ENABLED!
    echo The bot will automatically scrape menus every weekday at 6:50 AM.
    echo Working directory: %SCRIPT_DIR%
) else (
    echo.
    echo ❌ Failed to enable morning scrape
    echo Make sure you run this as Administrator!
)
echo.
pause
goto MENU

:DISABLE
echo.
echo Disabling morning scrape...
schtasks /delete /tn "KumohPorkFreeBot_MorningScrape" /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Morning scrape DISABLED!
    echo The automatic menu scraping has been removed.
    echo You'll need to use /refresh command manually.
) else (
    echo.
    echo ⚠️ Morning scrape task not found or already disabled.
)
echo.
pause
goto MENU

:STATUS
echo.
echo Checking morning scrape status...
schtasks /query /tn "KumohPorkFreeBot_MorningScrape" >nul 2>&1

if %errorlevel% == 0 (
    echo.
    echo ✅ Morning scrape is ENABLED
    echo.
    schtasks /query /tn "KumohPorkFreeBot_MorningScrape" /fo list | findstr /C:"Status" /C:"Last Run" /C:"Last Result" /C:"Next Run"
    echo.
    echo Last Result codes:
    echo   0 = Success
    echo   -2147024894 = File not found (working directory issue)
) else (
    echo.
    echo ❌ Morning scrape is DISABLED
    echo The automatic menu scraping is not scheduled.
)
echo.
pause
goto MENU

:TEST
echo.
echo Running morning scrape now...
echo This will analyze all weekdays (Mon-Fri) and update the cache.
echo.
cd /d "%SCRIPT_DIR%"
python morning_scrape.py
echo.
echo Test complete! Check the output above for results.
echo.
pause
goto MENU

:EXIT
echo.
echo Goodbye! 👋
exit
