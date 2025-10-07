# NFL Betting AI

AI-powered NFL betting assistant that predicts game scores using machine learning and compares predictions against Vegas odds to identify betting value.

## AWS Hosting Preparation

Preparing for AWS deployment with EC2 for hosting, automated cron jobs for daily data updates and weekly odds fetching, and S3 for model/data backups. Currently building and testing the ML pipeline locally.

**Note**: AI API expired. New API integration coming soon. Both the Hosting and updated AI API are expected by Mid October



---

## 📁 Project Structure

```
backend/ml/
├── nfl_tank_aggregator.py    # Daily game data collection
├── odds_fetcher.py             # Weekly Vegas odds fetching
├── score_predictor.py          # Score prediction engine
├── training_script.py          # Model training
├── nfl_training.csv            # Generated training data
├── cache/
│   ├── games_cache.json        # Processed games tracker
│   └── nfl_odds.json           # Cached odds
└── *.pkl                       # Trained models
```

---

## 📄 Core Files

### **`nfl_tank_aggregator.py`**
Fetches completed games from Tank01 API, parses play-by-play data, generates game-by-game stats with rolling 3-game averages (`_last3`) and season averages (`_season_avg`). Outputs `nfl_training.csv` with 2 rows per game.

**Usage**:
```bash
python nfl_tank_aggregator.py         # Daily update
python nfl_tank_aggregator.py --force # Rebuild all
```

### **`odds_fetcher.py`**
Fetches spreads, totals, and moneylines from The Odds API. Calculates consensus odds across bookmakers. Saves to `cache/nfl_odds.json`.

**Status**: Old API subscription expired. New API integration coming soon.

**Usage**:
```bash
python odds_fetcher.py --update                    # Fetch odds (3 API calls)
python odds_fetcher.py --home "Cowboys" --away "Eagles"  # Lookup game
```

### **`score_predictor.py`**
Predicts game scores using trained XGBoost models, compares to Vegas odds, identifies betting value (3+ point edge).

**Usage**:
```bash
python score_predictor.py "Commanders" "Cowboys"
python score_predictor.py WSH DAL
```

### **`training_script.py`**
Trains XGBoost models on `nfl_training.csv`. Outputs three models: `points_teamA_xgb_model.pkl`, `points_teamB_xgb_model.pkl`, `game_total_xgb_model.pkl`.

---

## 🔧 Setup

```bash
# Install dependencies
pip install requests pandas xgboost joblib scikit-learn

# Add API keys to scripts
# - Tank01 NFL API (RapidAPI): nfl_tank_aggregator.py
# - The Odds API: odds_fetcher.py

# Initial setup
python nfl_tank_aggregator.py --force  # Fetch game data
python training_script.py              # Train models
python odds_fetcher.py --update        # Fetch odds
python score_predictor.py WSH DAL      # Test prediction
```

---

## 🤖 Automation (Cron)

```bash
# Daily: Update game data at 3 AM
0 3 * * * cd /path/to/project && python nfl_tank_aggregator.py

# Weekly: Update odds on Sundays at 2 AM
0 2 * * 0 cd /path/to/project && python odds_fetcher.py --update
```

---

## 📊 Data Flow

```
Tank01 API → nfl_tank_aggregator.py → nfl_training.csv → training_script.py → *.pkl models
                                                              ↓
The Odds API → odds_fetcher.py → cache/nfl_odds.json → score_predictor.py → Predictions
```

---

## 🐛 Troubleshooting

**"No data found for team"**: Add team to `TEAM_MAPPINGS` in `score_predictor.py`

**"No odds data available"**: Run `python odds_fetcher.py --update`

**Model not found**: Run `python training_script.py` first

