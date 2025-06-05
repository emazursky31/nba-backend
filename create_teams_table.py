import sqlite3

conn = sqlite3.connect('nba_players.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_abbr TEXT UNIQUE NOT NULL,
    team_name TEXT NOT NULL
)
''')

conn.commit()
conn.close()

print("Teams table created successfully.")
