@echo off
echo ========================================
echo 🤖 Auto-Update Setup (Task Scheduler)
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
echo 1. Enable Daily Auto-Update (Runs at 9:00 AM)
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
echo Scheduling update_menu.bat to run daily at 9:00 AM...
schtasks /create ^
    /tn "KumohPorkFree_AutoUpdate" ^
    /tr "cmd /c cd /d \"%SCRIPT_DIR%\" && update_menu.bat auto" ^
    /sc daily ^
    /st 09:00 ^
    /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Auto-Update ENABLED!
    echo Your PC will check for menu changes every morning at 9:00 AM.
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
echo.
echo ✅ Auto-Update DISABLED.
echo.
pause
goto MENU

:EXIT
exit
