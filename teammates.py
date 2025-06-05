# teammates.py

def parse_player_data(filepath):
    data = {}
    current_player = None
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if ':' not in line:
                current_player = line
                data[current_player] = {}
            else:
                team, years_str = line.split(':', 1)
                years = eval(years_str.strip())
                data[current_player][team.strip()] = years
    return data

def were_teammates(player1, player2, data):
    if player1 not in data or player2 not in data:
        return []

    p1 = {(team, year) for team, years in data[player1].items() for year in years}
    p2 = {(team, year) for team, years in data[player2].items() for year in years}

    return sorted(p1 & p2)

# --- Load data from file ---
player_team_data = parse_player_data("players.txt")

# --- Test it ---
print(were_teammates("Kevin Durant", "Stephen Curry", player_team_data))
print(were_teammates("LeBron James", "Kevin Durant", player_team_data))
