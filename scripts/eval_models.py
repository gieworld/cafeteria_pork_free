"""Evaluate candidate AI models on the exact production prompt, before changing MODELS.

    python -u scripts/eval_models.py [--week=YYYY-MM-DD] [--ref-file=PATH] model [model ...]

--week      analyze a past week, fetched through the production scraper
            (default: the live week)
--ref-file  compare against an existing menu_data.json instead of calling a
            flaky reference model

Examples:
    python -u scripts/eval_models.py --week=2026-08-31 nvidia/nemotron-3-super-120b-a12b:free
    python -u scripts/eval_models.py --ref-file=data/menu_data.json nvidia/nemotron-3-super-120b-a12b:free

DANGEROUS = a dish the candidate lists as safe that the reference lists as pork.
Weeks with hand-judged TRUTH also get PASS/FAIL against reality. Starred dishes
are forced out of individual safe lists by _coerce_day_result, but Set Meal
verdicts are pure model judgment - that is where the truth checks matter most.
Raw model outputs are saved to .eval/ (gitignored) for inspection.
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import halal_lib as h  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), ".eval")
os.makedirs(OUT, exist_ok=True)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
opts = {k: v for k, _, v in (a[2:].partition("=") for a in sys.argv[1:] if a.startswith("--"))}
MODELS = [a for a in sys.argv[1:] if not a.startswith("--")]
WEEK = opts.get("week")

# Hand-judged truth, so models are checked against reality, not another model.
TRUTH = {
    "2026-08-31": {
        "verdicts": {("Monday", "Set Meal"): "SAFE",          # smoked duck
                     ("Tuesday", "Set Meal"): "SAFE",         # *개강특식* is decoration
                     ("Wednesday", "Set Meal"): "NOT WORTH",  # unstarred 닭갈비순대볶음: sundae is pork
                     ("Thursday", "Set Meal"): "NOT WORTH",   # *김치돈찜
                     ("Friday", "Set Meal"): "NOT WORTH"},    # *깻잎불고기
        "never_safe": {"돈가스류"},  # unstarred that week, but pork cutlet by name
    },
}

if WEEK:
    # Same "--- Name ---" wrapping and row format as fetch_all_menus()
    menu = "".join(f"--- {name} ---\n{h.get_menu_text(f'{url}?mode=menuList&srDt={WEEK}')}\n\n"
                   for name, url in h.URLS.items())
    stamp = f"({WEEK[5:7]}.{WEEK[8:10]})"
    assert stamp in menu, f"site did not return the week of {WEEK} (no {stamp} in header)"
else:
    menu = h.fetch_all_menus()

pork = h.extract_pork_items(menu)
corrections = h.load_corrections()
corrections_text = ""
if corrections:  # same block analyze_week builds
    corrections_text = "\n\nMANUAL CORRECTIONS (OVERRIDE AI):\n" + "".join(
        f"- {c['dish']} at {c['cafeteria']}: {c['status'].upper()} - {c['reason']}\n" for c in corrections)
prompt = h._build_week_prompt(menu, DAYS, corrections_text, pork)


def summarize(week):
    verdicts, mains, safe, avoid, ko_total, ko_filled = {}, {}, set(), set(), 0, 0
    for day, v in week.items():
        for c in v.get("cafeterias", []):
            for m in c.get("meals", []):
                verdicts[(day, c.get("name"))] = m.get("verdict")
                mains[(day, c.get("name"))] = m.get("main_dish_ko") or m.get("main_dish")
            for key, bucket in (("safe_options", safe), ("avoid", avoid)):
                for d in c.get(key, []):
                    ko_total += 1
                    ko_filled += bool(d.get("ko"))
                    bucket.add((day, c.get("name"), d.get("ko") or d.get("en")))
    return {"verdicts": verdicts, "mains": mains, "safe": safe, "avoid": avoid, "ko": f"{ko_filled}/{ko_total}"}


ref = None
if "ref-file" in opts:
    with open(opts["ref-file"], encoding="utf-8") as f:
        ref_data = json.load(f)
    menu_week = min(h.parse_menu_dates(menu).values())
    if ref_data.get("week_start") != menu_week:
        print(f"!! ref-file is week {ref_data.get('week_start')}, menu is week {menu_week}", flush=True)
    ref = summarize(ref_data["week_data"])

print(f"Week: {WEEK or 'live'} | site-marked pork: {', '.join(pork) or '(none)'}", flush=True)

results = {}
for model in MODELS:
    print(f"-> {model} ...", flush=True)
    t = time.time()
    raw, err = "", None
    for _ in range(2):  # one retry: providers have transient 503/429s
        try:
            raw = h._generate(model, prompt)
            break
        except Exception as e:  # noqa: BLE001 - record every failure mode, keep going
            err = f"{type(e).__name__}: {str(e)[:160]}"
            time.sleep(8)
    secs = time.time() - t
    with open(os.path.join(OUT, f"raw_{WEEK or 'live'}_{re.sub(r'[/:]', '_', model)}.txt"), "w", encoding="utf-8") as f:
        f.write(raw or f"ERROR: {err}")
    if not raw:
        results[model] = {"error": err, "secs": secs}
        print(f"   ERROR after {secs:.0f}s: {err}", flush=True)
        continue
    try:
        parsed = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        starred_in_safe = sum(  # model ignored the site's own marker (enforcement then fixed it)
            1 for d in DAYS if isinstance(parsed.get(d), dict)
            for c in parsed[d].get("cafeterias", []) for it in c.get("safe_options", [])
            if isinstance(it, dict) and h._clean_ko(it.get("ko")) in pork)
        week = {d: h._coerce_day_result(d, parsed[d], pork) for d in DAYS if isinstance(parsed.get(d), dict)}
    except Exception as e:  # noqa: BLE001
        results[model] = {"error": f"parse: {e}", "secs": secs}
        print(f"   PARSE ERROR after {secs:.0f}s: {e}", flush=True)
        continue
    results[model] = {"days": len(week), "secs": secs, "starred_in_safe": starred_in_safe, **summarize(week)}
    print(f"   done in {secs:.0f}s", flush=True)

print(f"\n{'model':42} days  secs  ko      starred->safe  verdict!=ref  DANGEROUS  over-cautious")
for model, r in results.items():
    if "error" in r:
        print(f"{model:42} ERROR {r['error']}")
        continue
    dangerous = sorted(r["safe"] & ref["avoid"]) if ref else None
    cautious = len(r["avoid"] & ref["safe"]) if ref else "-"
    verdict_diff = sum(1 for k, v in ref["verdicts"].items() if r["verdicts"].get(k) != v) if ref else "-"
    print(f"{model:42} {r['days']:>4}  {r['secs']:>4.0f}  {r['ko']:6}  {r['starred_in_safe']:>13}  "
          f"{verdict_diff!s:>12}  {len(dangerous) if dangerous is not None else '-'!s:>9}  {cautious!s:>13}")
    for day, cafe, name in dangerous or []:
        print(f"    !! {day} {cafe}: {name}  (candidate SAFE, reference PORK)")
    for (day, cafe), main in sorted(r["mains"].items()):
        ref_main = ref["mains"].get((day, cafe)) if ref else None
        note = "" if ref_main in (None, main) else f"   (reference: {ref_main})"
        print(f"    {day:9} {cafe} main: {main} [{r['verdicts'].get((day, cafe))}]{note}")

truth = TRUTH.get(WEEK or "")
if truth:
    print("\nGround truth:")
    for model, r in results.items():
        if "error" in r:
            continue
        misses = [f"{d} {c}: got {r['verdicts'].get((d, c))}, want {v}"
                  for (d, c), v in truth["verdicts"].items() if r["verdicts"].get((d, c)) != v]
        unsafe = sorted({n for (_, _, n) in r["safe"]
                         if n in truth["never_safe"] or re.search(r"pork|ham|bacon|sausage|cutlet|katsu", n, re.I)})
        print(f"  {'PASS' if not misses and not unsafe else 'FAIL'}  {model}")
        for m in misses:
            print(f"        verdict {m}")
        for u in unsafe:
            print(f"        !! listed as SAFE: {u}")
