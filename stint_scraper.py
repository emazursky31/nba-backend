import sqlite3
import time
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.library.parameters import SeasonAll
from requests.exceptions import RequestException
import pandas as pd

DB_PATH = "nba_players.db"
MAX_RETRIES = 5

def get_existing_player_ids():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT player_id FROM player_team_stints")
    rows = cur.fetchall()
    conn.close()
    return set(row[0] for row in rows)

def get_all_players():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT player_id, player_name FROM players")
    rows = cur.fetchall()
    conn.close()
    return rows

def safe_fetch_gamelog(player_id):
    retries = 0
    wait_time = 5
    while retries < MAX_RETRIES:
        try:
            print(f"Fetching game log for player {player_id} (attempt {retries+1})...")
            log = playergamelog.PlayerGameLog(player_id=player_id, season=SeasonAll.all)
            df = log.get_data_frames()[0]
            return df
        except (RequestException, ValueError) as e:
            print(f"Rate limit or network error for player {player_id}: {e}")
            print(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            retries += 1
            wait_time *= 2
    print(f"❌ Failed to fetch game log for player {player_id} after {MAX_RETRIES} retries.")
    return None


def insert_stints_into_db(player_id, team_stints):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for i, stint in enumerate(team_stints):
        cur.execute("""
            INSERT OR IGNORE INTO player_team_stints 
            (player_id, team_abbr, stint_number, start_season, end_season, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            stint["team_abbr"],
            i + 1,
            stint["start_season"],
            stint["end_season"],
            stint["start_date"],
            stint["end_date"]
        ))
    conn.commit()
    conn.close()

def process_player(player_id):
    df = safe_fetch_gamelog(player_id)
    if df is None or df.empty:
        return

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], format='mixed')
    df.sort_values("GAME_DATE", inplace=True)

    df["TEAM_ABBR"] = df["MATCHUP"].apply(lambda m: m.split(" ")[0] if "vs." in m or "@" in m else None)

    team_stints = []
    last_team = None
    prev_game_date = None
    prev_season = None

    for idx, row in df.iterrows():
        team = row["TEAM_ABBR"]
        game_date = row["GAME_DATE"]
        season_id = str(row["SEASON_ID"])[-4:]

        if team != last_team:
            if last_team is not None and team_stints:
                team_stints[-1]["end_date"] = prev_game_date.strftime("%Y-%m-%d")
                team_stints[-1]["end_season"] = prev_season
            team_stints.append({
                "team_abbr": team,
                "start_date": game_date.strftime("%Y-%m-%d"),
                "start_season": season_id,
                "end_date": None,
                "end_season": None
            })
            last_team = team
        prev_game_date = game_date
        prev_season = season_id

    if team_stints and prev_game_date:
        team_stints[-1]["end_date"] = prev_game_date.strftime("%Y-%m-%d")
        team_stints[-1]["end_season"] = prev_season

    insert_stints_into_db(player_id, team_stints)


def main():
    existing_ids = get_existing_player_ids()
    all_players = get_all_players()

    print(f"Found {len(all_players)} total players.")
    print(f"{len(existing_ids)} already processed.")

    for player_id, player_name in all_players:
        if player_id in existing_ids:
            continue
        print(f"\nProcessing {player_name} ({player_id})...")
        process_player(player_id)

if __name__ == "__main__":
    main()
