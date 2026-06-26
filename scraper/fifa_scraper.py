"""
FIFA.com Live Standings Scraper
Fetch live qualification standings from FIFA.com
"""
import json, os, re, time
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "fifa_live_standings.json")

# FIFA team name mapping (Indonesian -> English)
TEAM_MAP = {
    "Meksiko": "Mexico",
    "Afrika Selatan": "South Africa",
    "Republik Korea": "South Korea",
    "Ceko": "Czech Republic",
    "Swiss": "Switzerland",
    "Kanada": "Canada",
    "Bosnia dan Herzegovina": "Bosnia",
    "Qatar": "Qatar",
    "Brazil": "Brazil",
    "Maroko": "Morocco",
    "Skotlandia": "Scotland",
    "Haiti": "Haiti",
    "Amerika Serikat": "USA",
    "Australia": "Australia",
    "Paraguay": "Paraguay",
    "Turki": "Turkey",
    "Jerman": "Germany",
    "Pantai Gading": "Ivory Coast",
    "Ekuador": "Ecuador",
    "Curacao": "Curacao",
    "Belanda": "Netherlands",
    "Jepang": "Japan",
    "Swedia": "Sweden",
    "Tunisia": "Tunisia",
    "Kolombia": "Colombia",
    "Mesir": "Egypt",
    "Iran": "Iran",
    "Selandia Baru": "New Zealand",
    "Spanyol": "Spain",
    "Uruguay": "Uruguay",
    "Tanjung Verde": "Cape Verde",
    "Arab Saudi": "Saudi Arabia",
    "Prancis": "France",
    "Norwegia": "Norway",
    "Senegal": "Senegal",
    "Irak": "Iraq",
    "Argentina": "Argentina",
    "Austria": "Austria",
    "Aljazair": "Algeria",
    "Yordania": "Jordan",
    "Portugal": "Portugal",
    "Polandia": "Poland",
    "RD Kongo": "DR Congo",
    "Uzbekistan": "Uzbekistan",
    "Inggris": "England",
    "Ghana": "Ghana",
    "Panama": "Panama",
    "Kroasia": "Croatia",
}

def scrape_fifa_standings():
    """Scrape FIFA.com standings using curl + regex (no browser needed)."""
    import subprocess
    
    url = "https://www.fifa.com/id/tournaments/mens/worldcup/canadamexicousa2026/standings"
    cmd = [
        "curl", "-s", url,
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-H", "Accept: text/html,application/xhtml+xml",
        "-H", "Accept-Language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "--compressed"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        html = result.stdout
    except Exception as e:
        print(f"Error fetching: {e}")
        return None
    
    # FIFA.com is SPA - data is in __NEXT_DATA__ or similar JSON
    # Try to find JSON data in the page
    patterns = [
        r'window\.__NEXT_DATA__\s*=\s*({.*?});?</script>',
        r'window\.__INITIAL_STATE__\s*=\s*({.*?});?</script>',
        r'"standings"\s*:\s*(\[.*?\])',
        r'data-standings="([^"]+)"',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return parse_fifa_data(data)
            except:
                continue
    
    # Fallback: try to extract from HTML tables if rendered
    return extract_from_html(html)

def extract_from_html(html):
    """Extract standings from HTML table data."""
    groups = {}
    # Find group sections
    group_pattern = r'Grup\s+([A-L])'
    team_pattern = r'<tr[^>]*>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(-?\d+)</td>.*?<td[^>]*>(\d+)</td>.*?</tr>'
    
    # This won't work well for SPA - return None
    return None

def parse_fifa_data(data):
    """Parse FIFA JSON data into our format."""
    groups = []
    # Parse based on FIFA's data structure
    if isinstance(data, dict) and "standings" in data:
        for group_data in data["standings"]:
            group_name = group_data.get("group", "")
            teams = []
            for team in group_data.get("teams", []):
                teams.append({
                    "pos": team.get("position", 0),
                    "team": TEAM_MAP.get(team.get("name", ""), team.get("name", "")),
                    "p": team.get("played", 0),
                    "w": team.get("wins", 0),
                    "d": team.get("draws", 0),
                    "l": team.get("losses", 0),
                    "gf": team.get("goalsFor", 0),
                    "ga": team.get("goalsAgainst", 0),
                    "gd": team.get("goalDifference", 0),
                    "pts": team.get("points", 0)
                })
            groups.append({"group": group_name, "teams": teams})
    return groups

def save_standings(groups):
    """Save standings to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    data = {
        "last_updated": datetime.now().isoformat(),
        "source": "fifa.com",
        "groups": groups
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(groups)} groups to {OUTPUT_FILE}")

def load_standings():
    """Load standings from JSON file."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

if __name__ == "__main__":
    print("Fetching FIFA.com standings...")
    groups = scrape_fifa_standings()
    if groups:
        save_standings(groups)
        for g in groups:
            print(f"\nGrup {g['group']}:")
            for t in g["teams"]:
                print(f"  {t['pos']}. {t['team']} - {t['pts']}pts (W{t['w']} D{t['d']} L{t['l']}, GF{t['gf']} GA{t['ga']})")
    else:
        print("Could not fetch live data. Using cached data.")
        cached = load_standings()
        if cached:
            print(f"Last updated: {cached.get('last_updated', 'unknown')}")
