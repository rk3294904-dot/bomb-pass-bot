import sqlite3
from datetime import datetime

DB_PATH = "game_data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            coins INTEGER DEFAULT 100,
            games_played INTEGER DEFAULT 0,
            games_won INTEGER DEFAULT 0,
            total_guesses INTEGER DEFAULT 0,
            correct_guesses INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Game history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            winner_id INTEGER,
            players_count INTEGER,
            duration_seconds INTEGER,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()
    conn.close()
    return player

def create_player(user_id, username, first_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO players (user_id, username, first_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def update_coins(user_id, amount):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players SET coins = coins + ? WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()

def update_stats(user_id, won=False, guessed=False, correct=False):
    conn = get_db()
    cursor = conn.cursor()
    if won:
        cursor.execute("UPDATE players SET games_won = games_won + 1 WHERE user_id = ?", (user_id,))
    if guessed:
        cursor.execute("UPDATE players SET total_guesses = total_guesses + 1 WHERE user_id = ?", (user_id,))
    if correct:
        cursor.execute("UPDATE players SET correct_guesses = correct_guesses + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def increment_games_played(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET games_played = games_played + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players ORDER BY coins DESC LIMIT 10")
    leaders = cursor.fetchall()
    conn.close()
    return leaders