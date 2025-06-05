import sqlite3

conn = sqlite3.connect('nba_players.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_team_stints (
    player_id INTEGER NOT NULL,
    team_abbr TEXT NOT NULL,
    start_season TEXT NOT NULL,
    end_season TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    PRIMARY KEY (player_id, team_abbr)
''')

conn.commit()
conn.close()
print("Table created")
