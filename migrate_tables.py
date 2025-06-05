import sqlite3
import psycopg2
import urllib.parse
import sys

# === CONFIGURATION ===

# SQLite DB path
SQLITE_DB_PATH = "nba_players.db"

# Raw Supabase password (human-readable)
RAW_PASSWORD = "s3$ycj#eQ?u_V4L"

# Encode password for URL safety
ENCODED_PASSWORD = urllib.parse.quote_plus(RAW_PASSWORD)

# Supabase session pooler connection string
POSTGRES_CONN_INFO = (
    f"postgresql://postgres.rbjdlzgptvpfsnkakasj:{ENCODED_PASSWORD}"
    f"@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
)


# === MIGRATION FUNCTIONS ===

def migrate_players(sqlite_conn, pg_conn):
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    sqlite_cur.execute("SELECT player_id, player_name FROM players")
    players = sqlite_cur.fetchall()

    for player_id, player_name in players:
        pg_cur.execute(
            """
            INSERT INTO players (player_id, player_name)
            VALUES (%s, %s)
            ON CONFLICT (player_id) DO NOTHING
            """,
            (player_id, player_name),
        )
    pg_conn.commit()
    print(f"✅ Inserted {len(players)} players.")


def migrate_stints(sqlite_conn, pg_conn):
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    sqlite_cur.execute(
        """
        SELECT player_id, team_abbr, stint_number, start_season, end_season, start_date, end_date
        FROM player_team_stints
        """
    )
    stints = sqlite_cur.fetchall()

    for stint in stints:
        pg_cur.execute(
            """
            INSERT INTO player_team_stints (
                player_id, team_abbr, stint_number, start_season, end_season, start_date, end_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (player_id, team_abbr, stint_number) DO NOTHING
            """,
            stint,
        )
    pg_conn.commit()
    print(f"✅ Inserted {len(stints)} player_team_stints.")


# === MAIN EXECUTION ===

def main():
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        print("✅ Connected to SQLite.")
    except Exception as e:
        print(f"❌ Failed to connect to SQLite: {e}")
        sys.exit(1)

    try:
        pg_conn = psycopg2.connect(POSTGRES_CONN_INFO)
        print("✅ Connected to Supabase PostgreSQL.")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase PostgreSQL: {e}")
        sqlite_conn.close()
        sys.exit(1)

    try:
        migrate_players(sqlite_conn, pg_conn)
        migrate_stints(sqlite_conn, pg_conn)
    except Exception as e:
        print(f"❌ Migration error: {e}")
    finally:
        sqlite_conn.close()
        pg_conn.close()
        print("🔒 Closed both database connections.")


if __name__ == "__main__":
    main()
