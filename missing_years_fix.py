import sqlite3
import time
import random
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats
from requests.exceptions import HTTPError

DB_PATH = 'nba_players.db'
MAX_RETRIES = 5
INITIAL_DELAY = 1  # seconds
MAX_DELAY = 60

HISTORICAL_TEAM_ABBR = [
    'PHL', 'CIN', 'SEA', 'BUF', 'VAN', 'GOS', 'SYR', 'PIT', 'BOM', 'BAL',
    'SDR', 'NJN', 'CHH', 'NOJ', 'KCK', 'SAN', 'NOH', 'SFW', 'NOK', 'UTH',
    'SDC', 'STL', 'NYN', 'PHW', 'FTW', 'DEF', 'BLT', 'CHS', 'INO', 'DN',
    'CLR', 'MNL', 'TCB', 'PRO', 'MIH', 'CHP', 'CHZ', 'HUS', 'JET', 'AND',
    'WAT', 'SHE', 'ROC'
]

HISTORICAL_TEAM_FULL_NAMES = {
    # (You can fill this in or pull from your previous script)
}

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

def scrape_and_store():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tracking table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completed_players (
            player_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()

    # Load completed players
    cursor.execute("SELECT player_id FROM completed_players")
    completed_player_ids = set(row[0] for row in cursor.fetchall())

    all_players = players.get_players()
    nba_teams = teams.get_teams()

    historical_teams = []
    for abbr in HISTORICAL_TEAM_ABBR:
        full_name = HISTORICAL_TEAM_FULL_NAMES.get(abbr, abbr)
        historical_teams.append({'abbreviation': abbr, 'full_name': full_name})

    combined_teams = nba_teams + historical_teams
    team_lookup = {t['abbreviation']: t['full_name'] for t in combined_teams}

    print(f"Total players fetched: {len(all_players)}")
    print(f"Skipping {len(completed_player_ids)} already completed players")

    for idx, player in enumerate(all_players, start=1):
        player_name = player['full_name']
        player_id = player['id']

        if player_id in completed_player_ids:
            continue

        insert_player(cursor, player_id, player_name)
        conn.commit()

        # Retry logic for career stats
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                time.sleep(random.uniform(2, 5))
                career = playercareerstats.PlayerCareerStats(player_id=player_id)
                career_data = career.get_data_frames()[0]
                break
            except HTTPError as e:
                if e.response.status_code == 429:
                    delay = min(INITIAL_DELAY * 2 ** (attempt - 1), MAX_DELAY) + random.uniform(0, 2)
                    print(f"Rate limit hit for player {player_id} (Attempt {attempt}), sleeping {delay:.1f} sec")
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                delay = min(INITIAL_DELAY * 2 ** (attempt - 1), MAX_DELAY) + random.uniform(0, 1)
                print(f"Error fetching player {player_id} (Attempt {attempt}): {e}")
                time.sleep(delay)
        else:
            print(f"Failed to fetch data for player {player_id} after {MAX_RETRIES} attempts")
            continue

        played_historical_team = any(
            team in HISTORICAL_TEAM_ABBR for team in career_data['TEAM_ABBREVIATION'].dropna().unique()
        )
        if not played_historical_team:
            # Mark as completed even if no relevant teams
            cursor.execute("INSERT OR IGNORE INTO completed_players (player_id) VALUES (?)", (player_id,))
            conn.commit()
            continue

        print(f"[{idx}] Processing {player_name} (ID: {player_id}) who played for historical teams")

        for _, row in career_data.iterrows():
            season = row.get('SEASON_ID')
            team_abbr = row.get('TEAM_ABBREVIATION')
            if not team_abbr or not season:
                continue
            team_full_name = team_lookup.get(team_abbr)
            if not team_full_name:
                continue
            team_id = get_team_id(cursor, team_abbr, team_full_name)
            insert_player_team(cursor, player_id, team_id, season)

        conn.commit()

        # ✅ Mark this player as completed
        cursor.execute("INSERT OR IGNORE INTO completed_players (player_id) VALUES (?)", (player_id,))
        conn.commit()

        if idx % 50 == 0:
            print(f"Processed {idx} players. Sleeping 60s...")
            time.sleep(60)

    conn.close()
    print("✅ All applicable players processed.")

if __name__ == "__main__":
    scrape_and_store()
