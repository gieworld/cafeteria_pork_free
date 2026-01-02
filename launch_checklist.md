# 🚀 KIT Pork-Free Guide Launch

We have upgraded from a **Telegram Bot** (blocked mainly by network) to a **Web Dashboard** (unblockable & fast).

## ✅ What's Done
- [x] **Cleanup:** Removed old Windows tasks (no more daily scripts on your PC).
- [x] **Archive:** Moved old bot files to `legacy_bot/`.
- [x] **Data Generator:** Created `scripts/gen_menu.py` to auto-scrape & analyze.
- [x] **Frontend:** Created `index.html` (Dark mode dashboard).
- [x] **Automation:** Created GitHub Action (`daily_update.yml`) to run every morning.

## 🏁 Your Next Steps

1. **Verify Locally**
   - Wait for `scripts/gen_menu.py` to finish (it's creating `data/menu_data.json`).
   - Open `index.html` in your browser.
   - You should see the dashboard with data!

2. **Push to GitHub**
   ```bash
   git add .
   git commit -m "🚀 Launch Web Dashboard"
   git push
   ```

3. **Configure GitHub**
   - Go to your Repo **Settings** → **Secrets and variables** → **Actions**.
   - Add New Repository Secret:
     - Name: `GEMINI_API_KEY`
     - Value: (Paste your key from .env)

4. **Enable GitHub Pages**
   - Go to Repo **Settings** → **Pages**.
   - **Source:** Select `gh-pages` branch (It will appear AFTER the Action runs once).
     - *Tip:* You can manually trigger the Action in the "Actions" tab to create the branch faster.
   - **Save**.

5. **Bookmark It!**
   - Your URL will be: `https://gieworld.github.io/cafeteria_pork_free/`
   - Add to your phone home screen.

## ✨ Benefits
- **No VPN needed.**
- **No PC needed** (runs in cloud).
- **Fast Access** (just a link).
- **Auto-Updates** every morning at 6:50 AM KST.
