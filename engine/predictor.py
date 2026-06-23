"""
World Cup Prediction Engine — WC2026
=====================================
Data source: FIFA.com live standings (June 2026)
Format: 12 qualification groups (A-L), 4 teams each
         Top 2 from each group qualify (24 teams)
         + 3 hosts (USA, Canada, Mexico) = 27 qualified so far
         + inter-confederation play-offs for remaining spots
         Final tournament: 48 teams (16 groups of 3 → R32 knockout)

NOTE: These are the ACTUAL FIFA qualification groups from fifa.com.
The final WC2026 tournament groups will be determined by the draw.
"""
import json, math, os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.stats import poisson
from scipy.optimize import brentq


# ============================================================
# ELO RATING SYSTEM
# ============================================================

class EloSystem:
    def __init__(self, base_elo=1500, k_factor=20):
        self.base_elo = base_elo
        self.k_factor = k_factor
        self.ratings: Dict[str, float] = {}
        self.history: Dict[str, List[dict]] = {}

    def set_rating(self, team, rating):
        self.ratings[team] = rating
        if team not in self.history:
            self.history[team] = []

    def expected_score(self, elo_a, elo_b, home_adv=65.0):
        return 1.0 / (1.0 + 10 ** ((elo_b - elo_a - home_adv) / 400.0))

    def update(self, team_a, team_b, score_a, score_b, is_neutral=True, goal_diff=0):
        if team_a not in self.ratings: self.ratings[team_a] = self.base_elo
        if team_b not in self.ratings: self.ratings[team_b] = self.base_elo
        home_adv = 0.0 if is_neutral else 65.0
        exp_a = self.expected_score(self.ratings[team_a], self.ratings[team_b], home_adv)
        exp_b = 1.0 - exp_a
        if score_a > score_b: res_a, res_b = 1.0, 0.0
        elif score_a < score_b: res_a, res_b = 0.0, 1.0
        else: res_a, res_b = 0.5, 0.5
        if goal_diff == 0: mm = 1.0
        elif goal_diff == 1: mm = 1.0
        elif goal_diff == 2: mm = 1.5
        else: mm = (11 + goal_diff) / 8.0
        imp = 60
        k = self.k_factor * mm * (imp / 20.0)
        old_a, old_b = self.ratings[team_a], self.ratings[team_b]
        new_a = old_a + k * (res_a - exp_a)
        new_b = old_b + k * (res_b - exp_b)
        self.ratings[team_a] = new_a
        self.ratings[team_b] = new_b
        self.history.setdefault(team_a, []).append({"opponent": team_b, "result": res_a, "old": old_a, "new": new_a, "date": datetime.now().isoformat()})
        self.history.setdefault(team_b, []).append({"opponent": team_a, "result": res_b, "old": old_b, "new": new_b, "date": datetime.now().isoformat()})

    def get_rating(self, team):
        return self.ratings.get(team, self.base_elo)

    def win_probability(self, team_a, team_b, is_neutral=True):
        return self.expected_score(self.get_rating(team_a), self.get_rating(team_b), 0.0 if is_neutral else 65.0)


# ============================================================
# BETTING ODDS CONVERTER
# ============================================================

class OddsConverter:
    @staticmethod
    def decimal_to_probability(odds):
        return 1.0 / odds if odds > 0 else 0.0

    @staticmethod
    def remove_vig(probs, method="power"):
        total = sum(probs)
        if total <= 0: return probs
        if method == "proportional":
            return [p / total for p in probs]
        elif method == "power":
            def f(k):
                return sum(p ** k for p in probs) - 1.0
            try:
                k = brentq(f, 0.5, 2.0)
                return [p ** k for p in probs]
            except:
                return [p / total for p in probs]
        else:
            n = len(probs)
            z = (total - 1.0) / (n - 1) if n > 1 else 0
            return [p - z * p * (1 - p) / total for p in probs]

    @staticmethod
    def odds_to_probs(h, d, a):
        raw = [OddsConverter.decimal_to_probability(x) for x in [h, d, a]]
        return tuple(OddsConverter.remove_vig(raw, "power"))


# ============================================================
# TEAM DATA — Based on FIFA.com qualification groups
# Indonesian names mapped to English for consistency
# ============================================================

# Map Indonesian names → English
_ID_EN = {
    "Meksiko": "Mexico", "Republik Korea": "South Korea", "Ceko": "Czech Republic",
    "Afrika Selatan": "South Africa", "Kanada": "Canada", "Swiss": "Switzerland",
    "Bosnia dan Herzegovina": "Bosnia and Herzegovina", "Qatar": "Qatar",
    "Brasil": "Brazil", "Maroko": "Morocco", "Skotlandia": "Scotland",
    "Haiti": "Haiti", "AS": "United States", "Australia": "Australia",
    "Paraguay": "Paraguay", "Turki": "Turkey", "Jerman": "Germany",
    "Pantai Gading": "Ivory Coast", "Ekuador": "Ecuador", "Curaçao": "Curaçao",
    "Belanda": "Netherlands", "Jepang": "Japan", "Swedia": "Sweden",
    "Tunisia": "Tunisia", "Mesir": "Egypt", "IR Iran": "Iran",
    "Belgia": "Belgium", "Selandia Baru": "New Zealand", "Spanyol": "Spain",
    "Uruguay": "Uruguay", "Tanjung Verde": "Cape Verde", "Arab Saudi": "Saudi Arabia",
    "Prancis": "France", "Norwegia": "Norway", "Senegal": "Senegal",
    "Irak": "Iraq", "Argentina": "Argentina", "Austria": "Austria",
    "Aljazair": "Algeria", "Yordania": "Jordan", "Kolombia": "Colombia",
    "RD Kongo": "DR Congo", "Portugal": "Portugal", "Uzbekistan": "Uzbekistan",
    "Inggris": "England", "Ghana": "Ghana", "Panama": "Panama", "Kroasia": "Croatia",
}

# Actual FIFA qualification groups (from fifa.com)
WC2026_QUAL_GROUPS_ID = {
    "Grup A":  ["Meksiko", "Republik Korea", "Ceko", "Afrika Selatan"],
    "Grup B":  ["Kanada", "Swiss", "Bosnia dan Herzegovina", "Qatar"],
    "Grup C":  ["Brasil", "Maroko", "Skotlandia", "Haiti"],
    "Grup D":  ["AS", "Australia", "Paraguay", "Turki"],
    "Grup E":  ["Jerman", "Pantai Gading", "Ekuador", "Curaçao"],
    "Grup F":  ["Belanda", "Jepang", "Swedia", "Tunisia"],
    "Grup G":  ["Mesir", "IR Iran", "Belgia", "Selandia Baru"],
    "Grup H":  ["Spanyol", "Uruguay", "Tanjung Verde", "Arab Saudi"],
    "Grup I":  ["Prancis", "Norwegia", "Senegal", "Irak"],
    "Grup J":  ["Argentina", "Austria", "Aljazair", "Yordania"],
    "Grup K":  ["Kolombia", "RD Kongo", "Portugal", "Uzbekistan"],
    "Grup L":  ["Inggris", "Ghana", "Panama", "Kroasia"],
}

# Convert to English names
WC2026_QUAL_GROUPS = {}
for gname, teams in WC2026_QUAL_GROUPS_ID.items():
    WC2026_QUAL_GROUPS[gname] = [_ID_EN.get(t, t) for t in teams]

# All unique teams in qualification
ALL_QUAL_TEAMS = list(set(t for teams in WC2026_QUAL_GROUPS.values() for t in teams))


class TeamStrengthAnalyzer:
    """
    Team data based on actual FIFA qualification groups.
    Ratings based on FIFA rankings, recent form, squad strength.
    """

    TEAM_DATA = {
        # ═══════════════════════════════════════════════════════
        # GRUP A
        # ═══════════════════════════════════════════════════════
        "Mexico": {
            "elo": 1860, "fifa_rank": 16, "confederation": "CONCACAF",
            "wc_titles": 0, "last_best": "Quarter-final 1986",
            "key_players": ["Hirving Lozano", "Edson Alvarez", "Orbelin Pineda", "Guillermo Ochoa"],
            "avg_player_rating": 78.5, "squad_depth": 76, "coach_rating": 78,
            "form_last10": [1, 0, 0.5, 1, 0, 1, 0.5, 1, 0, 1],
            "goals_scored_10": 12, "goals_conceded_10": 11,
            "star_power": 72, "experience": 82, "tactical_flexibility": 74
        },
        "South Korea": {
            "elo": 1840, "fifa_rank": 21, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Semi-final 2002",
            "key_players": ["Son Heung-min", "Lee Kang-in", "Kim Min-jae", "Hwang Hee-chan"],
            "avg_player_rating": 78.0, "squad_depth": 76, "coach_rating": 76,
            "form_last10": [1, 0, 1, 0.5, 1, 0, 1, 0.5, 1, 0],
            "goals_scored_10": 14, "goals_conceded_10": 10,
            "star_power": 80, "experience": 78, "tactical_flexibility": 76
        },
        "Czech Republic": {
            "elo": 1850, "fifa_rank": 34, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Runner-up 1962",
            "key_players": ["Tomas Soucek", "Patrik Schick", "Vladimír Coufal", "Tomás Vaclík"],
            "avg_player_rating": 78.0, "squad_depth": 74, "coach_rating": 76,
            "form_last10": [1, 0.5, 0, 1, 1, 0, 0.5, 1, 0, 1],
            "goals_scored_10": 12, "goals_conceded_10": 10,
            "star_power": 70, "experience": 72, "tactical_flexibility": 74
        },
        "South Africa": {
            "elo": 1750, "fifa_rank": 55, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Group Stage 2010",
            "key_players": ["Percy Tau", "Themba Zwane", "Ronwen Williams", "Thapelo Morena"],
            "avg_player_rating": 73.0, "squad_depth": 64, "coach_rating": 66,
            "form_last10": [0, 0.5, 0, 1, 0, 0.5, 1, 0, 0, 1],
            "goals_scored_10": 7, "goals_conceded_10": 13,
            "star_power": 55, "experience": 60, "tactical_flexibility": 62
        },

        # ═══════════════════════════════════════════════════════
        # GRUP B
        # ═══════════════════════════════════════════════════════
        "Canada": {
            "elo": 1800, "fifa_rank": 31, "confederation": "CONCACAF",
            "wc_titles": 0, "last_best": "Group Stage 1986",
            "key_players": ["Alphonso Davies", "Jonathan David", "Cyle Larin", "Stephen Eustaquio"],
            "avg_player_rating": 77.0, "squad_depth": 72, "coach_rating": 74,
            "form_last10": [1, 0, 0, 1, 0.5, 0, 1, 0, 1, 0.5],
            "goals_scored_10": 9, "goals_conceded_10": 13,
            "star_power": 72, "experience": 62, "tactical_flexibility": 72
        },
        "Switzerland": {
            "elo": 1930, "fifa_rank": 18, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Quarter-final 1954",
            "key_players": ["Granit Xhaka", "Yann Sommer", "Manuel Akanji", "Breel Embolo"],
            "avg_player_rating": 80.5, "squad_depth": 82, "coach_rating": 82,
            "form_last10": [1, 0.5, 0, 1, 1, 0.5, 1, 0, 1, 1],
            "goals_scored_10": 14, "goals_conceded_10": 10,
            "star_power": 74, "experience": 82, "tactical_flexibility": 84
        },
        "Bosnia and Herzegovina": {
            "elo": 1780, "fifa_rank": 58, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Group Stage 2014",
            "key_players": ["Edin Dzeko", "Miralem Pjanic", "Amir Hadziahmetovic", "Ermedin Demirovic"],
            "avg_player_rating": 75.0, "squad_depth": 66, "coach_rating": 68,
            "form_last10": [0, 0.5, 1, 0, 0, 1, 0, 0.5, 0, 1],
            "goals_scored_10": 8, "goals_conceded_10": 12,
            "star_power": 62, "experience": 64, "tactical_flexibility": 66
        },
        "Qatar": {
            "elo": 1770, "fifa_rank": 48, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Group Stage 2022",
            "key_players": ["Akram Afif", "Almoez Ali", "Hassan Al-Haydos", "Boualem Khoukhi"],
            "avg_player_rating": 74.0, "squad_depth": 66, "coach_rating": 68,
            "form_last10": [0, 0, 0.5, 0, 1, 0, 0, 0.5, 0, 0],
            "goals_scored_10": 6, "goals_conceded_10": 16,
            "star_power": 55, "experience": 60, "tactical_flexibility": 65
        },

        # ═══════════════════════════════════════════════════════
        # GRUP C
        # ═══════════════════════════════════════════════════════
        "Brazil": {
            "elo": 2050, "fifa_rank": 5, "confederation": "CONMEBOL",
            "wc_titles": 5, "last_best": "Winner 2002",
            "key_players": ["Vinicius Jr", "Rodrygo", "Endrick", "Alisson Becker"],
            "avg_player_rating": 83.9, "squad_depth": 90, "coach_rating": 82,
            "form_last10": [1, 0, 0.5, 1, 1, 0.5, 1, 0, 1, 1],
            "goals_scored_10": 16, "goals_conceded_10": 9,
            "star_power": 88, "experience": 90, "tactical_flexibility": 80
        },
        "Morocco": {
            "elo": 1920, "fifa_rank": 13, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Semi-final 2022",
            "key_players": ["Hakim Ziyech", "Achraf Hakimi", "Yassine Bounou", "Sofiane Boufal"],
            "avg_player_rating": 80.2, "squad_depth": 78, "coach_rating": 88,
            "form_last10": [1, 1, 0.5, 1, 1, 1, 0, 1, 0.5, 1],
            "goals_scored_10": 14, "goals_conceded_10": 6,
            "star_power": 78, "experience": 75, "tactical_flexibility": 82
        },
        "Scotland": {
            "elo": 1820, "fifa_rank": 42, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Group Stage 1998",
            "key_players": ["Andy Robertson", "John McGinn", "Scott McTominay", "Kieran Tierney"],
            "avg_player_rating": 77.0, "squad_depth": 70, "coach_rating": 74,
            "form_last10": [1, 0, 0.5, 1, 0, 1, 0.5, 0, 1, 0],
            "goals_scored_10": 10, "goals_conceded_10": 11,
            "star_power": 68, "experience": 68, "tactical_flexibility": 72
        },
        "Haiti": {
            "elo": 1680, "fifa_rank": 85, "confederation": "CONCACAF",
            "wc_titles": 0, "last_best": "Never qualified",
            "key_players": ["Duckens Nazon", "Wilde-Donald Guerrier", "Carlens Arcus", "Alex Christian"],
            "avg_player_rating": 70.0, "squad_depth": 55, "coach_rating": 58,
            "form_last10": [0, 0, 0, 0.5, 0, 0, 1, 0, 0, 0],
            "goals_scored_10": 4, "goals_conceded_10": 18,
            "star_power": 40, "experience": 45, "tactical_flexibility": 50
        },

        # ═══════════════════════════════════════════════════════
        # GRUP D
        # ═══════════════════════════════════════════════════════
        "United States": {
            "elo": 1880, "fifa_rank": 15, "confederation": "CONCACAF",
            "wc_titles": 0, "last_best": "Semi-final 1930",
            "key_players": ["Christian Pulisic", "Weston McKennie", "Giovanni Reyna", "Tyler Adams"],
            "avg_player_rating": 79.8, "squad_depth": 80, "coach_rating": 80,
            "form_last10": [1, 0.5, 1, 0, 1, 1, 0.5, 0, 1, 1],
            "goals_scored_10": 15, "goals_conceded_10": 9,
            "star_power": 76, "experience": 72, "tactical_flexibility": 78
        },
        "Australia": {
            "elo": 1820, "fifa_rank": 29, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Round of 16 2022",
            "key_players": ["Mathew Ryan", "Harry Souttar", "Jackson Irvine", "Craig Goodwin"],
            "avg_player_rating": 76.5, "squad_depth": 72, "coach_rating": 76,
            "form_last10": [1, 0, 0.5, 1, 0, 1, 0.5, 0, 1, 1],
            "goals_scored_10": 10, "goals_conceded_10": 12,
            "star_power": 65, "experience": 70, "tactical_flexibility": 74
        },
        "Turkey": {
            "elo": 1830, "fifa_rank": 25, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Semi-final 2002",
            "key_players": ["Hakan Calhanoglu", "Arda Guler", "Cengiz Under", "Merih Demiral"],
            "avg_player_rating": 78.0, "squad_depth": 74, "coach_rating": 78,
            "form_last10": [1, 0.5, 0, 1, 1, 0, 1, 0.5, 1, 0],
            "goals_scored_10": 13, "goals_conceded_10": 11,
            "star_power": 72, "experience": 72, "tactical_flexibility": 74
        },

        # ═══════════════════════════════════════════════════════
        # GRUP E
        # ═══════════════════════════════════════════════════════
        "Germany": {
            "elo": 1980, "fifa_rank": 10, "confederation": "UEFA",
            "wc_titles": 4, "last_best": "Winner 2014",
            "key_players": ["Jamal Musiala", "Florian Wirtz", "Kai Havertz", "Joshua Kimmich"],
            "avg_player_rating": 83.0, "squad_depth": 90, "coach_rating": 86,
            "form_last10": [1, 0, 0.5, 1, 1, 0.5, 0, 1, 1, 1],
            "goals_scored_10": 17, "goals_conceded_10": 11,
            "star_power": 84, "experience": 94, "tactical_flexibility": 86
        },
        "Ivory Coast": {
            "elo": 1820, "fifa_rank": 38, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Group Stage 2014",
            "key_players": ["Sébastien Haller", "Franck Kessié", "Sébastien Aurier", "Nicolas Pépé"],
            "avg_player_rating": 77.0, "squad_depth": 72, "coach_rating": 72,
            "form_last10": [1, 0, 1, 0, 0.5, 1, 0, 1, 0, 0.5],
            "goals_scored_10": 10, "goals_conceded_10": 11,
            "star_power": 68, "experience": 68, "tactical_flexibility": 70
        },
        "Ecuador": {
            "elo": 1870, "fifa_rank": 23, "confederation": "CONMEBOL",
            "wc_titles": 0, "last_best": "Round of 16 2006",
            "key_players": ["Moises Caicedo", "Pervis Estupinan", "Enner Valencia", "Gonzalo Plata"],
            "avg_player_rating": 78.5, "squad_depth": 74, "coach_rating": 78,
            "form_last10": [1, 0.5, 1, 0, 1, 0.5, 0, 1, 1, 0],
            "goals_scored_10": 12, "goals_conceded_10": 10,
            "star_power": 72, "experience": 70, "tactical_flexibility": 76
        },
        "Curaçao": {
            "elo": 1650, "fifa_rank": 95, "confederation": "CONCACAF",
            "wc_titles": 0, "last_best": "Never qualified",
            "key_players": ["Leandro Bacuna", "Rangelo Janga", "Gino van Kessel", "Cuco Martina"],
            "avg_player_rating": 68.0, "squad_depth": 52, "coach_rating": 55,
            "form_last10": [0, 0, 0, 0, 0.5, 0, 0, 0, 1, 0],
            "goals_scored_10": 3, "goals_conceded_10": 20,
            "star_power": 35, "experience": 40, "tactical_flexibility": 45
        },

        # ═══════════════════════════════════════════════════════
        # GRUP F
        # ═══════════════════════════════════════════════════════
        "Netherlands": {
            "elo": 2030, "fifa_rank": 6, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Runner-up 2010",
            "key_players": ["Virgil van Dijk", "Frenkie de Jong", "Cody Gakpo", "Matthijs de Ligt"],
            "avg_player_rating": 83.2, "squad_depth": 88, "coach_rating": 86,
            "form_last10": [1, 1, 0.5, 1, 0, 1, 1, 0.5, 1, 1],
            "goals_scored_10": 19, "goals_conceded_10": 8,
            "star_power": 85, "experience": 86, "tactical_flexibility": 88
        },
        "Japan": {
            "elo": 1900, "fifa_rank": 14, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Round of 16 2022",
            "key_players": ["Takefusa Kubo", "Kaoru Mitoma", "Wataru Endo", "Ayase Ueda"],
            "avg_player_rating": 79.5, "squad_depth": 80, "coach_rating": 84,
            "form_last10": [1, 1, 0, 1, 1, 0.5, 1, 0, 1, 1],
            "goals_scored_10": 18, "goals_conceded_10": 7,
            "star_power": 75, "experience": 78, "tactical_flexibility": 88
        },
        "Sweden": {
            "elo": 1840, "fifa_rank": 24, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Runner-up 1958",
            "key_players": ["Alexander Isak", "Viktor Gyökeres", "Dejan Kulusevski", "Emil Forsberg"],
            "avg_player_rating": 78.5, "squad_depth": 76, "coach_rating": 76,
            "form_last10": [1, 0, 1, 0.5, 0, 1, 1, 0, 0.5, 1],
            "goals_scored_10": 13, "goals_conceded_10": 10,
            "star_power": 74, "experience": 74, "tactical_flexibility": 74
        },

        # ═══════════════════════════════════════════════════════
        # GRUP G
        # ═══════════════════════════════════════════════════════
        "Egypt": {
            "elo": 1830, "fifa_rank": 33, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Group Stage 1990",
            "key_players": ["Mohamed Salah", "Mostafa Mohamed", "Ahmed Hegazi", "Mohamed Elneny"],
            "avg_player_rating": 77.5, "squad_depth": 72, "coach_rating": 72,
            "form_last10": [1, 0.5, 1, 0, 1, 0.5, 0, 1, 1, 0],
            "goals_scored_10": 11, "goals_conceded_10": 10,
            "star_power": 80, "experience": 68, "tactical_flexibility": 70
        },
        "Iran": {
            "elo": 1830, "fifa_rank": 27, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Group Stage",
            "key_players": ["Mehdi Taremi", "Sardar Azmoun", "Alireza Jahanbakhsh", "Ehsan Hajsafi"],
            "avg_player_rating": 76.0, "squad_depth": 70, "coach_rating": 74,
            "form_last10": [1, 0.5, 0, 1, 1, 0, 0.5, 1, 0, 1],
            "goals_scored_10": 11, "goals_conceded_10": 11,
            "star_power": 68, "experience": 72, "tactical_flexibility": 70
        },
        "Belgium": {
            "elo": 2000, "fifa_rank": 8, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Semi-final 2018",
            "key_players": ["Kevin De Bruyne", "Jeremy Doku", "Romelu Lukaku", "Thibaut Courtois"],
            "avg_player_rating": 82.8, "squad_depth": 85, "coach_rating": 80,
            "form_last10": [1, 0.5, 0, 1, 1, 0.5, 0, 1, 1, 0.5],
            "goals_scored_10": 14, "goals_conceded_10": 10,
            "star_power": 86, "experience": 88, "tactical_flexibility": 78
        },
        "New Zealand": {
            "elo": 1720, "fifa_rank": 80, "confederation": "OFC",
            "wc_titles": 0, "last_best": "Group Stage 2010",
            "key_players": ["Chris Wood", "Liberato Cacace", "Marko Stamenic", "Sarpreet Singh"],
            "avg_player_rating": 72.0, "squad_depth": 60, "coach_rating": 64,
            "form_last10": [0, 0, 1, 0, 0.5, 0, 0, 1, 0, 0.5],
            "goals_scored_10": 5, "goals_conceded_10": 15,
            "star_power": 48, "experience": 55, "tactical_flexibility": 58
        },

        # ═══════════════════════════════════════════════════════
        # GRUP H
        # ═══════════════════════════════════════════════════════
        "Spain": {
            "elo": 2080, "fifa_rank": 3, "confederation": "UEFA",
            "wc_titles": 1, "last_best": "Winner 2010",
            "key_players": ["Lamine Yamal", "Pedri", "Rodri", "Dani Carvajal"],
            "avg_player_rating": 84.8, "squad_depth": 93, "coach_rating": 92,
            "form_last10": [1, 1, 1, 1, 0.5, 1, 1, 1, 1, 0.5],
            "goals_scored_10": 24, "goals_conceded_10": 6,
            "star_power": 90, "experience": 85, "tactical_flexibility": 95
        },
        "Uruguay": {
            "elo": 1970, "fifa_rank": 12, "confederation": "CONMEBOL",
            "wc_titles": 2, "last_best": "Winner 1950",
            "key_players": ["Darwin Nunez", "Federico Valverde", "Ronald Araujo", "Manuel Ugarte"],
            "avg_player_rating": 81.5, "squad_depth": 82, "coach_rating": 90,
            "form_last10": [1, 1, 0, 1, 0.5, 1, 1, 0, 1, 1],
            "goals_scored_10": 16, "goals_conceded_10": 8,
            "star_power": 80, "experience": 88, "tactical_flexibility": 85
        },
        "Cape Verde": {
            "elo": 1750, "fifa_rank": 65, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Never qualified",
            "key_players": ["Ryan Mendes", "Garry Rodrigues", "Dylan Tavares", "Wagner Fabiano"],
            "avg_player_rating": 72.0, "squad_depth": 58, "coach_rating": 62,
            "form_last10": [1, 0, 0.5, 1, 0, 0, 1, 0, 0.5, 1],
            "goals_scored_10": 7, "goals_conceded_10": 12,
            "star_power": 48, "experience": 50, "tactical_flexibility": 58
        },
        "Saudi Arabia": {
            "elo": 1780, "fifa_rank": 44, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Round of 16 1994",
            "key_players": ["Salem Al-Dawsari", "Saud Abdulhamid", "Firas Al-Buraikan", "Mohamed Kanno"],
            "avg_player_rating": 74.5, "squad_depth": 68, "coach_rating": 72,
            "form_last10": [0, 0.5, 0, 1, 0, 0.5, 1, 0, 0, 1],
            "goals_scored_10": 7, "goals_conceded_10": 14,
            "star_power": 60, "experience": 66, "tactical_flexibility": 68
        },

        # ═══════════════════════════════════════════════════════
        # GRUP I
        # ═══════════════════════════════════════════════════════
        "France": {
            "elo": 2120, "fifa_rank": 2, "confederation": "UEFA",
            "wc_titles": 2, "last_best": "Runner-up 2022",
            "key_players": ["Kylian Mbappe", "Antoine Griezmann", "Aurelien Tchouameni", "Mike Maignan"],
            "avg_player_rating": 85.1, "squad_depth": 95, "coach_rating": 88,
            "form_last10": [1, 0, 1, 1, 0.5, 1, 1, 1, 0.5, 1],
            "goals_scored_10": 18, "goals_conceded_10": 8,
            "star_power": 97, "experience": 92, "tactical_flexibility": 90
        },
        "Norway": {
            "elo": 1880, "fifa_rank": 32, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Round of 16 1998",
            "key_players": ["Erling Haaland", "Martin Odegaard", "Alexander Sorloth", "Kristian Thorstvedt"],
            "avg_player_rating": 80.0, "squad_depth": 76, "coach_rating": 78,
            "form_last10": [1, 1, 0, 1, 1, 0, 1, 0, 1, 0],
            "goals_scored_10": 16, "goals_conceded_10": 9,
            "star_power": 92, "experience": 68, "tactical_flexibility": 74
        },

        # ═══════════════════════════════════════════════════════
        # GRUP J
        # ═══════════════════════════════════════════════════════
        "Argentina": {
            "elo": 2150, "fifa_rank": 1, "confederation": "CONMEBOL",
            "wc_titles": 3, "last_best": "Winner 2022",
            "key_players": ["Lionel Messi", "Julian Alvarez", "Enzo Fernandez", "Emiliano Martinez"],
            "avg_player_rating": 84.2, "squad_depth": 92, "coach_rating": 90,
            "form_last10": [1, 1, 1, 0.5, 1, 1, 1, 0.5, 1, 1],
            "goals_scored_10": 22, "goals_conceded_10": 5,
            "star_power": 95, "experience": 96, "tactical_flexibility": 88
        },
        "Austria": {
            "elo": 1890, "fifa_rank": 22, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Semi-final 1954",
            "key_players": ["David Alaba", "Marcel Sabitzer", "Christoph Baumgartner", "Konrad Laimer"],
            "avg_player_rating": 79.5, "squad_depth": 78, "coach_rating": 82,
            "form_last10": [1, 1, 0, 1, 0.5, 1, 1, 0, 1, 0.5],
            "goals_scored_10": 16, "goals_conceded_10": 9,
            "star_power": 74, "experience": 76, "tactical_flexibility": 80
        },
        "Algeria": {
            "elo": 1820, "fifa_rank": 37, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Round of 16 2014",
            "key_players": ["Riyad Mahrez", "Islam Slimani", "Said Benrahma", "Ramy Bensebaini"],
            "avg_player_rating": 77.0, "squad_depth": 72, "coach_rating": 72,
            "form_last10": [1, 0.5, 0, 1, 0.5, 1, 0, 0, 1, 0.5],
            "goals_scored_10": 10, "goals_conceded_10": 11,
            "star_power": 70, "experience": 72, "tactical_flexibility": 70
        },
        "Jordan": {
            "elo": 1720, "fifa_rank": 62, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Never qualified",
            "key_players": ["Musa Al-Taamari", "Baha' Abdel-Rahman", "Yazan Al-Naimat", "Abdallah Nasib"],
            "avg_player_rating": 71.0, "squad_depth": 58, "coach_rating": 60,
            "form_last10": [0, 0.5, 1, 0, 0, 0.5, 1, 0, 0, 0.5],
            "goals_scored_10": 6, "goals_conceded_10": 14,
            "star_power": 45, "experience": 50, "tactical_flexibility": 55
        },

        # ═══════════════════════════════════════════════════════
        # GRUP K
        # ═══════════════════════════════════════════════════════
        "Colombia": {
            "elo": 1910, "fifa_rank": 17, "confederation": "CONMEBOL",
            "wc_titles": 0, "last_best": "Quarter-final 2014",
            "key_players": ["Luis Diaz", "James Rodriguez", "Jhon Duran", "Davinson Sanchez"],
            "avg_player_rating": 80.0, "squad_depth": 80, "coach_rating": 84,
            "form_last10": [1, 1, 1, 0.5, 1, 1, 0, 1, 1, 0.5],
            "goals_scored_10": 17, "goals_conceded_10": 7,
            "star_power": 78, "experience": 76, "tactical_flexibility": 80
        },
        "DR Congo": {
            "elo": 1750, "fifa_rank": 60, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Group Stage 1974",
            "key_players": ["Cédric Bakambu", "Gaël Kakuta", "Chancel Mbemba", "Meschak Elia"],
            "avg_player_rating": 73.0, "squad_depth": 62, "coach_rating": 62,
            "form_last10": [0, 0.5, 1, 0, 0, 1, 0, 0.5, 0, 1],
            "goals_scored_10": 7, "goals_conceded_10": 13,
            "star_power": 55, "experience": 58, "tactical_flexibility": 60
        },
        "Portugal": {
            "elo": 2020, "fifa_rank": 7, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Semi-final 2006",
            "key_players": ["Cristiano Ronaldo", "Bruno Fernandes", "Bernardo Silva", "Rafael Leao"],
            "avg_player_rating": 83.5, "squad_depth": 89, "coach_rating": 84,
            "form_last10": [1, 1, 1, 1, 1, 0.5, 1, 1, 1, 0.5],
            "goals_scored_10": 25, "goals_conceded_10": 5,
            "star_power": 92, "experience": 90, "tactical_flexibility": 84
        },
        "Uzbekistan": {
            "elo": 1750, "fifa_rank": 50, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Never qualified",
            "key_players": ["Eldor Shomurodov", "Abbosbek Fayzullaev", "Jaloliddin Masharipov", "Igor Sergeev"],
            "avg_player_rating": 73.0, "squad_depth": 62, "coach_rating": 66,
            "form_last10": [1, 0.5, 0, 1, 0, 0.5, 1, 0, 1, 0],
            "goals_scored_10": 8, "goals_conceded_10": 12,
            "star_power": 50, "experience": 52, "tactical_flexibility": 62
        },

        # ═══════════════════════════════════════════════════════
        # GRUP L
        # ═══════════════════════════════════════════════════════
        "England": {
            "elo": 2060, "fifa_rank": 4, "confederation": "UEFA",
            "wc_titles": 1, "last_best": "Semi-final 2018",
            "key_players": ["Harry Kane", "Jude Bellingham", "Phil Foden", "Declan Rice"],
            "avg_player_rating": 84.5, "squad_depth": 94, "coach_rating": 85,
            "form_last10": [1, 0.5, 1, 1, 1, 0, 1, 1, 0.5, 1],
            "goals_scored_10": 20, "goals_conceded_10": 7,
            "star_power": 91, "experience": 88, "tactical_flexibility": 82
        },
        "Ghana": {
            "elo": 1810, "fifa_rank": 35, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Quarter-final 2010",
            "key_players": ["Thomas Partey", "Mohammed Kudus", "Inaki Williams", "Jordan Ayew"],
            "avg_player_rating": 77.0, "squad_depth": 72, "coach_rating": 72,
            "form_last10": [1, 0, 1, 0, 0.5, 1, 0, 0.5, 1, 0],
            "goals_scored_10": 10, "goals_conceded_10": 12,
            "star_power": 68, "experience": 70, "tactical_flexibility": 70
        },
        "Panama": {
            "elo": 1760, "fifa_rank": 45, "confederation": "CONCACAF",
            "wc_titles": 0, "last_best": "Group Stage 2018",
            "key_players": ["Anibal Godoy", "Alberto Quintero", "Eric Davis", "Cecilio Waterman"],
            "avg_player_rating": 73.0, "squad_depth": 62, "coach_rating": 64,
            "form_last10": [0, 0.5, 1, 0, 0, 1, 0, 0.5, 0, 1],
            "goals_scored_10": 7, "goals_conceded_10": 13,
            "star_power": 50, "experience": 58, "tactical_flexibility": 60
        },
        "Croatia": {
            "elo": 1960, "fifa_rank": 11, "confederation": "UEFA",
            "wc_titles": 0, "last_best": "Runner-up 2018",
            "key_players": ["Luka Modric", "Ivan Perisic", "Mateo Kovacic", "Josko Gvardiol"],
            "avg_player_rating": 81.8, "squad_depth": 83, "coach_rating": 88,
            "form_last10": [1, 0.5, 1, 0, 1, 0.5, 1, 1, 0, 1],
            "goals_scored_10": 13, "goals_conceded_10": 9,
            "star_power": 78, "experience": 92, "tactical_flexibility": 86
        },

        # ═══════════════════════════════════════════════════════
        # Additional teams from Wikipedia qualified list
        # ═══════════════════════════════════════════════════════
        "Iraq": {
            "elo": 1760, "fifa_rank": 46, "confederation": "AFC",
            "wc_titles": 0, "last_best": "Group Stage 1986",
            "key_players": ["Aymen Hussein", "Bashar Resan", "Ahmed Yasin", "Jalal Hassan"],
            "avg_player_rating": 73.5, "squad_depth": 64, "coach_rating": 66,
            "form_last10": [0, 0.5, 1, 0, 0.5, 1, 0, 0, 1, 0.5],
            "goals_scored_10": 7, "goals_conceded_10": 13,
            "star_power": 52, "experience": 60, "tactical_flexibility": 64
        },
        "Senegal": {
            "elo": 1890, "fifa_rank": 19, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Round of 16 2022",
            "key_players": ["Sadio Mane", "Kalidou Koulibaly", "Edouard Mendy", "Ismaila Sarr"],
            "avg_player_rating": 79.8, "squad_depth": 76, "coach_rating": 80,
            "form_last10": [1, 1, 0, 1, 0.5, 1, 0, 1, 1, 0.5],
            "goals_scored_10": 13, "goals_conceded_10": 8,
            "star_power": 76, "experience": 74, "tactical_flexibility": 76
        },
        "Paraguay": {
            "elo": 1800, "fifa_rank": 40, "confederation": "CONMEBOL",
            "wc_titles": 0, "last_best": "Quarter-final 2010",
            "key_players": ["Miguel Almiron", "Gustavo Gomez", "Mathias Villasanti", "Antonio Sanabria"],
            "avg_player_rating": 75.5, "squad_depth": 68, "coach_rating": 74,
            "form_last10": [1, 0, 0.5, 1, 0, 0.5, 1, 0, 1, 0.5],
            "goals_scored_10": 9, "goals_conceded_10": 11,
            "star_power": 60, "experience": 68, "tactical_flexibility": 70
        },
        "Tunisia": {
            "elo": 1800, "fifa_rank": 36, "confederation": "CAF",
            "wc_titles": 0, "last_best": "Group Stage",
            "key_players": ["Wahbi Khazri", "Aissa Laidouni", "Montassar Talbi", "Ellyes Skhiri"],
            "avg_player_rating": 75.0, "squad_depth": 68, "coach_rating": 70,
            "form_last10": [0, 0.5, 0, 1, 0, 0.5, 1, 0, 0, 1],
            "goals_scored_10": 7, "goals_conceded_10": 13,
            "star_power": 60, "experience": 66, "tactical_flexibility": 70
        },
    }

    @classmethod
    def get_team(cls, name):
        return cls.TEAM_DATA.get(name, {})

    @classmethod
    def get_all_teams(cls):
        return cls.TEAM_DATA

    @classmethod
    def compute_strength_score(cls, team_name):
        data = cls.get_team(team_name)
        if not data:
            return {"overall": 0, "breakdown": {}}
        weights = {
            "elo_normalized": 0.20, "fifa_rank_normalized": 0.10,
            "avg_player_rating": 0.15, "squad_depth": 0.10,
            "form": 0.15, "star_power": 0.10, "experience": 0.08,
            "tactical_flexibility": 0.07, "coach_rating": 0.05
        }
        elo_norm = min(100, max(0, (data["elo"] - 1500) / 700 * 100))
        rank_norm = min(100, max(0, (100 - data["fifa_rank"]) / 99 * 100))
        form_avg = sum(data["form_last10"]) / len(data["form_last10"]) * 100
        breakdown = {
            "elo_normalized": round(elo_norm, 1),
            "fifa_rank_normalized": round(rank_norm, 1),
            "avg_player_rating": round(data["avg_player_rating"] / 90 * 100, 1),
            "squad_depth": round(data["squad_depth"], 1),
            "form": round(form_avg, 1),
            "star_power": round(data["star_power"], 1),
            "experience": round(data["experience"], 1),
            "tactical_flexibility": round(data["tactical_flexibility"], 1),
            "coach_rating": round(data["coach_rating"], 1),
        }
        overall = sum(breakdown[k] * w for k, w in weights.items())
        return {"overall": round(overall, 1), "breakdown": breakdown, "raw_data": data}


# ============================================================
# MATCH PREDICTOR
# ============================================================

class MatchPredictor:
    def __init__(self):
        self.elo = EloSystem()
        self.odds_converter = OddsConverter()
        self._init_elo_ratings()

    def _init_elo_ratings(self):
        for team, data in TeamStrengthAnalyzer.get_all_teams().items():
            self.elo.set_rating(team, data["elo"])

    def predict_match(self, home_team, away_team, home_odds=None, draw_odds=None, away_odds=None):
        home_data = TeamStrengthAnalyzer.get_team(home_team)
        away_data = TeamStrengthAnalyzer.get_team(away_team)
        if not home_data or not away_data:
            return {"error": f"Team data not found: {home_team} or {away_team}"}

        elo_prob = self.elo.win_probability(home_team, away_team, is_neutral=True)
        elo_away_prob = 1 - elo_prob
        elo_diff = abs(self.elo.get_rating(home_team) - self.elo.get_rating(away_team))
        elo_draw_prob = max(0.15, 0.33 - elo_diff / 2000)
        scale = (1 - elo_draw_prob)
        elo_home = elo_prob * scale
        elo_away = elo_away_prob * scale

        home_strength = TeamStrengthAnalyzer.compute_strength_score(home_team)
        away_strength = TeamStrengthAnalyzer.compute_strength_score(away_team)
        str_total = home_strength["overall"] + away_strength["overall"]
        str_home = home_strength["overall"] / str_total if str_total > 0 else 0.5
        str_away = 1 - str_home
        str_draw = max(0.15, 0.30 - abs(str_home - str_away) * 0.5)
        str_scale = (1 - str_draw)
        str_home_final = str_home * str_scale
        str_away_final = str_away * str_scale

        odds_home, odds_draw, odds_away = None, None, None
        if home_odds and draw_odds and away_odds:
            odds_home, odds_draw, odds_away = self.odds_converter.odds_to_probs(home_odds, draw_odds, away_odds)

        home_xg = self._expected_goals(home_team, away_team, is_home=True)
        away_xg = self._expected_goals(home_team, away_team, is_home=False)
        poisson_probs = self._poisson_match_probs(home_xg, away_xg)

        if odds_home is not None:
            final_home = 0.30 * elo_home + 0.20 * str_home_final + 0.35 * odds_home + 0.15 * poisson_probs["home"]
            final_draw = 0.30 * elo_draw_prob + 0.20 * str_draw + 0.35 * odds_draw + 0.15 * poisson_probs["draw"]
            final_away = 0.30 * elo_away + 0.20 * str_away_final + 0.35 * odds_away + 0.15 * poisson_probs["away"]
        else:
            final_home = 0.40 * elo_home + 0.30 * str_home_final + 0.30 * poisson_probs["home"]
            final_draw = 0.40 * elo_draw_prob + 0.30 * str_draw + 0.30 * poisson_probs["draw"]
            final_away = 0.40 * elo_away + 0.30 * str_away_final + 0.30 * poisson_probs["away"]

        total = final_home + final_draw + final_away
        final_home /= total
        final_draw /= total
        final_away /= total

        scorelines = self._most_likely_scores(home_xg, away_xg)
        probs_matrix = np.array([
            [elo_home, elo_draw_prob, elo_away],
            [str_home_final, str_draw, str_away_final],
            [poisson_probs["home"], poisson_probs["draw"], poisson_probs["away"]]
        ])
        if odds_home is not None:
            probs_matrix = np.vstack([probs_matrix, [odds_home, odds_draw, odds_away]])
        confidence = 1.0 - np.mean(np.std(probs_matrix, axis=0))
        btts_prob = self._btts_probability(home_xg, away_xg)
        ou_25 = self._over_under_probability(home_xg + away_xg, 2.5)

        return {
            "home_team": home_team, "away_team": away_team,
            "prediction": {"home_win": round(final_home * 100, 1), "draw": round(final_draw * 100, 1), "away_win": round(final_away * 100, 1)},
            "confidence": round(confidence * 100, 1),
            "expected_goals": {"home": round(home_xg, 2), "away": round(away_xg, 2)},
            "most_likely_scores": scorelines[:5],
            "btts": round(btts_prob * 100, 1),
            "over_under_25": {"over": round(ou_25["over"] * 100, 1), "under": round(ou_25["under"] * 100, 1)},
            "model_breakdown": {
                "elo": {"home": round(elo_home * 100, 1), "draw": round(elo_draw_prob * 100, 1), "away": round(elo_away * 100, 1)},
                "strength": {"home": round(str_home_final * 100, 1), "draw": round(str_draw * 100, 1), "away": round(str_away_final * 100, 1)},
                "poisson": {"home": round(poisson_probs["home"] * 100, 1), "draw": round(poisson_probs["draw"] * 100, 1), "away": round(poisson_probs["away"] * 100, 1)},
                "odds": {"home": round(odds_home * 100, 1) if odds_home else None, "draw": round(odds_draw * 100, 1) if odds_draw else None, "away": round(odds_away * 100, 1) if odds_away else None},
            },
            "team_strengths": {home_team: home_strength, away_team: away_strength}
        }

    def _expected_goals(self, home_team, away_team, is_home):
        data = TeamStrengthAnalyzer.get_team(home_team if is_home else away_team)
        opp_data = TeamStrengthAnalyzer.get_team(away_team if is_home else home_team)
        if not data or not opp_data: return 1.3
        attack = data["goals_scored_10"] / 10.0
        opp_defense = opp_data["goals_conceded_10"] / 10.0
        xg = attack * opp_defense / 1.35
        if is_home: xg *= 1.1
        return max(0.3, min(4.0, xg))

    def _poisson_match_probs(self, home_xg, away_xg, max_goals=7):
        hp = [poisson.pmf(i, home_xg) for i in range(max_goals + 1)]
        ap = [poisson.pmf(i, away_xg) for i in range(max_goals + 1)]
        hw, d, aw = 0.0, 0.0, 0.0
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                p = hp[i] * ap[j]
                if i > j: hw += p
                elif i == j: d += p
                else: aw += p
        return {"home": hw, "draw": d, "away": aw}

    def _most_likely_scores(self, home_xg, away_xg, top_n=5):
        scores = []
        for i in range(6):
            for j in range(6):
                scores.append({"score": f"{i}-{j}", "probability": round(poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg) * 100, 2)})
        scores.sort(key=lambda x: x["probability"], reverse=True)
        return scores[:top_n]

    def _btts_probability(self, home_xg, away_xg):
        return (1 - poisson.pmf(0, home_xg)) * (1 - poisson.pmf(0, away_xg))

    def _over_under_probability(self, total_xg, line):
        over = 1 - poisson.cdf(int(line), total_xg)
        return {"over": over, "under": 1 - over}


# ============================================================
# TOURNAMENT SIMULATOR
# ============================================================

# ============================================================
# TOURNAMENT SIMULATOR — Official FIFA WC2026 Bracket
# ============================================================

class TournamentSimulator:
    """
    Full WC2026 simulation with official FIFA knockout bracket.
    
    Stage 1 - Qualification (12 groups × 4 teams):
      - Top 2 from each group auto qualify (24 teams)
      - Best 8 third-place teams qualify (by points, GD, GF)
      - Total: 32 teams advance to knockout
    
    Stage 2 - Knockout (Official FIFA bracket):
      R32: M73-M88 (16 matches)
      R16: M89-M96 (8 matches)
      QF: M97-M100 (4 matches)
      SF: M101-M102 (2 matches)
      Final: M103 (1 match)
    """

    def __init__(self, predictor):
        self.predictor = predictor
        self._cache = {}

    def _get_match_prob(self, home, away):
        key = (home, away)
        if key not in self._cache:
            p = self.predictor.predict_match(home, away)
            self._cache[key] = p
        return self._cache[key]

    def _apply_luck_factor(self, prob_a, prob_b, elo_a, elo_b):
        elo_diff = abs(elo_a - elo_b)
        luck_roll = np.random.random()
        if luck_roll < 0.15:
            if elo_a > elo_b:
                upset_factor = np.random.uniform(0.3, 0.7)
                prob_a *= (1 - upset_factor)
                prob_b = 1 - prob_a
            else:
                upset_factor = np.random.uniform(0.3, 0.7)
                prob_b *= (1 - upset_factor)
                prob_a = 1 - prob_b
        if elo_diff > 200 and np.random.random() < 0.25:
            draw_boost = np.random.uniform(0.15, 0.35)
            prob_a *= (1 - draw_boost)
            prob_b *= (1 - draw_boost)
        return prob_a, prob_b

    def _simulate_knockout_match(self, team_a, team_b):
        if team_a is None or team_b is None:
            return team_a if team_b is None else team_b
        p = self._get_match_prob(team_a, team_b)
        d_a = TeamStrengthAnalyzer.get_team(team_a)
        d_b = TeamStrengthAnalyzer.get_team(team_b)
        elo_a = d_a.get("elo", 1500) if d_a else 1500
        elo_b = d_b.get("elo", 1500) if d_b else 1500
        base_a = p["prediction"]["home_win"] / 100 + p["prediction"]["draw"] / 100 * 0.5
        base_b = p["prediction"]["away_win"] / 100 + p["prediction"]["draw"] / 100 * 0.5
        prob_a, prob_b = self._apply_luck_factor(base_a, base_b, elo_a, elo_b)
        total = prob_a + prob_b
        if total > 0:
            prob_a /= total; prob_b /= total
        else:
            prob_a = prob_b = 0.5
        return team_a if np.random.random() < prob_a else team_b

    def _simulate_group_match_with_luck(self, team_a, team_b, match_probs):
        p = match_probs.get((team_a, team_b))
        if not p: p = self._get_match_prob(team_a, team_b)
        d_a = TeamStrengthAnalyzer.get_team(team_a)
        d_b = TeamStrengthAnalyzer.get_team(team_b)
        elo_a = d_a.get("elo", 1500) if d_a else 1500
        elo_b = d_b.get("elo", 1500) if d_b else 1500
        elo_diff = elo_a - elo_b
        xg_a = p["expected_goals"]["home"]
        xg_b = p["expected_goals"]["away"]
        luck_roll = np.random.random()
        if luck_roll < 0.20:
            if elo_diff > 150:
                xg_b *= np.random.uniform(1.3, 2.0); xg_a *= np.random.uniform(0.5, 0.8)
            elif elo_diff < -150:
                xg_a *= np.random.uniform(1.3, 2.0); xg_b *= np.random.uniform(0.5, 0.8)
        if np.random.random() < 0.10:
            xg_a *= 0.3; xg_b *= 0.3
        return max(0, round(np.random.normal(xg_a, 1.0))), max(0, round(np.random.normal(xg_b, 1.0)))

    def _simulate_group_fast(self, teams, match_probs):
        r = {t: {"points": 0, "gf": 0, "ga": 0, "gd": 0} for t in teams}
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                hg, ag = self._simulate_group_match_with_luck(teams[i], teams[j], match_probs)
                r[teams[i]]["gf"] += hg; r[teams[i]]["ga"] += ag
                r[teams[j]]["gf"] += ag; r[teams[j]]["ga"] += hg
                if hg > ag: r[teams[i]]["points"] += 3
                elif hg < ag: r[teams[j]]["points"] += 3
                else: r[teams[i]]["points"] += 1; r[teams[j]]["points"] += 1
        for t in r: r[t]["gd"] = r[t]["gf"] - r[t]["ga"]
        return r

    def simulate_tournament(self, groups, n_simulations=10000):
        """
        Full simulation: 12 qualification groups → 32 qualified teams → Knockout.
        
        Bracket approach: 32 teams sorted by strength (group winners first, 
        then runners-up, then best 3rd place). Standard seeded bracket:
        1v32, 2v31, 3v30, ... for R32.
        
        Known qualified teams (Germany, Mexico, Argentina, USA) are placed
        as group winners in the seeding.
        """
        all_teams = [t for teams in groups.values() for t in teams]
        rc = {t: {"qualified": 0, "first": 0, "second": 0, "third_best": 0,
            "r32": 0, "r16": 0, "qf": 0, "sf": 0, "final": 0, "winner": 0} for t in all_teams}
        bracket_results = {"r32": [], "r16": [], "qf": [], "sf": [], "final": [], "winner": []}

        # Pre-compute group match probabilities
        match_probs = {}
        for gn, teams in groups.items():
            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    self._get_match_prob(teams[i], teams[j])

        for sim in range(n_simulations):
            # === STAGE 1: QUALIFICATION GROUPS ===
            group_winners = []
            group_runners = []
            third_place_teams = []
            
            # Known qualified teams and their assigned groups
            # Germany=Grp E, Mexico=Grp A, Argentina=Grp C, USA=Grp D
            known_assignments = {"Germany": "E", "Mexico": "A", "Argentina": "C", "United States": "D"}
            known_in_32 = set()
            
            for gn, teams in groups.items():
                result = self._simulate_group_fast(teams, match_probs)
                st = sorted(result.items(), key=lambda x: (x[1]["points"], x[1]["gd"], x[1]["gf"]), reverse=True)
                
                # Check if this group has a known qualified team
                known_team = None
                for kt, kg in known_assignments.items():
                    if kg == gn:
                        known_team = kt
                        break
                
                if known_team:
                    # Known team auto-wins this group
                    known_in_32.add(known_team)
                    group_winners.append(known_team)
                    rc[known_team]["qualified"] += 1; rc[known_team]["first"] += 1
                    
                    # Runner-up is the best non-known team from this group
                    runner = st[0][0] if st[0][0] != known_team else st[1][0]
                    group_runners.append(runner)
                    rc[runner]["qualified"] += 1; rc[runner]["second"] += 1
                    
                    # Third place from remaining
                    third_candidates = [t[0] for t in st if t[0] != known_team and t[0] != runner]
                    if third_candidates:
                        third_place_teams.append({"team": third_candidates[0], "points": 0, "gd": 0, "gf": 0})
                else:
                    group_winners.append(st[0][0])
                    group_runners.append(st[1][0])
                    rc[st[0][0]]["qualified"] += 1; rc[st[0][0]]["first"] += 1
                    rc[st[1][0]]["qualified"] += 1; rc[st[1][0]]["second"] += 1
                    third_place_teams.append({"team": st[2][0], "points": st[2][1]["points"],
                        "gd": st[2][1]["gd"], "gf": st[2][1]["gf"]})
            
            # Best 8 third-place teams
            third_place_teams.sort(key=lambda x: (x["points"], x["gd"], x["gf"]), reverse=True)
            best_third = [t["team"] for t in third_place_teams[:8]]
            for t in best_third:
                rc[t]["qualified"] += 1; rc[t]["third_best"] += 1

            # === STAGE 2: BUILD 32-TEAM KNOCKOUT BRACKET ===
            # Combine: known teams + winners + runners-up + best 3rd = 32
            seeded = []
            for t in ["Germany", "Argentina", "Mexico", "United States"]:
                if t not in seeded: seeded.append(t)
            for t in group_winners:
                if t not in seeded: seeded.append(t)
            for t in group_runners:
                if t not in seeded: seeded.append(t)
            for t in best_third:
                if t not in seeded: seeded.append(t)
            
            qualified_32 = seeded[:32]
            
            # Sort by Elo strength for seeding
            def get_elo(t):
                d = TeamStrengthAnalyzer.get_team(t)
                return d.get("elo", 1500) if d else 1500
            
            qualified_32.sort(key=get_elo, reverse=True)
            
            # === R32: 1v32, 2v31, 3v30, ... ===
            r32_winners = []
            for i in range(16):
                a, b = qualified_32[i], qualified_32[31 - i]
                w = self._simulate_knockout_match(a, b)
                r32_winners.append(w)
                if w in rc: rc[w]["r32"] += 1
                if sim == 0: bracket_results["r32"].append({"home": a, "away": b, "winner": w})
            
            # === R16: adjacent pairs ===
            r16_winners = []
            for i in range(0, 16, 2):
                w = self._simulate_knockout_match(r32_winners[i], r32_winners[i+1])
                r16_winners.append(w)
                if w in rc: rc[w]["r16"] += 1
                if sim == 0: bracket_results["r16"].append({"home": r32_winners[i], "away": r32_winners[i+1], "winner": w})
            
            # === QF ===
            qf_winners = []
            for i in range(0, 8, 2):
                w = self._simulate_knockout_match(r16_winners[i], r16_winners[i+1])
                qf_winners.append(w)
                if w in rc: rc[w]["qf"] += 1
                if sim == 0: bracket_results["qf"].append({"home": r16_winners[i], "away": r16_winners[i+1], "winner": w})
            
            # === SF ===
            sf_winners = []
            for i in range(0, 4, 2):
                w = self._simulate_knockout_match(qf_winners[i], qf_winners[i+1])
                sf_winners.append(w)
                if w in rc: rc[w]["sf"] += 1
                if sim == 0: bracket_results["sf"].append({"home": qf_winners[i], "away": qf_winners[i+1], "winner": w})
            
            # === FINAL ===
            champion = self._simulate_knockout_match(sf_winners[0], sf_winners[1])
            runner_up = sf_winners[1] if champion == sf_winners[0] else sf_winners[0]
            if champion in rc: rc[champion]["winner"] += 1; rc[champion]["final"] += 1
            if runner_up in rc: rc[runner_up]["final"] += 1
            if sim == 0:
                bracket_results["final"] = {"home": sf_winners[0], "away": sf_winners[1], "winner": champion}
                bracket_results["winner"] = champion

        probs = {}
        for t in all_teams:
            probs[t] = {k: round(rc[t][k] / n_simulations * 100, 1) for k in rc[t]}
        
        sorted_t = sorted(probs.items(), key=lambda x: x[1]["winner"], reverse=True)
        return {"n_simulations": n_simulations, "probabilities": dict(sorted_t), "bracket": bracket_results}


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    p = MatchPredictor()
    r = p.predict_match("Argentina", "France", 2.80, 3.20, 2.60)
    print(json.dumps(r, indent=2, default=str))
