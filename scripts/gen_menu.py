import os
import sys
import json
from datetime import datetime

# Path setup - ensure we can import halal_lib from scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)  # Add scripts/ to path for halal_lib

import halal_lib

DATA_FILE = os.path.join(BASE_DIR, "data", "menu_data.json")

def main():
    print("=" * 50)
    print(f"🌍 Web Dashboard Generator - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # Authenticate
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Missing GEMINI_API_KEY! Set it in env or secrets.")
        # For local testing, ensure .env is loaded (halal_lib does this)
    
    # 1. Fetch Menu
    print("📥 Fetching menus from Kumoh website...")
    full_menu = halal_lib.fetch_all_menus()
    menu_hash = halal_lib.get_menu_hash(full_menu)
    print(f"🔑 Menu Hash: {menu_hash}")

    # 2. Analyze ALL Weekdays (Mon-Fri) always
    # We want the dashboard to show the whole week
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    week_data = {}
    
    print("🤖 Analyzing week...")
    for day in days:
        print(f"   > Analyzing {day}...")
        # Note: We rely on Gemini caching inside halal_lib if we want, 
        # but for the web app, let's just force fresh or use simplistic approach.
        # Actually halal_lib.analyze_with_gemini calls the API.
        
        # Optimization: We could cache locally to avoid re-generating if hash same.
        # But since valid GitHub Actions run daily, we might just run fresh.
        # Let's try to be smart if possible, but simplest is just run.
        result = halal_lib.analyze_with_gemini(full_menu, day)
        if result:
            week_data[day] = result
    
    # 3. Build Final JSON Structure
    output = {
        "updated_at": datetime.now().isoformat(),
        "menu_hash": menu_hash,
        "week_data": week_data
    }
    
    # 4. Save
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Saved web data to {DATA_FILE}")
    print("=" * 50)

if __name__ == "__main__":
    main()
