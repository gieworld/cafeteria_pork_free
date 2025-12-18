# 🍽️ Kumoh Halal Menu Checker

A Telegram bot that automatically checks **Kumoh National Institute of Technology** cafeteria menus daily and alerts you about halal-safe options using Google's Gemini AI.

Perfect for Muslim students who need to know which meals are safe to eat each day! 🌙

## 📋 Features

- ✅ **Daily automated checks** - Runs every morning at 7:00 AM KST
- 🤖 **AI-powered analysis** - Uses Gemini to detect pork and hidden non-halal ingredients
- 📱 **Telegram notifications** - Get alerts directly on your phone
- 🏫 **Three cafeterias** - Covers Student, Professor, and A La Carte cafeterias
- 🕐 **Meal-specific info** - Know what's safe for breakfast, lunch, and dinner

## 🚀 Quick Start

### Step 1: Get Your Credentials

#### 1.1 Telegram Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the instructions
3. Copy the API token you receive (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### 1.2 Telegram Chat ID
1. Search for `@userinfobot` on Telegram
2. Start a conversation
3. Copy your numeric ID (e.g., `987654321`)

#### 1.3 Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

### Step 2: Local Testing (Optional)

```bash
# Clone this repository
git clone <your-repo-url>
cd cafeteria_halal

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your real credentials
# Use notepad, VS Code, or any text editor
notepad .env

# Run the bot
python kumoh_halal_bot.py
```

You should receive a Telegram message with today's menu analysis! 🎉

### Step 3: Automate with GitHub Actions

#### 3.1 Upload to GitHub
1. Create a new repository on GitHub
2. Push your code:
```bash
git init
git add .
git commit -m "Initial commit: Halal menu checker"
git remote add origin <your-repo-url>
git push -u origin main
```

#### 3.2 Add Secrets
1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these three secrets:
   - `GEMINI_API_KEY` = Your Gemini API key
   - `TELEGRAM_TOKEN` = Your Telegram bot token
   - `TELEGRAM_CHAT_ID` = Your Telegram chat ID

#### 3.3 Enable Workflow
1. Go to the **Actions** tab
2. You should see "Daily Halal Menu Check" workflow
3. Click **Enable workflow** if needed
4. Click **Run workflow** to test immediately

## 📅 Schedule

The bot automatically runs **every day at 7:00 AM Korea Time (KST)**.

This ensures you get fresh updates each morning about today's menu!

## 🛠️ How It Works

1. **Scrapes** cafeteria menus from Kumoh website
2. **Analyzes** with Gemini AI to identify:
   - ✅ Safe items (beef, chicken, seafood, vegetarian)
   - ❌ Unsafe items (pork, ham, bacon, sausage)
   - ⚠️ Suspicious items (unknown ingredients)
3. **Sends** a formatted Telegram message with recommendations

## 📱 Example Telegram Message

```
🍽️ **Kumoh Halal Menu - Monday** 🍽️

🏫 **Student Cafeteria**

✅ **Lunch**: SAFE
   Chicken Bulgogi, Rice, Kimchi

❌ **Dinner**: UNSAFE
   Pork Cutlet (contains pork)

📝 Breakfast not available on weekdays

🏫 **Professor Cafeteria**

⚠️ **Lunch**: SUSPICIOUS
   Kimchi Stew (verify ingredients)
```

## 🔧 Customization

### Change Schedule
Edit `.github/workflows/menu_check.yml`:
```yaml
schedule:
  # Change the cron expression
  # Format: minute hour day month day-of-week
  # Current: 22:00 UTC = 7:00 AM KST
  - cron: '0 22 * * *'
```

### Add More Cafeterias
Edit `kumoh_halal_bot.py`:
```python
URLS = {
    "Student Cafeteria": "https://www.kumoh.ac.kr/ko/restaurant01.do",
    "Your New Cafeteria": "https://your-url-here.com"
}
```

## ❓ Troubleshooting

### "No message received"
- Check your Telegram credentials are correct
- Verify you've started a conversation with your bot (send `/start`)
- Check GitHub Actions logs for errors

### "Error scraping"
- The cafeteria website might be down
- The HTML structure may have changed (requires code update)

### "AI could not analyze"
- Check your Gemini API key is valid
- Verify you haven't exceeded free tier limits

### GitHub Actions not running
- Make sure secrets are added correctly
- Check the Actions tab is enabled
- Verify the workflow file syntax is correct

## 📝 License

MIT License - Feel free to use and modify!

## 🤝 Contributing

Found a bug? Have a suggestion? Open an issue or PR!

## 🙏 Credits

Built with:
- [Google Gemini AI](https://ai.google.dev/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)

---

**Stay halal, stay healthy!** 🌙✨
