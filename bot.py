import os
import asyncio
import logging
import random
from dotenv import load_dotenv
from telegram import Update, BotCommand, BotCommandScopeAllGroupChats
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

from database import init_db, get_player, create_player, update_coins, update_stats, increment_games_played, get_leaderboard
from words import get_random_word
from game_state import game_state

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# PythonAnywhere proxy (remove if running locally)
PROXY_URL = "http://proxy.server:3128"
request = HTTPXRequest(proxy_url=PROXY_URL)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TIMER_SECONDS = 30
MIN_PLAYERS = 3
SOLO_ROUNDS = 5
BORDER = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"

# ═══════════════════════════════════════
# 🔊 SINGLE EMOJI SOUNDS
# ═══════════════════════════════════════

SOUNDS = {
    "join": "🔔",
    "leave": "🚪",
    "start": "🚀",
    "correct": "✅",
    "wrong": "❌",
    "victory": "🏆",
    "eliminated": "💀",
    "coins": "💰",
    "warning": "⚠️",
    "bomb": "💣",
    "explosion": "💥",
}

async def play_sound(chat_id, context, sound_key):
    try:
        emoji = SOUNDS.get(sound_key, "🔔")
        msg = await context.bot.send_message(chat_id=chat_id, text=emoji)
        await asyncio.sleep(2)
        await msg.delete()
    except:
        pass

def get_progress_bar(seconds_left, total=30):
    filled = int((seconds_left / total) * 10)
    empty = 10 - filled
    
    if seconds_left <= 5:
        bar = "🔴"
    elif seconds_left <= 10:
        bar = "🟠"
    elif seconds_left <= 20:
        bar = "🟡"
    else:
        bar = "🟢"
    
    progress = "█" * filled + "░" * empty
    return f"💣 [{progress}] {seconds_left}s {bar}"

# ═══════════════════════════════════════
# 🎮 COMMANDS
# ═══════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"✨ {BORDER} ✨\n"
        f"     💣 BOMB PASS\n"
        f"{BORDER}\n\n"
        f"🎯 Guess the word from emoji hints!\n"
        f"⏱️ 30 seconds per turn\n"
        f"💰 Earn coins for surviving!\n\n"
        f"📋 Commands:\n"
        f"  ▸ /join - Join the lobby\n"
        f"  ▸ /leave - Leave the lobby\n"
        f"  ▸ /startgame - Start group game (3+)\n"
        f"  ▸ /solo - Start solo practice\n"
        f"  ▸ /guess <word> - Submit guess\n"
        f"  ▸ Just type the word to guess!\n"
        f"  ▸ /stats - Your stats\n"
        f"  ▸ /leaderboard - Top players\n"
        f"  ▸ /help - How to play"
    )
    await update.message.reply_text(msg)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"📖 HOW TO PLAY\n\n"
        f"🎮 GROUP MODE:\n"
        f"1. /join to enter the lobby\n"
        f"2. Wait for 3+ players\n"
        f"3. /startgame to begin\n"
        f"4. See emoji hints\n"
        f"5. Type word OR /guess <word>\n"
        f"6. Pass the bomb before 30s!\n\n"
        f"🧑 SOLO MODE:\n"
        f"1. /solo to start\n"
        f"2. Guess {SOLO_ROUNDS} words in 30s each\n"
        f"3. Earn coins for correct guesses!\n\n"
        f"💰 Rewards:\n"
        f"  +10 per correct guess\n"
        f"  +2 per elimination for winner\n"
        f"  +25 bonus for perfect solo\n\n"
        f"❌ No penalties for wrong guesses!"
    )
    await update.message.reply_text(msg)

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if game_state.get_status(chat_id) == "playing":
        await update.message.reply_text("⏳ Game in progress! Please wait...")
        return
    
    if game_state.get_status(chat_id) == "solo":
        await update.message.reply_text("🧑 Solo game in progress! Wait for it to finish.")
        return
    
    create_player(user.id, user.username, user.first_name)
    added = game_state.add_player(chat_id, user.id, user.first_name)
    
    if added:
        await play_sound(chat_id, context, "join")
        
        players = game_state.get_players(chat_id)
        names = game_state.get_player_names(chat_id)
        remaining = max(0, MIN_PLAYERS - len(players))
        
        player_list = "\n".join([f"  👤 {name}" for name in names.values()])
        
        if remaining > 0:
            msg = (
                f"🎮 LOBBY ({len(players)}/{MIN_PLAYERS})\n\n"
                f"{player_list}\n\n"
                f"⏳ Need {remaining} more player(s)!\n"
                f"Type /join to enter!"
            )
        else:
            msg = (
                f"🎮 LOBBY READY! ({len(players)}/{MIN_PLAYERS})\n\n"
                f"{player_list}\n\n"
                f"🚀 Type /startgame to begin!"
            )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("😅 You're already in the lobby!")

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if game_state.get_status(chat_id) == "playing":
        await update.message.reply_text("⏳ Can't leave during a game!")
        return
    
    removed = game_state.remove_player(chat_id, user.id)
    
    if removed:
        await play_sound(chat_id, context, "leave")
        players = game_state.get_players(chat_id)
        await update.message.reply_text(f"👋 {user.first_name} left. ({len(players)} remaining)")
    else:
        await update.message.reply_text("🤔 You're not in the lobby!")

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    players = game_state.get_players(chat_id)
    if len(players) < MIN_PLAYERS:
        await update.message.reply_text(f"❌ Need {MIN_PLAYERS} players! Currently: {len(players)}")
        return
    
    if game_state.get_status(chat_id) == "playing":
        await update.message.reply_text("⏳ Game already running!")
        return
    
    game_state.set_status(chat_id, "playing")
    random.shuffle(players)
    game_state.games[chat_id]["players"] = players
    game_state.games[chat_id]["current_player_index"] = 0
    game_state.games[chat_id]["eliminated_count"] = 0
    game_state.games[chat_id]["mode"] = "group"
    
    player_names = game_state.get_player_names(chat_id)
    names_list = "\n".join([f"  🎮 {name}" for name in player_names.values()])
    
    await play_sound(chat_id, context, "start")
    
    msg = (
        f"💣 BOMB PASS - GAME ON!\n\n"
        f"👥 Players:\n{names_list}\n\n"
        f"⏱️ Timer: {TIMER_SECONDS}s per turn\n"
        f"💡 Type word OR /guess <word>\n\n"
        f"🍀 Good luck, survivors!"
    )
    await update.message.reply_text(msg)
    
    await asyncio.sleep(1)
    await start_turn(chat_id, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user.id)
    
    if not player:
        create_player(user.id, user.username, user.first_name)
        player = get_player(user.id)
    
    msg = (
        f"📊 {user.first_name}'s STATS\n"
        f"{BORDER}\n"
        f"💰 Coins: {player['coins']}\n"
        f"🎮 Games: {player['games_played']}\n"
        f"🏆 Wins: {player['games_won']}\n"
        f"🎯 Guesses: {player['total_guesses']}\n"
        f"✅ Correct: {player['correct_guesses']}\n"
        f"{BORDER}"
    )
    await update.message.reply_text(msg)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaders = get_leaderboard()
    
    if not leaders:
        await update.message.reply_text("🏆 No players yet! Join a game!")
        return
    
    text = f"🏆 TOP 10 - HALL OF FAME\n\n{BORDER}\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, player in enumerate(leaders):
        medal = medals[i] if i < 3 else f"  {i+1}."
        name = player['first_name'] or player['username'] or "Unknown"
        text += f"{medal} {name} - 💰 {player['coins']} coins\n"
    
    text += BORDER
    await update.message.reply_text(text)

# ═══════════════════════════════════════
# 🧑 SOLO MODE
# ═══════════════════════════════════════

async def solo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if game_state.get_status(chat_id) == "playing":
        await update.message.reply_text("⏳ Group game in progress! Please wait...")
        return
    
    if game_state.get_status(chat_id) == "solo":
        await update.message.reply_text("🧑 Solo game already running!")
        return
    
    game_state.init_game(chat_id)
    game_state.set_status(chat_id, "solo")
    game_state.games[chat_id]["mode"] = "solo"
    game_state.games[chat_id]["solo_player"] = user.id
    game_state.games[chat_id]["solo_name"] = user.first_name
    game_state.games[chat_id]["solo_round"] = 1
    game_state.games[chat_id]["solo_score"] = 0
    game_state.games[chat_id]["solo_correct"] = 0
    
    create_player(user.id, user.username, user.first_name)
    
    await play_sound(chat_id, context, "start")
    
    msg = (
        f"🧑 SOLO MODE\n"
        f"{BORDER}\n\n"
        f"🎯 {user.first_name} vs THE BOMB!\n\n"
        f"📝 Guess {SOLO_ROUNDS} words\n"
        f"⏱️ {TIMER_SECONDS}s per word\n"
        f"💰 +10 coins per correct guess\n\n"
        f"🚀 Starting..."
    )
    await update.message.reply_text(msg)
    
    await asyncio.sleep(2)
    await solo_round(chat_id, context)

async def solo_round(chat_id, context):
    game = game_state.games[chat_id]
    
    if game["solo_round"] > SOLO_ROUNDS:
        await solo_end(chat_id, context)
        return
    
    used_words = game_state.get_used_words(chat_id)
    word_data = get_random_word(exclude_words=used_words)
    game_state.set_current_word(chat_id, word_data["word"], word_data["emoji"])
    
    round_num = game["solo_round"]
    progress_bar = get_progress_bar(TIMER_SECONDS)
    
    msg = (
        f"🧑 SOLO - Round {round_num}/{SOLO_ROUNDS}\n"
        f"{BORDER}\n\n"
        f"📝 Guess:\n   {word_data['emoji']}\n\n"
        f"{progress_bar}\n"
        f"✅ {game['solo_correct']} | 💰 {game['solo_score']}\n\n"
        f"💡 Type word OR /guess <word>"
    )
    sent_msg = await context.bot.send_message(chat_id=chat_id, text=msg)
    
    game["bomb_start_time"] = asyncio.get_event_loop().time()
    game["timer_message_id"] = sent_msg.message_id
    game["timer_task"] = asyncio.create_task(solo_timer(chat_id, context))
    game["countdown_task"] = asyncio.create_task(solo_countdown(chat_id, context, sent_msg.message_id))

async def solo_countdown(chat_id, context, message_id):
    try:
        for remaining in range(TIMER_SECONDS - 5, 0, -5):
            await asyncio.sleep(5)
            
            if game_state.get_status(chat_id) != "solo":
                return
            
            game = game_state.games[chat_id]
            word_emoji = game_state.get_current_emoji(chat_id)
            progress_bar = get_progress_bar(remaining)
            
            if remaining <= 10:
                await play_sound(chat_id, context, "warning")
            
            updated_msg = (
                f"🧑 SOLO - Round {game['solo_round']}/{SOLO_ROUNDS}\n"
                f"{BORDER}\n\n"
                f"📝 Guess:\n   {word_emoji}\n\n"
                f"{progress_bar}\n"
                f"✅ {game['solo_correct']} | 💰 {game['solo_score']}\n\n"
                f"💡 Type word OR /guess <word>"
            )
            
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=updated_msg)
            except:
                pass
    except asyncio.CancelledError:
        pass

async def solo_timer(chat_id, context):
    try:
        await asyncio.sleep(TIMER_SECONDS)
        
        if game_state.get_status(chat_id) == "solo":
            game = game_state.games[chat_id]
            current_word = game_state.get_current_word(chat_id)
            current_emoji = game_state.get_current_emoji(chat_id)
            
            msg = (
                f"⏰ TIME'S UP!\n"
                f"📝 Answer: {current_emoji} -> {current_word}\n\n"
                f"➡️ Next word..."
            )
            await context.bot.send_message(chat_id=chat_id, text=msg)
            
            game["solo_round"] += 1
            await asyncio.sleep(1.5)
            await solo_round(chat_id, context)
    except asyncio.CancelledError:
        pass

async def solo_guess(chat_id, user, guess_text, context):
    game = game_state.games[chat_id]
    current_word = game_state.get_current_word(chat_id)
    
    update_stats(user.id, guessed=True)
    
    if words_match(guess_text, current_word):
        update_stats(user.id, correct=True)
        update_coins(user.id, 10)
        
        game["solo_correct"] += 1
        game["solo_score"] += 10
        
        if game["timer_task"]:
            game["timer_task"].cancel()
        if game.get("countdown_task"):
            game["countdown_task"].cancel()
        
        await play_sound(chat_id, context, "correct")
        await play_sound(chat_id, context, "coins")
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ CORRECT! +10 💰\n'{current_word}'\n\n➡️ Next word..."
        )
        
        game["solo_round"] += 1
        await asyncio.sleep(1)
        await solo_round(chat_id, context)
    else:
        await play_sound(chat_id, context, "wrong")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Wrong! Try again!")

async def solo_end(chat_id, context):
    game = game_state.games[chat_id]
    player_name = game["solo_name"]
    correct = game["solo_correct"]
    score = game["solo_score"]
    
    if correct == SOLO_ROUNDS:
        bonus = 25
        update_coins(game["solo_player"], bonus)
        score += bonus
        perfect_msg = f"\n🔥 PERFECT! +{bonus} bonus!"
        await play_sound(chat_id, context, "victory")
    else:
        perfect_msg = ""
    
    if correct >= SOLO_ROUNDS:
        rating = "🏆 LEGEND"
    elif correct >= 4:
        rating = "🌟 PRO"
    elif correct >= 3:
        rating = "👍 GOOD"
    elif correct >= 1:
        rating = "📚 LEARNING"
    else:
        rating = "💀 OOPS"
    
    msg = (
        f"🧑 SOLO - FINISHED!\n{BORDER}\n\n"
        f"🎯 {player_name}\n"
        f"🏅 {rating}\n\n"
        f"✅ {correct}/{SOLO_ROUNDS}\n"
        f"💰 +{score} coins\n"
        f"{perfect_msg}\n\n{BORDER}\n\n"
        f"🔄 /solo | 🎮 /join"
    )
    await context.bot.send_message(chat_id=chat_id, text=msg)
    game_state.cleanup(chat_id)

# ═══════════════════════════════════════
# 🧠 SMART GUESS DETECTION
# ═══════════════════════════════════════

def normalize_text(text):
    text = " ".join(text.split())
    text = text.lower()
    text = text.strip(".,!?;:'\"-")
    return text

def words_match(guess, answer):
    guess = normalize_text(guess)
    answer = normalize_text(answer)
    
    if guess == answer:
        return True
    if guess.replace(" ", "") == answer.replace(" ", ""):
        return True
    if len(guess) >= 3 and guess in answer:
        return True
    if len(answer) >= 3 and answer in guess:
        return True
    return False

# ═══════════════════════════════════════
# 🎯 /guess COMMAND
# ═══════════════════════════════════════

async def guess_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /guess <word>")
        return
    
    guess_text = " ".join(context.args)
    status = game_state.get_status(chat_id)
    
    if status == "solo":
        game = game_state.games[chat_id]
        if user.id == game.get("solo_player"):
            await solo_guess(chat_id, user, guess_text, context)
        return
    
    if status != "playing":
        await update.message.reply_text("❌ No game in progress!")
        return
    
    current_player = game_state.get_current_player(chat_id)
    if user.id != current_player:
        await update.message.reply_text("⏳ Not your turn!")
        return
    
    current_word = game_state.get_current_word(chat_id)
    update_stats(user.id, guessed=True)
    
    if words_match(guess_text, current_word):
        update_stats(user.id, correct=True)
        update_coins(user.id, 10)
        
        game = game_state.games[chat_id]
        if game["timer_task"]:
            game["timer_task"].cancel()
        if game.get("countdown_task"):
            game["countdown_task"].cancel()
        
        await play_sound(chat_id, context, "correct")
        await play_sound(chat_id, context, "coins")
        
        await update.message.reply_text(
            f"✅ CORRECT! {user.first_name} +10 💰\n'{current_word}'\n\n🔥 Passing bomb..."
        )
        
        await asyncio.sleep(1)
        game_state.next_player(chat_id)
        await start_turn(chat_id, context)
    else:
        await play_sound(chat_id, context, "wrong")
        await update.message.reply_text(f"❌ Wrong! Try again!")

# ═══════════════════════════════════════
# 💬 AUTO-DETECT
# ═══════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text.strip()
    
    if text.startswith("/"):
        return
    
    status = game_state.get_status(chat_id)
    
    if status == "solo":
        game = game_state.games[chat_id]
        if user.id == game.get("solo_player"):
            await solo_guess(chat_id, user, text, context)
        return
    
    if status != "playing":
        return
    
    current_player = game_state.get_current_player(chat_id)
    if user.id != current_player:
        return
    
    current_word = game_state.get_current_word(chat_id)
    update_stats(user.id, guessed=True)
    
    if words_match(text, current_word):
        update_stats(user.id, correct=True)
        update_coins(user.id, 10)
        
        game = game_state.games[chat_id]
        if game["timer_task"]:
            game["timer_task"].cancel()
        if game.get("countdown_task"):
            game["countdown_task"].cancel()
        
        await play_sound(chat_id, context, "correct")
        await play_sound(chat_id, context, "coins")
        
        await update.message.reply_text(
            f"✅ CORRECT! {user.first_name} +10 💰\n'{current_word}'\n\n🔥 Passing bomb..."
        )
        
        await asyncio.sleep(1)
        game_state.next_player(chat_id)
        await start_turn(chat_id, context)
    else:
        await play_sound(chat_id, context, "wrong")
        await update.message.reply_text(f"❌ Wrong! Try again!")

# ═══════════════════════════════════════
# 🎯 GROUP GAME LOGIC
# ═══════════════════════════════════════

async def start_turn(chat_id, context):
    game = game_state.games[chat_id]
    current_player = game_state.get_current_player(chat_id)
    
    if not current_player:
        return
    
    used_words = game_state.get_used_words(chat_id)
    word_data = get_random_word(exclude_words=used_words)
    game_state.set_current_word(chat_id, word_data["word"], word_data["emoji"])
    
    player_name = game_state.get_current_player_name(chat_id)
    players_left = len(game_state.get_players(chat_id))
    progress_bar = get_progress_bar(TIMER_SECONDS)
    
    msg = (
        f"💣 BOMB TURN!\n{BORDER}\n\n"
        f"🎯 {player_name}\n\n"
        f"📝 {word_data['emoji']}\n\n"
        f"{progress_bar}\n"
        f"🎮 {players_left} players\n\n"
        f"💡 Type word OR /guess"
    )
    sent_msg = await context.bot.send_message(chat_id=chat_id, text=msg)
    
    game["bomb_start_time"] = asyncio.get_event_loop().time()
    game["timer_message_id"] = sent_msg.message_id
    game["timer_task"] = asyncio.create_task(bomb_timer(chat_id, current_player, context))
    game["countdown_task"] = asyncio.create_task(live_countdown(chat_id, current_player, context, sent_msg.message_id))

async def live_countdown(chat_id, player_id, context, message_id):
    try:
        for remaining in range(TIMER_SECONDS - 5, 0, -5):
            await asyncio.sleep(5)
            
            if (game_state.get_status(chat_id) != "playing" or 
                game_state.get_current_player(chat_id) != player_id):
                return
            
            word_emoji = game_state.get_current_emoji(chat_id)
            player_name = game_state.get_current_player_name(chat_id)
            players_left = len(game_state.get_players(chat_id))
            progress_bar = get_progress_bar(remaining)
            
            if remaining <= 10:
                await play_sound(chat_id, context, "warning")
            
            updated_msg = (
                f"💣 BOMB TURN!\n{BORDER}\n\n"
                f"🎯 {player_name}\n\n"
                f"📝 {word_emoji}\n\n"
                f"{progress_bar}\n"
                f"🎮 {players_left} players\n\n"
                f"💡 Type word OR /guess"
            )
            
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=updated_msg)
            except:
                pass
    except asyncio.CancelledError:
        pass

async def bomb_timer(chat_id, player_id, context):
    try:
        await asyncio.sleep(TIMER_SECONDS)
        
        if (game_state.get_status(chat_id) == "playing" and 
            game_state.get_current_player(chat_id) == player_id):
            
            game = game_state.games[chat_id]
            if game.get("countdown_task"):
                game["countdown_task"].cancel()
            
            game_state.eliminate_player(chat_id, player_id)
            game_state.games[chat_id]["eliminated_count"] += 1
            player_name = game_state.games[chat_id]["player_names"].get(player_id, "Unknown")
            
            current_word = game_state.get_current_word(chat_id)
            current_emoji = game_state.get_current_emoji(chat_id)
            remaining = game_state.get_players(chat_id)
            
            await play_sound(chat_id, context, "explosion")
            await play_sound(chat_id, context, "eliminated")
            
            msg = (
                f"💥 BOOM! {player_name} OUT!\n"
                f"📝 Answer: {current_emoji} -> {current_word}\n"
                f"👥 {len(remaining)} remaining"
            )
            await context.bot.send_message(chat_id=chat_id, text=msg)
            
            if len(remaining) <= 1:
                await end_game(chat_id, context)
            else:
                await asyncio.sleep(2)
                await start_turn(chat_id, context)
    except asyncio.CancelledError:
        pass

async def end_game(chat_id, context):
    game_state.set_status(chat_id, "finished")
    remaining = game_state.get_players(chat_id)
    eliminated = game_state.games[chat_id].get("eliminated_count", 0)
    
    if remaining:
        winner_id = remaining[0]
        winner_name = game_state.games[chat_id]["player_names"].get(winner_id, "Unknown")
        
        winner_bonus = eliminated * 2
        update_coins(winner_id, winner_bonus)
        update_stats(winner_id, won=True)
        increment_games_played(winner_id)
        
        await play_sound(chat_id, context, "victory")
        await play_sound(chat_id, context, "coins")
        
        msg = (
            f"🏆 {winner_name} WINS!\n{BORDER}\n\n"
            f"💰 +{winner_bonus} coins\n"
            f"💀 {eliminated} eliminated\n\n{BORDER}\n\n"
            f"🔄 /startgame"
        )
        await context.bot.send_message(chat_id=chat_id, text=msg)
    else:
        await context.bot.send_message(chat_id=chat_id, text="🤷 No survivors!\n\n🔄 /startgame")
    
    game_state.cleanup(chat_id)

# ═══════════════════════════════════════
# ⚙️ COMMAND MENU
# ═══════════════════════════════════════

async def set_commands(app):
    commands = [
        BotCommand("join", "🎮 Join the group lobby"),
        BotCommand("leave", "👋 Leave the lobby"),
        BotCommand("startgame", "🚀 Start group game"),
        BotCommand("solo", "🧑 Start solo practice"),
        BotCommand("guess", "🎯 Submit your guess"),
        BotCommand("stats", "📊 View your stats"),
        BotCommand("leaderboard", "🏆 Top players"),
        BotCommand("help", "❓ How to play"),
    ]
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())

# ═══════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════

def main():
    init_db()
    
    # Use proxy for PythonAnywhere, remove for local
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CommandHandler("solo", solo))
    app.add_handler(CommandHandler("guess", guess_cmd))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.post_init = set_commands

    print("💣 Bomb Pass Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()