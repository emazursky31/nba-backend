import requests
from bs4 import BeautifulSoup
import time
import re

# Sample list of players to scrape team history for
player_names = [
    "Kareem Abdul-Jabbar",
    "Michael Jordan",
    "LeBron James",
    "Shaquille O'Neal",
    "Larry Bird"
]

BASE_SEARCH_URL = "https://www.basketball-reference.com/search/search.fcgi?search="

def get_player_url(name):
    """Search Basketball Reference and get the first player result URL"""
    search_url = BASE_SEARCH_URL + requests.utils.quote(name)
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Try to find the first search result that links to a player page
    results = soup.select("div.search-item-url")
    for result in results:
        link = result.get_text()
        if "/players/" in link:
            return "https://www.basketball-reference.com" + link
    return None

def get_player_teams(player_url):
    """Scrape the player page for all team abbreviations they've played for"""
    response = requests.get(player_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    teams = set()
    table = soup.find('table', {'id': 'per_game'})
    if not table:
        return []

    for row in table.tbody.find_all('tr'):
        if row.get('class') == ['thead']:
            continue
        team_cell = row.find('td', {'data-stat': 'team_id'})
        if team_cell:
            team_abbr = team_cell.get_text(strip=True)
            if team_abbr != 'TOT':  # Ignore totals row
                teams.add(team_abbr)
    return sorted(teams)

# Main logic to scrape for each player
player_teams = {}

for name in player_names:
    print(f"Processing: {name}")
    url = get_player_url(name)
    if url:
        teams = get_player_teams(url)
        player_teams[name] = teams
        print(f"{name}: {teams}")
    else:
        print(f"Could not find URL for {name}")
    time.sleep(1.5)  # Be kind to the server

player_teams
