@echo off
echo ========================================
echo 🍱 KIT Pork-Free Menu Updater
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

rem Check if there are changes to commit
git diff --quiet data/menu_data.json
if %errorlevel% == 0 (
    echo.
    echo ✨ No changes detected. Skipping GitHub update.
    goto :done
)

git add data/menu_data.json
git commit -m "🍱 Manual Menu Update"

rem Only push if commit succeeded
if %errorlevel% == 0 (
    echo Pushing changes...
    git push
    if %errorlevel% == 0 (
        echo.
        echo ✅ Menu Updated Successfully!
        echo Your web dashboard will update in ~1 minute.
    ) else (
        echo.
        echo ⚠️ Git push failed (Network or Auth issue^).
    )
) else (
    echo.
    echo ⚠️ Nothing to commit.
)

:done

if "%1"=="auto" exit /b
echo.
pause
