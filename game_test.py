import sqlite3
import threading
import time
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import HTML
from collections import defaultdict

DB_PATH = 'nba_players.db'

# Normalize historical team IDs to franchise IDs
TEAM_FRANCHISE_MAP = {
    'NOH': 'NOP',
    'NOK': 'NOP',
    'SEA': 'OKC',
    'VAN': 'MEM',
    'NJN': 'BKN',
    'KCK': 'SAC',
    'CIN': 'SAC',
    'ROC': 'SAC',
    'SDC': 'LAC',
    'SDR': 'HOU',
    'NOJ': 'UTA',
    'CHZ': 'WAS',
    'BAL': 'WAS',
    'BUF': 'LAC',
    'STL': 'ATL',
    'CHA': 'CHA',
}

# Build franchise map: franchise ID → all its associated historical team IDs (including itself)
FRANCHISE_MAP = {}
for hist_id, franchise_id in TEAM_FRANCHISE_MAP.items():
    FRANCHISE_MAP.setdefault(franchise_id, set()).add(hist_id)
for fid in TEAM_FRANCHISE_MAP.values():
    FRANCHISE_MAP.setdefault(fid, set()).add(fid)


def build_franchise_team_map(team_franchise_map):
    franchise_map = defaultdict(set)
    for historical_id, franchise_id in team_franchise_map.items():
        franchise_map[franchise_id].add(historical_id)
    for team_id in set(team_franchise_map.values()):
        franchise_map[team_id].add(team_id)  # add the normalized ID itself
    return franchise_map


# Load all players from DB upfront
def load_all_players(cursor):
    cursor.execute("SELECT player_id, player_name FROM players")
    return cursor.fetchall()

# Get teammates of a player (any season)
def normalize_team_id(team_id):
    return TEAM_FRANCHISE_MAP.get(team_id, team_id)

def get_teammates(cursor, player_id):
    cursor.execute("SELECT team_id, season FROM player_teams WHERE player_id = ?", (player_id,))
    rows = cursor.fetchall()
    teammates = set()

    for team_id, season in rows:
        franchise_id = TEAM_FRANCHISE_MAP.get(team_id, team_id)
        team_ids_to_check = FRANCHISE_MAP.get(franchise_id, {franchise_id})

        placeholders = ",".join(["?"] * len(team_ids_to_check))
        cursor.execute(f"""
            SELECT player_id FROM player_teams
            WHERE team_id IN ({placeholders})
              AND season = ?
              AND player_id != ?
        """, (*team_ids_to_check, season, player_id))
        teammates.update(row[0] for row in cursor.fetchall())

    return teammates



# Build mapping from player_id to player_name and vice versa
def build_player_maps(all_players):
    id_to_name = {}
    name_to_id = {}
    for pid, pname in all_players:
        id_to_name[pid] = pname
        name_to_id[pname.lower()] = pid
    return id_to_name, name_to_id

# Autocomplete for player names
class PlayerCompleter(Completer):
    def __init__(self, player_names):
        self.player_names = player_names

    def get_completions(self, document, complete_event):
        text = document.text.lower()
        for name in self.player_names:
            if text in name.lower():
                yield Completion(name, start_position=-len(document.text))

# Validate player is in list
class PlayerValidator(Validator):
    def __init__(self, player_names):
        self.player_names = set(player_names)

    def validate(self, document):
        text = document.text.strip()
        if text not in self.player_names:
            raise ValidationError(message="Please select a valid player from the list.")

# Input with timeout and live countdown in bottom toolbar
def input_with_timeout(prompt_text, completer, validator, timeout=15):
    session = PromptSession()
    remaining_time = [int(timeout)]
    stop_event = threading.Event()

    def update_timer():
        while remaining_time[0] > 0 and not stop_event.is_set():
            time.sleep(1)
            remaining_time[0] -= 1
            app = get_app()
            if app:
                app.invalidate()
        stop_event.set()

    def get_toolbar():
        return HTML(f"<b>⏳ {remaining_time[0]:2d} seconds left</b>")

    thread = threading.Thread(target=update_timer)
    thread.start()

    result = None
    try:
        result = session.prompt(prompt_text, completer=completer,
                                validator=validator, validate_while_typing=False,
                                bottom_toolbar=get_toolbar)
    except (KeyboardInterrupt, EOFError):
        result = None

    stop_event.set()
    thread.join()

    if remaining_time[0] <= 0 and not result:
        return None
    return result.strip()

# Main game loop
def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    all_players = load_all_players(cursor)
    id_to_name, name_to_id = build_player_maps(all_players)
    all_player_names = list(id_to_name.values())

    completer = PlayerCompleter(all_player_names)
    validator = PlayerValidator(all_player_names)

    print("Welcome to the NBA Teammate Guessing Game!")
    print("Rules:")
    print("- Player 1 names an NBA player.")
    print("- Player 2 names a valid teammate from ANY season.")
    print("- No repeats allowed.")
    print("- You can guess as many times as you want in 15 seconds.")
    print("- Game ends if invalid guess or time expires.\n")

    used_player_ids = set()
    current_player = 1
    prev_player_id = None

    while True:
        if prev_player_id is None:
            prompt_text = f"Player {current_player}, name any NBA player: "
        else:
            prev_name = id_to_name[prev_player_id]
            prompt_text = f"Player {current_player}, name a teammate of {prev_name}: "

        valid_guess = False
        start_time = time.time()
        while time.time() - start_time < 15:
            guess_name = input_with_timeout(prompt_text, completer, validator,
                                            timeout=15 - int(time.time() - start_time))
            if guess_name is None:
                print(f"\nTime expired or input interrupted. Player {current_player} loses. Game over.")
                return

            guess_id = name_to_id.get(guess_name.lower())
            if guess_id is None:
                print(f"{guess_name} is not a valid player. Try again.")
                continue

            if guess_id in used_player_ids:
                print(f"{guess_name} was already used. Try again.")
                continue

            if prev_player_id is not None:
                teammates = get_teammates(cursor, prev_player_id)
                if guess_id not in teammates:
                    print(f"{guess_name} is NOT a teammate of {id_to_name[prev_player_id]}. Try again.")
                    continue

            # Valid guess
            used_player_ids.add(guess_id)
            prev_player_id = guess_id
            current_player = 2 if current_player == 1 else 1
            valid_guess = True
            break

        if not valid_guess:
            print(f"\nPlayer {current_player} ran out of time. Game over.")
            break

    conn.close()

if __name__ == "__main__":
    main()
