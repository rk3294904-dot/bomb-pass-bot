import sys
import os

# Add parent folder to path FIRST
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import get_player, get_leaderboard
from words import get_random_word

app = Flask(__name__)
CORS(app)

# ═══════════════════════════════════
# ROUTES
# ═══════════════════════════════════

@app.route('/')
def index():
    """Main game page"""
    return render_template('game.html')

@app.route('/api/player/<int:user_id>')
def get_player_data(user_id):
    """Get player stats"""
    player = get_player(user_id)
    if player:
        return jsonify({
            "user_id": player["user_id"],
            "name": player["first_name"] or player["username"] or "Unknown",
            "coins": player["coins"],
            "games_played": player["games_played"],
            "games_won": player["games_won"],
            "correct_guesses": player["correct_guesses"]
        })
    return jsonify({"error": "Player not found"}), 404

@app.route('/api/leaderboard')
def api_leaderboard():
    """Get top 10 players"""
    leaders = get_leaderboard()
    result = []
    for p in leaders:
        result.append({
            "name": p["first_name"] or p["username"] or "Unknown",
            "coins": p["coins"],
            "games_won": p["games_won"]
        })
    return jsonify(result)

@app.route('/api/word')
def get_word_api():
    """Get a random word"""
    word_data = get_random_word()
    return jsonify({
        "emoji": word_data["emoji"],
        "word": word_data["word"]
    })

@app.route('/api/check_guess', methods=['POST'])
def check_guess():
    """Check if guess is correct"""
    data = request.json
    guess = data.get("guess", "").lower().strip()
    answer = data.get("answer", "").lower().strip()
    
    guess_clean = " ".join(guess.split())
    answer_clean = " ".join(answer.split())
    
    if guess_clean == answer_clean:
        return jsonify({"correct": True, "message": "Perfect!"})
    elif guess_clean.replace(" ", "") == answer_clean.replace(" ", ""):
        return jsonify({"correct": True, "message": "Correct!"})
    else:
        return jsonify({"correct": False, "message": "Try again!"})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "game": "Bomb Pass"})

# ═══════════════════════════════════
# MAIN
# ═══════════════════════════════════

if __name__ == '__main__':
    app.run(debug=True, port=5000)