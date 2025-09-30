import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
import joblib

#data loading
df = pd.read_csv("../data/nfl_training.csv")

#matchup building
def build_matchup_data(df):
    games = []
    for gid, g in df.groupby("game_id"):
        if len(g) != 2:
            continue
        teamA, teamB = g.iloc[0], g.iloc[1]

        row = {
            "game_id": gid,
            "teamA": teamA["TeamWithPossession"],
            "teamB": teamB["TeamWithPossession"],
            # offensive (season + last3)
            **{f"off_{col}_A": teamA[col] for col in df.columns if col.endswith("_season_avg") or col.endswith("_last3")},
            # defensive (season + last3)
            **{f"def_{col}_B": teamB[col] for col in df.columns if col.endswith("_season_avg") or col.endswith("_last3")},
            # targets
            "points_teamA": teamA["points"],
            "points_teamB": teamB["points"],
            "game_total": teamA["game_total"]
        }
        games.append(row)
    return pd.DataFrame(games)

games = build_matchup_data(df)

print("Matchup data shape:", games.shape)
print(games.head(3))

#features + targets
feature_cols = [c for c in games.columns if c.startswith("off_") or c.startswith("def_")]
X = games[feature_cols]
y = games[["points_teamA", "points_teamB", "game_total"]]

#taking train and test data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

#creating the model 
base_model = XGBRegressor(
    n_estimators=800,
    learning_rate=0.03,
    max_depth=6,
    subsample=0.9,
    colsample_bytree=0.9,
    reg_alpha=1,
    reg_lambda=2,
    random_state=42,
    n_jobs=-1,
    eval_metric="mae",              
    early_stopping_rounds=50         
)

# Train separately for each target
results = {}
for target in y.columns:
    model = base_model
    model.fit(
        X_train, y_train[target],
        eval_set=[(X_test, y_test[target])],
        verbose=False
    )
    
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test[target], y_pred)
    r2 = r2_score(y_test[target], y_pred)
    results[target] = (mae, r2)
    print(f"{target}: MAE={mae:.3f}, R²={r2:.3f}")
    joblib.dump(model, f"{target}_xgb_model.pkl")
