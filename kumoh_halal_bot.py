import requests
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import halal_lib  # Import shared library

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_day_name(offset=0):
    """Returns day name with offset (0=today, 1=tomorrow)."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    target = datetime.now() + timedelta(days=offset)
    return days[target.weekday()]

# --- MESSAGE FORMATTING ---
def format_message(analysis, is_tomorrow=False):
    """Format analysis into a clean Telegram message."""
    if not analysis:
        return "⚠️ Could not analyze menu."
    
    day = analysis.get("day", "Today")
    prefix = "Tomorrow's" if is_tomorrow else f"{day}'s"
    msg = f"🍽️ *{prefix} Pork-Free Guide*\n\n"
    
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
                
                if verdict == "NONE" or not verdict:
                    continue
                
                if verdict == "SAFE":
                    emoji = "✅"
                elif verdict == "WORTH IT":
                    emoji = "💰"
                else:
                    emoji = "❌"
                
                msg += f"{emoji} *{time}*"
                if main_dish:
                    msg += f" - {main_dish}\n"
                else:
                    msg += "\n"
                
                if safe_items:
                    # Handle both strings and dicts in list
                    safe_str = ', '.join(str(item) if isinstance(item, str) else str(item) for item in safe_items)
                    msg += f"  ✅ {safe_str}\n"
                
                if skip_items:
                    # Handle both strings and dicts in list
                    skip_str = ', '.join(str(item) if isinstance(item, str) else str(item) for item in skip_items)
                    msg += f"  ⏭️ {skip_str}\n"
                
            msg += "\n"
            
        elif cafe_type == "individual":
            msg += f"🍴 *{name}*\n"
            safe = cafe.get("safe_options", [])
            avoid = cafe.get("avoid", [])
            
            if safe:
                safe_str = ', '.join(str(item) if isinstance(item, str) else str(item) for item in safe)
                msg += f"✅ {safe_str}\n"
            if avoid:
                avoid_str = ', '.join(str(item) if isinstance(item, str) else str(item) for item in avoid)
                msg += f"❌ {avoid_str}\n"
            msg += "\n"
    
    msg += "_⚠️ This is a PORK-FREE guide only._\n"
    msg += "_Not halal certified. Always verify if important._"
    
    return msg

# --- TELEGRAM ---
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
            payload["parse_mode"] = None
            requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# --- ANALYSIS ---
def run_analysis(chat_id=None, day_offset=0, force_refresh=False):
    """Run menu analysis for a specific day."""
    target_chat = chat_id or TELEGRAM_CHAT_ID
    target_day = get_day_name(day_offset)
    is_tomorrow = day_offset == 1
    
    print(f"📅 Target day: {target_day}")
    
    # Check cache first (skip fetch if cache valid and no refresh)
    # But wait, we need to check HASH to know if menu changed. So we MUST fetch.
    
    # 1. Fetch menu
    full_menu = halal_lib.fetch_all_menus()
    current_hash = halal_lib.get_menu_hash(full_menu)
    
    # 2. Check Cache
    use_cache = False
    if not force_refresh and halal_lib.is_cache_valid(target_day):
        if not halal_lib.has_menu_changed(target_day, current_hash):
            print("📦 Using cached analysis (menu unchanged)...")
            use_cache = True
        else:
            print("🔄 Menu changed! Re-analyzing...")
    
    if use_cache:
        result = halal_lib.get_cached_analysis(target_day)
    else:
        print("🤖 Analyzing with Gemini...")
        result = halal_lib.analyze_with_gemini(full_menu, target_day)
        
        # Save to cache with hash
        if result:
            halal_lib.save_cache(target_day, result, current_hash)
            print("💾 Cached for future requests")
    
    print("📤 Sending notification...")
    message = format_message(result, is_tomorrow)
    success = send_telegram_message(target_chat, message)
    
    return success

def run_week_analysis(chat_id):
    """Generate weekly overview (today + next 4 weekdays)."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    today_idx = datetime.now().weekday()
    
    msg = "📅 *This Week's Pork-Free Overview*\n\n"
    
    # Only weekdays
    for i, day in enumerate(days):
        if i < today_idx:
            continue  # Skip past days
        
        # Check cache
        cache = halal_lib.load_cache()
        if day in cache:
            analysis = cache[day].get("analysis", {})
            status_summary = []
            for cafe in analysis.get("cafeterias", []):
                if cafe.get("type") == "individual":
                    safe = cafe.get("safe_options", [])
                    if safe:
                        # Handle potential dicts
                        safe_list = [str(x) for x in safe]
                        status_summary.append(f"🍴 {', '.join(safe_list[:2])}")
                else:
                    for meal in cafe.get("meals", []):
                        v = meal.get("verdict", "")
                        if v == "SAFE":
                            status_summary.append(f"✅ {meal.get('time')}")
                        elif v == "WORTH IT":
                            status_summary.append(f"💰 {meal.get('time')}")
            
            if status_summary:
                msg += f"*{day}*: {', '.join(status_summary[:3])}\n"
            else:
                msg += f"*{day}*: Check with /today or /tomorrow\n"
        else:
            msg += f"*{day}*: Not cached yet\n"
    
    msg += "\n_Use /today or /tomorrow for full details_"
    send_telegram_message(chat_id, msg)

# --- BOT COMMANDS ---
def check_bot_updates():
    """Check for new messages/commands sent to the bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
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
            
            if text in ["/start", "/check", "/menu", "/today"]:
                if text == "/start":
                    welcome_msg = f"""👋 *Welcome to Kumoh Pork-Free Bot!*

I help students at Kumoh University find pork-free cafeteria meals.

⚠️ *Important Disclaimer:*
This bot checks for PORK only. Not full halal certification.
Always verify ingredients if halal is important to you.

📱 *Commands:*
/today - Today's pork-free menu
/tomorrow - Tomorrow's menu
/week - Weekly overview
/refresh - Force refresh (bypass cache)
/feedback [msg] - Report errors
/help - Show all commands

💡 *Understanding Results:*
✅ SAFE = No pork detected
💰 WORTH IT = Main dish safe, skip some sides
❌ NOT WORTH = Main contains pork

📦 Package = Full set meal
🍴 Order = Pick individual dish"""
                    send_telegram_message(chat_id, welcome_msg)
                    send_telegram_message(chat_id, "⏳ Checking today's menu...")
                else:
                    send_telegram_message(chat_id, f"👋 Hi {user_name}! Checking today's pork-free menu...\n\n⏳ Please wait...")
                run_analysis(chat_id, day_offset=0)
                
            elif text == "/tomorrow":
                send_telegram_message(chat_id, f"👋 Hi {user_name}! Checking tomorrow's menu...\n\n⏳ Please wait...")
                run_analysis(chat_id, day_offset=1)
            
            elif text == "/week":
                send_telegram_message(chat_id, "📅 Getting weekly overview...")
                run_week_analysis(chat_id)
                
            elif text == "/refresh":
                send_telegram_message(chat_id, "🔄 Force refreshing menu (bypassing cache)...\n\n⏳ Please wait...")
                run_analysis(chat_id, day_offset=0, force_refresh=True)
                
            elif text == "/help":
                help_msg = """🤖 *Kumoh Pork-Free Bot*

Commands:
/today - Today's pork-free menu
/tomorrow - Tomorrow's menu
/week - Weekly overview
/refresh - Force refresh (new data)
/feedback [msg] - Report errors
/help - Show this message

⚠️ This checks for PORK only.
Not halal certified."""
                send_telegram_message(chat_id, help_msg)
                
            elif text.startswith("/feedback"):
                feedback_text = text.replace("/feedback", "").strip()
                if feedback_text:
                    with open("feedback_log.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] User: {user_name} (ID: {chat_id})\n")
                        f.write(f"Feedback: {feedback_text}\n\n")
                    
                    admin_msg = f"📝 *New Feedback*\nFrom: {user_name} (ID: {chat_id})\nMessage: {feedback_text}"
                    send_telegram_message(TELEGRAM_CHAT_ID, admin_msg)
                    send_telegram_message(chat_id, "✅ Thank you! Your feedback has been sent to the admin.")
                else:
                    send_telegram_message(chat_id, "Usage: /feedback [your message]\nExample: /feedback Curry contains pork")
            
            with open(offset_file, "w") as f:
                f.write(str(update_id))
                
    except Exception as e:
        print(f"Error checking updates: {e}")

def main():
    print("=" * 50)
    print("🍽️  Kumoh Pork-Free Menu Checker")
    print("=" * 50)
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: Missing credentials!")
        print("Please set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID")
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "--bot":
        print("🤖 Running in bot mode - listening for commands...")
        print("Press Ctrl+C to stop\n")
        while True:
            check_bot_updates()
    else:
        run_analysis()
        print("\n✅ Done!")
        print("=" * 50)

if __name__ == "__main__":
    main()
