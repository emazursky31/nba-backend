import ast

raw_data = """
LeBron James
  CLE: ['2003-04', '2004-05', '2005-06', '2006-07', '2007-08', '2008-09', '2009-10', '2014-15', '2015-16', '2016-17', '2017-18']
  MIA: ['2010-11', '2011-12', '2012-13', '2013-14']
  LAL: ['2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24', '2024-25']

Kevin Durant
  SEA: ['2007-08']
  OKC: ['2008-09', '2009-10', '2010-11', '2011-12', '2012-13', '2013-14', '2014-15', '2015-16']
  GSW: ['2016-17', '2017-18', '2018-19']
  BKN: ['2020-21', '2021-22', '2022-23']
  PHX: ['2022-23', '2023-24', '2024-25']
  TOT: ['2022-23']

Stephen Curry
  GSW: ['2009-10', '2010-11', '2011-12', '2012-13', '2013-14', '2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24', '2024-25']
"""

player_team_data = {}
current_player = None

for idx, line in enumerate(raw_data.strip().splitlines()):
    print(f"Line {idx}: '{line}'")
    if not line.strip():
        print("  Skipping empty line")
        continue
    if not line.startswith(" "):
        current_player = line.strip()
        print(f"  Found player: {current_player}")
        player_team_data[current_player] = {}
    else:
        line_stripped = line.strip()
        print(f"  Team line detected: {line_stripped}")
        team_abbr, years_str = line_stripped.split(":", 1)
        team_abbr = team_abbr.strip()
        years_list = ast.literal_eval(years_str.strip())
        print(f"    Parsed team: {team_abbr}, years: {years_list}")
        player_team_data[current_player][team_abbr] = years_list

print("\nFinal dict:")
print(player_team_data)

def were_teammates(player1, player2, data):
    if player1 not in data or player2 not in data:
        return []

    p1 = {(team, year) for team, years in data[player1].items() for year in years}
    p2 = {(team, year) for team, years in data[player2].items() for year in years}

    return sorted(p1 & p2)
print(were_teammates("LeBron James", "Kevin Durant", player_team_data))
# Output: []

print(were_teammates("LeBron James", "Stephen Curry", player_team_data))
# Output: [] (no shared team + year)

