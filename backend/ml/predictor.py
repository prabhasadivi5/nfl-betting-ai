import requests
import pandas as pd
import os
from datetime import datetime

# ---------------- CONFIG ----------------
RAPID_API_KEY = "ee87724469mshfb9109f83959035p15c075jsn24eaed4d56cd"  
BASE_URL = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"

HEADERS = {
    "x-rapidapi-key": RAPID_API_KEY,
    "x-rapidapi-host": "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
}

SCHEDULE_FILE = "cached_schedule.csv"
TEAM_STATS_FILE = "team_stats.csv"


# ---------------- FETCH SEASON SCHEDULE ----------------
def fetch_schedule(season_year=None):
    """Fetch and cache full season schedule (using weekly endpoint)."""
    if season_year is None:
        season_year = datetime.now().year

    games = []
    for week in range(1, 19):  # NFL regular season weeks (1–18)
        url = f"{BASE_URL}/getNFLGamesForWeek?season={season_year}&week={week}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            continue
        data = r.json()
        for g in data.get("body", []):
            games.append({
                "gameID": g["gameID"],
                "season": season_year,
                "week": g["gameWeek"],
                "date": g["gameDate"],
                "homeTeam": g["home"],
                "awayTeam": g["away"]
            })

    if not games:
        raise ValueError(f"No schedule data found for {season_year}")

    df = pd.DataFrame(games)
    df.to_csv(SCHEDULE_FILE, index=False)
    print(f"✅ Cached schedule for {season_year}, {len(df)} games")
    return df


def load_schedule():
    if not os.path.exists(SCHEDULE_FILE):
        return fetch_schedule()
    return pd.read_csv(SCHEDULE_FILE)


# ---------------- FETCH GAME BOXSCORE ----------------
def fetch_game_boxscore(game_id):
    """Fetch detailed game info (boxscore) for a given game_id."""
    url = f"{BASE_URL}/getNFLBoxScore?gameID={game_id}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


# ---------------- GAME LOOKUP ----------------
def get_game_id(home, away, season=None):
    """Find gameID from cached schedule."""
    if season is None:
        season = datetime.now().year
    sched = load_schedule()
    row = sched[((sched["homeTeam"] == home) & (sched["awayTeam"] == away)) |
                ((sched["homeTeam"] == away) & (sched["awayTeam"] == home))]
    row = row[row["season"] == season]
    if row.empty:
        raise ValueError(f"No game found for {home} vs {away} in {season}")
    return row.iloc[0]["gameID"]


# ---------------- AGGREGATE TEAM STATS ----------------
def extract_season_year(game_data):
    """Safely extract season year from API response."""
    body = game_data.get("body", {})
    if "seasonYear" in body:
        return int(body["seasonYear"])
    # fallback: parse year from gameID
    gid = body.get("gameID", "")
    if gid and len(gid) >= 8:
        return int(gid[:4])
    return datetime.now().year


def aggregate_team_stats(game_data):
    """Extract offense + defense stats per team from boxscore."""
    stats = []
    team_stats = game_data.get("body", {}).get("teamStats", {})
    if not team_stats:
        return pd.DataFrame()

    season = extract_season_year(game_data)
    game_id = game_data["body"]["gameID"]
    game_week = int(game_data["body"].get("gameWeek", -1))

    for side in ["home", "away"]:
        team = team_stats[side]
        stats.append({
            "team": team["teamAbv"],
            "gameID": game_id,
            "season": season,
            "week": game_week,
            "points": int(team.get("pf", team.get("points", 0))),
            "totalYards": int(team.get("totalYards", 0)),
            "rushingYards": int(team.get("rushingYards", 0)),
            "passingYards": int(team.get("passingYards", 0)),
            "totalPlays": int(team.get("totalPlays", 1)),
            "turnovers": int(team.get("turnovers", 0)),
            "yardsPerPlay": float(team.get("yardsPerPlay", 0)),
            "rushTD": int(team.get("rushTD", 0)),
            "passTD": int(team.get("passTD", 0)),
            "defensiveInts": int(team.get("defensiveInterceptions", 0)),
            "sacks": int(team.get("sacksAndYardsLost", "0-0").split("-")[0]),
        })
    return pd.DataFrame(stats)


# ---------------- UPDATE TEAM STATS CACHE ----------------
def update_team_stats(game_id):
    """Fetch a single game and append to team stats cache."""
    game_data = fetch_game_boxscore(game_id)
    stats_df = aggregate_team_stats(game_data)

    if stats_df.empty:
        print(f"⚠️ No stats available for game {game_id}")
        return None

    if os.path.exists(TEAM_STATS_FILE):
        existing = pd.read_csv(TEAM_STATS_FILE)
        updated = pd.concat([existing, stats_df]).drop_duplicates(
            subset=["team", "gameID"], keep="last"
        )
    else:
        updated = stats_df

    updated.to_csv(TEAM_STATS_FILE, index=False)
    print(f"✅ Updated team stats with {game_id}")
    return stats_df


def update_all_completed_games(season=None):
    """Update stats for all games in a season that have been played."""
    if season is None:
        season = datetime.now().year
    sched = load_schedule()
    season_games = sched[sched["season"] == season]

    for _, row in season_games.iterrows():
        gid = row["gameID"]
        try:
            update_team_stats(gid)
        except Exception as e:
            print(f"⚠️ Skipped {gid}: {e}")


# ---------------- TEAM FEATURES (last3 + season with fallback) ----------------
def compute_team_features(team_abv, last_n=3):
    """Compute rolling last_n and season averages for a team.
       If fewer than n games this season, pull from previous season too.
    """
    if not os.path.exists(TEAM_STATS_FILE):
        raise ValueError("No team stats cache found. Run update_team_stats first.")

    df = pd.read_csv(TEAM_STATS_FILE)
    this_year = datetime.now().year

    # Current season games
    current_games = df[(df["team"] == team_abv) & (df["season"] == this_year)].sort_values(by=["week"])
    games_needed = last_n - len(current_games)

    # If not enough games this season → pad with last year's games
    if games_needed > 0:
        prev_games = df[(df["team"] == team_abv) & (df["season"] == this_year - 1)].sort_values(by=["week"])
        current_games = pd.concat([prev_games.tail(games_needed), current_games])

    if current_games.empty:
        raise ValueError(f"No games found for {team_abv}")

    # Last n
    last_n_avg = current_games.tail(last_n).mean(numeric_only=True).to_dict()

    # Season avg (current season only)
    season_avg = df[(df["team"] == team_abv) & (df["season"] == this_year)].mean(numeric_only=True).to_dict()

    return {
        "last_n": last_n_avg,
        "season": season_avg,
        "all_games": current_games
    }


# ---------------- EXAMPLE ----------------
if __name__ == "__main__":
    season = datetime.now().year

    # nightly update of schedule
    fetch_schedule(season)

    # update stats for all completed games
    update_all_completed_games(season)

    # Example: Washington vs ATL game
    try:
        gid = get_game_id("WSH", "ATL", season)
        update_team_stats(gid)
    except Exception as e:
        print("⚠️", e)

    # Features for Washington
    try:
        features = compute_team_features("WSH", last_n=3)
        print("\nWashington last 3 games avg:", features["last_n"])
        print("\nWashington season avg:", features["season"])
    except Exception as e:
        print("⚠️", e)
