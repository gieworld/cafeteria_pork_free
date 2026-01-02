@echo off
echo ========================================
echo 🍱 Kumoh Pork-Free Menu Updater
echo ========================================
echo.

echo 1. Generating Menu Data (Scraping ^& AI Analysis)...
echo    PLEASE WAIT (This takes about 30 seconds)...
python scripts/gen_menu.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error generating menu!
    pause
    exit /b
)

echo.
echo 2. Uploading to GitHub...
git add data/menu_data.json
git commit -m "🍱 Manual Menu Update"
git push

if %errorlevel% == 0 (
    echo.
    echo ✅ Menu Updated Successfully!
    echo Your web dashboard will update in ~1 minute.
) else (
    echo.
    echo ⚠️ Git push failed (maybe no changes or network issue)
)

if "%1"=="auto" exit /b
echo.
pause
