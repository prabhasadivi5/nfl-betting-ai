import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

df = pd.read_csv("../data/nfl_training.csv")

# Features to use (no IDs, no labels, no text)
feature_cols = [
    "pass_yards_last3", "rush_yards_last3", "total_yards_last3",
    "yards_per_play_last3", "points_per_possession_last3",
    "turnovers_last3", "scoring_efficiency_last3"
]

X = df[feature_cols]
y_points = df["points"]       
y_allowed = df["points_allowed"]  

X_train, X_test, y_train, y_test = train_test_split(X, y_points, test_size=0.2, random_state=42)

model = LinearRegression()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("MAE:", mean_absolute_error(y_test, y_pred))
print("R²:", r2_score(y_test, y_pred))

joblib.dump(model, "points_model.pkl")
print("✅ Saved model to points_model.pkl")