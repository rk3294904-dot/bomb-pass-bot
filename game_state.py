import asyncio
import random
from datetime import datetime, timedelta

class GameState:
    def __init__(self):
        # Structure: { chat_id: game_data }
        self.games = {}
    
    def init_game(self, chat_id):
        """Initialize a new game for a chat"""
        self.games[chat_id] = {
            "players": [],           # List of user_ids
            "player_names": {},      # {user_id: name}
            "current_player_index": 0,
            "status": "lobby",       # lobby, playing, finished
            "used_words": [],
            "current_word": None,
            "current_emoji": None,
            "timer_task": None,
            "bomb_start_time": None,
            "round_number": 0,
        }
    
    def add_player(self, chat_id, user_id, name):
        """Add a player to the game"""
        if chat_id not in self.games:
            self.init_game(chat_id)
        
        game = self.games[chat_id]
        if user_id not in game["players"]:
            game["players"].append(user_id)
            game["player_names"][user_id] = name
            return True
        return False
    
    def remove_player(self, chat_id, user_id):
        """Remove a player from the game"""
        if chat_id in self.games:
            game = self.games[chat_id]
            if user_id in game["players"]:
                game["players"].remove(user_id)
                if user_id in game["player_names"]:
                    del game["player_names"][user_id]
                return True
        return False
    
    def get_players(self, chat_id):
        """Get list of players in the game"""
        if chat_id in self.games:
            return self.games[chat_id]["players"]
        return []
    
    def get_player_names(self, chat_id):
        """Get all players and their names"""
        if chat_id in self.games:
            return self.games[chat_id]["player_names"]
        return {}
    
    def get_current_player(self, chat_id):
        """Get the current player who holds the bomb"""
        if chat_id in self.games:
            game = self.games[chat_id]
            if game["players"]:
                return game["players"][game["current_player_index"]]
        return None
    
    def get_current_player_name(self, chat_id):
        """Get the name of the current player"""
        user_id = self.get_current_player(chat_id)
        if user_id and chat_id in self.games:
            return self.games[chat_id]["player_names"].get(user_id, "Unknown")
        return None
    
    def next_player(self, chat_id):
        """Move bomb to the next player"""
        if chat_id in self.games:
            game = self.games[chat_id]
            if game["players"]:
                game["current_player_index"] = (game["current_player_index"] + 1) % len(game["players"])
                return game["players"][game["current_player_index"]]
        return None
    
    def eliminate_player(self, chat_id, user_id):
        """Eliminate a player from the current round"""
        if chat_id in self.games:
            game = self.games[chat_id]
            if user_id in game["players"]:
                idx = game["players"].index(user_id)
                game["players"].remove(user_id)
                # Adjust current_player_index
                if game["current_player_index"] >= len(game["players"]):
                    game["current_player_index"] = 0
                return True
        return False
    
    def set_status(self, chat_id, status):
        """Set game status"""
        if chat_id in self.games:
            self.games[chat_id]["status"] = status
    
    def get_status(self, chat_id):
        """Get game status"""
        if chat_id in self.games:
            return self.games[chat_id]["status"]
        return "no_game"
    
    def set_current_word(self, chat_id, word, emoji):
        """Set the current word and emoji hint"""
        if chat_id in self.games:
            self.games[chat_id]["current_word"] = word
            self.games[chat_id]["current_emoji"] = emoji
            if word:
                self.games[chat_id]["used_words"].append(word)
    
    def get_current_word(self, chat_id):
        """Get the current word to guess"""
        if chat_id in self.games:
            return self.games[chat_id]["current_word"]
        return None
    
    def get_current_emoji(self, chat_id):
        """Get the current emoji hint"""
        if chat_id in self.games:
            return self.games[chat_id]["current_emoji"]
        return None
    
    def get_used_words(self, chat_id):
        """Get list of already used words"""
        if chat_id in self.games:
            return self.games[chat_id]["used_words"]
        return []
    
    def reset_game(self, chat_id):
        """Reset the game for a new round"""
        if chat_id in self.games:
            game = self.games[chat_id]
            game["current_word"] = None
            game["current_emoji"] = None
            game["bomb_start_time"] = None
            game["round_number"] += 1
            if game["timer_task"]:
                game["timer_task"].cancel()
                game["timer_task"] = None
    
    def cleanup(self, chat_id):
        """Remove a game entirely"""
        if chat_id in self.games:
            game = self.games[chat_id]
            if game["timer_task"]:
                game["timer_task"].cancel()
            del self.games[chat_id]

# Global game state instance
game_state = GameState()