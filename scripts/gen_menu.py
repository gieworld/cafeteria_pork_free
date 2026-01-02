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
    
    # 2. Check for Changes (Optimization)
    print(f"🔑 Menu Hash: {menu_hash}")
    
    existing_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except:
            pass
            
    old_hash = existing_data.get("menu_hash")
    
    if old_hash == menu_hash:
        print("\n✨ Menu has NOT changed. Using existing analysis (Savings: 100% Tokens).")
        # We still might want to update the "updated_at" to show we checked
        existing_data["updated_at"] = datetime.now().isoformat()
        
        # Save just the timestamp update
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Data touched at {DATA_FILE}")
        return

    # 3. Analyze ALL Weekdays (Mon-Fri)
    # We want the dashboard to show the whole week
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    week_data = {}
    
    print("\n🤖 Menu CHANGED! Starting AI analysis...")
    print("   (This uses Gemini tokens - approx 5 calls)")
    
    for day in days:
        print(f"   > Analyzing {day}...")
        result = halal_lib.analyze_with_gemini(full_menu, day)
        if result:
            week_data[day] = result
        else:
            print(f"     ⚠️ Analysis failed for {day}")
    
    # 4. Build Final JSON Structure
    output = {
        "updated_at": datetime.now().isoformat(),
        "menu_hash": menu_hash,
        "week_data": week_data
    }
    
    # 5. Save
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Helper: Saved NEW analysis to {DATA_FILE}")
    print("=" * 50)

if __name__ == "__main__":
    main()
