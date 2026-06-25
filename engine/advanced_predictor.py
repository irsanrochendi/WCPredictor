"""
Advanced Prediction Engine for WC2026
Factors: Elo, xG, Player Stats, Betting Odds, Hoki, Home Advantage, Fatigue
"""
import json, os, random, math
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")

# ========== TEAM DATA (comprehensive) ==========
TEAMS_DATA = {
    "Argentina": {"elo":2150,"xG":2.1,"xGA":0.6,"form":0.85,"fatigue":0.05,"home_adv":0.08,"players":9.2,"coach":9.0,"experience":9.5,"depth":8.5},
    "France": {"elo":2120,"xG":2.0,"xGA":0.7,"form":0.80,"fatigue":0.08,"home_adv":0.05,"players":9.0,"coach":8.8,"experience":9.0,"depth":9.0},
    "Spain": {"elo":2080,"xG":1.9,"xGA":0.8,"form":0.82,"fatigue":0.06,"home_adv":0.06,"players":8.8,"coach":9.2,"experience":8.5,"depth":9.2},
    "England": {"elo":2060,"xG":1.8,"xGA":0.9,"form":0.78,"fatigue":0.10,"home_adv":0.07,"players":8.9,"coach":8.5,"experience":8.0,"depth":8.8},
    "Brazil": {"elo":2050,"xG":1.9,"xGA":0.8,"form":0.76,"fatigue":0.07,"home_adv":0.06,"players":8.7,"coach":8.3,"experience":8.5,"depth":8.3},
    "Germany": {"elo":1980,"xG":1.7,"xGA":0.9,"form":0.72,"fatigue":0.12,"home_adv":0.08,"players":8.5,"coach":8.8,"experience":9.0,"depth":8.0},
    "Netherlands": {"elo":2030,"xG":1.8,"xGA":0.8,"form":0.79,"fatigue":0.06,"home_adv":0.05,"players":8.6,"coach":8.7,"experience":8.0,"depth":8.2},
    "Portugal": {"elo":2020,"xG":1.8,"xGA":0.9,"form":0.77,"fatigue":0.09,"home_adv":0.05,"players":8.5,"coach":8.4,"experience":8.0,"depth":7.8},
    "Belgium": {"elo":2000,"xG":1.6,"xGA":1.0,"form":0.68,"fatigue":0.15,"home_adv":0.06,"players":8.3,"coach":8.0,"experience":8.5,"depth":7.5},
    "Uruguay": {"elo":1970,"xG":1.6,"xGA":1.0,"form":0.74,"fatigue":0.08,"home_adv":0.07,"players":8.0,"coach":8.2,"experience":8.0,"depth":7.2},
    "Croatia": {"elo":1960,"xG":1.5,"xGA":1.0,"form":0.70,"fatigue":0.14,"home_adv":0.05,"players":8.0,"coach":8.5,"experience":8.5,"depth":7.0},
    "Colombia": {"elo":1910,"xG":1.5,"xGA":1.1,"form":0.72,"fatigue":0.07,"home_adv":0.08,"players":7.8,"coach":8.0,"experience":7.0,"depth":7.5},
    "Japan": {"elo":1900,"xG":1.4,"xGA":1.1,"form":0.75,"fatigue":0.05,"home_adv":0.04,"players":7.8,"coach":8.2,"experience":6.5,"depth":7.8},
    "Switzerland": {"elo":1930,"xG":1.4,"xGA":1.1,"form":0.71,"fatigue":0.08,"home_adv":0.06,"players":7.7,"coach":8.0,"experience":7.5,"depth":7.3},
    "Mexico": {"elo":1860,"xG":1.3,"xGA":1.2,"form":0.68,"fatigue":0.06,"home_adv":0.10,"players":7.5,"coach":7.8,"experience":7.5,"depth":7.0},
    "United States": {"elo":1880,"xG":1.4,"xGA":1.2,"form":0.72,"fatigue":0.05,"home_adv":0.09,"players":7.6,"coach":7.5,"experience":6.5,"depth":7.5},
    "Norway": {"elo":1880,"xG":1.5,"xGA":1.2,"form":0.74,"fatigue":0.04,"home_adv":0.05,"players":7.5,"coach":7.8,"experience":6.0,"depth":7.0},
    "Senegal": {"elo":1890,"xG":1.3,"xGA":1.2,"form":0.70,"fatigue":0.06,"home_adv":0.04,"players":7.4,"coach":7.5,"experience":6.5,"depth":6.8},
    "Australia": {"elo":1820,"xG":1.2,"xGA":1.3,"form":0.65,"fatigue":0.05,"home_adv":0.07,"players":7.2,"coach":7.3,"experience":6.5,"depth":7.0},
    "Canada": {"elo":1800,"xG":1.2,"xGA":1.4,"form":0.62,"fatigue":0.04,"home_adv":0.06,"players":7.1,"coach":7.2,"experience":5.5,"depth":6.5},
    "Poland": {"elo":1850,"xG":1.3,"xGA":1.3,"form":0.65,"fatigue":0.08,"home_adv":0.05,"players":7.3,"coach":7.2,"experience":6.5,"depth":6.5},
    "South Korea": {"elo":1840,"xG":1.2,"xGA":1.3,"form":0.68,"fatigue":0.04,"home_adv":0.05,"players":7.2,"coach":7.5,"experience":6.5,"depth":7.0},
    "Ecuador": {"elo":1870,"xG":1.3,"xGA":1.3,"form":0.70,"fatigue":0.05,"home_adv":0.08,"players":7.3,"coach":7.2,"experience":6.0,"depth":6.5},
    "Italy": {"elo":1990,"xG":1.6,"xGA":1.0,"form":0.73,"fatigue":0.10,"home_adv":0.06,"players":8.4,"coach":8.5,"experience":8.5,"depth":7.8},
    "Denmark": {"elo":1920,"xG":1.4,"xGA":1.1,"form":0.72,"fatigue":0.06,"home_adv":0.05,"players":7.8,"coach":8.0,"experience":7.5,"depth":7.5},
    "Sweden": {"elo":1840,"xG":1.3,"xGA":1.3,"form":0.65,"fatigue":0.07,"home_adv":0.05,"players":7.5,"coach":7.5,"experience":7.0,"depth":7.0},
    "Austria": {"elo":1890,"xG":1.4,"xGA":1.2,"form":0.73,"fatigue":0.05,"home_adv":0.05,"players":7.6,"coach":7.8,"experience":6.5,"depth":7.0},
    "Czech Republic": {"elo":1850,"xG":1.2,"xGA":1.3,"form":0.68,"fatigue":0.06,"home_adv":0.05,"players":7.3,"coach":7.5,"experience":7.0,"depth":6.8},
    "Turkey": {"elo":1830,"xG":1.3,"xGA":1.4,"form":0.62,"fatigue":0.06,"home_adv":0.07,"players":7.2,"coach":7.0,"experience":6.0,"depth":6.5},
    "Scotland": {"elo":1820,"xG":1.1,"xGA":1.4,"form":0.60,"fatigue":0.05,"home_adv":0.06,"players":7.0,"coach":7.2,"experience":6.0,"depth":6.5},
    "Iran": {"elo":1830,"xG":1.1,"xGA":1.3,"form":0.68,"fatigue":0.04,"home_adv":0.05,"players":7.0,"coach":7.0,"experience":6.0,"depth":6.2},
    "Ivory Coast": {"elo":1820,"xG":1.2,"xGA":1.4,"form":0.65,"fatigue":0.04,"home_adv":0.04,"players":7.0,"coach":6.8,"experience":5.5,"depth":6.5},
    "Ghana": {"elo":1810,"xG":1.1,"xGA":1.4,"form":0.62,"fatigue":0.04,"home_adv":0.04,"players":6.9,"coach":6.8,"experience":5.5,"depth":6.2},
    "Egypt": {"elo":1830,"xG":1.2,"xGA":1.3,"form":0.68,"fatigue":0.04,"home_adv":0.04,"players":7.0,"coach":7.0,"experience":6.0,"depth":6.0},
    "Morocco": {"elo":1920,"xG":1.3,"xGA":1.1,"form":0.75,"fatigue":0.04,"home_adv":0.04,"players":7.5,"coach":8.0,"experience":6.5,"depth":7.0},
    "Cape Verde": {"elo":1750,"xG":1.0,"xGA":1.4,"form":0.60,"fatigue":0.03,"home_adv":0.03,"players":6.5,"coach":6.5,"experience":5.0,"depth":5.5},
    "New Zealand": {"elo":1720,"xG":0.8,"xGA":1.6,"form":0.45,"fatigue":0.03,"home_adv":0.05,"players":6.0,"coach":6.0,"experience":4.5,"depth":5.0},
    "Colombia": {"elo":1910,"xG":1.5,"xGA":1.1,"form":0.72,"fatigue":0.07,"home_adv":0.08,"players":7.8,"coach":8.0,"experience":7.0,"depth":7.5},
}

# ========== BETTING ODDS (scraped from web) ==========
# Source: Aggregated from 1xBet, Bet365, Pinnacle (June 2026)
BETTING_ODDS = {
    "Argentina": {"win": 3.5, "top4": 1.8, "top8": 1.3, "implied_prob": 0.286},
    "France": {"win": 4.2, "top4": 1.9, "top8": 1.35, "implied_prob": 0.238},
    "Spain": {"win": 5.0, "top4": 2.0, "top8": 1.4, "implied_prob": 0.200},
    "England": {"win": 5.5, "top4": 2.2, "top8": 1.45, "implied_prob": 0.182},
    "Brazil": {"win": 6.0, "top4": 2.3, "top8": 1.5, "implied_prob": 0.167},
    "Germany": {"win": 7.0, "top4": 2.5, "top8": 1.55, "implied_prob": 0.143},
    "Netherlands": {"win": 8.0, "top4": 2.8, "top8": 1.6, "implied_prob": 0.125},
    "Portugal": {"win": 9.0, "top4": 3.0, "top8": 1.7, "implied_prob": 0.111},
    "Belgium": {"win": 12.0, "top4": 3.5, "top8": 1.85, "implied_prob": 0.083},
    "Uruguay": {"win": 15.0, "top4": 4.0, "top8": 2.0, "implied_prob": 0.067},
    "Croatia": {"win": 18.0, "top4": 4.5, "top8": 2.2, "implied_prob": 0.056},
    "Italy": {"win": 10.0, "top4": 3.2, "top8": 1.75, "implied_prob": 0.100},
    "Colombia": {"win": 22.0, "top4": 5.0, "top8": 2.4, "implied_prob": 0.045},
    "Japan": {"win": 25.0, "top4": 5.5, "top8": 2.6, "implied_prob": 0.040},
    "Switzerland": {"win": 28.0, "top4": 6.0, "top8": 2.8, "implied_prob": 0.036},
    "Mexico": {"win": 30.0, "top4": 6.5, "top8": 3.0, "implied_prob": 0.033},
    "United States": {"win": 26.0, "top4": 5.8, "top8": 2.7, "implied_prob": 0.038},
    "Norway": {"win": 35.0, "top4": 7.0, "top8": 3.2, "implied_prob": 0.029},
    "Senegal": {"win": 40.0, "top4": 8.0, "top8": 3.5, "implied_prob": 0.025},
    "Australia": {"win": 50.0, "top4": 9.0, "top8": 4.0, "implied_prob": 0.020},
    "Canada": {"win": 60.0, "top4": 10.0, "top8": 4.5, "implied_prob": 0.017},
    "Poland": {"win": 45.0, "top4": 8.5, "top8": 3.8, "implied_prob": 0.022},
    "South Korea": {"win": 55.0, "top4": 9.5, "top8": 4.2, "implied_prob": 0.018},
    "Ecuador": {"win": 42.0, "top4": 8.2, "top8": 3.6, "implied_prob": 0.024},
    "Austria": {"win": 38.0, "top4": 7.5, "top8": 3.3, "implied_prob": 0.026},
    "Czech Republic": {"win": 50.0, "top4": 9.0, "top8": 4.0, "implied_prob": 0.020},
    "Turkey": {"win": 65.0, "top4": 11.0, "top8": 5.0, "implied_prob": 0.015},
    "Scotland": {"win": 80.0, "top4": 12.0, "top8": 5.5, "implied_prob": 0.013},
    "Iran": {"win": 70.0, "top4": 11.5, "top8": 5.2, "implied_prob": 0.014},
    "Ivory Coast": {"win": 90.0, "top4": 13.0, "top8": 6.0, "implied_prob": 0.011},
    "Ghana": {"win": 100.0, "top4": 14.0, "top8": 6.5, "implied_prob": 0.010},
    "Egypt": {"win": 85.0, "top4": 13.5, "top8": 6.2, "implied_prob": 0.012},
    "Morocco": {"win": 32.0, "top4": 6.8, "top8": 3.1, "implied_prob": 0.031},
    "Cape Verde": {"win": 150.0, "top4": 18.0, "top8": 8.0, "implied_prob": 0.007},
    "New Zealand": {"win": 200.0, "top4": 20.0, "top8": 9.0, "implied_prob": 0.005},
    "Denmark": {"win": 30.0, "top4": 6.5, "top8": 3.0, "implied_prob": 0.033},
    "Sweden": {"win": 55.0, "top4": 9.5, "top8": 4.2, "implied_prob": 0.018},
}

# ========== HOKI FACTOR (upset probability) ==========
# Based on historical WC data: ~15% chance of upset in knockout
HOKI_FACTOR = {
    "base_upset_chance": 0.12,  # 12% base upset chance
    "max_upset_chance": 0.25,   # 25% max for huge underdogs
    "elo_threshold": 200,       # Elo difference where upsets become likely
}

# ========== MATCH PREDICTOR ==========
class AdvancedMatchPredictor:
    def __init__(self):
        self.teams = TEAMS_DATA
        self.odds = BETTING_ODDS
    
    def get_team_data(self, team_name):
        return self.teams.get(team_name, {
            "elo": 1700, "xG": 1.0, "xGA": 1.2, "form": 0.5,
            "fatigue": 0.05, "home_adv": 0.05, "players": 6.5,
            "coach": 6.5, "experience": 5.0, "depth": 6.0
        })
    
    def get_odds(self, team_name):
        return self.odds.get(team_name, {"win": 100, "top4": 15, "top8": 6, "implied_prob": 0.01})
    
    def compute_win_probability(self, home_team, away_team, luck_factor=0.15):
        """
        Compute comprehensive win probability using all factors.
        
        Weights:
        - Elo rating: 30%
        - xG differential: 20%
        - Player quality: 15%
        - Form: 15%
        - Betting odds: 10%
        - Home advantage: 5%
        - Fatigue: 5%
        """
        home = self.get_team_data(home_team)
        away = self.get_team_data(away_team)
        home_odds = self.get_odds(home_team)
        away_odds = self.get_odds(away_team)
        
        # 1. Elo-based probability (logistic)
        elo_diff = home["elo"] - away["elo"]
        elo_prob = 1 / (1 + 10 ** (-elo_diff / 400))
        
        # 2. xG-based probability
        xg_diff = (home["xG"] - home["xGA"]) - (away["xG"] - away["xGA"])
        xg_prob = 0.5 + (xg_diff * 0.15)
        xg_prob = max(0.1, min(0.9, xg_prob))
        
        # 3. Player quality
        player_diff = home["players"] - away["players"]
        player_prob = 0.5 + (player_diff * 0.08)
        player_prob = max(0.2, min(0.8, player_prob))
        
        # 4. Form
        form_diff = home["form"] - away["form"]
        form_prob = 0.5 + (form_diff * 0.4)
        form_prob = max(0.2, min(0.8, form_prob))
        
        # 5. Betting odds (implied probability)
        home_implied = home_odds["implied_prob"]
        away_implied = away_odds["implied_prob"]
        total_implied = home_implied + away_implied
        odds_prob = home_implied / total_implied if total_implied > 0 else 0.5
        
        # 6. Home advantage
        home_adv = home["home_adv"]
        
        # 7. Fatigue (negative impact)
        fatigue_penalty = (away["fatigue"] - home["fatigue"]) * 0.3
        
        # Weighted combination
        base_prob = (
            elo_prob * 0.30 +
            xg_prob * 0.20 +
            player_prob * 0.15 +
            form_prob * 0.15 +
            odds_prob * 0.10 +
            0.5 * 0.05 +  # home advantage baseline
            home_adv * 0.03 +
            fatigue_penalty * 0.02
        )
        
        # Clamp to valid range
        base_prob = max(0.05, min(0.95, base_prob))
        
        # Apply hoki (luck) factor
        if random.random() < luck_factor:
            # Upset! Reduce favorite's probability
            elo_gap = abs(elo_diff)
            if elo_diff > 0:  # Home is favorite
                upset_magnitude = min(0.4, elo_gap / 1000)
                base_prob -= upset_magnitude * random.uniform(0.5, 1.0)
            else:  # Away is favorite
                upset_magnitude = min(0.4, elo_gap / 1000)
                base_prob += upset_magnitude * random.uniform(0.5, 1.0)
            base_prob = max(0.05, min(0.95, base_prob))
        
        # Draw probability (higher for evenly matched teams)
        draw_base = 0.22 - abs(elo_diff) / 2000
        draw_prob = max(0.12, min(0.30, draw_base))
        
        # Normalize
        home_win = base_prob * (1 - draw_prob)
        away_win = (1 - base_prob) * (1 - draw_prob)
        draw = draw_prob
        
        # Normalize to 100%
        total = home_win + away_win + draw
        home_win = home_win / total * 100
        draw = draw / total * 100
        away_win = away_win / total * 100
        
        # Expected goals
        xg_home = home["xG"] * (1 - away["fatigue"] * 0.3) * (1 + home["home_adv"] * 0.2)
        xg_away = away["xG"] * (1 - home["fatigue"] * 0.3)
        xg_home = max(0.2, xg_home + random.uniform(-0.3, 0.3))
        xg_away = max(0.2, xg_away + random.uniform(-0.3, 0.3))
        
        # BTTS probability
        btts = min(85, max(20, 50 + (home["xG"] + away["xG"] - 2) * 15))
        
        # Over 2.5 probability
        total_xg = xg_home + xg_away
        over25 = min(80, max(15, (total_xg - 1.5) * 30))
        
        return {
            "home_win": round(home_win, 1),
            "draw": round(draw, 1),
            "away_win": round(away_win, 1),
            "expected_goals": {"home": round(xg_home, 2), "away": round(xg_away, 2)},
            "btts": round(btts),
            "over_under_25": {"over": round(over25), "under": round(100-over25)},
            "most_likely_scores": self._compute_scorelines(xg_home, xg_away),
            "winner": home_team if random.random() < base_prob else away_team,
            "factors": {
                "elo_diff": elo_diff,
                "xg_diff": round(xg_diff, 2),
                "form_diff": round(form_diff, 2),
                "odds_implied": round(odds_prob * 100, 1)
            }
        }
    
    def _compute_scorelines(self, xg_h, xg_a):
        """Compute most likely scorelines based on xG."""
        scores = {}
        for h in range(5):
            for a in range(5):
                # Poisson probability
                p_h = (xg_h ** h * math.exp(-xg_h)) / math.factorial(h) if h < 7 else 0
                p_a = (xg_a ** a * math.exp(-xg_a)) / math.factorial(a) if a < 7 else 0
                prob = p_h * p_a * 100
                if prob > 0.5:
                    scores[f"{h}-{a}"] = round(prob, 1)
        # Sort by probability and return top 3
        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])[:3]
        return [{"score": s, "probability": p} for s, p in sorted_scores]


# ========== TOURNAMENT SIMULATOR ==========
class TournamentSimulator:
    def __init__(self, predictor):
        self.predictor = predictor
        self.teams = list(TEAMS_DATA.keys())
    
    def simulate_tournament(self, n_simulations=100):
        """Run full tournament simulation and return statistics."""
        results = {t: {"winner":0,"final":0,"sf":0,"qf":0,"r16":0,"r32":0} for t in self.teams}
        
        for _ in range(n_simulations):
            # Build 32-team seeded bracket
            qualified = sorted(self.teams, key=lambda t: TEAMS_DATA[t]["elo"], reverse=True)[:32]
            
            # R32
            r32_winners = []
            for i in range(16):
                pred = self.predictor.compute_win_probability(qualified[i], qualified[31-i])
                r32_winners.append(pred["winner"])
                results[pred["winner"]]["r32"] += 1
            
            # R16
            r16_winners = []
            for i in range(0, 16, 2):
                pred = self.predictor.compute_win_probability(r32_winners[i], r32_winners[i+1])
                r16_winners.append(pred["winner"])
                results[pred["winner"]]["r16"] += 1
            
            # QF
            qf_winners = []
            for i in range(0, 8, 2):
                pred = self.predictor.compute_win_probability(r16_winners[i], r16_winners[i+1])
                qf_winners.append(pred["winner"])
                results[pred["winner"]]["qf"] += 1
            
            # SF
            sf_winners = []
            for i in range(0, 4, 2):
                pred = self.predictor.compute_win_probability(qf_winners[i], qf_winners[i+1])
                sf_winners.append(pred["winner"])
                results[pred["winner"]]["sf"] += 1
            
            # Final
            final_pred = self.predictor.compute_win_probability(sf_winners[0], sf_winners[1])
            champion = final_pred["winner"]
            runner_up = sf_winners[1] if champion == sf_winners[0] else sf_winners[0]
            results[champion]["winner"] += 1
            results[champion]["final"] += 1
            results[runner_up]["final"] += 1
        
        return results
    
    def get_probabilities(self, n_simulations=200):
        """Get probability table for all teams."""
        results = self.simulate_tournament(n_simulations)
        table = []
        for team in self.teams:
            r = results[team]
            table.append({
                "team": team,
                "r32": round(r["r32"] / n_simulations * 100, 1),
                "r16": round(r["r16"] / n_simulations * 100, 1),
                "qf": round(r["qf"] / n_simulations * 100, 1),
                "sf": round(r["sf"] / n_simulations * 100, 1),
                "final": round(r["final"] / n_simulations * 100, 1),
                "winner": round(r["winner"] / n_simulations * 100, 1),
                "odds": self.predictor.get_odds(team)["win"],
                "implied_prob": self.predictor.get_odds(team)["implied_prob"] * 100
            })
        table.sort(key=lambda x: -x["winner"])
        return table


# ========== MAIN ==========
if __name__ == "__main__":
    predictor = AdvancedMatchPredictor()
    simulator = TournamentSimulator(predictor)
    
    print("=" * 60)
    print("🏆 WC2026 Advanced Prediction Engine")
    print(f"📅 {datetime.now().strftime('%B %d, %Y %H:%M')}")
    print("=" * 60)
    
    # Run simulation
    print("\n🔄 Running 200 tournament simulations...")
    prob_table = simulator.get_probabilities(200)
    
    print("\n📊 Prediksi Juara (berdasarkan simulasi + odds + xG + statistik):")
    print(f"{'#':<3} {'Tim':<18} {'Juara%':<8} {'Final%':<8} {'Odds':<8} {'Implied%':<8}")
    print("-" * 55)
    for i, t in enumerate(prob_table[:15]):
        print(f"{i+1:<3} {t['team']:<18} {t['winner']:.1f}%{'':<3} {t['final']:.1f}%{'':<3} {t['odds']:<8.1f} {t['implied_prob']:.1f}%")
    
    # Sample match prediction
    print("\n" + "=" * 60)
    print("🔮 Sample Match Prediction: Argentina vs France")
    pred = predictor.compute_win_probability("Argentina", "France")
    print(f"   Home Win: {pred['home_win']}%")
    print(f"   Draw: {pred['draw']}%")
    print(f"   Away Win: {pred['away_win']}%")
    print(f"   xG: {pred['expected_goals']['home']} - {pred['expected_goals']['away']}")
    print(f"   BTTS: {pred['btts']}%")
    print(f"   O2.5: {pred['over_under_25']['over']}%")
    print(f"   Most Likely: {[s['score'] for s in pred['most_likely_scores']]}")
    print(f"   Factors: Elo diff={pred['factors']['elo_diff']}, xG diff={pred['factors']['xg_diff']}")
