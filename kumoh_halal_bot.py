import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
# Best to use Environment Variables for security
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Cafeteria URLs
URLS = {
    "Student Cafeteria": "https://www.kumoh.ac.kr/ko/restaurant01.do",
    "Professor Cafeteria": "https://www.kumoh.ac.kr/ko/restaurant02.do",
    "A La Carte": "https://www.kumoh.ac.kr/ko/restaurant04.do"
}

def get_menu_text(url):
    """Scrapes the weekly menu table from the website."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Kumoh website usually puts the menu in a standard <table>
        menu_table = soup.find('table') 
        if not menu_table:
            return "No menu found."
            
        # Extract text clearly
        menu_text = ""
        rows = menu_table.find_all('tr')
        for row in rows:
            cols = row.find_all(['th', 'td'])
            row_data = [ele.text.strip().replace('\n', ' ') for ele in cols]
            menu_text += " | ".join(row_data) + "\n"
            
        return menu_text
    except Exception as e:
        return f"Error scraping: {e}"

def get_current_day():
    """Returns the current day of the week in English."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[datetime.now().weekday()]

def analyze_with_gemini(menu_data, current_day):
    """Sends menu text to Gemini to find pork and identify safe options for today."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    prompt = f"""
    You are a Halal food assistant for a student in Korea. 
    Analyze the following Korean cafeteria menu.
    
    TODAY IS: {current_day}
    
    RULES:
    1. Identify items containing PORK, HAM, BACON, SAUSAGE, or SPAM.
    2. Be careful of hidden pork (e.g., Budae-jjigae, Sundae, Jeyuk, Tangsuyuk, Gamjatang).
    3. If a dish is definitely Beef, Chicken, Seafood, or Vegetarian, mark it SAFE.
    4. If unsure (like just "Kimchi Stew"), mark it SUSPICIOUS.
    5. FOCUS ON TODAY'S MENU ({current_day}) - provide specific meal times (Breakfast, Lunch, Dinner).

    MENU DATA:
    {menu_data}

    OUTPUT FORMAT:
    Return ONLY a JSON object. Do not write markdown. Structure:
    {{
        "today": "{current_day}",
        "analysis": [
            {{
                "cafeteria": "Name",
                "breakfast": {{"status": "SAFE/UNSAFE/SUSPICIOUS", "menu": "Menu items"}},
                "lunch": {{"status": "SAFE/UNSAFE/SUSPICIOUS", "menu": "Menu items"}},
                "dinner": {{"status": "SAFE/UNSAFE/SUSPICIOUS", "menu": "Menu items"}},
                "notes": "Any important warnings or recommendations"
            }}
        ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean response to ensure it's pure JSON
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"Error analyzing with Gemini: {e}")
        return None

def send_telegram_alert(analysis_json):
    """Formats the AI analysis into a nice Telegram message."""
    if not analysis_json:
        message = "⚠️ Error: AI could not analyze the menu today."
    else:
        today = analysis_json.get("today", "Today")
        message = f"🍽️ **Kumoh Halal Menu - {today}** 🍽️\n\n"
        
        for item in analysis_json.get("analysis", []):
            message += f"🏫 **{item['cafeteria']}**\n\n"
            
            # Breakfast
            breakfast = item.get('breakfast', {})
            if breakfast:
                status_emoji = "✅" if breakfast.get('status') == 'SAFE' else "❌" if breakfast.get('status') == 'UNSAFE' else "⚠️"
                message += f"{status_emoji} **Breakfast**: {breakfast.get('status', 'N/A')}\n"
                if breakfast.get('menu'):
                    message += f"   {breakfast['menu']}\n"
            
            # Lunch
            lunch = item.get('lunch', {})
            if lunch:
                status_emoji = "✅" if lunch.get('status') == 'SAFE' else "❌" if lunch.get('status') == 'UNSAFE' else "⚠️"
                message += f"{status_emoji} **Lunch**: {lunch.get('status', 'N/A')}\n"
                if lunch.get('menu'):
                    message += f"   {lunch['menu']}\n"
            
            # Dinner
            dinner = item.get('dinner', {})
            if dinner:
                status_emoji = "✅" if dinner.get('status') == 'SAFE' else "❌" if dinner.get('status') == 'UNSAFE' else "⚠️"
                message += f"{status_emoji} **Dinner**: {dinner.get('status', 'N/A')}\n"
                if dinner.get('menu'):
                    message += f"   {dinner['menu']}\n"
            
            # Notes
            if item.get('notes'):
                message += f"\n📝 {item['notes']}\n"
            
            message += "\n"

    # Send to Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Telegram message sent successfully!")
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")

def main():
    print("=" * 50)
    print("🍽️  Kumoh Halal Menu Checker")
    print("=" * 50)
    
    # Check if credentials are set
    if not GEMINI_API_KEY or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: Missing credentials!")
        print("Please set GEMINI_API_KEY, TELEGRAM_TOKEN, and TELEGRAM_CHAT_ID")
        return
    
    current_day = get_current_day()
    print(f"📅 Today is: {current_day}")
    
    print("\n📥 Fetching menus...")
    full_menu_context = ""
    
    for name, url in URLS.items():
        print(f"   - {name}...")
        text = get_menu_text(url)
        full_menu_context += f"--- {name} ---\n{text}\n\n"
    
    print("\n🤖 Analyzing with Gemini AI...")
    result = analyze_with_gemini(full_menu_context, current_day)
    
    print("\n📤 Sending Telegram notification...")
    send_telegram_alert(result)
    
    print("\n✅ Done!")
    print("=" * 50)

if __name__ == "__main__":
    main()
