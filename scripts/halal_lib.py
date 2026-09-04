import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
import os
import re
import hashlib
from datetime import date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

URLS = {
    "Set Meal": "https://www.kumoh.ac.kr/ko/restaurant02.do",       # 정찬식당
    "A La Carte": "https://www.kumoh.ac.kr/ko/restaurant01.do",     # 일품식당
    "Snack Bar": "https://www.kumoh.ac.kr/ko/restaurant04.do",      # 분식당
}

def get_menu_hash(menu_text):
    """Generate hash of menu text to detect changes."""
    return hashlib.md5(menu_text.encode()).hexdigest()

# --- DATA FETCHING ---
def get_menu_text(url):
    """Scrapes the weekly menu table from the website.

    Raises on any failure. Returning an error *string* here used to feed
    "Error scraping: ..." to Gemini as if it were the menu, so the run
    "succeeded" and overwrote a good menu_data.json with garbage.
    """
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    menu_table = soup.find('table')
    if not menu_table:
        raise ValueError(f"No menu table found at {url}")

    rows = menu_table.find_all('tr')
    if len(rows) <= 1:
        raise ValueError(f"Menu table at {url} has no data rows")

    menu_text = ""
    for row in rows:
        cols = row.find_all(['th', 'td'])
        row_data = [ele.text.strip().replace('\n', ' ') for ele in cols]
        menu_text += " | ".join(row_data) + "\n"

    return menu_text

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

_KO_DAY_NAMES = {"월": "Monday", "화": "Tuesday", "수": "Wednesday",
                 "목": "Thursday", "금": "Friday", "토": "Saturday", "일": "Sunday"}


def parse_menu_dates(menu_text):
    """Map day name -> ISO date from the table header ("월(08.31)" -> "2026-08-31").

    The page omits the year, so pick the candidate year nearest today; that keeps
    a December->January week correct.
    """
    today = date.today()
    dates = {}
    for ko, mm, dd in re.findall(r"([월화수목금토일])\s*\((\d{1,2})\.(\d{1,2})\)", menu_text):
        candidates = []
        for offset in (-1, 0, 1):
            try:
                candidates.append(date(today.year + offset, int(mm), int(dd)))
            except ValueError:
                pass  # e.g. Feb 29 in a non-leap candidate year
        if candidates:
            nearest = min(candidates, key=lambda d: abs((d - today).days))
            dates.setdefault(_KO_DAY_NAMES[ko], nearest.isoformat())
    return dates


def extract_pork_items(menu_text):
    """Dish names the cafeteria itself flagged with a LEADING "*".

    Site note: "*로 표시된 항목은 돈육이 포함된 메뉴입니다" (items marked * contain pork).
    Skips the two asterisk uses that are NOT pork flags:
      - wrapped on both sides, e.g. "*개강특식*" (semester-opening special) = decoration
      - eligibility footnotes, e.g. "*재학생만 해당" (enrolled students only)
    """
    items = []
    for token, trailing_star in re.findall(r"\*([^\s*]+)(\*?)", menu_text):
        if trailing_star:
            continue
        name = token.strip("()[]{}<>,.·:;&")
        if not name or name == "로" or name.startswith("재학생"):
            continue
        if name not in items:
            items.append(name)
    return items


MODELS = ["gemini-3.8-flash", "gemini-3.7-flash"]  # primary, fallback


FIXED_MENU_CAFES = {"Snack Bar"}  # same short menu every weekday -> render collapsed


def _coerce_dish(item):
    """Normalize one orderable dish to {"en": ..., "ko": ...}.

    The Korean name is what is actually printed on the counter sign, so it is
    the name a student points at. Bare strings (older data files, or a model
    that ignored the schema) still come through with an empty `ko`.
    """
    if isinstance(item, dict):
        return {"en": str(item.get("en") or item.get("menu") or "").strip(),
                "ko": str(item.get("ko") or "").strip().lstrip("*").strip()}
    return {"en": str(item).strip(), "ko": ""}


def _coerce_day_result(day, result):
    """Normalize one day's result: the 'day' field, {en,ko} dishes, fixed-menu flag."""
    result.setdefault("day", day)
    for cafe in result.get("cafeterias", []):
        cafe["fixed_menu"] = cafe.get("name") in FIXED_MENU_CAFES
        if cafe.get("type") == "individual":
            for key in ("safe_options", "avoid"):
                dishes = [_coerce_dish(it) for it in cafe.get(key, [])]
                cafe[key] = [d for d in dishes if d["en"]]
    return result


def _build_week_prompt(menu_data, days, corrections_text, pork_items):
    day_list = ", ".join(days)
    pork_list = "\n".join(f"- {i}" for i in pork_items) if pork_items else "(none marked this week)"
    # One JSON object per day, keyed by day name, each matching the original per-day schema.
    return f"""
You are a PORK-FREE food assistant for foreign students in Korea who don't eat pork.

IMPORTANT: We are checking for PORK only, not full halal certification.
This is a PORK-FREE guide, not halal certification.

TARGET DAYS: {day_list}
Analyze EVERY one of these days from the weekly menu data below.

CONTEXT (three cafeterias):
- Set Meal (restaurant02, 정찬식당) = PACKAGE MEAL. Lunch only, ~6000 won. You get all dishes, cannot choose.
- A La Carte (restaurant01, 일품식당) = INDIVIDUAL ORDER. Rotating daily lunch/dinner specials (일품요리). A cheap breakfast (조식 / 천원의 아침밥) is served ONLY during regular semester and is often suspended during vacations/holidays.
- Snack Bar (restaurant04, 분식당) = SNACK COUNTER, individual order. Mostly a fixed short menu (udon, ramen, pork cutlet, sweet & sour chicken). Some days it shows "일품식당에서 주문 가능" (order at the A La Carte hall instead) or "미운영" (not operating) - on those days leave safe_options/avoid empty and say so in `note`.

SITE-MARKED PORK ITEMS (extracted mechanically from the cafeteria's own "*" markers - treat as ABSOLUTE truth):
{pork_list}
Every dish in that list contains pork. It must NEVER appear in safe_items or safe_options, and must appear in avoid / skip_items on the day it is served.

BREAKFAST RULE (CRITICAL - do NOT invent breakfast):
- Only report a breakfast if the menu data for that day ACTUALLY lists breakfast items (look for "조식" / "천원의 아침밥" / explicit 08:20~10:00 items).
- If the data shows NO breakfast for that day (e.g. it only lists "일품요리"/lunch-dinner specials, or shows "미운영"/not operating), set breakfast to: verdict "NONE", main_dish "Not served", reason "Breakfast not served".
- NEVER guess or fabricate a breakfast dish that is not present in the menu data.

CLOSED-DAY RULE:
- If a day shows "미운영" (not operating) or a holiday marker like "[제헌절]", treat that cafeteria as closed: verdict "NONE" and empty safe_options/avoid lists.

ASTERISK PORK MARKER (how to read the raw data yourself):
- A LEADING "*" on a dish name means it contains pork. The site's own note reads: "*로 표시된 항목은 돈육이 포함된 메뉴입니다."
- These asterisks are NOT pork markers - ignore them:
  - text wrapped in asterisks on BOTH sides, e.g. "*개강특식*" (semester-opening special) or "*종강특식*". That is decoration, NOT a pork flag. The dishes in such a meal must be judged by name like any other.
  - eligibility footnotes, e.g. "*재학생만 해당" (enrolled students only).
- WARNING: the absence of "*" does NOT guarantee pork-free. Pork can appear WITHOUT a "*", especially inside the "일품정식(...)" set-meal parentheses. So still apply the name rules below to every un-starred item.

PORK DETECTION RULES (apply by dish name, in addition to the * marker):
- CONTAINS PORK: Pork, Ham, Bacon, Sausage, Spam, Tonkatsu/Donkatsu (돈가스/카츠동), Mandu/Dumplings (usually pork), Budae-jjigae, Gamjatang, Jeyuk/Jeyuk-deopbap (제육), Menchi Katsu, Samgyeopsal, Daepaesam, Pork shank (돈사태/돈사태찜), Sundae/blood sausage (순대), anything with "돈"/"돼지" in the Korean name
- PORK-FREE: Chicken, Beef, Fish, Seafood, Tofu, Eggs, Vegetables
- SUSPICIOUS (may contain pork): Ramen (pork broth), Kimchi Stew, Soft Tofu Stew, Curry (often contains pork in Korea)
- "일품정식(...)" = a rotating set meal; judge it ENTIRELY by the dish named inside the parentheses (e.g. "일품정식(돈사태찜" = pork shank -> pork; "일품정식(낙지볶음" = stir-fried octopus -> pork-free).
{corrections_text}
PACKAGE MEAL WORTHINESS (for Set Meal only):
- SAFE = All items are pork-free
- WORTH IT = Main dish is pork-free, but some side dishes contain pork (can skip those sides)
- NOT WORTH = Main dish contains pork (don't buy this package)
- NONE = No meal available

PRICE & TIME RULE (the example values below are placeholders, NOT facts):
- Read `price` and `selling_time` for each meal from the MENU DATA of that day. The cafeteria changes them.
- e.g. "중식 [정식: 6000원] 11:40~13:30" -> price "6000 won", selling_time "11:40~13:30".
- If the data adds an extra service window, append it. e.g. with "(11:00~11:40) 일품식당에서 위의 정식메뉴 운영" -> selling_time "11:40~13:30 (also 11:00~11:40 at the A La Carte hall)".
- If a price or time is genuinely absent from the data, use "" (empty string). NEVER invent a number.

LANGUAGE RULE (CRITICAL - the student has to order at a Korean counter):
- `reason`, `safe_items`, `skip_items` and `time` MUST be English only. No Korean characters in those.
- A dish the student ORDERS BY NAME carries BOTH names, because the counter sign is in Korean:
  - every `safe_options` / `avoid` entry is an OBJECT: {{"en": "English name", "ko": "exact Korean name"}}
  - `main_dish` stays English; add `main_dish_ko` next to it (on Set Meal meals AND on breakfast).
- Every `ko` value MUST be copied VERBATIM from the MENU DATA above, minus any leading "*". Never transliterate, never invent Korean, never translate English back into Korean. If the data has no Korean source for that dish, use "".
- `safe_items` / `skip_items` are Set Meal side dishes: plain English strings, no Korean. The tray comes as-is, so those are never ordered by name.

NOT-SERVING NOTE:
- Give each individual-order cafeteria a `note`: one short English line ONLY when it is not serving normally that day - e.g. "Not operating" for 미운영, "Order at the A La Carte hall" for 일품식당에서 주문 가능. Otherwise "".

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
            "price": "<from data, e.g. 6000 won>",
            "selling_time": "<from data, e.g. 11:40~13:30>",
            "verdict": "SAFE/WORTH IT/NOT WORTH/NONE",
            "main_dish": "name of main protein/dish, in English",
            "main_dish_ko": "the same dish's exact Korean name from the data, or ''",
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
          "price": "<from data, e.g. 1000 won>",
          "selling_time": "<from data, e.g. 08:20~10:00>",
          "verdict": "SAFE/NOT WORTH/NONE (use NONE if breakfast is not in the data)",
          "main_dish": "actual breakfast item from the data, or 'Not served' if none",
          "main_dish_ko": "that item's exact Korean name from the data, or ''",
          "reason": "brief explanation, or 'Breakfast not served' if none"
        }},
        "selling_time": "<from data, e.g. 11:00~14:00, 16:00~18:30>",
        "note": "",
        "safe_options": [{{"en": "Chicken Cream Stew Udon", "ko": "치킨크림스튜우동"}}],
        "avoid": [{{"en": "Tonkotsu Ramen", "ko": "돈코츠라멘"}}]
      }},
      {{
        "name": "Snack Bar",
        "type": "individual",
        "selling_time": "<from data, e.g. 11:00~14:00, 16:00~18:30>",
        "note": "",
        "safe_options": [{{"en": "Udon", "ko": "우동"}}],
        "avoid": [{{"en": "Pork Cutlet Varieties", "ko": "돈가스류"}}]
      }}
    ]
  }}
}}

Repeat the SAME structure for EVERY target day, each keyed by its day name (Monday, Tuesday, ...).
Output raw JSON only: no markdown, no code fences, no comments, and no text before or after the JSON object.

IMPORTANT: For A La Carte and Snack Bar, EVERY safe_options / avoid entry MUST be an object with exactly the keys "en" and "ko". Never a bare string.
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

    # The site marks its own pork dishes with "*". Extract them here rather than
    # trusting the model to spot every asterisk in a wall of Korean text.
    pork_items = extract_pork_items(menu_data)
    if pork_items:
        print(f"   🐖 Site-marked pork items: {', '.join(pork_items)}")

    prompt = _build_week_prompt(menu_data, days, corrections_text, pork_items)

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


if __name__ == "__main__":
    # Self-check for the two bits of real parsing logic: `python scripts/halal_lib.py`
    sample = """월(08.31) | 화(09.01) | 수(09.02)
조식 [천원의 아침밥] *재학생만 해당 08:20~10:00 든든한제육&돈까스정식 | 일품요리 *돈코츠라멘 *제육덮밥 일품정식(*돈사태찜) | 중식 [정식: 6000원] *개강특식* 기장밥 전복갈비탕 깍두기
"""

    pork = extract_pork_items(sample)
    assert "돈코츠라멘" in pork and "제육덮밥" in pork, pork
    assert "돈사태찜" in pork, "leading * inside parentheses still marks pork"
    assert "개강특식" not in pork, "'*개강특식*' is decoration, not a pork marker"
    assert not any(p.startswith("재학생") for p in pork), "'*재학생만 해당' is a footnote, not a pork marker"

    dates = parse_menu_dates(sample)
    assert dates["Monday"].endswith("-08-31"), dates
    assert dates["Tuesday"].endswith("-09-01"), dates
    assert dates["Wednesday"].endswith("-09-02"), dates
    assert len(dates) == 3, dates

    # ASCII-only output so this runs on a bare Windows console (no PYTHONIOENCODING).
    print(f"halal_lib self-check OK ({len(pork)} pork items, {len(dates)} dates)")
