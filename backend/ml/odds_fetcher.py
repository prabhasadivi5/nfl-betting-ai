import requests
import json
from datetime import datetime
from pathlib import Path

ODDS_API_KEY = "74b08f734ff323029cffe6cdacccb9cd"
ODDS_BASE_URL = "https://api.the-odds-api.com/v4"
ODDS_CACHE_FILE = Path("cache/nfl_odds.json")

ODDS_CACHE_FILE.parent.mkdir(exist_ok=True)

def fetch_nfl_odds():
    #fetch nfl odds
    
    url = f"{ODDS_BASE_URL}/sports/americanfootball_nfl/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
        
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        
        remaining = r.headers.get('x-requests-remaining', 'unknown')
        used = r.headers.get('x-requests-used', 'unknown')
        last_cost = r.headers.get('x-requests-last', 'unknown')
        
        print(f"📊 API Usage: {used} used, {remaining} remaining (last call cost: {last_cost})")
        
        odds_data = r.json()
        
        #timestamp
        cache = {
            "last_updated": datetime.now().isoformat(),
            "games": odds_data
        }
        
        # Save to cache
        with open(ODDS_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        
        print(f"✅ Saved odds for {len(odds_data)} games to {ODDS_CACHE_FILE}")
        return cache
        
    except requests.exceptions.RequestException as e:
        #error cases
        return None

def load_cached_odds():
    #cached odds if we need
    if ODDS_CACHE_FILE.exists():
        with open(ODDS_CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        last_updated = datetime.fromisoformat(cache["last_updated"])
        age_days = (datetime.now() - last_updated).days
        
        print(f"📂 Loaded cached odds (last updated {age_days} days ago)")
        return cache
    return None

def find_game_odds(home_team, away_team, cached_odds=None):
    """Find odds for a specific matchup."""
    if cached_odds is None:
        cached_odds = load_cached_odds()
    
    if not cached_odds:
        print("⚠️ No cached odds available")
        return None
    
    # Normalize team names for matching
    home_norm = home_team.lower().strip()
    away_norm = away_team.lower().strip()
    
    for game in cached_odds["games"]:
        game_home = game["home_team"].lower()
        game_away = game["away_team"].lower()
        
        if home_norm in game_home and away_norm in game_away:
            return game
    
    print(f"⚠️ No odds found for {away_team} @ {home_team}")
    return None

def extract_consensus_odds(game_data):
    """Extract consensus odds from multiple bookmakers."""
    if not game_data or not game_data.get("bookmakers"):
        return None
    
    spreads = []
    totals = []
    moneylines_home = []
    moneylines_away = []
    
    for book in game_data["bookmakers"]:
        for market in book["markets"]:
            if market["key"] == "spreads":
                for outcome in market["outcomes"]:
                    if outcome["name"] == game_data["home_team"]:
                        spreads.append(outcome.get("point", 0))
            
            elif market["key"] == "totals":
                for outcome in market["outcomes"]:
                    if outcome["name"] == "Over":
                        totals.append(outcome.get("point", 0))
            
            elif market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    if outcome["name"] == game_data["home_team"]:
                        moneylines_home.append(outcome.get("price", 0))
                    else:
                        moneylines_away.append(outcome.get("price", 0))
    
    # Calculate consensus (median)
    consensus = {
        "spread": round(sum(spreads) / len(spreads), 1) if spreads else None,
        "total": round(sum(totals) / len(totals), 1) if totals else None,
        "ml_home": int(sum(moneylines_home) / len(moneylines_home)) if moneylines_home else None,
        "ml_away": int(sum(moneylines_away) / len(moneylines_away)) if moneylines_away else None
    }
    
    return consensus

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch and cache NFL odds')
    parser.add_argument('--update', action='store_true', help='Fetch fresh odds from API')
    parser.add_argument('--home', type=str, help='Home team name to lookup')
    parser.add_argument('--away', type=str, help='Away team name to lookup')
    
    args = parser.parse_args()
    
    if args.update:
        fetch_nfl_odds()
    elif args.home and args.away:
        game = find_game_odds(args.home, args.away)
        if game:
            odds = extract_consensus_odds(game)
            print(f"\n📊 {args.away} @ {args.home}")
            print(f"   Spread: {odds['spread']}")
            print(f"   Total: {odds['total']}")
            print(f"   ML: {args.home} ({odds['ml_home']}) / {args.away} ({odds['ml_away']})")
    else:
        # Just show cache status
        cache = load_cached_odds()
        if cache:
            print(f"✓ {len(cache['games'])} games in cache")