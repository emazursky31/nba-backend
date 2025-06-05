print("Starting app...")

from flask import Flask, request, render_template_string

app = Flask(__name__)

# Mock player data — replace this with your real parsed data
player_team_data = {
    "LeBron James": {"CLE": ["2003-04", "2004-05"], "MIA": ["2010-11", "2011-12"]},
    "Kevin Durant": {"OKC": ["2008-09", "2009-10"], "GSW": ["2016-17", "2017-18"]},
    "Stephen Curry": {"GSW": ["2009-10", "2010-11", "2011-12"]}
}

def were_teammates(player1, player2, data):
    if player1 not in data or player2 not in data:
        return False
    p1 = {(team, year) for team, years in data[player1].items() for year in years}
    p2 = {(team, year) for team, years in data[player2].items() for year in years}
    return len(p1 & p2) > 0

# HTML template as a string (small, so no separate file needed)
HTML_PAGE = """
<!doctype html>
<html>
<head>
    <title>NBA Teammate Guessing Game</title>
</head>
<body>
    <h1>NBA Teammate Guessing Game</h1>
    <form method="POST">
        Your Player:<br>
        <input type="text" name="player1" value="{{ player1 or '' }}" required><br><br>
        Guess a Teammate:<br>
        <input type="text" name="player2" value="{{ player2 or '' }}" required><br><br>
        <input type="submit" value="Check">
    </form>
    {% if result is not none %}
        <h2>{{ message }}</h2>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    message = ""
    player1 = None
    player2 = None
    if request.method == "POST":
        player1 = request.form.get("player1").strip()
        player2 = request.form.get("player2").strip()

        if player1 not in player_team_data:
            message = f"Player '{player1}' not found."
        elif player2 not in player_team_data:
            message = f"Player '{player2}' not found."
        else:
            if were_teammates(player1, player2, player_team_data):
                message = f"Yes! {player1} and {player2} were teammates."
            else:
                message = f"No, {player1} and {player2} were never teammates."
        result = True

    return render_template_string(HTML_PAGE, result=result, message=message, player1=player1, player2=player2)

if __name__ == "__main__":
    app.run(debug=True)
