import sqlite3
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats
import time

DB_PATH = 'nba_players.db'

def get_team_id(cursor, team_abbr, team_full_name):
    cursor.execute("SELECT team_id FROM teams WHERE team_abbr = ?", (team_abbr,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute(
            "INSERT INTO teams (team_abbr, team_name) VALUES (?, ?)",
            (team_abbr, team_full_name)
        )
        return cursor.lastrowid

def insert_player(cursor, player_id, player_name):
    cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO players (player_id, player_name) VALUES (?, ?)",
            (player_id, player_name)
        )

def insert_player_team(cursor, player_id, team_id, season):
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO player_teams (player_id, team_id, season) VALUES (?, ?, ?)",
            (player_id, team_id, season)
        )
    except sqlite3.IntegrityError:
        pass  # Ignore duplicates or FK errors

def scrape_and_store(players_to_scrape):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for player_name, player_id in players_to_scrape:
        print(f"Fetching career stats for {player_name} (ID: {player_id})")

        # Insert player record if needed
        insert_player(cursor, player_id, player_name)
        conn.commit()

        # Fetch career stats from nba_api
        try:
            career = playercareerstats.PlayerCareerStats(player_id=player_id)
            time.sleep(0.6)  # be kind to the API
            career_data = career.get_data_frames()[0]

            for _, row in career_data.iterrows():
                team_abbr = row.get('TEAM_ABBREVIATION')
                season = row.get('SEASON_ID')  # e.g. '2020-21'
                if not team_abbr or not season:
                    continue

                # Fetch full team name from nba_api teams list
                nba_teams = teams.get_teams()
                team_info = next((t for t in nba_teams if t['abbreviation'] == team_abbr), None)
                if team_info is None:
                    continue
                team_full_name = team_info['full_name']

                # Insert team if needed and get team_id
                team_id = get_team_id(cursor, team_abbr, team_full_name)

                # Insert player-team-season link
                insert_player_team(cursor, player_id, team_id, season)
                print(f"Inserting: {player_name}, {team_abbr}, {season}")

            conn.commit()
        except Exception as e:
            print(f"Error fetching data for {player_name}: {e}")

    conn.close()


if __name__ == "__main__":
    # Example players to scrape (name, id)
    players_to_scrape = [
        ('Precious Achiuwa', 1630173),
        ('Steven Adams', 203500),
        ('Bam Adebayo', 1628389),
        ('Ochai Agbaji', 1630534),
        ('Santi Aldama', 1630583)
    ]

    scrape_and_store(players_to_scrape)
