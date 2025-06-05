import sqlite3

def list_tables(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return [table[0] for table in tables]
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    for db_file in ['nba_players.db', 'nba_rosters.db']:
        print(f"Tables in {db_file}:")
        result = list_tables(db_file)
        if isinstance(result, list):
            if result:
                for t in result:
                    print(f" - {t}")
            else:
                print(" No tables found.")
        else:
            print(f" Error: {result}")
        print()
