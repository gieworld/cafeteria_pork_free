# 🍽️ Kumoh Halal Menu Checker

Daily Telegram alerts for halal-safe cafeteria meals at Kumoh National Institute of Technology.

## Features

- ✅ **Daily alerts** at 7:00 AM KST
- 🤖 **Interactive commands** - Send `/check` to get today's menu
- 📦 **Package vs Order** - Distinguishes set meals from à la carte
- 🧠 **AI-powered** - Uses Gemini to detect hidden pork ingredients

## Quick Start

### 1. Get Credentials

| Credential | How to Get |
|------------|------------|
| `GEMINI_API_KEY` | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| `TELEGRAM_TOKEN` | Message [@BotFather](https://t.me/BotFather) → `/newbot` |
| `TELEGRAM_CHAT_ID` | Message [@userinfobot](https://t.me/userinfobot) |

### 2. Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and edit .env
cp .env.example .env
# Add your credentials to .env

# Run once
python kumoh_halal_bot.py

# Or run in bot mode (listens for /check commands)
python kumoh_halal_bot.py --bot
```

### 3. GitHub Actions (Automated Daily)

1. Push code to GitHub
2. Go to **Settings → Secrets → Actions**
3. Add: `GEMINI_API_KEY`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
4. The bot runs automatically every day at 7:00 AM KST

## Bot Commands

| Command | Description |
|---------|-------------|
| `/check` | Get today's halal menu |
| `/menu` | Same as /check |
| `/start` | Welcome message + menu |
| `/help` | Show commands |

## Sample Output

```
🍽️ Thursday's Halal Guide 🍽️

📦 Student Cafeteria (Package)
❌ Lunch: Contains Tonkatsu (pork)

📦 Professor Cafeteria (Package)
✅ Dinner: Beef soup, safe to eat

🍴 A La Carte (Order)
✅ Order: Chicken Karaage Bowl
❌ Avoid: Tonkatsu, Ramen

📌 Package = full set meal
📌 Order = pick individual dish
```

## Files

| File | Purpose |
|------|---------|
| `kumoh_halal_bot.py` | Main bot script |
| `requirements.txt` | Python dependencies |
| `.env.example` | Credential template |
| `.github/workflows/menu_check.yml` | Daily automation |

---

**Stay halal, stay healthy!** 🌙
