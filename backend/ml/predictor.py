import requests
import joblib
import pandas as pd

# Load trained models
models = {
    "points_teamA": joblib.load("points_teamA_xgb_model.pkl"),
    "points_teamB": joblib.load("points_teamB_xgb_model.pkl"),
    "game_total": joblib.load("game_total_xgb_model.pkl"),
}

def get_current_matchups(week, year=2024, seasonType=2):
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&year={year}&seasonType={seasonType}"
    data = requests.get(url).json()

    games = []
    for event in data["events"]:
        comp = event["competitions"][0]["competitors"]
        home = comp[0]["team"]["displayName"]
        away = comp[1]["team"]["displayName"]
        games.append((home, away))
    return games

if __name__ == "__main__":
    week = 1
    year = 2024
    matchups = get_current_matchups(week, year)

    print(f"Week {week} {year} NFL Matchups:")
    for home, away in matchups:
        print(f"{away} @ {home}")
