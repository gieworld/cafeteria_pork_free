import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
import os
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

URLS = {
    "Set Meal": "https://www.kumoh.ac.kr/ko/restaurant02.do",
    "A La Carte": "https://www.kumoh.ac.kr/ko/restaurant01.do",
}

def get_menu_hash(menu_text):
    """Generate hash of menu text to detect changes."""
    return hashlib.md5(menu_text.encode()).hexdigest()

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

MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]  # primary, fallback


def _coerce_day_result(day, result):
    """Normalize one day's result: ensure the 'day' field and string-only A La Carte lists."""
    result.setdefault("day", day)
    for cafe in result.get("cafeterias", []):
        if cafe.get("type") == "individual":
            for key in ("safe_options", "avoid"):
                items = cafe.get(key, [])
                cafe[key] = [it if isinstance(it, str) else it.get("menu", str(it)) for it in items]
    return result


def _build_week_prompt(menu_data, days, corrections_text):
    day_list = ", ".join(days)
    # One JSON object per day, keyed by day name, each matching the original per-day schema.
    return f"""
You are a PORK-FREE food assistant for foreign students in Korea who don't eat pork.

IMPORTANT: We are checking for PORK only, not full halal certification.
This is a PORK-FREE guide, not halal certification.

TARGET DAYS: {day_list}
Analyze EVERY one of these days from the weekly menu data below.

CONTEXT:
- Set Meal (restaurant02) = PACKAGE MEAL. Lunch only (11:30~13:30), 6000 won. You get all dishes, cannot choose.
- A La Carte (restaurant01) = INDIVIDUAL ORDER. Rotating daily lunch/dinner specials (11:00~14:00, 16:00~18:30). A cheap breakfast (조식, 1000 won, 08:20~10:00) is served ONLY during regular semester and is often suspended during vacations/holidays.

BREAKFAST RULE (CRITICAL - do NOT invent breakfast):
- Only report a breakfast if the menu data for that day ACTUALLY lists breakfast items (look for "조식" / "breakfast", or explicit 08:20~10:00 items).
- If the data shows NO breakfast for that day (e.g. it only lists "일품요리"/lunch-dinner specials, or shows "미운영"/not operating), set breakfast to: verdict "NONE", main_dish "Not served", reason "Breakfast not served".
- NEVER guess or fabricate a breakfast dish that is not present in the menu data.

CLOSED-DAY RULE:
- If a day shows "미운영" (not operating) or a holiday marker like "[제헌절]", treat that cafeteria as closed: Set Meal verdict "NONE", breakfast verdict "NONE", and empty safe_options/avoid lists.

ASTERISK PORK MARKER (AUTHORITATIVE - trust this first):
- The cafeteria marks items that contain pork with a leading "*". Their own note reads: "*로 표시된 항목은 돈육이 포함된 메뉴입니다." (items marked * contain pork).
- Therefore: ANY item written with a leading "*" (e.g. "*돈가스류", "*돼지국밥", "*제육덮밥", "*카츠동") DEFINITELY contains pork -> ALWAYS put it in `avoid` / mark as pork.
- WARNING: the absence of "*" does NOT guarantee pork-free. Pork can appear WITHOUT a "*", especially inside the "일품정식(...)" set-meal parentheses. So still apply the name rules below to every un-starred item.

PORK DETECTION RULES (apply by dish name, in addition to the * marker):
- CONTAINS PORK: Pork, Ham, Bacon, Sausage, Spam, Tonkatsu/Donkatsu (돈가스/카츠동), Mandu/Dumplings (usually pork), Budae-jjigae, Gamjatang, Jeyuk/Jeyuk-deopbap (제육), Menchi Katsu, Samgyeopsal, Daepaesam, Pork shank (돈사태/돈사태찜), anything with "돈"/"돼지" in the Korean name
- PORK-FREE: Chicken, Beef, Fish, Seafood, Tofu, Eggs, Vegetables
- SUSPICIOUS (may contain pork): Ramen (pork broth), Kimchi Stew, Soft Tofu Stew, Curry (often contains pork in Korea)
- "일품정식(...)" = a rotating set meal; judge it ENTIRELY by the dish named inside the parentheses (e.g. "일품정식(돈사태찜" = pork shank -> pork; "일품정식(낙지볶음" = stir-fried octopus -> pork-free).
{corrections_text}
PACKAGE MEAL WORTHINESS (for Set Meal only):
- SAFE = All items are pork-free
- WORTH IT = Main dish is pork-free, but some side dishes contain pork (can skip those sides)
- NOT WORTH = Main dish contains pork (don't buy this package)
- NONE = No meal available

TRANSLATION RULE (CRITICAL):
- ALL values in the JSON (including `main_dish`, `safe_items`, `skip_items`, `reason`, `safe_options`, `avoid`) MUST be translated into English.
- Do NOT output Korean characters in these fields.

MENU DATA:
{menu_data}

Return ONLY this JSON (no markdown). Include an entry for EVERY target day:
{{
  "Monday": {{
    "day": "Monday",
    "cafeterias": [
      {{
        "name": "Set Meal",
        "type": "package",
        "meals": [
          {{
            "time": "Lunch",
            "price": "6000 won",
            "selling_time": "11:30~13:30",
            "verdict": "SAFE/WORTH IT/NOT WORTH/NONE",
            "main_dish": "name of main protein/dish",
            "safe_items": ["list items you can eat"],
            "skip_items": ["list items with pork to skip"],
            "reason": "brief explanation"
          }}
        ]
      }},
      {{
        "name": "A La Carte",
        "type": "individual",
        "breakfast": {{
          "price": "1000 won",
          "selling_time": "08:20~10:00",
          "verdict": "SAFE/NOT WORTH/NONE (use NONE if breakfast is not in the data)",
          "main_dish": "actual breakfast item from the data, or 'Not served' if none",
          "reason": "brief explanation, or 'Breakfast not served' if none"
        }},
        "selling_time": "11:00~14:00, 16:00~18:30",
        "safe_options": ["Dish Name 1", "Dish Name 2"],
        "avoid": ["Dish Name 3", "Dish Name 4"]
      }}
    ]
  }}
}}

Repeat the SAME structure for EVERY target day, each keyed by its day name (Monday, Tuesday, ...).
Output raw JSON only: no markdown, no code fences, no comments, and no text before or after the JSON object.

IMPORTANT: For A La Carte, safe_options and avoid MUST be simple string arrays of dish names only.
Do NOT use objects/dicts. Just plain strings like: ["Chicken Steak", "Beef Soup"]
"""


# --- AI ANALYSIS ---
def analyze_week(menu_data, days):
    """Analyze all weekdays in a SINGLE Gemini call.

    Returns a dict mapping day name -> per-day analysis, or None if all attempts failed.
    Days missing from the model's response are simply absent from the returned dict;
    the caller fills those with a placeholder structure.
    """
    if not GEMINI_API_KEY:
        print("❌ Missing GEMINI_API_KEY")
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)

    corrections = load_corrections()
    corrections_text = ""
    if corrections:
        corrections_text = "\n\nMANUAL CORRECTIONS (OVERRIDE AI):\n"
        for corr in corrections:
            corrections_text += f"- {corr['dish']} at {corr['cafeteria']}: {corr['status'].upper()} - {corr['reason']}\n"

    prompt = _build_week_prompt(menu_data, days, corrections_text)

    max_retries = 3
    retry_delay = 5  # seconds
    cleaned_text = ""

    for attempt in range(max_retries):
        # Use the primary model, then switch to the fallback on the final attempt.
        model = MODELS[0] if attempt < max_retries - 1 else MODELS[-1]
        if attempt == max_retries - 1:
            print(f"   ↩️ Switching to fallback model: {model}")
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )

            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            # Always trim to the outermost braces: strips anything the model appends
            # before/after the JSON object (stray text, comments -> "Extra data" errors).
            start = cleaned_text.find("{")
            end = cleaned_text.rfind("}") + 1
            if start != -1 and end > start:
                cleaned_text = cleaned_text[start:end]

            parsed = json.loads(cleaned_text)

            # Normalize each requested day we got back.
            week = {}
            for day in days:
                if day in parsed and isinstance(parsed[day], dict):
                    week[day] = _coerce_day_result(day, parsed[day])
            if not week:
                raise ValueError("Response contained none of the requested days")
            if len(week) < len(days):
                missing = [d for d in days if d not in week]
                print(f"   ⚠️ Model omitted {len(missing)} day(s): {', '.join(missing)}")
            return week

        except (json.JSONDecodeError, ValueError) as e:
            print(f"   ⚠️ Parse error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                print(f"   ❌ Failed to parse response after {max_retries} attempts")
                print(f"   Raw response: {cleaned_text[:200]}...")

        except Exception as e:
            error_msg = str(e)
            print(f"   ⚠️ Gemini API error on attempt {attempt + 1}/{max_retries}: {error_msg}")
            if attempt < max_retries - 1:
                wait = retry_delay * 2 if ("quota" in error_msg.lower() or "rate" in error_msg.lower()) else retry_delay
                print(f"   ⏳ Retrying in {wait} seconds...")
                import time
                time.sleep(wait)
            else:
                print(f"   ❌ Failed after {max_retries} attempts")

    return None
