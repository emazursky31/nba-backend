import sqlite3
import time
import random
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats

DB_PATH = 'nba_players.db'
MAX_RETRIES = 5
INITIAL_DELAY = 1  # seconds
MAX_DELAY = 30

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
        pass

def get_existing_player_ids(cursor):
    cursor.execute("SELECT player_id FROM players")
    return {row[0] for row in cursor.fetchall()}

def scrape_and_store():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    all_players = players.get_players()
    existing_ids = get_existing_player_ids(cursor)

    nba_teams = teams.get_teams()  # cache this list for efficiency
    team_lookup = {t['abbreviation']: t['full_name'] for t in nba_teams}

    for idx, player in enumerate(all_players, start=1):
        player_name = player['full_name']
        player_id = player['id']

        insert_player(cursor, player_id, player_name)  # Ensures player exists in table


        print(f"[{idx}] Fetching: {player_name} (ID: {player_id})")

        insert_player(cursor, player_id, player_name)
        conn.commit()

        # Retry with exponential backoff
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                time.sleep(2)  # Delay before request (be kind to API)
                career = playercareerstats.PlayerCareerStats(player_id=player_id)
                career_data = career.get_data_frames()[0]
                break  # success
            except Exception as e:
                delay = min(INITIAL_DELAY * 2 ** (attempt - 1), MAX_DELAY)
                delay += random.uniform(0, 1)  # jitter
                print(f"Rate limit or network error on player {player_id} (Attempt {attempt}): {e}")
                if attempt == MAX_RETRIES:
                    print(f"Failed to fetch data for player {player_id} after {MAX_RETRIES} attempts")
                else:
                    print(f"Sleeping for {delay:.1f} seconds before retrying...")
                    time.sleep(delay)
        else:
            continue  # skip to next player after all retries

        for _, row in career_data.iterrows():
            team_abbr = row.get('TEAM_ABBREVIATION')
            season = row.get('SEASON_ID')
            if not team_abbr or not season:
                continue

            team_full_name = team_lookup.get(team_abbr)
            if not team_full_name:
                continue

            team_id = get_team_id(cursor, team_abbr, team_full_name)
            insert_player_team(cursor, player_id, team_id, season)

        conn.commit()

        if idx % 100 == 0:
            print(f"Checkpoint: Processed {idx} players so far...")

    conn.close()
    print("✅ Done scraping all players.")

if __name__ == "__main__":
    scrape_and_store()
