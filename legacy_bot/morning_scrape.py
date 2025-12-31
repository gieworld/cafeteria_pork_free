"""
Morning Scrape Script
Runs automatically each weekday morning to fetch and cache menu analysis.
Cache is used for all user requests throughout the day.
"""
import hashlib
from datetime import datetime
import halal_lib  # Shared library

def main():
    print("=" * 50)
    print(f"🕐 Morning Scrape - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # Fetch menu
    full_menu = halal_lib.fetch_all_menus()
    menu_hash = halal_lib.get_menu_hash(full_menu)
    
    # Load existing cache to check for unchanged menus
    existing_cache = halal_lib.load_cache()

    # Analyze each weekday
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    cache = {}
    
    for day in days:
        # Check if we can reuse existing analysis (same menu hash)
        if day in existing_cache and existing_cache[day].get("menu_hash") == menu_hash:
            print(f"📦 Menu unchanged for {day}, reused cache.")
            cache[day] = existing_cache[day]
            cache[day]["timestamp"] = datetime.now().isoformat() # Update timestamp
        else:
            print(f"🤖 Analyzing {day}...")
            result = halal_lib.analyze_with_gemini(full_menu, day)
            if result:
                cache[day] = {
                    "timestamp": datetime.now().isoformat(),
                    "analysis": result,
                    "menu_hash": menu_hash
                }
    
    # Save cache
    halal_lib.save_full_cache(cache)
    
    print(f"\n✅ Cached {len(cache)} days of analysis!")
    print(f"💾 Saved to {halal_lib.CACHE_FILE}")
    print("=" * 50)

if __name__ == "__main__":
    main()
