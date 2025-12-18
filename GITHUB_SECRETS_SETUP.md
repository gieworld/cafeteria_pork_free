# GitHub Actions Troubleshooting Guide

## The Problem
GitHub Actions shows: `❌ Error: Missing credentials!`

This means the GitHub Secrets are not configured in your repository.

## Solution: Add GitHub Secrets

### Step-by-Step:

1. **Go to your repository on GitHub** (in your browser)

2. **Click the "Settings" tab** (top right of the repo page)

3. **In the left sidebar:**
   - Click **"Secrets and variables"**
   - Then click **"Actions"**

4. **Click the green "New repository secret" button**

5. **Add these THREE secrets** (one at a time):

   **Secret 1: GEMINI_API_KEY**
   - Name: `GEMINI_API_KEY`
   - Value: Your actual Gemini API key (get from https://makersuite.google.com/app/apikey)
   - Click "Add secret"

   **Secret 2: TELEGRAM_TOKEN**
   - Name: `TELEGRAM_TOKEN`
   - Value: Your bot token from @BotFather (looks like `123456789:ABCdefGHI...`)
   - Click "Add secret"

   **Secret 3: TELEGRAM_CHAT_ID**
   - Name: `TELEGRAM_CHAT_ID`
   - Value: Your numeric chat ID from @userinfobot (looks like `987654321`)
   - Click "Add secret"

6. **Verify** all 3 secrets are listed

7. **Test the workflow:**
   - Go to the "Actions" tab
   - Click "Daily Halal Menu Check" workflow
   - Click "Run workflow" button
   - Check the logs

## Important Notes

⚠️ **Secret names MUST match exactly** (case-sensitive):
- `GEMINI_API_KEY` (not `gemini_api_key` or `GEMINI_KEY`)
- `TELEGRAM_TOKEN` (not `TELEGRAM_BOT_TOKEN`)
- `TELEGRAM_CHAT_ID` (not `CHAT_ID`)

✅ **Once added**, the secrets will be:
- Encrypted and hidden (you can't view them after saving)
- Available to all workflows in your repository

## Still Having Issues?

If you've added the secrets and it still fails:

1. **Double-check secret names** - They must match exactly
2. **Check for extra spaces** - Copy-paste carefully (no spaces before/after)
3. **Verify API key is valid** - Test your Gemini key at https://aistudio.google.com
4. **Check bot token** - Send `/start` to your bot on Telegram first
5. **Verify chat ID** - Make sure it's your numeric ID, not username

---

After adding secrets, run the workflow again and check if it works!
