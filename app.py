"""
World Cup Predictor - Flask Web Application
Data source: FIFA.com live qualification standings (June 2026)
"""
import json, os, sys, random, time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.predictor import (
    MatchPredictor, TeamStrengthAnalyzer, OddsConverter,
    TournamentSimulator, WC2026_QUAL_GROUPS, WC2026_QUAL_GROUPS_ID, _ID_EN
)
from scraper.odds_scraper import OddsScraper, TeamDataCollector
from scraper.live_scraper import load_live_data, save_live_data, generate_sample_data

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(os.path.join(PROJECT_DIR, "engine")):
    PROJECT_DIR = r"C:\Users\ThinkPad\worldcup-predictor"
LIVE_DATA_FILE = os.path.join(PROJECT_DIR, "data", "live_standings.json")
SCHEDULE_FILE = os.path.join(PROJECT_DIR, "data", "schedule_predictions.json")
CACHE_FILE = os.path.join(PROJECT_DIR, "data", "live_knockout_cache.json")

app = Flask(__name__)
app.config["SECRET_KEY"] = "worldcup2026-predictor-secret"

predictor = MatchPredictor()
simulator = TournamentSimulator(predictor)
odds_scraper = OddsScraper()
odds_converter = OddsConverter()


@app.route("/")
def index():
    winner_odds = odds_scraper.get_fallback_worldcup_odds()
    winner_probs = odds_scraper.convert_winner_odds_to_probability(winner_odds)
    sorted_teams = sorted(winner_probs.items(), key=lambda x: x[1], reverse=True)[:16]

    all_teams = TeamStrengthAnalyzer.get_all_teams()
    rankings = []
    for team_name in all_teams:
        strength = TeamStrengthAnalyzer.compute_strength_score(team_name)
        rankings.append({
            "name": team_name, "overall": strength["overall"],
            "elo": all_teams[team_name]["elo"],
            "fifa_rank": all_teams[team_name]["fifa_rank"],
            "wc_titles": all_teams[team_name]["wc_titles"],
            "confederation": all_teams[team_name]["confederation"],
            "winner_prob": winner_probs.get(team_name, 0) * 100,
        })
    rankings.sort(key=lambda x: x["overall"], reverse=True)

    return render_template("index.html",
        rankings=rankings, winner_odds=sorted_teams[:20],
        groups=WC2026_QUAL_GROUPS,
        groups_id=WC2026_QUAL_GROUPS_ID,
        now=datetime.now().strftime("%B %d, %Y %H:%M UTC")
    )


@app.route("/predict", methods=["GET", "POST"])
def predict():
    all_teams = sorted(TeamStrengthAnalyzer.get_all_teams().keys())
    prediction = None
    home_team = away_team = ""
    home_odds = draw_odds = away_odds = ""

    if request.method == "POST":
        home_team = request.form.get("home_team", "")
        away_team = request.form.get("away_team", "")
        home_odds = request.form.get("home_odds", "")
        draw_odds = request.form.get("draw_odds", "")
        away_odds = request.form.get("away_odds", "")
        h_odds = float(home_odds) if home_odds else None
        d_odds = float(draw_odds) if draw_odds else None
        a_odds = float(away_odds) if away_odds else None
        if home_team and away_team:
            prediction = predictor.predict_match(home_team, away_team, h_odds, d_odds, a_odds)

    return render_template("predict.html", teams=all_teams, prediction=prediction,
        home_team=home_team, away_team=away_team,
        home_odds=home_odds, draw_odds=draw_odds, away_odds=away_odds)


@app.route("/team/<team_name>")
def team_detail(team_name):
    team_data = TeamStrengthAnalyzer.get_team(team_name)
    if not team_data:
        return redirect(url_for("index"))
    strength = TeamStrengthAnalyzer.compute_strength_score(team_name)
    all_teams = list(TeamStrengthAnalyzer.get_all_teams().keys())
    match_preds = []
    for opponent in all_teams:
        if opponent != team_name:
            pred = predictor.predict_match(team_name, opponent)
            match_preds.append({
                "opponent": opponent,
                "home_win": pred["prediction"]["home_win"],
                "draw": pred["prediction"]["draw"],
                "away_win": pred["prediction"]["away_win"],
                "confidence": pred["confidence"],
                "expected_goals_home": pred["expected_goals"]["home"],
                "expected_goals_away": pred["expected_goals"]["away"],
            })
    match_preds.sort(key=lambda x: x["home_win"], reverse=True)
    return render_template("team.html", team=team_name, data=team_data, strength=strength, match_preds=match_preds)


@app.route("/players")
def players():
    all_players = TeamDataCollector.get_all_player_stats()
    players_list = [{"name": n, **d} for n, d in all_players.items()]
    players_list.sort(key=lambda x: x.get("rating", 0), reverse=True)
    return render_template("players.html", players=players_list)


@app.route("/player/<player_name>")
def player_detail(player_name):
    player_data = TeamDataCollector.get_player_stats(player_name)
    return render_template("player.html", player=player_name, data=player_data)


@app.route("/tournament")
def tournament():
    return render_template("tournament.html", groups=WC2026_QUAL_GROUPS)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    data = request.get_json() or {}
    n_sims = min(50000, max(100, int(data.get("simulations", 10000))))
    result = simulator.simulate_tournament(WC2026_QUAL_GROUPS, n_simulations=n_sims)
    return jsonify(result)


@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json() or {}
    home = data.get("home_team", "")
    away = data.get("away_team", "")
    if not home or not away:
        return jsonify({"error": "home_team and away_team required"}), 400
    result = predictor.predict_match(home, away, data.get("home_odds"), data.get("draw_odds"), data.get("away_odds"))
    return jsonify(result)


@app.route("/api/teams")
def api_teams():
    teams = {}
    for name, data in TeamStrengthAnalyzer.get_all_teams().items():
        strength = TeamStrengthAnalyzer.compute_strength_score(name)
        teams[name] = {**data, "strength_score": strength["overall"]}
    return jsonify(teams)


@app.route("/api/odds")
def api_odds():
    odds = odds_scraper.get_fallback_worldcup_odds()
    probs = odds_scraper.convert_winner_odds_to_probability(odds)
    return jsonify({"odds": odds, "probabilities": probs})


@app.route("/live-predictions")
def live_predictions():
    """Serve the fully client-side live predictions page."""
    return send_from_directory(os.path.join(PROJECT_DIR, "static"), "live.html")


def run_knockout_simulation(live_data):
    """
    Run knockout simulation based on current standings.
    Teams already qualified get their position, others are predicted.
    """
    # Get current group standings
    group_winners = []
    group_runners = []
    third_place = []
    
    for gname, teams in live_data.get("groups", {}).items():
        for t in teams:
            if t.get("status") == "qualified":
                if t["pos"] == 1:
                    group_winners.append(t["team"])
                elif t["pos"] == 2:
                    group_runners.append(t["team"])
                elif t["pos"] == 3:
                    third_place.append(t["team"])
            else:
                # Not yet decided — use current position as prediction
                if t["pos"] == 1:
                    group_winners.append(t["team"])
                elif t["pos"] == 2:
                    group_runners.append(t["team"])
                elif t["pos"] == 3:
                    third_place.append({"team": t["team"], "pts": t["pts"], "gd": t["gd"], "gf": t.get("gf", 0)})
    
    # Sort 3rd place by points, GD, GF
    third_place.sort(key=lambda x: (-x.get("pts", 0), -x.get("gd", 0), -x.get("gf", 0)))
    best_third = [t["team"] if isinstance(t, dict) else t for t in third_place[:8]]
    
    # Combine into 32 teams
    known = ["Germany", "Argentina", "Mexico", "United States"]
    seeded = []
    for t in known:
        if t not in seeded: seeded.append(t)
    for t in group_winners:
        if t not in seeded: seeded.append(t)
    for t in group_runners:
        if t not in seeded: seeded.append(t)
    for t in best_third:
        if t not in seeded: seeded.append(t)
    
    qualified_32 = seeded[:32]
    
    # Sort by Elo
    def get_elo(t):
        d = TeamStrengthAnalyzer.get_team(t)
        return d.get("elo", 1500) if d else 1500
    qualified_32.sort(key=get_elo, reverse=True)
    
    # Run knockout bracket (30 simulations for speed)
    n_sims = 30
    stage_counts = {t: {"r32": 0, "r16": 0, "qf": 0, "sf": 0, "final": 0, "winner": 0} for t in qualified_32}

    def sim_match(a, b):
        """Helper to simulate a knockout match (fast version)."""
        d_a = TeamStrengthAnalyzer.get_team(a)
        d_b = TeamStrengthAnalyzer.get_team(b)
        elo_a = d_a.get("elo", 1500) if d_a else 1500
        elo_b = d_b.get("elo", 1500) if d_b else 1500
        # Simplified probability based on Elo
        prob_a = elo_a / (elo_a + elo_b)
        # Apply luck
        if random.random() < 0.15:
            if elo_a > elo_b:
                prob_a *= random.uniform(0.3, 0.7)
            else:
                prob_a = 1 - (1 - prob_a) * random.uniform(0.3, 0.7)
        prob_a = max(0.05, min(0.95, prob_a))
        return a if random.random() < prob_a else b
    
    for _ in range(n_sims):
        # R32
        r32_w = []
        for i in range(16):
            a, b = qualified_32[i], qualified_32[31 - i]
            w = sim_match(a, b)
            r32_w.append(w)
            stage_counts[w]["r32"] += 1
        
        # R16
        r16_w = []
        for i in range(0, 16, 2):
            w = sim_match(r32_w[i], r32_w[i+1])
            r16_w.append(w)
            stage_counts[w]["r16"] += 1
        
        # QF
        qf_w = []
        for i in range(0, 8, 2):
            w = sim_match(r16_w[i], r16_w[i+1])
            qf_w.append(w)
            stage_counts[w]["qf"] += 1
        
        # SF
        sf_w = []
        for i in range(0, 4, 2):
            w = sim_match(qf_w[i], qf_w[i+1])
            sf_w.append(w)
            stage_counts[w]["sf"] += 1
        
        # Final
        champion = sim_match(sf_w[0], sf_w[1])
        runner_up = sf_w[1] if champion == sf_w[0] else sf_w[0]
        stage_counts[champion]["final"] += 1
        stage_counts[runner_up]["final"] += 1
        stage_counts[champion]["winner"] += 1
    
    # Build bracket display data (using most likely outcomes)
    r32_matchups = []
    for i in range(16):
        a, b = qualified_32[i], qualified_32[31 - i]
        pa = get_elo(a)
        pb = get_elo(b)
        prob_a = pa / (pa + pb)
        r32_matchups.append({
            "home": a, "away": b,
            "home_elo": pa, "away_elo": pb,
            "home_prob": round(prob_a * 100, 1),
            "predicted_winner": a if prob_a > 0.5 else b,
        })
    
    # Build R16 matchups (based on R32 winners)
    r16_matchups = []
    for i in range(0, 16, 2):
        m1 = r32_matchups[i]
        m2 = r32_matchups[i+1]
        w1 = m1["predicted_winner"]
        w2 = m2["predicted_winner"]
        pa = get_elo(w1)
        pb = get_elo(w2)
        prob_a = pa / (pa + pb)
        r16_matchups.append({
            "home": w1, "away": w2,
            "home_prob": round(prob_a * 100, 1),
            "predicted_winner": w1 if prob_a > 0.5 else w2,
        })
    
    # Build QF matchups
    qf_matchups = []
    for i in range(0, 8, 2):
        w1 = r16_matchups[i]["predicted_winner"]
        w2 = r16_matchups[i+1]["predicted_winner"]
        pa = get_elo(w1)
        pb = get_elo(w2)
        prob_a = pa / (pa + pb)
        qf_matchups.append({
            "home": w1, "away": w2,
            "home_prob": round(prob_a * 100, 1),
            "predicted_winner": w1 if prob_a > 0.5 else w2,
        })
    
    # Build SF matchups
    sf_matchups = []
    for i in range(0, 4, 2):
        w1 = qf_matchups[i]["predicted_winner"]
        w2 = qf_matchups[i+1]["predicted_winner"]
        pa = get_elo(w1)
        pb = get_elo(w2)
        prob_a = pa / (pa + pb)
        sf_matchups.append({
            "home": w1, "away": w2,
            "home_prob": round(prob_a * 100, 1),
            "predicted_winner": w1 if prob_a > 0.5 else w2,
        })
    
    # Final
    final_home = sf_matchups[0]["predicted_winner"]
    final_away = sf_matchups[1]["predicted_winner"]
    pa = get_elo(final_home)
    pb = get_elo(final_away)
    prob_a = pa / (pa + pb)
    predicted_champion = final_home if prob_a > 0.5 else final_away
    
    # Build probability table
    prob_table = []
    for t in qualified_32:
        c = stage_counts[t]
        prob_table.append({
            "team": t,
            "r32": 100.0,  # All 32 teams play R32
            "r16": round(c["r16"] / n_sims * 100, 1),
            "qf": round(c["qf"] / n_sims * 100, 1),
            "sf": round(c["sf"] / n_sims * 100, 1),
            "final": round(c["final"] / n_sims * 100, 1),
            "winner": round(c["winner"] / n_sims * 100, 1),
        })
    prob_table.sort(key=lambda x: -x["winner"])
    
    return {
        "qualified_32": qualified_32,
        "r32_matchups": r32_matchups,
        "r16_matchups": r16_matchups,
        "qf_matchups": qf_matchups,
        "sf_matchups": sf_matchups,
        "final": {"home": final_home, "away": final_away, "home_prob": round(prob_a * 100, 1), "predicted_winner": predicted_champion},
        "prob_table": prob_table,
        "n_sims": n_sims,
    }


def generate_qualification_predictions(live_data):
    """Generate qualification probability for each team based on current standings."""
    predictions = []
    
    for gname, teams in live_data.get("groups", {}).items():
        group_teams = []
        for t in teams:
            team_data = TeamStrengthAnalyzer.get_team(t["team"])
            elo = team_data.get("elo", 1500) if team_data else 1500
            
            # Calculate qualification probability based on position and points
            pos = t["pos"]
            pts = t["pts"]
            gd = t["gd"]
            status = t.get("status", "")
            
            if status == "qualified":
                qual_prob = 100.0
            elif status == "eliminated":
                qual_prob = 0.0
            elif pos <= 2:
                # Position 1-2: high chance
                base_prob = 85 - (pos - 1) * 15
                pts_bonus = min(15, pts * 2)
                qual_prob = min(99, base_prob + pts_bonus)
            elif pos == 3:
                # Position 3: depends on points ranking among all 3rd places
                base_prob = 35
                pts_bonus = min(25, pts * 3)
                qual_prob = min(75, base_prob + pts_bonus)
            else:
                # Position 4: eliminated unless many teams still have 0 matches
                played = t.get("p", 0)
                if played == 0:
                    qual_prob = 15
                elif played <= 2:
                    qual_prob = 5
                else:
                    qual_prob = 0
            
            group_teams.append({
                "team": t["team"],
                "pos": pos,
                "pts": pts,
                "gd": gd,
                "gf": t.get("gf", 0),
                "ga": t.get("ga", 0),
                "p": t.get("p", 0),
                "w": t.get("w", 0),
                "d": t.get("d", 0),
                "l": t.get("l", 0),
                "elo": elo,
                "qual_prob": round(qual_prob, 1),
                "status": status,
            })
        
        # Sort by qualification probability
        group_teams.sort(key=lambda x: (-x["qual_prob"], -x["pts"], -x["gd"]))
        predictions.append({"group": gname, "teams": group_teams})
    
    return predictions


@app.route("/api/groups")
def api_groups():
    return jsonify({"groups": WC2026_QUAL_GROUPS, "groups_id": WC2026_QUAL_GROUPS_ID})


@app.route("/api/live-predictions")
def api_live_predictions():
    """Get live knockout predictions as JSON (cached)."""
    cache_file = CACHE_FILE
    
    # Check if cache exists and is fresh (< 30 min old)
    if os.path.exists(cache_file):
        cache_age = time.time() - os.path.getmtime(cache_file)
        if cache_age < 1800:  # 30 minutes
            with open(cache_file, "r") as f:
                return jsonify(json.load(f))
    
    # Generate new simulation
    live_data = load_live_data()
    if not live_data:
        live_data = generate_sample_data()
        save_live_data(live_data)
    
    knockout_sim = run_knockout_simulation(live_data)
    
    # Cache the result
    with open(cache_file, "w") as f:
        json.dump(knockout_sim, f, default=str)
    
    return jsonify(knockout_sim)


@app.route("/api/live")
def api_live():
    """Get live qualification standings from FIFA.com."""
    data = load_live_data()
    if not data:
        data = generate_sample_data()
        save_live_data(data)
    return jsonify(data)

@app.route("/api/live/refresh", methods=["POST"])
def api_live_refresh():
    """Force refresh live data."""
    data = generate_sample_data()
    save_live_data(data)
    return jsonify({"status": "ok", "data": data})

@app.route("/api/groups.js")
def api_groups_js():
    """Serve live groups data as JavaScript."""
    data = load_live_data()
    if not data:
        data = generate_sample_data()
        save_live_data(data)
    groups_data = {}
    for gname, teams in data.get("groups", {}).items():
        letters = {"Grup A":"A","Grup B":"B","Grup C":"C","Grup D":"D","Grup E":"E","Grup F":"F","Grup G":"G","Grup H":"H","Grup I":"I","Grup J":"J","Grup K":"K","Grup L":"L"}
        letter = letters.get(gname, gname.replace("Grup ",""))
        groups_data[letter] = teams
    js_content = "var G = " + json.dumps(groups_data, ensure_ascii=False) + ";"
    return js_content, 200, {"Content-Type": "application/javascript"}
    return jsonify({"status": "ok", "data": data})


@app.route("/api/schedule")
def api_schedule():
    """Get today's match predictions."""
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"date": datetime.now().strftime("%Y-%m-%d"), "predictions": []})


@app.route("/api/daily-update", methods=["POST"])
def api_daily_update():
    """Trigger daily update - generates new predictions based on latest standings."""
    data = generate_sample_data()
    save_live_data(data)
    return jsonify({
        "status": "ok",
        "message": "Daily update completed",
        "last_updated": data["last_updated"],
        "groups_count": len(data["groups"]),
        "qualified_count": sum(1 for g in data["groups"].values() for t in g if t.get("status") == "qualified")
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  ⚽ WORLD CUP 2026 PREDICTOR ⚽")
    print("  Data: FIFA.com live qualification standings")
    print("  http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
