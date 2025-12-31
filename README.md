# 🍽️ Kumoh Pork-Free Bot

Daily pork-free cafeteria guide for Kumoh University students.

> ⚠️ **Disclaimer**: This bot checks for PORK only. Not halal certification.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
Copy `.env.example` to `.env` and fill in your credentials.

### 3. Run the Bot
**Double-click `start_bot.bat`** or:
```bash
python kumoh_halal_bot.py --bot
```

### 4. (Optional) Auto Morning Scrape
Right-click `setup_scheduler.bat` → **Run as Administrator**

This sets up automatic 6:50 AM scraping on weekdays.

## Commands

| Command | Description |
|---------|-------------|
| `/today` | Today's pork-free menu |
| `/tomorrow` | Tomorrow's menu |
| `/week` | Weekly overview |
| `/refresh` | Force refresh (bypass cache) |
| `/feedback` | Report errors |
| `/help` | Show commands |

## Files

| File | Purpose |
|------|---------|
| `kumoh_halal_bot.py` | Main bot (run with `--bot`) |
| `morning_scrape.py` | Scheduled scraping script |
| `corrections.json` | Korean food corrections |
| `start_bot.bat` | Easy bot launcher |
| `setup_scheduler.bat` | Set up auto-scraping |

## How It Works

1. **Morning (6:50 AM)**: Auto-scrapes and caches all weekday menus
2. **All Day**: Users send `/today`, bot responds from cache instantly
3. **Change Detection**: If menu changes, bot auto re-analyzes

## Korean Food Knowledge

Bot knows these Korean dishes typically contain pork:
- Curry rice (카레라이스)
- Ramen broth (라면)
- Mandu/dumplings (만두)
- Jjigae stews (찌개)
- Sundubu (순두부)

---

Made for Kumoh international students 🌍
