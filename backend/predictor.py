import pandas as pd
import joblib
import json
import os
from pathlib import Path
from datetime import datetime

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- CONFIG ----------------
TRAINING_DATA = os.path.join(BASE_DIR, "data/nfl_training.csv")
ODDS_CACHE = Path(os.path.join(BASE_DIR, "cache/nfl_odds.json"))

def load_models():
    #load the models for the 3
    models = {
        "points_teamA": joblib.load(os.path.join(BASE_DIR, "ml/points_teamA_xgb_model.pkl")),
        "points_teamB": joblib.load(os.path.join(BASE_DIR, "ml/points_teamB_xgb_model.pkl")),
        "game_total": joblib.load(os.path.join(BASE_DIR, "ml/game_total_xgb_model.pkl"))
    }
    return models

def normalize_team_name(team_name):
    """Map team abbreviations and names to searchable strings for odds matching"""
    normalized = team_name.lower().strip()
    
    # Comprehensive mapping of abbreviations to searchable strings
    team_map = {
        # AFC East
        "buf": "buffalo",
        "mia": "miami",
        "ne": "new england",
        "nep": "new england",
        "nyj": "jets",
        
        # AFC North
        "bal": "baltimore",
        "cin": "cincinnati",
        "cle": "cleveland",
        "pit": "pittsburgh",
        
        # AFC South
        "hou": "houston",
        "ind": "indianapolis",
        "jax": "jacksonville",
        "ten": "tennessee",
        
        # AFC West
        "den": "denver",
        "kc": "kansas city",
        "lv": "las vegas",
        "lac": "chargers",
        
        # NFC East
        "dal": "dallas",
        "nyg": "giants",
        "phi": "philadelphia",
        "wsh": "washington",
        "was": "washington",
        
        # NFC North
        "chi": "chicago",
        "det": "detroit",
        "gb": "green bay",
        "min": "minnesota",
        
        # NFC South
        "atl": "atlanta",
        "car": "carolina",
        "no": "new orleans",
        "tb": "tampa bay",
        
        # NFC West
        "ari": "arizona",
        "lar": "rams",
        "sf": "san francisco",
        "sea": "seattle",
    }
    
    return team_map.get(normalized, normalized)

def get_team_stats(df, team_abv):
    #calling data
    team_data = df[df["TeamWithPossession"] == team_abv].sort_values(
        ["Season", "Week"], ascending=False
    )
    
    if len(team_data) == 0:
        raise ValueError(f"No data found for team: {team_abv}")
    
    latest = team_data.iloc[0]
    return latest

def build_prediction_features(teamA_stats, teamB_stats, feature_cols):
    #im building the prediction here
    features = {}
    for col in teamA_stats.index:
        if col.endswith("_season_avg") or col.endswith("_last3"):
            features[f"off_{col}_A"] = teamA_stats[col]
    
    # Team B defensive stats (use their points_allowed stats as defense)
    for col in teamB_stats.index:
        if col.endswith("_season_avg") or col.endswith("_last3"):
            features[f"def_{col}_B"] = teamB_stats[col]
    
    # Create DataFrame with correct column order
    feature_df = pd.DataFrame([features])
    
    # Ensure all expected columns exist
    for col in feature_cols:
        if col not in feature_df.columns:
            feature_df[col] = 0
    
    return feature_df[feature_cols]

def load_odds_cache():
    """Load cached odds."""
    if ODDS_CACHE.exists():
        with open(ODDS_CACHE, 'r') as f:
            return json.load(f)
    return None

def find_game_odds(teamA, teamB, odds_cache):
    """Find game odds using normalized team names"""
    if not odds_cache:
        return None
    
    # Normalize team names to searchable strings
    teamA_search = normalize_team_name(teamA)
    teamB_search = normalize_team_name(teamB)
    
    for game in odds_cache.get("games", []):
        home = game["home_team"].lower()
        away = game["away_team"].lower()
        
        # Check both home/away combinations
        if (teamA_search in home and teamB_search in away) or (teamA_search in away and teamB_search in home):
            # Extract consensus odds
            spreads = []
            totals = []
            
            for book in game.get("bookmakers", []):
                for market in book.get("markets", []):
                    if market["key"] == "spreads":
                        for outcome in market["outcomes"]:
                            if game["home_team"] in outcome["name"]:
                                spreads.append(outcome.get("point", 0))
                    elif market["key"] == "totals":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == "Over":
                                totals.append(outcome.get("point", 0))
            
            return {
                "spread": round(sum(spreads) / len(spreads), 1) if spreads else None,
                "total": round(sum(totals) / len(totals), 1) if totals else None,
                "home_team": game["home_team"],
                "away_team": game["away_team"]
            }
    
    return None

def predict_game(teamA_name, teamB_name, verbose=True):    
    # Load data and models
    df = pd.read_csv(TRAINING_DATA)
    models = load_models()
    
    # Keep original names for model (they expect abbreviations like WSH, LAC)
    teamA = teamA_name.upper()
    teamB = teamB_name.upper()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"NFL GAME PREDICTION: {teamA} vs {teamB}")
        print(f"{'='*60}\n")
    
    # Get team stats
    try:
        teamA_stats = get_team_stats(df, teamA)
        teamB_stats = get_team_stats(df, teamB)
    except ValueError as e:
        print(f"Error: {e}")
        return None
    
    # Get feature columns from a sample matchup
    sample_game = df[df["game_id"].notna()].iloc[0]
    feature_cols = [c for c in df.columns if c.endswith("_season_avg") or c.endswith("_last3")]
    feature_cols = [f"off_{c}_A" for c in feature_cols] + [f"def_{c}_B" for c in feature_cols]
    
    # Build features
    X = build_prediction_features(teamA_stats, teamB_stats, feature_cols)
    
    # Make predictions
    pred_teamA = models["points_teamA"].predict(X)[0]
    pred_teamB = models["points_teamB"].predict(X)[0]
    pred_total = models["game_total"].predict(X)[0]
    
    # Load odds - use original input names for matching
    odds_cache = load_odds_cache()
    odds = find_game_odds(teamA_name, teamB_name, odds_cache) if odds_cache else None
    
    # Display results
    if verbose:
        print(f"PREDICTED SCORE")
        print(f"   {teamA}: {pred_teamA:.1f}")
        print(f"   {teamB}: {pred_teamB:.1f}")
        print(f"   Total: {pred_total:.1f}")
        
        if odds:
            print(f"\nVEGAS LINES")
            print(f"   Spread: {odds['spread']} ({odds['home_team']})")
            print(f"   Total: {odds['total']}")
            
            # Determine which team is home
            is_teamA_home = normalize_team_name(teamA) in odds['home_team'].lower()
            home_team_name = teamA if is_teamA_home else teamB
            away_team_name = teamB if is_teamA_home else teamA
            
            # Calculate predicted margin (positive = teamA wins, negative = teamB wins)
            pred_margin_teamA = pred_teamA - pred_teamB
            
            # Convert Vegas spread to teamA perspective
            vegas_spread = odds['spread']
            
            if is_teamA_home:
                vegas_margin_teamA = vegas_spread
            else:
                vegas_margin_teamA = -vegas_spread
            
            spread_edge = pred_margin_teamA - vegas_margin_teamA
            
            print(f"\nBETTING ANALYSIS - SPREAD")
            print(f"   Model: {teamA} {pred_margin_teamA:+.1f}")
            print(f"   Vegas: {home_team_name} {vegas_spread:+.1f}")
            print(f"   Difference: {abs(spread_edge):.1f} points")
            
            if abs(spread_edge) >= 3:
                if spread_edge > 0:
                    print(f"   VALUE: Model likes {teamA} (model is {spread_edge:.1f} pts better on {teamA})")
                else:
                    print(f"   VALUE: Model likes {teamB} (model is {abs(spread_edge):.1f} pts better on {teamB})")
            else:
                print(f"   No significant edge (< 3 points)")
            
            # Total analysis
            total_edge = pred_total - odds['total']
            print(f"\nBETTING ANALYSIS - TOTAL")
            print(f"   Model total: {pred_total:.1f}")
            print(f"   Vegas total: {odds['total']}")
            print(f"   Difference: {abs(total_edge):.1f} points")
            
            if abs(total_edge) >= 3:
                if total_edge > 0:
                    print(f"   VALUE: Model likes OVER {odds['total']} (edge: {total_edge:.1f} pts)")
                else:
                    print(f"   VALUE: Model likes UNDER {odds['total']} (edge: {abs(total_edge):.1f} pts)")
            else:
                print(f"   No significant edge (< 3 points)")
        else:
            print(f"\nNo odds data available")
            print(f"   Run 'python3 odds_fetcher.py --update' to fetch odds")
        
        print(f"\n{'='*60}\n")
    
    return {
    "teamA": teamA,
    "teamB": teamB,
    "pred_teamA": float(pred_teamA),  # Convert np.float32 to Python float
    "pred_teamB": float(pred_teamB),  # Convert np.float32 to Python float
    "pred_total": float(pred_total),  # Convert np.float32 to Python float
    "odds": odds
}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Predict NFL game scores')
    parser.add_argument('teamA', type=str, help='First team name or abbreviation')
    parser.add_argument('teamB', type=str, help='Second team name or abbreviation')
    args = parser.parse_args()
    
    predict_game(args.teamA, args.teamB)