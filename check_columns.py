from nba_api.stats.endpoints import playercareerstats, playergamelog

player_id = 76001  # Example player id

# Fetch career stats DataFrame and print columns and first 5 rows
career = playercareerstats.PlayerCareerStats(player_id=player_id)
df_career = career.get_data_frames()[0]
print("Career stats columns:", df_career.columns.tolist())
print(df_career.head())

# Fetch game log DataFrame and print columns and first 5 rows
gamelog = playergamelog.PlayerGameLog(player_id=player_id, season='1991-92')  # example season
df_gamelog = gamelog.get_data_frames()[0]
print("Game log columns:", df_gamelog.columns.tolist())
print(df_gamelog.head())
