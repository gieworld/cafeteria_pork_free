@echo off
echo ========================================
echo 🤖 KIT Auto-Update Setup (Task Scheduler)
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
echo 1. Enable Daily Auto-Update (hourly, 8:00-12:00)
echo 2. Disable Auto-Update
echo 3. Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto ENABLE
if "%choice%"=="2" goto DISABLE
if "%choice%"=="3" goto EXIT
goto MENU

:ENABLE
echo.
echo Scheduling update_menu.bat to run hourly from 8:00 to 12:00...
rem Older builds installed this under a different name. Remove it first, or a
rem machine set up back then ends up running the update twice every morning.
schtasks /delete /tn "KITPorkFree_AutoUpdate" /f >nul 2>&1
schtasks /create ^
    /tn "KumohPorkFree_AutoUpdate" ^
    /tr "cmd /c cd /d \"%SCRIPT_DIR%\" && update_menu.bat auto >> update.log 2>&1" ^
    /sc daily ^
    /st 08:00 ^
    /ri 60 ^
    /du 04:00 ^
    /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Auto-Update ENABLED!
    rem Hourly because the site posts a new week at no fixed hour (a 9:00-only run
rem left Monday's dashboard a week stale). An unchanged menu makes no AI call, so
rem the repeats are free. Output goes to update.log: scheduled runs have no console.
echo Your PC will check for menu changes every hour from 8:00 to 12:00.
    echo It will update the website automatically in the background.
) else (
    echo.
    echo ❌ Failed (Run as Administrator!)
)
echo.
pause
goto MENU

:DISABLE
echo.
echo Removing Auto-Update task...
schtasks /delete /tn "KumohPorkFree_AutoUpdate" /f
schtasks /delete /tn "KITPorkFree_AutoUpdate" /f >nul 2>&1
echo.
echo ✅ Auto-Update DISABLED.
echo.
pause
goto MENU

:EXIT
exit
