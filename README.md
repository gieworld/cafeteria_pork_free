# 🍽️ KIT Pork-Free Guide

A weekly pork-free guide to the Kumoh National Institute of Technology cafeterias, for students who don't eat pork.

**Dashboard:** https://gieworld.github.io/cafeteria_pork_free/

> ⚠️ **Pork-free guide only — not halal certified.** It checks for pork, nothing else. Always confirm at the counter.

## What it shows

Mon–Fri for three cafeterias, each dish in English with the Korean name from the counter sign:

| Dashboard name | Korean | Page |
|---|---|---|
| Set Meal | 정찬식당 | `restaurant02.do` |
| A La Carte | 일품식당 | `restaurant01.do` |
| Snack Bar | 분식당 | `restaurant04.do` |

A "SERVING NOW" box on today's tab shows what is open right now.

## How it works

1. **Windows Task Scheduler** on the maintainer's PC runs `update_menu.bat` every hour from 08:00 to 12:00. The kumoh.ac.kr site posts each new week at no fixed hour, so one early run can miss it.
2. `scripts/gen_menu.py` scrapes the three pages. **If the menu hasn't changed, it stops there** — no AI call.
3. If it has changed, it makes one AI call for the whole week:
   - **Primary:** `gemini-3.8-flash` (Google) — 2 attempts
   - **Fallback:** `nvidia/nemotron-3-super-120b-a12b:free` (OpenRouter) — 2 attempts. A different company on purpose: Gemini's "high demand" 503s hit all Gemini models at once.
4. The result is checked in code before it is saved. Dishes the cafeteria itself marks with `*` (돈육 포함) are always moved out of the safe lists, whatever the AI said. `corrections.json` holds manual overrides.
5. `data/menu_data.json` is committed and pushed, and GitHub Pages publishes `index.html`.

Output of scheduled runs goes to `update.log`. Note that the batch file pushes **every** local commit on `main`, so anything committed locally goes live on the next run.

## Setup

1. Create the virtual environment and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in:
   - `GEMINI_API_KEY` — https://aistudio.google.com/app/apikey
   - `OPENROUTER_API_KEY` — https://openrouter.ai/keys. Free models may also need *free-model providers* allowed at https://openrouter.ai/settings/privacy, or calls fail with "No endpoints found matching your data policy".

   Either key alone works; models without a key are skipped.
3. Right-click `setup_auto_update.bat` → **Run as administrator** → choose **1**.

The task only runs while you are logged in to Windows. To update by hand, run `update_menu.bat`.

## Checking it works

- **Last scheduled run:** read `update.log`.
- **Schedule:** `schtasks /query /tn "KumohPorkFree_AutoUpdate" /v /fo LIST`
- **Parsing and safety logic:** `python scripts/halal_lib.py` (self-check: pork markers, dates, enforcement, retry order)
- **Dashboard logic:** open the dashboard, then run `selfCheck()` in the browser devtools console.

## Changing the AI model

Test before editing `MODELS` in `scripts/halal_lib.py`:

```bash
# Hand-checked week: must PASS (includes an unmarked 순대 and a decorative *개강특식*)
python -u scripts/eval_models.py --week=2026-08-31 <model>

# This week, compared with the current menu_data.json
python -u scripts/eval_models.py --ref-file=data/menu_data.json <model>
```

A model should PASS the ground truth, list **0** pork dishes as safe (`DANGEROUS`), and keep Korean names intact. Raw outputs land in `.eval/`.

## Files

| File | Purpose |
|---|---|
| `index.html` | The dashboard |
| `data/menu_data.json` | This week's analysis (published) |
| `scripts/gen_menu.py` | Scrape → analyze → save |
| `scripts/halal_lib.py` | Scraper, prompt, model calls, pork-marker enforcement |
| `scripts/eval_models.py` | Test a model before switching to it |
| `corrections.json` | Manual food corrections fed to the AI |
| `update_menu.bat` | One update run, plus commit and push |
| `setup_auto_update.bat` | Installs the hourly scheduled task |

---

Made for Kumoh international students 🌍
