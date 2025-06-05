import sqlite3

# Connect (or create) the database
conn = sqlite3.connect('nba_players.db')
c = conn.cursor()

# Create table
c.execute('''
CREATE TABLE IF NOT EXISTS players_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbr TEXT NOT NULL,
    season TEXT NOT NULL
)
''')

# Minimal seed data - example players and teams/seasons
seed_data = [
    ('LeBron James', 'CLE', '2003-04'),
    ('LeBron James', 'CLE', '2004-05'),
    ('Kevin Durant', 'OKC', '2007-08'),
    ('Kevin Durant', 'OKC', '2008-09'),
    ('Stephen Curry', 'GSW', '2009-10'),
    ('Stephen Curry', 'GSW', '2010-11')
]

# Insert seed data
c.executemany('INSERT INTO players_teams (player_name, team_abbr, season) VALUES (?, ?, ?)', seed_data)

conn.commit()
conn.close()

print("Database created and seeded with minimal data.")
