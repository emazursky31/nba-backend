import sqlite3
import time
import random
import logging
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats
from requests.exceptions import ReadTimeout, HTTPError


# Constants
DB_PATH = 'nba_players.db'
FAILED_LOG = 'failed_players.log'
MAX_RETRIES = 5
INITIAL_DELAY = 1
MAX_DELAY = 30
BATCH_SIZE = 200
SLEEP_BETWEEN_BATCHES = 3600  # 1 hour

# Logging setup
logging.basicConfig(filename=FAILED_LOG, level=logging.INFO)

# Historical team abbreviations
HISTORICAL_TEAM_ABBRS = {
    'PHL', 'CIN', 'SEA', 'BUF', 'VAN', 'GOS', 'SYR', 'PIT', 'BOM', 'BAL',
    'SDR', 'NJN', 'CHH', 'NOJ', 'KCK', 'SAN', 'NOH', 'SFW', 'NOK', 'UTH',
    'SDC', 'STL', 'NYN', 'PHW', 'FTW', 'DEF', 'BLT', 'CHS', 'INO', 'DN',
    'CLR', 'MNL', 'TCB', 'PRO', 'MIH', 'CHP', 'CHZ', 'HUS', 'JET', 'AND',
    'WAT', 'SHE', 'ROC'
}


def get_existing_player_ids(cursor):
    cursor.execute("SELECT player_id FROM players")
    return {row[0] for row in cursor.fetchall()}


def get_team_id(cursor, team_abbr, team_full_name):
    cursor.execute("SELECT team_id FROM teams WHERE team_abbr = ?", (team_abbr,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO teams (team_abbr, team_name) VALUES (?, ?)", (team_abbr, team_full_name))
    return cursor.lastrowid


def insert_player(cursor, player_id, player_name):
    cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO players (player_id, player_name) VALUES (?, ?)", (player_id, player_name))


def insert_player_team(cursor, player_id, team_id, season):
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO player_teams (player_id, team_id, season) VALUES (?, ?, ?)",
            (player_id, team_id, season)
        )
    except sqlite3.IntegrityError:
        pass


def scrape_batch(start_index, player_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    nba_teams = teams.get_teams()
    historical_teams = [{'abbreviation': abbr, 'full_name': abbr} for abbr in HISTORICAL_TEAM_ABBRS]
    team_lookup = {t['abbreviation']: t['full_name'] for t in nba_teams + historical_teams}

    end_index = min(start_index + BATCH_SIZE, len(player_list))
    print(f"📦 Processing batch: {start_index}–{end_index - 1}")

    for idx in range(start_index, end_index):
        player = player_list[idx]
        player_id = player['id']
        player_name = player['full_name']

        insert_player(cursor, player_id, player_name)
        conn.commit()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                time.sleep(2)
                career = playercareerstats.PlayerCareerStats(player_id=player_id)
                career_data = career.get_data_frames()[0]
                break
            except (HTTPError, ReadTimeout, Exception) as e:
                delay = min(INITIAL_DELAY * 2 ** (attempt - 1), MAX_DELAY) + random.uniform(0, 1)
                print(f"⚠️ Error fetching {player_name} (Attempt {attempt}): {e}")
                if attempt == MAX_RETRIES:
                    logging.info(f"{player_id},{player_name}")
                    print(f"❌ Failed after {MAX_RETRIES} attempts")
                    continue
                print(f"⏳ Retrying after {delay:.1f} seconds...")
                time.sleep(delay)
        else:
            continue

        # Only save if played for historical team
        unique_teams = set(career_data['TEAM_ABBREVIATION'].dropna().unique())
        if not unique_teams.intersection(HISTORICAL_TEAM_ABBRS):
            continue

        print(f"✅ {player_name} played for historical team")

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

    conn.close()
    print(f"✅ Batch complete: {start_index}–{end_index - 1}")


def scrape_all_auto():
    all_players = players.get_players()
    print(f"🔍 Total NBA players: {len(all_players)}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    scraped_ids = get_existing_player_ids(cursor)
    conn.close()

    unsaved_players = [p for p in all_players if p['id'] not in scraped_ids]

    print(f"⏭️ Resuming from index 0 of {len(unsaved_players)} unsaved players")

    for i in range(0, len(unsaved_players), BATCH_SIZE):
        scrape_batch(i, unsaved_players)

        if i + BATCH_SIZE < len(unsaved_players):
            print(f"⏳ Waiting {SLEEP_BETWEEN_BATCHES // 60} minutes before next batch...")
            time.sleep(SLEEP_BETWEEN_BATCHES)

    print("🏁 All remaining players processed.")


if __name__ == "__main__":
    scrape_all_auto()
