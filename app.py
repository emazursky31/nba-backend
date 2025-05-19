from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "NBA Scraper API is running!"

@app.route("/api/test")
def test():
    return jsonify({"message": "It works!"})

if __name__ == "__main__":
    app.run(debug=True)
