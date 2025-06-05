import sqlite3
import time
from datetime import datetime
from threading import Thread, Event

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

DB_PATH = "nba_players.db"

def get_all_player_names():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT player_id, player_name FROM players")
    rows = cur.fetchall()
    conn.close()
    
    name_map = {}
    for player_id, full_name in rows:
        last_name = full_name.split()[-1].lower()
        name_map[full_name] = {
            "id": player_id,
            "full_name": full_name,
            "last_name": last_name
        }
    return name_map

class PlayerNameCompleter(Completer):
    def __init__(self, name_map):
        self.name_map = name_map

    def get_completions(self, document, complete_event):
        text = document.text.lower()
        for name, data in self.name_map.items():
            if text in name.lower() or text in data["last_name"]:
                yield Completion(name, start_position=-len(document.text))

def were_teammates(player1_id, player2_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    query = """
    SELECT 1
    FROM player_team_stints p1
    JOIN player_team_stints p2
      ON p1.team_abbr = p2.team_abbr
    WHERE p1.player_id = ?
      AND p2.player_id = ?
      AND DATE(p1.start_date) <= DATE(p2.end_date)
      AND DATE(p1.end_date) >= DATE(p2.start_date)
    LIMIT 1;
    """
    cur.execute(query, (player1_id, player2_id))
    result = cur.fetchone()
    conn.close()
    return result is not None

def timed_turn_input(prompt_text, completer, timeout=15):
    session = PromptSession(completer=completer)
    done = Event()
    player_input = [None]
    time_remaining = [timeout]

    def countdown():
        for remaining in range(timeout, 0, -1):
            if done.is_set():
                return
            time_remaining[0] = remaining
            time.sleep(1)
        time_remaining[0] = 0
        done.set()

    def get_input():
        try:
            answer = session.prompt(
                prompt_text,
                bottom_toolbar=lambda: HTML(f"<b>⏳ {time_remaining[0]}s remaining</b>") if time_remaining[0] > 0 else HTML("<b>⏰ Time's up!</b>"),
            )
            player_input[0] = answer
            done.set()
        except Exception:
            pass

    input_thread = Thread(target=get_input)
    countdown_thread = Thread(target=countdown)

    input_thread.daemon = True
    countdown_thread.daemon = True
    input_thread.start()
    countdown_thread.start()

    input_thread.join(timeout + 1)

    return player_input[0] if done.is_set() and player_input[0] else None

def play_game():
    used_ids = set()
    prev_player_id = None
    last_player_name = None
    turn = 1

    name_map = get_all_player_names()
    name_completer = PlayerNameCompleter(name_map)

    print("🏀 NBA Teammate Game")
    print("Take turns naming players who were teammates. You have 15 seconds per turn.\n")

    while True:
        current_player = f"Player {1 if turn % 2 else 2}"
        print(f"\n{current_player}'s turn. You have 15 seconds!")
        if last_player_name:
            print(f"Last correct player: {last_player_name}")

        while True:
            name_input = timed_turn_input("Enter a player: ", name_completer, timeout=15)
            if name_input is None:
                print(f"❌ {current_player} ran out of time. Game over.")
                return

            result = name_map.get(name_input.strip())
            if not result:
                print("❌ Invalid player. Try again.")
                continue

            player_id = result["id"]
            player_name = result["full_name"]

            if player_id in used_ids:
                print(f"❌ {player_name} has already been used.")
                continue

            if prev_player_id and not were_teammates(prev_player_id, player_id):
                print(f"❌ {player_name} was not a teammate of the previous player.")
                continue

            print(f"✅ {player_name} accepted!\n")
            used_ids.add(player_id)
            prev_player_id = player_id
            last_player_name = player_name
            turn += 1
            break

if __name__ == "__main__":
    play_game()
