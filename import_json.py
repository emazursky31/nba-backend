import json
import time
from collections import defaultdict
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats

# Step 1: Get all players
all_players = players.get_players()
print(f"Total players found: {len(all_players)}")

# Step 2: Prepare the output data
player_team_history = []

for player in all_players:
    player_id = player['id']
    full_name = player['full_name']
    try:
        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        time.sleep(0.6)  # To avoid hitting rate limits
        df = career.get_data_frames()[0]

        team_years = defaultdict(list)
        for _, row in df.iterrows():
            team_name = row.get('TEAM_NAME')
            season = row.get('SEASON_ID')
            if team_name and season:
                start_year = int(season.split('-')[0])
                team_years[team_name].append(start_year)

        # Convert to list of dicts
        teams = [
            {"team_name": team, "years": sorted(set(years))}
            for team, years in team_years.items()
        ]

        player_team_history.append({
            "player_name": full_name,
            "teams": teams
        })

        print(f"Processed: {full_name}")

    except Exception as e:
        print(f"Error processing {full_name}: {e}")

# Step 3: Write to JSON
with open('player_team_history.json', 'w') as f:
    json.dump(player_team_history, f, indent=2)

print("All player data written to player_team_history.json")
