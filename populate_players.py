from nba_api.stats.static import players
from nba_api.stats.endpoints import PlayerCareerStats
import time
from collections import defaultdict

# Step 1: Define your player list
target_players = ['LeBron James', 'Kevin Durant', 'Stephen Curry']

# Step 2: Get all players from nba_api
all_players = players.get_players()

# Step 3: Map names to player IDs
player_id_map = {p['full_name']: p['id'] for p in all_players if p['full_name'] in target_players}

# Step 4: Fetch team + season data
player_team_data = defaultdict(lambda: defaultdict(list))

for name in target_players:
    player_id = player_id_map.get(name)
    if not player_id:
        print(f"Player ID not found for {name}")
        continue

    try:
        stats = PlayerCareerStats(player_id=player_id)
        time.sleep(0.6)  # Avoid rate limits
        df = stats.get_data_frames()[0]

        for _, row in df.iterrows():
            season = row['SEASON_ID']
            team = row['TEAM_ABBREVIATION']
            player_team_data[name][team].append(season)

    except Exception as e:
        print(f"Error fetching stats for {name}: {e}")
