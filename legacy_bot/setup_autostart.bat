@echo off
echo ========================================
echo Kumoh Pork-Free Bot - Auto-Start Setup
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
echo 1. Enable auto-start (bot runs on Windows login)
echo 2. Disable auto-start (remove startup task)
echo 3. Check status (see if auto-start is enabled)
echo 4. Exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto ENABLE
if "%choice%"=="2" goto DISABLE
if "%choice%"=="3" goto STATUS
if "%choice%"=="4" goto EXIT
echo Invalid choice! Please try again.
echo.
goto MENU

:ENABLE
echo.
echo Enabling auto-start...
schtasks /create ^
    /tn "KumohPorkFreeBot_AutoStart" ^
    /tr "cmd /c cd /d \"%SCRIPT_DIR%\" && python kumoh_halal_bot.py --bot" ^
    /sc onlogon ^
    /rl highest ^
    /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Auto-start ENABLED!
    echo The bot will now start automatically when you log in to Windows.
) else (
    echo.
    echo ❌ Failed to enable auto-start
    echo Make sure you run this as Administrator!
)
echo.
pause
goto MENU

:DISABLE
echo.
echo Disabling auto-start...
schtasks /delete /tn "KumohPorkFreeBot_AutoStart" /f

if %errorlevel% == 0 (
    echo.
    echo ✅ Auto-start DISABLED!
    echo The bot will no longer start automatically.
    echo You'll need to run start_bot.bat manually.
) else (
    echo.
    echo ⚠️ Auto-start task not found or already disabled.
)
echo.
pause
goto MENU

:STATUS
echo.
echo Checking auto-start status...
schtasks /query /tn "KumohPorkFreeBot_AutoStart" >nul 2>&1

if %errorlevel% == 0 (
    echo.
    echo ✅ Auto-start is ENABLED
    echo.
    schtasks /query /tn "KumohPorkFreeBot_AutoStart" /fo list | findstr /C:"Status" /C:"Last Run" /C:"Next Run"
) else (
    echo.
    echo ❌ Auto-start is DISABLED
    echo The bot will not start automatically on login.
)
echo.
pause
goto MENU

:EXIT
echo.
echo Goodbye! 👋
exit
