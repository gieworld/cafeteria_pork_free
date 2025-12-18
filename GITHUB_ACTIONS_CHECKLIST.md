# GitHub Actions Setup Checklist

## ✅ Code Pushed
- [x] All files committed and pushed to main branch

## 🔐 Verify GitHub Secrets

Go to your repository: https://github.com/gieworld/cafeteria_halal

### Check Environment Secrets:
1. Go to **Settings** → **Environments** → **Configure env**
2. Verify these 3 secrets exist and have **actual values** (not empty):
   - ✅ `GEMINI_API_KEY`
   - ✅ `TELEGRAM_TOKEN`
   - ✅ `TELEGRAM_CHAT_ID`

### If secrets are empty, re-add them:
1. Delete each secret
2. Click "Add secret"
3. Paste the **actual values** from your `.env` file

## 🧪 Test the Workflow

### Manual Test:
1. Go to **Actions** tab
2. Click "Daily Halal Menu Check"
3. Click "Run workflow" → "Run workflow"
4. Wait ~1 minute
5. Check your Telegram for the message!

### Check Logs:
If it fails:
1. Click on the failed run
2. Click "check-menu"
3. Expand "Run Halal Menu Checker"
4. Look for error messages

## 📅 Verify Schedule

The workflow runs automatically at:
- **7:00 AM KST** every day
- Cron: `0 22 * * *` (22:00 UTC = 7:00 AM KST)

## 🐛 Common Issues

### Issue: "Missing credentials"
**Fix:** Secrets are empty, re-add them with actual values

### Issue: "chat not found"
**Fix:** Make sure you've sent `/start` to your bot on Telegram

### Issue: Workflow doesn't run
**Fix:** Check the Actions tab is enabled in Settings

## ✅ Success Indicators

When working correctly:
- ✅ Workflow shows green checkmark
- ✅ You receive Telegram message
- ✅ Message shows today's menu analysis
- ✅ Corrections.json is applied (curry marked unsafe)
