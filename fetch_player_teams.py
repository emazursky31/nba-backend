from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
import time

# Your list of 50 player names
player_names = [
    "Alaa Abdelnaby",
    "Zaid Abdul-Aziz",
    "Kareem Abdul-Jabbar",
    "Mahmoud Abdul-Rauf",
    "Tariq Abdul-Wahad",
    "Shareef Abdur-Rahim",
    "Tom Abernethy",
    "Forest Able",
    "John Abramovic",
    "Alex Abrines",
    "Precious Achiuwa",
    "Alex Acker",
    "Donald Ackerman",
    "Mark Acres",
    "Charles Acton",
    "Quincy Acy",
    "Alvan Adams",
    "Don Adams",
    "Hassan Adams",
    "Jaylen Adams",
    "Jordan Adams",
    "Michael Adams",
    "Steven Adams",
    "Rafael Addison",
    "Bam Adebayo",
    "Deng Adel",
    "Rick Adelman",
    "Jeff Adrien",
    "Arron Afflalo",
    "Ochai Agbaji",
    "Maurice Ager",
    "Mark Aguirre",
    "Blake Ahearn",
    "Danny Ainge",
    "Alexis Ajinca",
    "Henry Akin",
    "Josh Akognon",
    "DeVaughn Akoon-Purcell",
    "Solomon Alabi",
    "Mark Alarie",
    "Gary Alcorn",
    "Santi Aldama",
    "Furkan Aldemir",
    "Cole Aldrich",
    "LaMarcus Aldridge",
    "Chuck Aleksinas",
    "Cliff Alexander",
    "Cory Alexander",
    "Courtney Alexander",
    "Gary Alexander"
]


# Step 1: Map names to IDs
all_players = players.get_players()
name_to_id = {}
for name in player_names:
    matched = [p for p in all_players if p['full_name'].lower() == name.lower()]
    if matched:
        name_to_id[name] = matched[0]['id']
    else:
        print(f"Player not found: {name}")

# Step 2: Fetch all-time teams for each player
player_teams = {}

for name, pid in name_to_id.items():
    try:
        career = playercareerstats.PlayerCareerStats(player_id=pid)
        time.sleep(0.6)  # be kind to the API
        stats = career.get_data_frames()[0]

        if 'TEAM_NAME' in stats.columns and not stats.empty:
            teams = stats['TEAM_NAME'].dropna().unique().tolist()
            player_teams[name] = teams
            print(f"{name}: {teams}")
        else:
            player_teams[name] = ['Unknown']
            print(f"{name}: Unknown (No TEAM_NAME data)")
    except Exception as e:
        player_teams[name] = ['Unknown']
        print(f"Error fetching teams for {name}: {e}")


# player_teams now holds all-time teams by player name
