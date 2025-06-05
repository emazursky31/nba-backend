import json

with open('player_team_history.json', 'r') as f:
    data = json.load(f)

print(f"Total players: {len(data)}")

for entry in data[:10]:
    player = entry.get('player_name', 'Unknown')
    teams = entry.get('teams', [])
    print(f"{player}:")
    if teams:
        for team in teams:
            print(f"  - {team}")
    else:
        print("  No teams found.")
