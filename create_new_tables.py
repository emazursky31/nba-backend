import sqlite3

conn = sqlite3.connect('nba_players.db')
cursor = conn.cursor()

# Create teams table
cursor.execute('''
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_abbr TEXT UNIQUE NOT NULL,
    team_name TEXT NOT NULL
)
''')

# Create players table
cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL
)
''')

# Create player_teams join table
cursor.execute('''
CREATE TABLE IF NOT EXISTS player_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season TEXT NOT NULL,
    UNIQUE(player_id, team_id, season),
    FOREIGN KEY(player_id) REFERENCES players(player_id),
    FOREIGN KEY(team_id) REFERENCES teams(team_id)
)
''')

conn.commit()
conn.close()
print("Tables created")
