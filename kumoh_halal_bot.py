import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
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

def get_current_day():
    """Returns the current day of the week in English."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[datetime.now().weekday()]

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

def analyze_with_gemini(menu_data, current_day):
    """Sends menu text to Gemini to find halal-safe options."""
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
You are a Halal food assistant for Muslim students in Korea.

TODAY: {current_day}

CONTEXT:
- Student & Professor Cafeteria = PACKAGE MEAL (you get everything, cannot choose individual items)
- A La Carte = INDIVIDUAL ORDER (you can pick specific safe dishes)

HALAL RULES:
- UNSAFE: Pork, Ham, Bacon, Sausage, Spam, Tonkatsu, Mandu/Dumplings (usually pork), Budae-jjigae, Gamjatang, Jeyuk
- SAFE: Chicken, Beef, Fish, Seafood, Tofu, Eggs, Vegetables
- SUSPICIOUS: Ramen (pork broth), Kimchi Stew, Soft Tofu Stew (may contain pork)
{corrections_text}

PACKAGE MEAL WORTHINESS:
- SAFE = All items are halal-safe
- WORTH IT = Main dish is safe, but some side dishes contain pork (student can skip those sides)
- NOT WORTH = Main dish contains pork (don't buy this package)
- NONE = No meal available

MENU DATA:
{menu_data}

Return ONLY this JSON (no markdown):
{{
  "today": "{current_day}",
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
        {{"time": "Lunch", "verdict": "SAFE/WORTH IT/NOT WORTH/NONE", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
        {{"time": "Dinner", "verdict": "SAFE/WORTH IT/NOT WORTH/NONE", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}}
      ]
    }},
    {{
      "name": "Professor Cafeteria",
      "type": "package",
      "meals": [
        {{"time": "Breakfast", "verdict": "SAFE/WORTH IT/NOT WORTH/NONE", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
        {{"time": "Lunch", "verdict": "SAFE/WORTH IT/NOT WORTH/NONE", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}},
        {{"time": "Dinner", "verdict": "SAFE/WORTH IT/NOT WORTH/NONE", "main_dish": "...", "safe_items": [], "skip_items": [], "reason": "..."}}
      ]
    }},
    {{
      "name": "A La Carte",
      "type": "individual",
      "safe_options": ["list of safe dishes to order"],
      "avoid": ["list of pork dishes to avoid"]
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

def format_message(analysis):
    """Format analysis into a clean Telegram message."""
    if not analysis:
        return "⚠️ Could not analyze menu today."
    
    today = analysis.get("today", "Today")
    msg = f"🍽️ *{today}'s Halal Guide*\n\n"
    
    for cafe in analysis.get("cafeterias", []):
        name = cafe.get("name", "")
        cafe_type = cafe.get("type", "")
        
        if cafe_type == "package":
            msg += f"📦 *{name}*\n"
            for meal in cafe.get("meals", []):
                time = meal.get("time", "")
                verdict = meal.get("verdict", "")
                main_dish = meal.get("main_dish", "")
                safe_items = meal.get("safe_items", [])
                skip_items = meal.get("skip_items", [])
                reason = meal.get("reason", "")
                
                if verdict == "NONE" or not verdict:
                    continue
                
                # Emoji based on verdict
                if verdict == "SAFE":
                    emoji = "✅"
                elif verdict == "WORTH IT":
                    emoji = "💰"
                else:  # NOT WORTH
                    emoji = "❌"
                
                msg += f"{emoji} *{time}*"
                if main_dish:
                    msg += f" - {main_dish}\n"
                else:
                    msg += "\n"
                
                if safe_items:
                    msg += f"  ✅ {', '.join(safe_items)}\n"
                
                if skip_items:
                    msg += f"  ⏭️ {', '.join(skip_items)}\n"
                
            msg += "\n"
            
        elif cafe_type == "individual":
            msg += f"🍴 *{name}*\n"
            safe = cafe.get("safe_options", [])
            avoid = cafe.get("avoid", [])
            
            if safe:
                msg += f"✅ {', '.join(safe)}\n"
            if avoid:
                msg += f"❌ {', '.join(avoid)}\n"
            msg += "\n"
    
    msg += "_💡 ✅=Safe 💰=Worth it ❌=Skip_"
    
    return msg

def send_telegram_message(chat_id, message):
    """Send message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            # Try without markdown
            payload["parse_mode"] = None
            requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def run_analysis(chat_id=None):
    """Run the full menu analysis and send results."""
    target_chat = chat_id or TELEGRAM_CHAT_ID
    
    print(f"📅 Today: {get_current_day()}")
    print("📥 Fetching menus...")
    
    full_menu = ""
    for name, url in URLS.items():
        print(f"   - {name}...")
        full_menu += f"--- {name} ---\n{get_menu_text(url)}\n\n"
    
    print("🤖 Analyzing with Gemini...")
    result = analyze_with_gemini(full_menu, get_current_day())
    
    print("📤 Sending notification...")
    message = format_message(result)
    success = send_telegram_message(target_chat, message)
    
    return success

def check_bot_updates():
    """Check for new messages/commands sent to the bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    # Get the last update ID we processed
    offset_file = ".last_update_id"
    last_update_id = 0
    if os.path.exists(offset_file):
        with open(offset_file, "r") as f:
            try:
                last_update_id = int(f.read().strip())
            except:
                pass
    
    try:
        response = requests.get(url, params={"offset": last_update_id + 1, "timeout": 5}, timeout=10)
        data = response.json()
        
        if not data.get("ok"):
            return
        
        for update in data.get("result", []):
            update_id = update.get("update_id", 0)
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            user_name = message.get("from", {}).get("first_name", "User")
            
            print(f"📨 Received: '{text}' from {user_name}")
            
            if text in ["/start", "/check", "/menu"]:
                if text == "/start":
                    # Welcome tutorial for new users
                    welcome_msg = f"""👋 *Welcome to Kumoh Halal Bot!*

I help Muslim students at Kumoh University find halal-safe cafeteria meals.

🎯 *What I Do:*
• Check 3 cafeterias daily for halal options
• Identify pork & suspicious dishes
• Tell you if package meals are worth buying

📱 *Commands:*
/check - Get today's menu now
/feedback [msg] - Report errors
/help - Show all commands

⏰ *Daily Alerts:*
You'll get automatic updates every morning at 7:00 AM KST!

💡 *Understanding Results:*
✅ SAFE = All halal
💰 WORTH IT = Main dish safe, skip some sides
❌ NOT WORTH = Main has pork

📦 Package = Full set meal (Student/Prof)
🍴 Order = Pick individual (A La Carte)

Ready to check today's menu?"""
                    send_telegram_message(chat_id, welcome_msg)
                    # Also send today's menu
                    send_telegram_message(chat_id, "⏳ Checking today's menu...")
                else:
                    send_telegram_message(chat_id, f"👋 Hi {user_name}! Checking today's halal menu...\n\n⏳ Please wait...")
                run_analysis(chat_id)
            elif text == "/help":
                help_msg = """🤖 *Kumoh Halal Bot*

Commands:
/check - Get today's halal menu
/menu - Same as /check
/feedback [message] - Report an error
/help - Show this message

The bot also sends daily updates at 7:00 AM KST!"""
                send_telegram_message(chat_id, help_msg)
            elif text.startswith("/feedback"):
                feedback_text = text.replace("/feedback", "").strip()
                if feedback_text:
                    # Log feedback
                    with open("feedback_log.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] User: {user_name} (ID: {chat_id})\n")
                        f.write(f"Feedback: {feedback_text}\n\n")
                    
                    # Send to admin (you)
                    admin_msg = f"📝 *New Feedback*\nFrom: {user_name} (ID: {chat_id})\nMessage: {feedback_text}"
                    send_telegram_message(TELEGRAM_CHAT_ID, admin_msg)
                    
                    # Confirm to user
                    send_telegram_message(chat_id, "✅ Thank you! Your feedback has been sent to the admin.")
                else:
                    send_telegram_message(chat_id, "Usage: /feedback [your message]\nExample: /feedback Curry contains pork")
            
            # Save the last processed update ID
            with open(offset_file, "w") as f:
                f.write(str(update_id))
                
    except Exception as e:
        print(f"Error checking updates: {e}")

def main():
    print("=" * 50)
    print("🍽️  Kumoh Halal Menu Checker")
    print("=" * 50)
    
    if not GEMINI_API_KEY or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: Missing credentials!")
        print("Please set GEMINI_API_KEY, TELEGRAM_TOKEN, and TELEGRAM_CHAT_ID")
        return
    
    # Check if running in bot mode (listening for commands)
    if len(sys.argv) > 1 and sys.argv[1] == "--bot":
        print("🤖 Running in bot mode - listening for commands...")
        print("Press Ctrl+C to stop\n")
        while True:
            check_bot_updates()
    else:
        # Normal mode - just run analysis once
        run_analysis()
        print("\n✅ Done!")
        print("=" * 50)

if __name__ == "__main__":
    main()
