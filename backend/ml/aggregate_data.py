import pandas as pd
import re
import glob

# ------------ Play Parsing ----------------
def parse_play(outcome):
    outcome = str(outcome).lower()
    
    # Yardage (positive or negative)
    match = re.match(r"(-?\d+)\s+yard\s+(\w+)", outcome)
    if match:
        yards = int(match.group(1))
        play_type = match.group(2)  
        return yards, play_type, 0
    
    # Touchdown
    if "touchdown" in outcome:
        return 0, "touchdown", 6
    
    # Field Goal
    if "field goal" in outcome and "good" in outcome:
        return 0, "field_goal", 3
    
    # Extra Point
    if "extra point" in outcome and "good" in outcome:
        return 0, "extra_point", 1
    
    # Safety
    if "safety" in outcome:
        return 0, "safety", 2
    
    # Incomplete pass
    if "incomplete" in outcome:
        return 0, "incomplete_pass", 0
    
    # Interception
    if "intercept" in outcome:
        return 0, "interception", 0
    
    # Fumble
    if "fumble" in outcome:
        return 0, "fumble", 0
    
    return 0, "other", 0


#load up the data
def load_data(play_files):
    df = pd.concat([pd.read_csv(f) for f in play_files], ignore_index=True)
    print(f"Loaded plays: {df.shape}")

    # Parse plays into structured columns
    df[["yards", "play_type", "points"]] = df["PlayOutcome"].apply(
        lambda x: pd.Series(parse_play(x))
    )
    return df

#try to aggregate the stats here 
def aggregate_team_stats(df):
    grouped = df.groupby(["Season", "Week", "HomeTeam", "AwayTeam", "TeamWithPossession"])

    stats = grouped.agg(
        total_plays=("PlayOutcome", "count"),
        pass_yards=("yards", lambda x: x[df.loc[x.index, "play_type"] == "pass"].sum()),
        rush_yards=("yards", lambda x: x[df.loc[x.index, "play_type"] == "run"].sum()),
        total_yards=("yards", "sum"),
        points=("points", "sum"),
        incompletions=("play_type", lambda x: (x == "incomplete_pass").sum()),
        interceptions=("play_type", lambda x: (x == "interception").sum()),
        fumbles=("play_type", lambda x: (x == "fumble").sum()),
        touchdowns=("play_type", lambda x: (x == "touchdown").sum()),
        safeties=("play_type", lambda x: (x == "safety").sum()),
        drives=("DriveNumber", "nunique"),
    ).reset_index()

    # Derived offensive stats
    stats["yards_per_play"] = stats["total_yards"] / stats["total_plays"]
    stats["points_per_possession"] = stats["points"] / stats["drives"].replace(0, 1)
    stats["avg_length_possession"] = stats["total_plays"] / stats["drives"].replace(0, 1)
    stats["turnovers"] = stats["interceptions"] + stats["fumbles"]
    stats["scoring_efficiency"] = stats["touchdowns"] / stats["drives"].replace(0, 1)

    return stats


#defensive stats here 
def add_defensive_stats(stats):
    stats["Opponent"] = stats.apply(
        lambda row: row["HomeTeam"] if row["TeamWithPossession"] == row["AwayTeam"] else row["AwayTeam"],
        axis=1
    )

    # Create a game identifier
    stats["game_id"] = (
        stats["Season"].astype(str) + "_" +
        stats["Week"].astype(str) + "_" +
        stats["HomeTeam"] + "_" +
        stats["AwayTeam"]
    )

    # Build a lookup of each game’s teams and points
    game_points = stats[["game_id", "TeamWithPossession", "points"]]

    # Merge opponents points from same game
    merged = stats.merge(
        game_points,
        left_on=["game_id", "Opponent"],
        right_on=["game_id", "TeamWithPossession"],
        how="left",
        suffixes=("", "_opp")
    )

    # Clean up
    merged = merged.drop(columns=["TeamWithPossession_opp"])
    merged = merged.rename(columns={"points_opp": "points_allowed"})

    # Fallback if something slips
    merged["points_allowed"] = merged["points_allowed"].fillna(merged["points"])

    # Add game total
    merged["game_total"] = merged["points"] + merged["points_allowed"]

    return merged


#recent form from the last 3 games
def add_recent_form(df, n=3):
    df = df.sort_values(by=["TeamWithPossession", "Season", "Week"])
    rolling_cols = [
        "pass_yards", "rush_yards", "total_yards",
        "yards_per_play", "points_per_possession",
        "turnovers", "scoring_efficiency",
        "points", "points_allowed"
    ]

    for col in rolling_cols:
        df[f"{col}_last{n}"] = df.groupby("TeamWithPossession")[col].transform(
            lambda x: x.rolling(n, min_periods=1).mean()
        )

    return df


#main method to do the work 
if __name__ == "__main__":
    # Grab all *_plays.csv files
    play_files = glob.glob("../data/*_plays.csv")
    print("Found play files:", play_files)

    # Load + parse plays
    df = load_data(play_files)

    # Aggregate stats
    team_stats = aggregate_team_stats(df)

    # Add defensive stats
    full_stats = add_defensive_stats(team_stats)

    # Add rolling last-3-game averages
    final_df = add_recent_form(full_stats, n=3)

    # Save clean dataset
    final_df.to_csv("../data/nfl_training.csv", index=False)
