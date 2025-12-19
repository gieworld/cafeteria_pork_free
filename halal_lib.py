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
            
        menu_text = ""
        rows = menu_table.find_all('tr')
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
    try:
        if os.path.exists("corrections.json"):
            with open("corrections.json", "r", encoding="utf-8") as f:
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
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
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
          "verdict": "SAFE/WORTH IT/NOT WORTH/NONE",
          "main_dish": "name of main protein/dish",
          "safe_items": ["list items you can eat"],
          "skip_items": ["list items with pork to skip"],
          "reason": "brief explanation"
        }},
        {{"time": "Lunch", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
        {{"time": "Dinner", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}}
      ]
    }},
    {{
      "name": "Professor Cafeteria",
      "type": "package",
      "meals": [
        {{"time": "Breakfast", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
        {{"time": "Lunch", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
        {{"time": "Dinner", "verdict": "...", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}}
      ]
    }},
    {{
      "name": "A La Carte",
      "type": "individual",
      "safe_options": ["list of pork-free dishes to order"],
      "avoid": ["list of dishes containing pork"]
    }}
  ]
}}
"""
    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"Error analyzing with Gemini: {e}")
        return None
