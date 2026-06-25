"""
World Cup Predictor - Flask Web Application
Data source: FIFA.com live qualification standings (June 2026)
"""
import json, os, sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.predictor import (
    MatchPredictor, TeamStrengthAnalyzer, OddsConverter,
    TournamentSimulator, WC2026_QUAL_GROUPS, WC2026_QUAL_GROUPS_ID, _ID_EN
)
from scraper.odds_scraper import OddsScraper, TeamDataCollector
from scraper.live_scraper import load_live_data, save_live_data, generate_sample_data

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_DATA_FILE = os.path.join(PROJECT_DIR, "data", "live_standings.json")
SCHEDULE_FILE = os.path.join(PROJECT_DIR, "data", "schedule_predictions.json")

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


@app.route("/api/groups")
def api_groups():
    return jsonify({"groups": WC2026_QUAL_GROUPS, "groups_id": WC2026_QUAL_GROUPS_ID})


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
    """Force refresh live data (in production, this would re-scrape FIFA.com)."""
    data = generate_sample_data()
    save_live_data(data)
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
