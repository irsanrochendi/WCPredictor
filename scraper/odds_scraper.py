"""
Betting Odds Scraper
Scrapes odds from multiple free sources and aggregates them.
"""
import json
import time
import random
from typing import Dict, List, Optional
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass
class MatchOdds:
    home_team: str
    away_team: str
    home_win: float
    draw: float
    away_win: float
    source: str
    over_25: Optional[float] = None
    under_25: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None


class OddsScraper:
    """Scrape and aggregate betting odds from multiple free sources."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Odds API (free tier) - https://the-odds-api.com
    ODDS_API_BASE = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._cached_odds: Dict[str, MatchOdds] = {}

    def get_worldcup_odds_api(self) -> List[MatchOdds]:
        """Fetch World Cup winner odds from The Odds API (free tier)."""
        if not self.api_key:
            return []

        try:
            url = f"{self.ODDS_API_BASE}/sports/soccer_fifa_world_cup/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "eu,uk,au",
                "markets": "h2h",
                "oddsFormat": "decimal",
            }
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                odds_list = []
                for event in data:
                    home = event.get("home_team", "")
                    away = event.get("away_team", "")
                    for bookmaker in event.get("bookmakers", []):
                        for market in bookmaker.get("markets", []):
                            if market["key"] == "h2h":
                                outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                                odds_list.append(MatchOdds(
                                    home_team=home, away_team=away,
                                    home_win=outcomes.get(home, 0),
                                    draw=outcomes.get("Draw", 0),
                                    away_win=outcomes.get(away, 0),
                                    source=bookmaker["key"]
                                ))
                return odds_list
        except Exception as e:
            print(f"Odds API error: {e}")
        return []

    def scrape_flashscore(self, url: str = "https://www.flashscore.com") -> List[MatchOdds]:
        """
        Scrape odds from Flashscore.
        Note: May require JavaScript rendering; returns empty if blocked.
        """
        odds_list = []
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                # Look for match containers - structure may vary
                events = soup.find_all("div", class_=lambda x: x and "event__match" in str(x))
                for event in events:
                    try:
                        home_el = event.find("div", class_=lambda x: x and "event__participant--home" in str(x))
                        away_el = event.find("div", class_=lambda x: x and "event__participant--away" in str(x))
                        odds_els = event.find_all("div", class_=lambda x: x and "odds__odd" in str(x))

                        if home_el and away_el and len(odds_els) >= 3:
                            odds_list.append(MatchOdds(
                                home_team=home_el.text.strip(),
                                away_team=away_el.text.strip(),
                                home_win=float(odds_els[0].text.strip()),
                                draw=float(odds_els[1].text.strip()),
                                away_win=float(odds_els[2].text.strip()),
                                source="flashscore"
                            ))
                    except (ValueError, AttributeError, IndexError):
                        continue
        except Exception as e:
            print(f"Flashscore scrape error: {e}")
        return odds_list

    def get_fallback_worldcup_odds(self) -> Dict[str, float]:
        """
        Fallback: approximate current World Cup 2026 winner odds.
        Based on aggregated bookmaker odds as of mid-2025.
        These are reasonable estimates - replace with live scraping for production.
        """
        return {
            "Brazil": 5.50,
            "France": 6.00,
            "Argentina": 6.50,
            "England": 7.00,
            "Spain": 8.00,
            "Germany": 10.00,
            "Portugal": 12.00,
            "Netherlands": 15.00,
            "Italy": 17.00,
            "Belgium": 21.00,
            "Croatia": 26.00,
            "Uruguay": 29.00,
            "United States": 41.00,
            "Colombia": 41.00,
            "Denmark": 41.00,
            "Mexico": 51.00,
            "Switzerland": 51.00,
            "Japan": 67.00,
            "Morocco": 67.00,
            "Senegal": 81.00,
            "Serbia": 81.00,
            "Poland": 101.00,
            "South Korea": 126.00,
            "Ecuador": 151.00,
            "Canada": 201.00,
            "Australia": 251.00,
            "Ghana": 251.00,
            "Cameroon": 301.00,
            "Iran": 351.00,
            "Costa Rica": 501.00,
            "Saudi Arabia": 501.00,
            "Tunisia": 501.00,
            "Qatar": 1001.00,
            "Chile": 151.00,
            "Nigeria": 81.00,
            "Egypt": 101.00,
            "Austria": 101.00,
            "Ukraine": 151.00,
            "Turkey": 126.00,
            "Ivory Coast": 201.00,
            "Mali": 301.00,
            "Algeria": 201.00,
            "Paraguay": 301.00,
            "Uzbekistan": 401.00,
            "Iraq": 401.00,
            "Jamaica": 501.00,
            "New Zealand": 501.00,
            "Panama": 501.00,
        }

    def convert_winner_odds_to_probability(self, odds: Dict[str, float]) -> Dict[str, float]:
        """Convert winner odds to implied probabilities."""
        raw_probs = {}
        for team, odd in odds.items():
            if odd > 0:
                raw_probs[team] = 1.0 / odd

        total = sum(raw_probs.values())
        if total <= 0:
            return raw_probs

        # Remove vig proportionally
        return {team: prob / total for team, prob in raw_probs.items()}


class TeamDataCollector:
    """Collect and aggregate team/player statistics from multiple sources."""

    # World Cup historical data
    WC_HISTORY = {
        "Brazil": {"titles": 5, "runner_up": 2, "semi_finals": 7, "appearances": 22,
                    "years_won": [1958, 1962, 1970, 1994, 2002]},
        "Germany": {"titles": 4, "runner_up": 4, "semi_finals": 13, "appearances": 20,
                     "years_won": [1954, 1974, 1990, 2014]},
        "Italy": {"titles": 4, "runner_up": 2, "semi_finals": 8, "appearances": 18,
                   "years_won": [1934, 1938, 1982, 2006]},
        "Argentina": {"titles": 3, "runner_up": 3, "semi_finals": 6, "appearances": 18,
                       "years_won": [1978, 1986, 2022]},
        "France": {"titles": 2, "runner_up": 2, "semi_finals": 7, "appearances": 16,
                    "years_won": [1998, 2018]},
        "Uruguay": {"titles": 2, "runner_up": 0, "semi_finals": 5, "appearances": 14,
                     "years_won": [1930, 1950]},
        "England": {"titles": 1, "runner_up": 0, "semi_finals": 3, "appearances": 16,
                     "years_won": [1966]},
        "Spain": {"titles": 1, "runner_up": 0, "semi_finals": 2, "appearances": 16,
                   "years_won": [2010]},
        "Netherlands": {"titles": 0, "runner_up": 3, "semi_finals": 5, "appearances": 11},
        "Croatia": {"titles": 0, "runner_up": 1, "semi_finals": 3, "appearances": 6},
        "Belgium": {"titles": 0, "runner_up": 0, "semi_finals": 2, "appearances": 14},
        "Portugal": {"titles": 0, "runner_up": 0, "semi_finals": 2, "appearances": 8},
        "Morocco": {"titles": 0, "runner_up": 0, "semi_finals": 1, "appearances": 6},
        "Japan": {"titles": 0, "runner_up": 0, "semi_finals": 0, "appearances": 7},
        "USA": {"titles": 0, "runner_up": 0, "semi_finals": 1, "appearances": 11},
        "South Korea": {"titles": 0, "runner_up": 0, "semi_finals": 1, "appearances": 11},
    }

    # Notable players with career stats
    PLAYER_STATS = {
        "Lionel Messi": {
            "country": "Argentina", "age": 37, "position": "Forward",
            "club": "Inter Miami", "caps": 180, "goals": 106,
            "wc_appearances": 5, "wc_goals": 13, "wc_assists": 8,
            "ballon_dor": 8, "rating": 93,
            "description": "GOAT contender, 2022 World Cup winner, 8 Ballon d'Or awards"
        },
        "Cristiano Ronaldo": {
            "country": "Portugal", "age": 39, "position": "Forward",
            "club": "Al-Nassr", "caps": 207, "goals": 130,
            "wc_appearances": 5, "wc_goals": 8, "wc_assists": 2,
            "ballon_dor": 5, "rating": 88,
            "description": "All-time international top scorer, 5 Ballon d'Or awards"
        },
        "Kylian Mbappe": {
            "country": "France", "age": 25, "position": "Forward",
            "club": "Real Madrid", "caps": 78, "goals": 48,
            "wc_appearances": 2, "wc_goals": 12, "wc_assists": 2,
            "ballon_dor": 0, "rating": 94,
            "description": "2018 WC winner, hat-trick in 2022 WC final, future Ballon d'Or"
        },
        "Erling Haaland": {
            "country": "Norway", "age": 24, "position": "Forward",
            "club": "Manchester City", "caps": 35, "goals": 34,
            "wc_appearances": 0, "wc_goals": 0, "wc_assists": 0,
            "ballon_dor": 0, "rating": 93,
            "description": "Prolific goalscorer, Premier League record holder"
        },
        "Jude Bellingham": {
            "country": "England", "age": 21, "position": "Midfielder",
            "club": "Real Madrid", "caps": 30, "goals": 4,
            "wc_appearances": 1, "wc_goals": 1, "wc_assists": 1,
            "ballon_dor": 0, "rating": 89,
            "description": "Rising superstar, key player for England and Real Madrid"
        },
        "Harry Kane": {
            "country": "England", "age": 31, "position": "Forward",
            "club": "Bayern Munich", "caps": 98, "goals": 68,
            "wc_appearances": 2, "wc_goals": 8, "wc_assists": 2,
            "ballon_dor": 0, "rating": 90,
            "description": "England captain, all-time England top scorer"
        },
        "Vinicius Jr": {
            "country": "Brazil", "age": 24, "position": "Forward",
            "club": "Real Madrid", "caps": 32, "goals": 5,
            "wc_appearances": 1, "wc_goals": 1, "wc_assists": 0,
            "ballon_dor": 0, "rating": 92,
            "description": "Brazil's main star, 2024 La Liga best player"
        },
        "Jamal Musiala": {
            "country": "Germany", "age": 21, "position": "Midfielder",
            "club": "Bayern Munich", "caps": 34, "goals": 7,
            "wc_appearances": 1, "wc_goals": 1, "wc_assists": 0,
            "ballon_dor": 0, "rating": 91,
            "description": "Golden Boy 2023, Germany's most talented player"
        },
        "Florian Wirtz": {
            "country": "Germany", "age": 21, "position": "Midfielder",
            "club": "Bayer Leverkusen", "caps": 25, "goals": 6,
            "wc_appearances": 1, "wc_goals": 0, "wc_assists": 1,
            "ballon_dor": 0, "rating": 90,
            "description": "2024 Bundesliga champion, creative playmaker"
        },
        "Lamine Yamal": {
            "country": "Spain", "age": 17, "position": "Forward",
            "club": "Barcelona", "caps": 15, "goals": 3,
            "wc_appearances": 0, "wc_goals": 0, "wc_assists": 0,
            "ballon_dor": 0, "rating": 88,
            "description": "Youngest Euro 2024 scorer, most talented teenager in the world"
        },
        "Rodri": {
            "country": "Spain", "age": 28, "position": "Midfielder",
            "club": "Manchester City", "caps": 55, "goals": 4,
            "wc_appearances": 1, "wc_goals": 0, "wc_assists": 1,
            "ballon_dor": 1, "rating": 92,
            "description": "2024 Ballon d'Or winner, best defensive midfielder in the world"
        },
        "Virgil van Dijk": {
            "country": "Netherlands", "age": 33, "position": "Defender",
            "club": "Liverpool", "caps": 68, "goals": 7,
            "wc_appearances": 1, "wc_goals": 0, "wc_assists": 0,
            "ballon_dor": 0, "rating": 88,
            "description": "Netherlands captain, one of the best defenders in history"
        },
        "Son Heung-min": {
            "country": "South Korea", "age": 32, "position": "Forward",
            "club": "Tottenham", "caps": 127, "goals": 48,
            "wc_appearances": 3, "wc_goals": 3, "wc_assists": 1,
            "ballon_dor": 0, "rating": 89,
            "description": "South Korea captain, Premier League Golden Boot winner"
        },
        "Takefusa Kubo": {
            "country": "Japan", "age": 23, "position": "Forward",
            "club": "Real Sociedad", "caps": 38, "goals": 5,
            "wc_appearances": 1, "wc_goals": 0, "wc_assists": 1,
            "ballon_dor": 0, "rating": 84,
            "description": "Japan's most talented winger, La Liga standout"
        },
        "Mohamed Salah": {
            "country": "Egypt", "age": 32, "position": "Forward",
            "club": "Liverpool", "caps": 95, "goals": 53,
            "wc_appearances": 1, "wc_goals": 2, "wc_assists": 0,
            "ballon_dor": 0, "rating": 89,
            "description": "Egypt's all-time top scorer, Premier League legend"
        },
        "Kevin De Bruyne": {
            "country": "Belgium", "age": 33, "position": "Midfielder",
            "club": "Manchester City", "caps": 100, "goals": 27,
            "wc_appearances": 2, "wc_goals": 1, "wc_assists": 3,
            "ballon_dor": 0, "rating": 91,
            "description": "Belgium captain, one of the best playmakers ever"
        },
        "Julian Alvarez": {
            "country": "Argentina", "age": 24, "position": "Forward",
            "club": "Atletico Madrid", "caps": 36, "goals": 11,
            "wc_appearances": 1, "wc_goals": 4, "wc_assists": 0,
            "ballon_dor": 0, "rating": 86,
            "description": "2022 WC winner, versatile forward"
        },
        "Antoine Griezmann": {
            "country": "France", "age": 33, "position": "Forward",
            "club": "Atletico Madrid", "caps": 130, "goals": 44,
            "wc_appearances": 3, "wc_goals": 4, "wc_assists": 3,
            "ballon_dor": 0, "rating": 85,
            "description": "France's all-time caps leader, complete forward"
        },
        "Alphonso Davies": {
            "country": "Canada", "age": 24, "position": "Defender",
            "club": "Bayern Munich", "caps": 46, "goals": 4,
            "wc_appearances": 1, "wc_goals": 0, "wc_assists": 0,
            "ballon_dor": 0, "rating": 84,
            "description": "Canada's star, world-class left-back"
        },
        "Federico Valverde": {
            "country": "Uruguay", "age": 26, "position": "Midfielder",
            "club": "Real Madrid", "caps": 60, "goals": 7,
            "wc_appearances": 1, "wc_goals": 0, "wc_assists": 0,
            "ballon_dor": 0, "rating": 88,
            "description": "Uruguay captain, Real Madrid key player"
        },
    }

    @classmethod
    def get_team_history(cls, team: str) -> dict:
        return cls.WC_HISTORY.get(team, {
            "titles": 0, "runner_up": 0, "semi_finals": 0,
            "appearances": 0, "years_won": []
        })

    @classmethod
    def get_player_stats(cls, player: str) -> dict:
        return cls.PLAYER_STATS.get(player, {})

    @classmethod
    def get_all_player_stats(cls) -> dict:
        return cls.PLAYER_STATS


# ============================================================
# MAIN - Quick test
# ============================================================

if __name__ == "__main__":
    scraper = OddsScraper()

    # Test fallback odds
    odds = scraper.get_fallback_worldcup_odds()
    print("World Cup Winner Odds:")
    for team, odd in sorted(odds.items(), key=lambda x: x[1])[:10]:
        print(f"  {team}: {odd:.2f}")

    probs = scraper.convert_winner_odds_to_probability(odds)
    print("\nImplied Probabilities (top 10):")
    for team, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {team}: {prob*100:.1f}%")

    # Test team history
    history = TeamDataCollector.get_team_history("Brazil")
    print(f"\nBrazil WC History: {history}")
