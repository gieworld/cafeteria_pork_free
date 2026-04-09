@echo off
set PYTHONIOENCODING=utf-8
echo ========================================
echo 🍱 KIT Pork-Free Menu Updater
echo ========================================
echo.

echo 1. Generating Menu Data (Scraping ^& AI Analysis)...
echo    PLEASE WAIT (This takes about 30 seconds)...
venv\Scripts\python.exe scripts/gen_menu.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error generating menu!
    pause
    exit /b
)

echo.
echo 2. Uploading to GitHub...

rem Check if there are changes to commit
git diff --quiet data/menu_data.json
if %errorlevel% neq 0 (
    echo.
    echo 📝 Changes detected. Committing...
    git add data/menu_data.json
    git commit -m "🍱 Manual Menu Update"
) else (
    echo.
    echo ✨ No new menu changes to commit.
)

echo.
echo 3. Syncing with GitHub...
git push
if %errorlevel% == 0 (
    echo.
    echo ✅ Cloud Sync Successful!
    echo Your web dashboard will update in ~1 minute.
) else (
    echo.
    echo ⚠️ Cloud Sync failed (Network or Auth issue^).
)

:done

if "%1"=="auto" exit /b
echo.
pause
