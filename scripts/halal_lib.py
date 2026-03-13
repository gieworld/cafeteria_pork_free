import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration
CACHE_FILE = "menu_cache.json"
CACHE_DURATION_HOURS = 24

URLS = {
    "Student Cafeteria": "https://www.kumoh.ac.kr/ko/restaurant01.do",
    "Professor Cafeteria": "https://www.kumoh.ac.kr/ko/restaurant02.do",
    "A La Carte": "https://www.kumoh.ac.kr/ko/restaurant04.do"
}

# --- CACHE FUNCTIONS ---
def load_cache():
    """Load cached menu analysis."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_cache(day, analysis, menu_hash=None):
    """Save menu analysis to cache with menu hash for change detection."""
    cache = load_cache()
    # If overwriting, preserve existing menu_hash if new one not provided (though usually provided)
    # Actually, simplistic approach: just overwrite.
    cache[day] = {
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis,
        "menu_hash": menu_hash
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def save_full_cache(cache_data):
    """Save the entire cache dictionary (used by bulk operations)."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

def is_cache_valid(day):
    """Check if cache for a day is still valid."""
    cache = load_cache()
    if day not in cache:
        return False
    
    try:
        cached_time = datetime.fromisoformat(cache[day]["timestamp"])
        age = datetime.now() - cached_time
        return age.total_seconds() < (CACHE_DURATION_HOURS * 3600)
    except:
        return False

def get_cached_analysis(day):
    """Get cached analysis for a day."""
    cache = load_cache()
    if day in cache:
        return cache[day].get("analysis")
    return None

def get_menu_hash(menu_text):
    """Generate hash of menu text to detect changes."""
    return hashlib.md5(menu_text.encode()).hexdigest()

def has_menu_changed(day, current_hash):
    """Check if menu has changed since last cache."""
    cache = load_cache()
    if day not in cache:
        return True
    cached_hash = cache[day].get("menu_hash")
    return cached_hash != current_hash

# --- DATA FETCHING ---
def get_menu_text(url):
    """Scrapes the weekly menu table from the website."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        menu_table = soup.find('table') 
        if not menu_table:
            return "No menu found."
            
        rows = menu_table.find_all('tr')
        # Check if table has only headers (1 row) or no rows
        if len(rows) <= 1:
            return "No menu data available."
            
        menu_text = ""
        for row in rows:
            cols = row.find_all(['th', 'td'])
            row_data = [ele.text.strip().replace('\n', ' ') for ele in cols]
            menu_text += " | ".join(row_data) + "\n"
            
        return menu_text
    except Exception as e:
        return f"Error scraping: {e}"

def fetch_all_menus():
    """Fetches menus from all cafeterias and returns combined string."""
    print("📥 Fetching menus...")
    full_menu = ""
    for name, url in URLS.items():
        print(f"   - {name}...")
        full_menu += f"--- {name} ---\n{get_menu_text(url)}\n\n"
    return full_menu

def load_corrections():
    """Load manual corrections from corrections.json."""
    # corrections.json is in repo root (parent of scripts/)
    lib_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(lib_dir)
    corrections_file = os.path.join(repo_root, "corrections.json")
    
    try:
        if os.path.exists(corrections_file):
            with open(corrections_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("corrections", [])
    except Exception as e:
        print(f"Warning: Could not load corrections: {e}")
    return []

# --- AI ANALYSIS ---
def analyze_with_gemini(menu_data, target_day):
    """Sends menu text to Gemini to find pork-free options."""
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return None

    genai.configure(api_key=GEMINI_API_KEY)
    
    # Try the requested model, fallback if needed
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Load manual corrections
    corrections = load_corrections()
    corrections_text = ""
    if corrections:
        corrections_text = "\n\nMANUAL CORRECTIONS (OVERRIDE AI):\n"
        for corr in corrections:
            corrections_text += f"- {corr['dish']} at {corr['cafeteria']}: {corr['status'].upper()} - {corr['reason']}\n"

    prompt = f"""
You are a PORK-FREE food assistant for foreign students in Korea who don't eat pork.

IMPORTANT: We are checking for PORK only, not full halal certification. 
This is a PORK-FREE guide, not halal certification.

TARGET DAY: {target_day}

CONTEXT:
- Student & Professor Cafeteria = PACKAGE MEAL (you get everything, cannot choose individual items)
- A La Carte = INDIVIDUAL ORDER (you can pick specific safe dishes)

PORK DETECTION RULES:
- CONTAINS PORK: Pork, Ham, Bacon, Sausage, Spam, Tonkatsu/Donkatsu, Mandu/Dumplings (usually pork), Budae-jjigae, Gamjatang, Jeyuk, Menchi Katsu
- PORK-FREE: Chicken, Beef, Fish, Seafood, Tofu, Eggs, Vegetables
- SUSPICIOUS (may contain pork): Ramen (pork broth), Kimchi Stew, Soft Tofu Stew, Curry (often contains pork in Korea)
{corrections_text}
PACKAGE MEAL WORTHINESS:
- SAFE = All items are pork-free
- WORTH IT = Main dish is pork-free, but some side dishes contain pork (can skip those sides)
- NOT WORTH = Main dish contains pork (don't buy this package)
- NONE = No meal available

TRANSLATION RULE (CRITICAL):
- ALL values in the JSON (including `main_dish`, `safe_items`, `skip_items`, `reason`, `safe_options`, `avoid`) MUST be translated into English.
- Do NOT output Korean characters in these fields.

MENU DATA:
{menu_data}

    Return ONLY this JSON (no markdown):
    {{
      "day": "{target_day}",
      "cafeterias": [
        {{
          "name": "Student Cafeteria",
          "type": "package",
          "meals": [
            {{
              "time": "Breakfast",
              "price": "e.g. 5000원",
              "selling_time": "e.g. 08:00~09:00",
              "verdict": "SAFE/WORTH IT/NOT WORTH/NONE",
              "main_dish": "name of main protein/dish",
              "safe_items": ["list items you can eat"],
              "skip_items": ["list items with pork to skip"],
              "reason": "brief explanation"
            }},
            {{"time": "Lunch", "price": "...", "selling_time": "...", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
            {{"time": "Dinner", "price": "...", "selling_time": "...", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}}
          ]
        }},
        {{
          "name": "Professor Cafeteria",
          "type": "package",
          "meals": [
            {{"time": "Breakfast", "price": "...", "selling_time": "...", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
            {{"time": "Lunch", "price": "...", "selling_time": "...", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
            {{"time": "Dinner", "price": "...", "selling_time": "...", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}}
          ]
        }},
        {{
          "name": "A La Carte",
          "type": "individual",
          "price": "Range or specific price",
          "selling_time": "Operating hours",
          "safe_options": ["Dish Name 1", "Dish Name 2"],
          "avoid": ["Dish Name 3", "Dish Name 4"]
        }}
      ]
    }}

IMPORTANT: For A La Carte, safe_options and avoid MUST be simple string arrays of dish names only.
Do NOT use objects/dicts. Just plain strings like: ["Chicken Steak", "Beef Soup"]
"""
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Call Gemini using the official SDK inside our venv
            # We explicitly request JSON output for better accuracy
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                ),
                request_options={"timeout": 60}
            )
            
            # Clean and parse response
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            
            # Try to find JSON in the response if it's wrapped in other text
            if not cleaned_text.startswith("{"):
                # Look for JSON object in the text
                start = cleaned_text.find("{")
                end = cleaned_text.rfind("}") + 1
                if start != -1 and end > start:
                    cleaned_text = cleaned_text[start:end]
            
            result = json.loads(cleaned_text)
            
            # Fix any dict items in safe_options/avoid (fallback)
            for cafe in result.get("cafeterias", []):
                if cafe.get("type") == "individual":
                    # Convert dicts to strings if AI misbehaved
                    safe = cafe.get("safe_options", [])
                    cafe["safe_options"] = [item if isinstance(item, str) else item.get("menu", str(item)) for item in safe]
                    
                    avoid = cafe.get("avoid", [])
                    cafe["avoid"] = [item if isinstance(item, str) else item.get("menu", str(item)) for item in avoid]
            
            # Success! Return result
            return result
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parsing error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                print(f"   ❌ Failed to parse JSON after {max_retries} attempts")
                print(f"   Raw response: {cleaned_text[:200]}...")
                
        except Exception as e:
            error_msg = str(e)
            print(f"   ⚠️ Gemini API error on attempt {attempt + 1}/{max_retries}: {error_msg}")
            
            # Check if it's a rate limit error
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                print(f"   ⏳ Rate limit detected, waiting {retry_delay * 2} seconds...")
                import time
                time.sleep(retry_delay * 2)
            elif attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                print(f"   ❌ Failed after {max_retries} attempts")
    
    return None
