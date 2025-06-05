import sqlite3
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster

# Connect to SQLite DB
conn = sqlite3.connect('nba.db')
cursor = conn.cursor()

# Create tables if not exist
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    team TEXT
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS teammates (
                    player_id INTEGER,
                    teammate_id INTEGER,
                    PRIMARY KEY (player_id, teammate_id),
                    FOREIGN KEY(player_id) REFERENCES players(id),
                    FOREIGN KEY(teammate_id) REFERENCES players(id)
                )''')

# Fetch all NBA teams
all_teams = teams.get_teams()

for team in all_teams:
    team_id = team['id']
    team_name = team['full_name']
    print(f"Scraping roster for {team_name}...")

    # Get team roster for 2023-24 season
    roster = commonteamroster.CommonTeamRoster(team_id=team_id, season='2023-24')
    players_df = roster.get_data_frames()[0]

    players = players_df['PLAYER'].tolist()
    print(f"Found {len(players)} players for {team_name}")

    # Insert players into DB
    for player in players:
        cursor.execute("INSERT OR IGNORE INTO players (name, team) VALUES (?, ?)", (player, team_name))
    conn.commit()
    print(f"Inserted players for {team_name}")

    # Get player IDs from DB for this team
    cursor.execute("SELECT id, name FROM players WHERE team=?", (team_name,))
    player_rows = cursor.fetchall()
    name_to_id = {name: pid for pid, name in player_rows}

    # Insert teammate relationships (bidirectional)
    for pid, pname in player_rows:
        for teammate in players:
            if teammate != pname:
                teammate_id = name_to_id.get(teammate)
                if teammate_id:
                    cursor.execute("INSERT OR IGNORE INTO teammates (player_id, teammate_id) VALUES (?, ?)", (pid, teammate_id))
                    cursor.execute("INSERT OR IGNORE INTO teammates (player_id, teammate_id) VALUES (?, ?)", (teammate_id, pid))
    conn.commit()
    print(f"Inserted teammate relationships for {team_name}\n")

print("✅ Done scraping and storing NBA player data.")
conn.close()
