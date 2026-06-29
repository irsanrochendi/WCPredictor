#!/usr/bin/env python3
"""Update live standings & bracket data from FIFA.com"""
import json, os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DATA_FILE = os.path.join(DATA_DIR, "live_standings.json")

GROUPS = {
    "Grup A": [
        {"team": "Mexico", "pos": 1, "p": 3, "w": 3, "d": 0, "l": 0, "gf": 6, "ga": 0, "gd": 6, "pts": 9, "status": "qualified"},
        {"team": "South Africa", "pos": 2, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 2, "ga": 3, "gd": -1, "pts": 4, "status": ""},
        {"team": "South Korea", "pos": 3, "p": 3, "w": 1, "d": 0, "l": 2, "gf": 2, "ga": 3, "gd": -1, "pts": 3, "status": ""},
        {"team": "Czech Republic", "pos": 4, "p": 3, "w": 0, "d": 1, "l": 2, "gf": 2, "ga": 6, "gd": -4, "pts": 1, "status": "eliminated"},
    ],
    "Grup B": [
        {"team": "Switzerland", "pos": 1, "p": 3, "w": 2, "d": 1, "l": 0, "gf": 7, "ga": 3, "gd": 4, "pts": 7, "status": "qualified"},
        {"team": "Canada", "pos": 2, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 8, "ga": 3, "gd": 5, "pts": 4, "status": ""},
        {"team": "Bosnia and Herzegovina", "pos": 3, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 5, "ga": 6, "gd": -1, "pts": 4, "status": ""},
        {"team": "Qatar", "pos": 4, "p": 3, "w": 0, "d": 1, "l": 2, "gf": 2, "ga": 10, "gd": -8, "pts": 1, "status": "eliminated"},
    ],
    "Grup C": [
        {"team": "Brazil", "pos": 1, "p": 3, "w": 2, "d": 1, "l": 0, "gf": 7, "ga": 1, "gd": 6, "pts": 7, "status": "qualified"},
        {"team": "Morocco", "pos": 2, "p": 3, "w": 2, "d": 1, "l": 0, "gf": 6, "ga": 3, "gd": 3, "pts": 7, "status": ""},
        {"team": "Scotland", "pos": 3, "p": 3, "w": 1, "d": 0, "l": 2, "gf": 1, "ga": 4, "gd": -3, "pts": 3, "status": "eliminated"},
        {"team": "Haiti", "pos": 4, "p": 3, "w": 0, "d": 0, "l": 3, "gf": 2, "ga": 8, "gd": -6, "pts": 0, "status": "eliminated"},
    ],
    "Grup D": [
        {"team": "United States", "pos": 1, "p": 3, "w": 2, "d": 0, "l": 1, "gf": 8, "ga": 4, "gd": 4, "pts": 6, "status": ""},
        {"team": "Australia", "pos": 2, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 2, "ga": 2, "gd": 0, "pts": 4, "status": ""},
        {"team": "Paraguay", "pos": 3, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 2, "ga": 4, "gd": -2, "pts": 4, "status": ""},
        {"team": "Turkey", "pos": 4, "p": 3, "w": 1, "d": 0, "l": 2, "gf": 3, "ga": 5, "gd": -2, "pts": 3, "status": ""},
    ],
    "Grup E": [
        {"team": "Germany", "pos": 1, "p": 3, "w": 2, "d": 0, "l": 1, "gf": 10, "ga": 4, "gd": 6, "pts": 6, "status": ""},
        {"team": "Ivory Coast", "pos": 2, "p": 3, "w": 2, "d": 0, "l": 1, "gf": 4, "ga": 2, "gd": 2, "pts": 6, "status": ""},
        {"team": "Ecuador", "pos": 3, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 2, "ga": 2, "gd": 0, "pts": 4, "status": ""},
        {"team": "Curacao", "pos": 4, "p": 3, "w": 0, "d": 1, "l": 2, "gf": 1, "ga": 9, "gd": -8, "pts": 1, "status": "eliminated"},
    ],
    "Grup F": [
        {"team": "Netherlands", "pos": 1, "p": 3, "w": 2, "d": 1, "l": 0, "gf": 10, "ga": 4, "gd": 6, "pts": 7, "status": "qualified"},
        {"team": "Japan", "pos": 2, "p": 3, "w": 1, "d": 2, "l": 0, "gf": 7, "ga": 3, "gd": 4, "pts": 5, "status": ""},
        {"team": "Sweden", "pos": 3, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 7, "ga": 7, "gd": 0, "pts": 4, "status": ""},
        {"team": "Tunisia", "pos": 4, "p": 3, "w": 0, "d": 0, "l": 3, "gf": 2, "ga": 12, "gd": -10, "pts": 0, "status": "eliminated"},
    ],
    "Grup G": [
        {"team": "Belgium", "pos": 1, "p": 3, "w": 1, "d": 2, "l": 0, "gf": 6, "ga": 2, "gd": 4, "pts": 5, "status": ""},
        {"team": "Egypt", "pos": 2, "p": 3, "w": 1, "d": 2, "l": 0, "gf": 5, "ga": 3, "gd": 2, "pts": 5, "status": ""},
        {"team": "Iran", "pos": 3, "p": 3, "w": 0, "d": 3, "l": 0, "gf": 3, "ga": 3, "gd": 0, "pts": 3, "status": ""},
        {"team": "New Zealand", "pos": 4, "p": 3, "w": 0, "d": 1, "l": 2, "gf": 4, "ga": 10, "gd": -6, "pts": 1, "status": "eliminated"},
    ],
    "Grup H": [
        {"team": "Spain", "pos": 1, "p": 3, "w": 2, "d": 1, "l": 0, "gf": 5, "ga": 0, "gd": 5, "pts": 7, "status": "qualified"},
        {"team": "Cape Verde", "pos": 2, "p": 3, "w": 0, "d": 3, "l": 0, "gf": 2, "ga": 2, "gd": 0, "pts": 3, "status": ""},
        {"team": "Uruguay", "pos": 3, "p": 3, "w": 0, "d": 2, "l": 1, "gf": 3, "ga": 4, "gd": -1, "pts": 2, "status": ""},
        {"team": "Saudi Arabia", "pos": 4, "p": 3, "w": 0, "d": 2, "l": 1, "gf": 1, "ga": 5, "gd": -4, "pts": 2, "status": "eliminated"},
    ],
    "Grup I": [
        {"team": "France", "pos": 1, "p": 3, "w": 3, "d": 0, "l": 0, "gf": 10, "ga": 2, "gd": 8, "pts": 9, "status": "qualified"},
        {"team": "Norway", "pos": 2, "p": 3, "w": 2, "d": 0, "l": 1, "gf": 8, "ga": 7, "gd": 1, "pts": 6, "status": ""},
        {"team": "Senegal", "pos": 3, "p": 3, "w": 1, "d": 0, "l": 2, "gf": 8, "ga": 6, "gd": 2, "pts": 3, "status": "eliminated"},
        {"team": "Iraq", "pos": 4, "p": 3, "w": 0, "d": 0, "l": 3, "gf": 1, "ga": 12, "gd": -11, "pts": 0, "status": "eliminated"},
    ],
    "Grup J": [
        {"team": "Argentina", "pos": 1, "p": 3, "w": 3, "d": 0, "l": 0, "gf": 8, "ga": 1, "gd": 7, "pts": 9, "status": "qualified"},
        {"team": "Austria", "pos": 2, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 6, "ga": 6, "gd": 0, "pts": 4, "status": ""},
        {"team": "Algeria", "pos": 3, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 5, "ga": 7, "gd": -2, "pts": 4, "status": ""},
        {"team": "Jordan", "pos": 4, "p": 3, "w": 0, "d": 0, "l": 3, "gf": 3, "ga": 8, "gd": -5, "pts": 0, "status": "eliminated"},
    ],
    "Grup K": [
        {"team": "Colombia", "pos": 1, "p": 3, "w": 2, "d": 1, "l": 0, "gf": 4, "ga": 1, "gd": 3, "pts": 7, "status": "qualified"},
        {"team": "Portugal", "pos": 2, "p": 3, "w": 1, "d": 2, "l": 0, "gf": 6, "ga": 1, "gd": 5, "pts": 5, "status": ""},
        {"team": "DR Congo", "pos": 3, "p": 3, "w": 1, "d": 1, "l": 1, "gf": 4, "ga": 3, "gd": 1, "pts": 4, "status": ""},
        {"team": "Uzbekistan", "pos": 4, "p": 3, "w": 0, "d": 0, "l": 3, "gf": 2, "ga": 11, "gd": -9, "pts": 0, "status": "eliminated"},
    ],
    "Grup L": [
        {"team": "England", "pos": 1, "p": 3, "w": 2, "d": 1, "l": 0, "gf": 6, "ga": 2, "gd": 4, "pts": 7, "status": "qualified"},
        {"team": "Ghana", "pos": 2, "p": 3, "w": 1, "d": 1, "l": 0, "gf": 1, "ga": 0, "gd": 1, "pts": 4, "status": ""},
        {"team": "Croatia", "pos": 3, "p": 3, "w": 1, "d": 0, "l": 1, "gf": 3, "ga": 4, "gd": -1, "pts": 3, "status": ""},
        {"team": "Panama", "pos": 4, "p": 3, "w": 0, "d": 0, "l": 2, "gf": 0, "ga": 2, "gd": -2, "pts": 0, "status": "eliminated"},
    ],
}

# R32 Bracket (from FIFA.com)
R32 = [
    {"id": "M73", "home": "South Africa", "away": "Canada", "score_h": 0, "score_a": 1, "date": "29/6", "winner": "Canada"},
    {"id": "M74", "home": "Germany", "away": "Paraguay", "date": "30/6"},
    {"id": "M75", "home": "Netherlands", "away": "Morocco", "date": "30/6"},
    {"id": "M76", "home": "Brazil", "away": "Japan", "date": "30/6"},
    {"id": "M77", "home": "France", "away": "Sweden", "date": "1/7"},
    {"id": "M78", "home": "Ivory Coast", "away": "Norway", "date": "1/7"},
    {"id": "M79", "home": "Mexico", "away": "Ecuador", "date": "1/7"},
    {"id": "M80", "home": "England", "away": "DR Congo", "date": "1/7"},
    {"id": "M81", "home": "USA", "away": "Bosnia", "date": "2/7"},
    {"id": "M82", "home": "Belgium", "away": "Senegal", "date": "2/7"},
    {"id": "M83", "home": "Portugal", "away": "Croatia", "date": "3/7"},
    {"id": "M84", "home": "Spain", "away": "Austria", "date": "3/7"},
    {"id": "M85", "home": "Switzerland", "away": "Algeria", "date": "3/7"},
    {"id": "M86", "home": "Argentina", "away": "Cape Verde", "date": "4/7"},
    {"id": "M87", "home": "Colombia", "away": "Ghana", "date": "4/7"},
    {"id": "M88", "home": "Australia", "away": "Egypt", "date": "4/7"},
]

os.makedirs(DATA_DIR, exist_ok=True)
data = json.load(open(DATA_FILE)) if os.path.exists(DATA_FILE) else {}
data["last_updated"] = datetime.now().isoformat()
data["source"] = "fifa.com"
data["groups"] = GROUPS
data["r32"] = R32
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated {len(GROUPS)} groups + {len(R32)} R32 matches")
for gname, teams in GROUPS.items():
    print(f"\n{gname}:")
    for t in teams:
        s = "[Q]" if t["status"] == "qualified" else "[E]" if t["status"] == "eliminated" else ""
        print(f"  {t['pos']}. {t['team']:30s} {t['pts']}pts (W{t['w']} D{t['d']} L{t['l']}) {s}")

print(f"\nR32 Bracket:")
for m in R32:
    if m.get("winner"):
        print(f"  {m['id']}: {m['home']} {m.get('score_h','')}-{m.get('score_a','')} {m['away']} -> {m['winner']}")
    else:
        print(f"  {m['id']}: {m['home']} vs {m['away']} ({m['date']})")
