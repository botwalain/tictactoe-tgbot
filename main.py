import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import uuid
import json
import os
import random
import time
import threading
from datetime import datetime, timedelta
import sqlite3
from collections import defaultdict

# -------------------- BOT CONFIGURATION --------------------
BOT_TOKEN = ''  # Replace with your actual bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Admin Configuration
ADMIN_IDS = []  # Your admin ID

# --- Enhanced Constants ---
EMPTY = "⬜"
PLAYER_X = "❌"
PLAYER_O = "⭕"
WATERMARK = "\n\n*Made With 💗 By @IBMBotSupport*"
BOARD_SIZE = 3

# --- Enhanced Emojis for UI ---
EMOJI_MENU = "☰"
EMOJI_BACK = "⬅️"
EMOJI_REFRESH = "🔄"
EMOJI_RESIGN = "🏳️"
EMOJI_AI = "🤖"
EMOJI_FRIEND = "👥"
EMOJI_STATS = "📊"
EMOJI_LEADERBOARD = "🏆"
EMOJI_SETTINGS = "⚙️"
EMOJI_NAME = "✏️"
EMOJI_EASY = "🟢"
EMOJI_MEDIUM = "🟡"
EMOJI_HARD = "🔴"
EMOJI_IMPOSSIBLE = "💀"
EMOJI_REMATCH = "🔁"
EMOJI_DRAW = "🤝"
EMOJI_WIN = "🎉"
EMOJI_TOURNAMENT = "🏟️"
EMOJI_ACHIEVEMENTS = "🏅"
EMOJI_THEMES = "🎨"
EMOJI_SOUND = "🔊"
EMOJI_HISTORY = "📜"
EMOJI_CHALLENGE = "⚔️"
EMOJI_SPECTATE = "👁️"
EMOJI_HINT = "💡"
EMOJI_UNDO = "↩️"
EMOJI_TIMER = "⏱️"
EMOJI_CROWN = "👑"
EMOJI_TROPHY = "🏆"

# --- Game Themes ---
THEMES = {
    'classic': {'x': '❌', 'o': '⭕', 'empty': '⬜'},
    'animals': {'x': '🐱', 'o': '🐶', 'empty': '🟫'},
    'space': {'x': '🚀', 'o': '🛸', 'empty': '🌌'},
    'food': {'x': '🍕', 'o': '🍔', 'empty': '🍽️'},
    'sports': {'x': '⚽', 'o': '🏀', 'empty': '🏟️'},
    'nature': {'x': '🌞', 'o': '🌙', 'empty': '🌿'}
}

# --- In-memory Storage ---
games = {}
user_input_state = {}
tournaments = {}
spectators = defaultdict(set)
game_history = defaultdict(list)
quick_match_queue = []
online_users = set()

# -------------------- DATABASE SETUP --------------------
def init_database():
    conn = sqlite3.connect('tictactoe_advanced.db')
    cursor = conn.cursor()
    
    # Enhanced user stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            total_games INTEGER DEFAULT 0,
            ai_wins INTEGER DEFAULT 0,
            ai_losses INTEGER DEFAULT 0,
            tournament_wins INTEGER DEFAULT 0,
            achievements TEXT DEFAULT '[]',
            theme TEXT DEFAULT 'classic',
            sound_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            elo_rating INTEGER DEFAULT 1200,
            fastest_win INTEGER DEFAULT 0,
            perfect_games INTEGER DEFAULT 0
        )
    ''')
    
    # Game history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            player1_id INTEGER,
            player2_id INTEGER,
            winner_id INTEGER,
            game_mode TEXT,
            duration INTEGER,
            moves_count INTEGER,
            board_state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tournament table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT UNIQUE,
            name TEXT,
            creator_id INTEGER,
            status TEXT DEFAULT 'waiting',
            max_players INTEGER DEFAULT 8,
            current_players INTEGER DEFAULT 0,
            prize_pool TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            winner_id INTEGER,
            current_round INTEGER DEFAULT 1
        )
    ''')
    
    # Tournament participants table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT,
            user_id INTEGER,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            eliminated_at TIMESTAMP,
            final_position INTEGER,
            current_round INTEGER DEFAULT 1
        )
    ''')
    
    # Tournament matches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT,
            round_number INTEGER,
            match_number INTEGER,
            player1_id INTEGER,
            player2_id INTEGER,
            winner_id INTEGER,
            game_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# -------------------- DATABASE OPERATIONS --------------------
def get_user_stats(user_id):
    conn = sqlite3.connect('tictactoe_advanced.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        columns = [description[0] for description in cursor.description]
        user_data = dict(zip(columns, result))
        conn.close()
        return user_data
    
    conn.close()
    return None

def update_user_stats(user_id, **kwargs):
    conn = sqlite3.connect('tictactoe_advanced.db')
    cursor = conn.cursor()
    
    # Check if user exists
    if not get_user_stats(user_id):
        cursor.execute('''
            INSERT INTO user_stats (user_id, name) VALUES (?, ?)
        ''', (user_id, kwargs.get('name', 'Player')))
    
    # Update stats
    if kwargs:
        set_clause = ', '.join([f'{key} = ?' for key in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        cursor.execute(f'UPDATE user_stats SET {set_clause}, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', values)
    
    conn.commit()
    conn.close()

def save_game_history(game_data):
    conn = sqlite3.connect('tictactoe_advanced.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO game_history (game_id, player1_id, player2_id, winner_id, game_mode, duration, moves_count, board_state)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', game_data)
    conn.commit()
    conn.close()

def get_game_history(user_id, limit=10):
    conn = sqlite3.connect('tictactoe_advanced.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM game_history 
        WHERE player1_id = ? OR player2_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, user_id, limit))
    results = cursor.fetchall()
    conn.close()
    return results

# -------------------- ENHANCED AI LOGIC --------------------
class AdvancedAI:
    def __init__(self, difficulty='medium'):
        self.difficulty = difficulty
        self.move_history = []
    
    def get_move(self, board, player_symbol):
        if self.difficulty == 'easy':
            return self._random_move(board)
        elif self.difficulty == 'medium':
            return self._medium_move(board, player_symbol)
        elif self.difficulty == 'hard':
            return self._minimax_move(board, player_symbol)
        elif self.difficulty == 'impossible':
            return self._impossible_move(board, player_symbol)
    
    def _random_move(self, board):
        empty_cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if board[r][c] == EMPTY]
        return random.choice(empty_cells) if empty_cells else (-1, -1)
    
    def _medium_move(self, board, player_symbol):
        # 70% chance to play optimally, 30% random
        if random.random() < 0.7:
            return self._minimax_move(board, player_symbol)
        return self._random_move(board)
    
    def _minimax_move(self, board, player_symbol):
        opponent_symbol = PLAYER_X if player_symbol == PLAYER_O else PLAYER_O
        best_score = -float('inf')
        best_move = (-1, -1)
        
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] == EMPTY:
                    board[r][c] = player_symbol
                    score = self._minimax(board, 0, False, player_symbol, opponent_symbol)
                    board[r][c] = EMPTY
                    if score > best_score:
                        best_score = score
                        best_move = (r, c)
        
        return best_move
    
    def _impossible_move(self, board, player_symbol):
        # Perfect play with strategic opening moves
        move_count = sum(1 for row in board for cell in row if cell != EMPTY)
        
        # Opening strategy
        if move_count == 0:
            return (1, 1)  # Center
        elif move_count == 1:
            if board[1][1] == EMPTY:
                return (1, 1)  # Take center
            else:
                return (0, 0)  # Take corner
        
        return self._minimax_move(board, player_symbol)
    
    def _minimax(self, board, depth, is_maximizing, max_player, min_player):
        if self._check_win(board, max_player):
            return 10 - depth
        if self._check_win(board, min_player):
            return depth - 10
        if self._is_board_full(board):
            return 0
        
        if is_maximizing:
            best_score = -float('inf')
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if board[r][c] == EMPTY:
                        board[r][c] = max_player
                        score = self._minimax(board, depth + 1, False, max_player, min_player)
                        board[r][c] = EMPTY
                        best_score = max(score, best_score)
            return best_score
        else:
            best_score = float('inf')
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if board[r][c] == EMPTY:
                        board[r][c] = min_player
                        score = self._minimax(board, depth + 1, True, max_player, min_player)
                        board[r][c] = EMPTY
                        best_score = min(score, best_score)
            return best_score
    
    def _check_win(self, board, player):
        # Check rows, columns, and diagonals
        for i in range(BOARD_SIZE):
            if all(board[i][j] == player for j in range(BOARD_SIZE)):
                return True
            if all(board[j][i] == player for j in range(BOARD_SIZE)):
                return True
        
        if all(board[i][i] == player for i in range(BOARD_SIZE)):
            return True
        if all(board[i][BOARD_SIZE - 1 - i] == player for i in range(BOARD_SIZE)):
            return True
        
        return False
    
    def _is_board_full(self, board):
        return all(cell != EMPTY for row in board for cell in row)

# -------------------- TOURNAMENT SYSTEM --------------------
class TournamentManager:
    def __init__(self):
        self.tournaments = {}
    
    def create_tournament(self, creator_id, name, max_players=8, prize_pool="Glory"):
        tournament_id = str(uuid.uuid4())[:8]
        
        conn = sqlite3.connect('tictactoe_advanced.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tournaments (tournament_id, name, creator_id, max_players, prize_pool, current_players)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (tournament_id, name, creator_id, max_players, prize_pool, 1))
            
            cursor.execute('''
                INSERT INTO tournament_participants (tournament_id, user_id)
                VALUES (?, ?)
            ''', (tournament_id, creator_id))
            
            conn.commit()
            
            self.tournaments[tournament_id] = {
                'id': tournament_id,
                'name': name,
                'creator': creator_id,
                'participants': [creator_id],
                'status': 'waiting',
                'max_players': max_players,
                'prize_pool': prize_pool,
                'bracket': {},
                'current_round': 1,
                'matches': {},
                'created_at': time.time()
            }
            
            return tournament_id
        except Exception as e:
            print(f"Error creating tournament: {e}")
            return None
        finally:
            conn.close()
    
    def join_tournament(self, tournament_id, user_id):
        if tournament_id not in self.tournaments:
            return False, "Tournament not found"
        
        tournament = self.tournaments[tournament_id]
        
        if tournament['status'] != 'waiting':
            return False, "Tournament has already started"
        
        if len(tournament['participants']) >= tournament['max_players']:
            return False, "Tournament is full"
        
        if user_id in tournament['participants']:
            return False, "You're already in this tournament"
        
        tournament['participants'].append(user_id)
        
        conn = sqlite3.connect('tictactoe_advanced.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tournament_participants (tournament_id, user_id)
                VALUES (?, ?)
            ''', (tournament_id, user_id))
            
            cursor.execute('''
                UPDATE tournaments SET current_players = ? WHERE tournament_id = ?
            ''', (len(tournament['participants']), tournament_id))
            
            conn.commit()
            return True, "Successfully joined tournament"
        except Exception as e:
            print(f"Error joining tournament: {e}")
            return False, "Database error"
        finally:
            conn.close()
    
    def start_tournament(self, tournament_id, starter_id):
        if tournament_id not in self.tournaments:
            return False, "Tournament not found"
        
        tournament = self.tournaments[tournament_id]
        
        if tournament['creator'] != starter_id and starter_id not in ADMIN_IDS:
            return False, "Only the creator or admin can start the tournament"
        
        if len(tournament['participants']) < 2:
            return False, "Need at least 2 players to start"
        
        tournament['status'] = 'active'
        tournament['bracket'] = self._create_bracket(tournament['participants'])
        
        conn = sqlite3.connect('tictactoe_advanced.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE tournaments SET status = 'active', started_at = CURRENT_TIMESTAMP
                WHERE tournament_id = ?
            ''', (tournament_id,))
            
            # Create first round matches
            self._create_tournament_matches(tournament_id, tournament['bracket'])
            
            conn.commit()
            return True, "Tournament started successfully"
        except Exception as e:
            print(f"Error starting tournament: {e}")
            return False, "Database error"
        finally:
            conn.close()
    
    def _create_bracket(self, participants):
        random.shuffle(participants)
        bracket = {}
        round_num = 1
        current_participants = participants[:]
        
        while len(current_participants) > 1:
            bracket[round_num] = []
            next_round = []
            
            for i in range(0, len(current_participants), 2):
                if i + 1 < len(current_participants):
                    match = {
                        'player1': current_participants[i],
                        'player2': current_participants[i + 1],
                        'winner': None,
                        'game_id': None,
                        'status': 'pending'
                    }
                    bracket[round_num].append(match)
                else:
                    # Bye - player advances automatically
                    next_round.append(current_participants[i])
            
            current_participants = next_round
            round_num += 1
        
        return bracket
    
    def _create_tournament_matches(self, tournament_id, bracket):
        conn = sqlite3.connect('tictactoe_advanced.db')
        cursor = conn.cursor()
        
        try:
            for round_num, matches in bracket.items():
                for match_num, match in enumerate(matches):
                    cursor.execute('''
                        INSERT INTO tournament_matches 
                        (tournament_id, round_number, match_number, player1_id, player2_id, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (tournament_id, round_num, match_num, match['player1'], match['player2'], 'pending'))
            
            conn.commit()
        except Exception as e:
            print(f"Error creating tournament matches: {e}")
        finally:
            conn.close()
    
    def get_tournament_info(self, tournament_id):
        if tournament_id in self.tournaments:
            return self.tournaments[tournament_id]
        
        # Try to load from database
        conn = sqlite3.connect('tictactoe_advanced.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM tournaments WHERE tournament_id = ?', (tournament_id,))
            tournament_data = cursor.fetchone()
            
            if tournament_data:
                cursor.execute('SELECT user_id FROM tournament_participants WHERE tournament_id = ?', (tournament_id,))
                participants = [row[0] for row in cursor.fetchall()]
                
                tournament_info = {
                    'id': tournament_data[1],
                    'name': tournament_data[2],
                    'creator': tournament_data[3],
                    'status': tournament_data[4],
                    'max_players': tournament_data[5],
                    'participants': participants,
                    'prize_pool': tournament_data[7] or "Glory",
                    'current_round': tournament_data[11] or 1
                }
                
                return tournament_info
        except Exception as e:
            print(f"Error getting tournament info: {e}")
        finally:
            conn.close()
        
        return None
    
    def get_active_tournaments(self):
        conn = sqlite3.connect('tictactoe_advanced.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT tournament_id, name, creator_id, status, current_players, max_players, prize_pool
                FROM tournaments 
                WHERE status IN ('waiting', 'active')
                ORDER BY created_at DESC
            ''')
            
            tournaments = []
            for row in cursor.fetchall():
                tournaments.append({
                    'id': row[0],
                    'name': row[1],
                    'creator': row[2],
                    'status': row[3],
                    'current_players': row[4],
                    'max_players': row[5],
                    'prize_pool': row[6] or "Glory"
                })
            
            return tournaments
        except Exception as e:
            print(f"Error getting active tournaments: {e}")
            return []
        finally:
            conn.close()
    
    def advance_tournament(self, tournament_id, match_winner_id):
        """Advance a player to the next round"""
        if tournament_id not in self.tournaments:
            return False
        
        tournament = self.tournaments[tournament_id]
        current_round = tournament['current_round']
        
        # Update bracket with winner
        for match in tournament['bracket'].get(current_round, []):
            if match['player1'] == match_winner_id or match['player2'] == match_winner_id:
                match['winner'] = match_winner_id
                match['status'] = 'completed'
                break
        
        # Check if round is complete
        round_matches = tournament['bracket'].get(current_round, [])
        if all(match['status'] == 'completed' for match in round_matches):
            # Advance to next round
            winners = [match['winner'] for match in round_matches if match['winner']]
            
            if len(winners) == 1:
                # Tournament complete
                tournament['status'] = 'completed'
                tournament['winner'] = winners[0]
                
                # Update database
                conn = sqlite3.connect('tictactoe_advanced.db')
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        UPDATE tournaments 
                        SET status = 'completed', winner_id = ?, finished_at = CURRENT_TIMESTAMP
                        WHERE tournament_id = ?
                    ''', (winners[0], tournament_id))
                    
                    # Update winner stats
                    stats = get_user_stats(winners[0]) or {}
                    update_user_stats(winners[0], 
                        tournament_wins=stats.get('tournament_wins', 0) + 1)
                    
                    conn.commit()
                except Exception as e:
                    print(f"Error completing tournament: {e}")
                finally:
                    conn.close()
                
                return True, f"Tournament completed! Winner: {get_user_name(winners[0])}"
            else:
                # Create next round
                tournament['current_round'] += 1
                next_round_bracket = self._create_next_round(winners)
                tournament['bracket'][tournament['current_round']] = next_round_bracket
                
                return True, f"Round {current_round} completed! Starting round {tournament['current_round']}"
        
        return True, "Match completed"
    
    def _create_next_round(self, winners):
        """Create matches for the next round"""
        matches = []
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                match = {
                    'player1': winners[i],
                    'player2': winners[i + 1],
                    'winner': None,
                    'game_id': None,
                    'status': 'pending'
                }
                matches.append(match)
        return matches

tournament_manager = TournamentManager()

# -------------------- QUICK MATCH SYSTEM --------------------
def add_to_quick_match_queue(user_id):
    if user_id not in quick_match_queue:
        quick_match_queue.append(user_id)
        return True
    return False

def remove_from_quick_match_queue(user_id):
    if user_id in quick_match_queue:
        quick_match_queue.remove(user_id)
        return True
    return False

def find_quick_match(user_id):
    if len(quick_match_queue) >= 1:  # Changed from >= 2 to >= 1
        # Find opponent from queue (excluding the requesting user)
        available_opponents = [uid for uid in quick_match_queue if uid != user_id]
        
        if available_opponents:
            opponent_id = available_opponents[0]
            # Remove both players from queue
            remove_from_quick_match_queue(opponent_id)
            remove_from_quick_match_queue(user_id)
            return opponent_id
    return None

# -------------------- SPECTATOR SYSTEM --------------------
def add_spectator(game_id, user_id):
    if game_id in games:
        spectators[game_id].add(user_id)
        return True
    return False

def remove_spectator(game_id, user_id):
    if game_id in spectators:
        spectators[game_id].discard(user_id)
        return True
    return False

def get_spectatable_games():
    active_games = []
    for game_id, game in games.items():
        if not game.get('is_over', False) and game.get('game_mode') != 'vs_ai':
            # Only show games with 2 human players
            human_players = [p for p in game['players'] if p != bot.get_me().id]
            if len(human_players) == 2:
                active_games.append({
                    'id': game_id,
                    'players': [get_user_name(p) for p in human_players],
                    'spectators': len(spectators.get(game_id, set())),
                    'mode': game.get('game_mode', 'unknown')
                })
    return active_games

def create_spectator_board_markup(game, spectator_id):
    """Create a non-interactive board for spectators"""
    markup = InlineKeyboardMarkup(row_width=BOARD_SIZE)
    
    # Board display (non-interactive)
    for r in range(BOARD_SIZE):
        row_buttons = []
        for c in range(BOARD_SIZE):
            cell = game['board'][r][c]
            if cell == EMPTY:
                cell = game.get('empty_symbol', '⬜')
            # Non-interactive button (same callback but will be ignored)
            row_buttons.append(InlineKeyboardButton(cell, callback_data=f"spectate_view_{game.get('game_id', 'unknown')}"))
        markup.row(*row_buttons)
    
    # Spectator controls
    controls = [
        InlineKeyboardButton(f"🔄 Refresh", callback_data=f"spectate_refresh_{game.get('game_id', 'unknown')}"),
        InlineKeyboardButton(f"❌ Stop Watching", callback_data=f"stop_spectate_{game.get('game_id', 'unknown')}")
    ]
    markup.row(*controls)
    
    return markup

# -------------------- ENHANCED UI FUNCTIONS --------------------
def get_user_name(user_id):
    if user_id == bot.get_me().id:
        return "AI"
    
    stats = get_user_stats(user_id)
    if stats and stats.get('name'):
        return stats['name']
    
    try:
        user = bot.get_chat(user_id)
        return user.first_name if user.first_name else "Player"
    except:
        return "Player"

def safe_edit_message(chat_id, message_id, text, markup=None, parse_mode=None):
    """Safely edit message with error handling"""
    try:
        # Get current message to compare
        try:
            current_msg = bot.get_message(chat_id, message_id)
            if current_msg.text == text and current_msg.reply_markup == markup:
                return True  # No change needed
        except:
            pass
        
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode=parse_mode)
        return True
    except Exception as e:
        if "message is not modified" in str(e):
            return True  # Message is already correct
        elif "can't parse entities" in str(e):
            # Try without markdown
            try:
                # Remove markdown formatting
                clean_text = text.replace('*', '').replace('_', '').replace('`', '')
                bot.edit_message_text(clean_text, chat_id, message_id, reply_markup=markup)
                return True
            except:
                pass
        print(f"Error editing message: {e}")
        return False

def create_enhanced_board_markup(game):
    markup = InlineKeyboardMarkup(row_width=BOARD_SIZE)
    
    # Get game_id safely
    game_id = game.get('game_id')
    if not game_id:
        # Try to find game_id from games dict
        for gid, g in games.items():
            if g == game:
                game_id = gid
                game['game_id'] = gid
                break
        if not game_id:
            game_id = 'unknown'
    
    # Board buttons
    for r in range(BOARD_SIZE):
        row_buttons = []
        for c in range(BOARD_SIZE):
            cell = game['board'][r][c]
            if cell == EMPTY:
                cell = game.get('empty_symbol', '⬜')
            row_buttons.append(InlineKeyboardButton(cell, callback_data=f"move_{game_id}_{r}_{c}"))
        markup.row(*row_buttons)
    
    # Game controls
    controls = []
    if not game.get('is_over', False):
        controls.extend([
            InlineKeyboardButton(f"{EMOJI_HINT} Hint", callback_data=f"hint_{game_id}"),
            InlineKeyboardButton(f"{EMOJI_UNDO} Undo", callback_data=f"undo_{game_id}")
        ])
    
    controls.extend([
        InlineKeyboardButton(f"{EMOJI_RESIGN} Resign", callback_data=f"resign_{game_id}"),
        InlineKeyboardButton(f"{EMOJI_MENU} Menu", callback_data=f"game_menu_{game_id}")
    ])
    
    # Add controls in rows of 2
    for i in range(0, len(controls), 2):
        markup.row(*controls[i:i+2])
    
    return markup

def send_enhanced_main_menu(chat_id, message_id=None):
    user_stats = get_user_stats(chat_id)
    if not user_stats:
        update_user_stats(chat_id, name=get_user_name(chat_id))
        user_stats = get_user_stats(chat_id)
    
    # Create safe text without problematic characters
    name = user_stats.get('name', 'Player')
    wins = user_stats.get('wins', 0)
    total = user_stats.get('total_games', 0)
    streak = user_stats.get('current_streak', 0)
    
    text = f"🎮 Advanced Tic-Tac-Toe\n\nWelcome back, {name}!\n\n"
    text += f"🏆 Wins: {wins} | 📊 Games: {total}\n"
    text += f"⚡ Current Streak: {streak}"
    
    # Add admin indicator
    if chat_id in ADMIN_IDS:
        text += f"\n\n{EMOJI_CROWN} Admin Access Enabled"
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"{EMOJI_AI} vs AI", callback_data="vs_ai_menu"),
        InlineKeyboardButton(f"{EMOJI_FRIEND} vs Friend", callback_data="vs_friend_menu")
    )
    markup.add(
        InlineKeyboardButton(f"{EMOJI_TOURNAMENT} Tournament", callback_data="tournament_menu"),
        InlineKeyboardButton(f"{EMOJI_CHALLENGE} Quick Match", callback_data="quick_match")
    )
    markup.add(
        InlineKeyboardButton(f"{EMOJI_STATS} Statistics", callback_data="stats_menu"),
        InlineKeyboardButton(f"{EMOJI_ACHIEVEMENTS} Achievements", callback_data="achievements")
    )
    markup.add(
        InlineKeyboardButton(f"{EMOJI_HISTORY} Game History", callback_data="history"),
        InlineKeyboardButton(f"{EMOJI_SPECTATE} Spectate Games", callback_data="spectate")
    )
    markup.add(
        InlineKeyboardButton(f"{EMOJI_SETTINGS} Settings", callback_data="settings_menu")
    )
    
    try:
        if message_id:
            safe_edit_message(chat_id, message_id, text + WATERMARK, markup)
        else:
            bot.send_message(chat_id, text + WATERMARK, reply_markup=markup)
    except Exception as e:
        print(f"Error in send_enhanced_main_menu: {e}")

# -------------------- BOT COMMAND HANDLERS --------------------
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    user_id = message.from_user.id
    online_users.add(user_id)
    
    if message.chat.type != 'private':
        bot.reply_to(message, "🎮 Start a private chat with me to access the full game menu!")
        return

    # Check if this is a friend game invitation
    payload = message.text.split(' ')[1] if ' ' in message.text else None
    if payload and payload in games:
        join_friend_game(payload, message.from_user)
        return

    # Initialize user stats
    if not get_user_stats(user_id):
        update_user_stats(user_id, name=message.from_user.first_name or "Player")
    
    send_enhanced_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: user_input_state.get(message.from_user.id, {}).get('state') == 'tournament_name')
def handle_tournament_name(message):
    user_id = message.from_user.id
    tournament_name = message.text.strip()
    
    if len(tournament_name) < 3:
        bot.reply_to(message, "❌ Tournament name must be at least 3 characters long. Please try again:")
        return
    
    if len(tournament_name) > 50:
        bot.reply_to(message, "❌ Tournament name must be less than 50 characters. Please try again:")
        return
    
    # Store tournament name and ask for max players
    user_input_state[user_id]['tournament_name'] = tournament_name
    user_input_state[user_id]['state'] = 'tournament_players'
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("4 Players", callback_data="tournament_players_4"),
        InlineKeyboardButton("8 Players", callback_data="tournament_players_8")
    )
    markup.add(
        InlineKeyboardButton("16 Players", callback_data="tournament_players_16"),
        InlineKeyboardButton("32 Players", callback_data="tournament_players_32")
    )
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="tournament_menu"))
    
    bot.reply_to(message, f"🏟️ Tournament: '{tournament_name}'\n\nChoose maximum number of players:", reply_markup=markup)

@bot.message_handler(func=lambda message: user_input_state.get(message.from_user.id, {}).get('state') == 'tournament_prize')
def handle_tournament_prize(message):
    user_id = message.from_user.id
    prize_pool = message.text.strip()
    
    if len(prize_pool) > 100:
        bot.reply_to(message, "❌ Prize description must be less than 100 characters. Please try again:")
        return
    
    # Get stored data
    tournament_data = user_input_state[user_id]
    tournament_name = tournament_data['tournament_name']
    max_players = tournament_data['max_players']
    
    # Create tournament
    tournament_id = tournament_manager.create_tournament(
        creator_id=user_id,
        name=tournament_name,
        max_players=max_players,
        prize_pool=prize_pool
    )
    
    if tournament_id:
        # Clear input state
        del user_input_state[user_id]
        
        # Send success message
        text = f"🎉 Tournament Created Successfully!\n\n"
        text += f"🏟️ Name: {tournament_name}\n"
        text += f"👥 Max Players: {max_players}\n"
        text += f"🏆 Prize: {prize_pool}\n"
        text += f"🆔 ID: {tournament_id}\n\n"
        text += f"Share this tournament ID with friends to join!"
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(f"📋 View Tournament", callback_data=f"view_tournament_{tournament_id}"),
            InlineKeyboardButton(f"🚀 Start Tournament", callback_data=f"start_tournament_{tournament_id}")
        )
        markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Tournament Menu", callback_data="tournament_menu"))
        
        bot.reply_to(message, text + WATERMARK, reply_markup=markup)
    else:
        bot.reply_to(message, "❌ Failed to create tournament. Please try again.")
        del user_input_state[user_id]

@bot.message_handler(func=lambda message: user_input_state.get(message.from_user.id, {}).get('state') == 'join_tournament')
def handle_join_tournament_id(message):
    user_id = message.from_user.id
    tournament_id = message.text.strip()
    
    success, msg = tournament_manager.join_tournament(tournament_id, user_id)
    
    if success:
        tournament = tournament_manager.get_tournament_info(tournament_id)
        if tournament:
            text = f"✅ {msg}\n\n"
            text += f"🏟️ Tournament: {tournament['name']}\n"
            text += f"👥 Players: {len(tournament['participants'])}/{tournament['max_players']}\n"
            text += f"📊 Status: {tournament['status'].title()}"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(f"📋 View Tournament", callback_data=f"view_tournament_{tournament_id}"))
            markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Tournament Menu", callback_data="tournament_menu"))
            
            bot.reply_to(message, text + WATERMARK, reply_markup=markup)
        else:
            bot.reply_to(message, "✅ Joined tournament successfully!")
    else:
        bot.reply_to(message, f"❌ {msg}")
    
    # Clear input state
    if user_id in user_input_state:
        del user_input_state[user_id]

def join_friend_game(game_id, p2_user):
    if game_id not in games:
        bot.send_message(p2_user.id, "❌ This game invitation has expired!")
        return
    
    game = games[game_id]
    p1_id = game['players'][0]
    p2_id = p2_user.id

    if p1_id == p2_id:
        bot.send_message(p2_id, "❌ You can't accept your own invitation!")
        return

    if len(game['players']) > 1:
        bot.send_message(p2_id, "❌ This game is already full!")
        return

    # Initialize second player
    if not get_user_stats(p2_id):
        update_user_stats(p2_id, name=p2_user.first_name or "Player")
    
    # Complete game setup
    game['players'].append(p2_id)
    game['player_symbols'] = {p1_id: PLAYER_X, p2_id: PLAYER_O}
    game['board'] = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    game['turn'] = p1_id
    game['game_mode'] = 'friend_dm'
    game['move_history'] = []
    game['hints_used'] = {p1_id: 0, p2_id: 0}
    game['empty_symbol'] = '⬜'
    game['is_over'] = False
    game['game_id'] = game_id  # Ensure game_id is set

    # Update P1's message
    try:
        safe_edit_message(p1_id, game['message_ids'][p1_id], 
                         f"🎮 Your opponent {get_user_name(p2_id)} has joined! Game starting..." + WATERMARK)
    except:
        pass

    # Send game board to P2
    try:
        p2_message = bot.send_message(p2_id, "🎮 You joined the game! Starting now..." + WATERMARK)
        game['message_ids'][p2_id] = p2_message.message_id
    except Exception as e:
        print(f"Error sending message to P2: {e}")

    # Update both players with the game board
    update_game_state(game_id)

def update_game_state(game_id):
    if game_id not in games:
        return
    
    game = games[game_id]
    markup = create_enhanced_board_markup(game)

    if game['game_mode'] == 'group':
        text = get_game_status_text(game) + WATERMARK
        try:
            safe_edit_message(game['chat_id'], game['message_id'], text, markup)
        except Exception as e:
            print(f"Error updating group game: {e}")
    else:  # DM vs AI or DM vs Friend
        for p_id in game['players']:
            if p_id == bot.get_me().id:
                continue
            text = get_game_status_text(game, p_id) + WATERMARK
            try:
                safe_edit_message(p_id, game['message_ids'][p_id], text, markup)
            except Exception as e:
                print(f"Error updating DM game for player {p_id}: {e}")
    
    # Update spectators
    if game_id in spectators:
        spectator_markup = create_spectator_board_markup(game, None)
        for spectator_id in spectators[game_id]:
            try:
                spectator_text = get_spectator_status_text(game) + WATERMARK
                safe_edit_message(spectator_id, game.get('spectator_messages', {}).get(spectator_id), 
                                spectator_text, spectator_markup)
            except Exception as e:
                print(f"Error updating spectator {spectator_id}: {e}")

def get_spectator_status_text(game):
    """Get status text for spectators"""
    p1_id, p2_id = game['players']
    p1_name = get_user_name(p1_id)
    p2_name = get_user_name(p2_id)
    
    header = f"👁️ Spectating: {p1_name} ({PLAYER_X}) vs {p2_name} ({PLAYER_O})\n"
    
    if game.get('is_over'):
        return header + game.get('end_message', "Game Over!")
    
    current_player_name = get_user_name(game['turn'])
    status = f"🎯 {current_player_name}'s turn"
    
    # Add spectator count
    spectator_count = len(spectators.get(game.get('game_id', ''), set()))
    if spectator_count > 1:
        status += f"\n👁️ {spectator_count} watching"
    
    return header + status

def get_game_status_text(game, perspective_of_player_id=None):
    p1_id, p2_id = game['players']

    if game['game_mode'] == 'group':
        p1_mention = f"[{get_user_name(p1_id)}](tg://user?id={p1_id})"
        p2_mention = f"[{get_user_name(p2_id)}](tg://user?id={p2_id})"
        header = f"{p1_mention} ({PLAYER_X}) vs {p2_mention} ({PLAYER_O})\n"
        if game.get('is_over'):
            return header + game.get('end_message', "Game Over!")
        turn_mention = f"[{get_user_name(game['turn'])}](tg://user?id={game['turn']})"
        status = f"🎯 It's {turn_mention}'s turn."
    else:  # DM or AI game
        you_id = perspective_of_player_id
        opponent_id = p2_id if you_id == p1_id else p1_id
        you_symbol = game['player_symbols'][you_id]
        opponent_symbol = game['player_symbols'][opponent_id]
        opponent_name = "AI" if opponent_id == bot.get_me().id else get_user_name(opponent_id)
        header = f"You ({you_symbol}) vs {opponent_name} ({opponent_symbol})\n"
        
        if game.get('is_over'):
            return header + game.get('end_message', "Game Over!")
        
        status = f"🎯 Your turn!" if game['turn'] == you_id else f"⏳ Waiting for {opponent_name}..."

    # Add spectator count if applicable
    game_id = game.get('game_id', '')
    if game_id in spectators and len(spectators[game_id]) > 0:
        status += f"\n👁️ {len(spectators[game_id])} watching"

    return header + status

def end_game(game_id, winner_id=None, is_draw=False, resigned_id=None):
    if game_id not in games or games[game_id].get('is_over'):
        return
    
    game = games[game_id]
    game['is_over'] = True
    
    p1_id, p2_id = game['players']
    
    # Save game to history
    duration = int(time.time() - game.get('start_time', time.time()))
    moves_count = len(game.get('move_history', []))
    board_state = json.dumps(game['board'])
    
    game_data = (
        game_id,
        p1_id,
        p2_id,
        winner_id,
        game.get('game_mode', 'unknown'),
        duration,
        moves_count,
        board_state
    )
    
    try:
        save_game_history(game_data)
    except Exception as e:
        print(f"Error saving game history: {e}")
    
    # Update user stats
    if resigned_id:
        winner_id = p2_id if resigned_id == p1_id else p1_id
        loser_id = resigned_id
        winner_name = "AI" if winner_id == bot.get_me().id else get_user_name(winner_id)
        loser_name = "AI" if loser_id == bot.get_me().id else get_user_name(loser_id)
        end_message = f"{EMOJI_RESIGN} {loser_name} resigned! {EMOJI_WIN} {winner_name} wins!"
        
        if winner_id != bot.get_me().id:
            stats = get_user_stats(winner_id) or {}
            update_user_stats(winner_id, 
                wins=stats.get('wins', 0) + 1,
                total_games=stats.get('total_games', 0) + 1,
                current_streak=stats.get('current_streak', 0) + 1,
                longest_streak=max(stats.get('longest_streak', 0), stats.get('current_streak', 0) + 1)
            )
        if loser_id != bot.get_me().id:
            stats = get_user_stats(loser_id) or {}
            update_user_stats(loser_id,
                losses=stats.get('losses', 0) + 1,
                total_games=stats.get('total_games', 0) + 1,
                current_streak=0
            )
            
    elif is_draw:
        end_message = f"{EMOJI_DRAW} It's a draw! Well played!"
        for player_id in [p1_id, p2_id]:
            if player_id != bot.get_me().id:
                stats = get_user_stats(player_id) or {}
                update_user_stats(player_id,
                    draws=stats.get('draws', 0) + 1,
                    total_games=stats.get('total_games', 0) + 1
                )
            
    elif winner_id:
        loser_id = p1_id if winner_id == p2_id else p2_id
        winner_name = "AI" if winner_id == bot.get_me().id else get_user_name(winner_id)
        end_message = f"{EMOJI_WIN} {winner_name} wins!"
        
        if winner_id != bot.get_me().id:
            stats = get_user_stats(winner_id) or {}
            update_user_stats(winner_id,
                wins=stats.get('wins', 0) + 1,
                total_games=stats.get('total_games', 0) + 1,
                current_streak=stats.get('current_streak', 0) + 1,
                longest_streak=max(stats.get('longest_streak', 0), stats.get('current_streak', 0) + 1)
            )
        if loser_id != bot.get_me().id:
            stats = get_user_stats(loser_id) or {}
            update_user_stats(loser_id,
                losses=stats.get('losses', 0) + 1,
                total_games=stats.get('total_games', 0) + 1,
                current_streak=0
            )
    else:
        end_message = "Game Over!"

    game['end_message'] = end_message
    
    # Check if this is a tournament game
    tournament_id = game.get('tournament_id')
    if tournament_id and winner_id:
        success, msg = tournament_manager.advance_tournament(tournament_id, winner_id)
        if success:
            end_message += f"\n\n🏟️ Tournament: {msg}"
    
    # Create end game markup
    if game['game_mode'] != 'group':
        if game['game_mode'] == 'vs_ai':
            difficulty = game.get('difficulty', 'easy')
            rematch_data = f"rematch_ai_{difficulty}"
        else:
            rematch_data = "vs_friend_menu"
        
        rematch_button = InlineKeyboardButton(f"{EMOJI_REMATCH} Play Again", callback_data=rematch_data)
        main_menu_button = InlineKeyboardButton(f"{EMOJI_BACK} Main Menu", callback_data="main_menu")
        end_markup = InlineKeyboardMarkup(row_width=2).add(rematch_button, main_menu_button)
    else:
        end_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(f"{EMOJI_REFRESH} New Game", callback_data="new_group_game")
        )

    # Send final update
    if game['game_mode'] == 'group':
        text = get_game_status_text(game) + WATERMARK
        try:
            safe_edit_message(game['chat_id'], game['message_id'], text, end_markup)
        except Exception as e:
            print(f"Error in end_game group: {e}")
    else:
        for p_id in game['players']:
            if p_id == bot.get_me().id:
                continue
            text = get_game_status_text(game, p_id) + WATERMARK
            try:
                safe_edit_message(p_id, game['message_ids'][p_id], text, end_markup)
            except Exception as e:
                print(f"Error in end_game DM: {e}")

    # Update spectators with final result
    if game_id in spectators:
        final_spectator_text = get_spectator_status_text(game) + WATERMARK
        spectator_markup = InlineKeyboardMarkup()
        spectator_markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Spectate Menu", callback_data="spectate"))
        
        for spectator_id in spectators[game_id]:
            try:
                safe_edit_message(spectator_id, game.get('spectator_messages', {}).get(spectator_id), 
                                final_spectator_text, spectator_markup)
            except Exception as e:
                print(f"Error updating final spectator {spectator_id}: {e}")

    # Clean up
    if game_id in games:
        del games[game_id]
    if game_id in spectators:
        del spectators[game_id]

# -------------------- ENHANCED CALLBACK HANDLER --------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_enhanced_callback(call):
    user_id = call.from_user.id
    data_parts = call.data.split('_')
    action = data_parts[0]
    
    try:
        # Main Menu Navigation
        if action == 'main' and len(data_parts) > 1 and data_parts[1] == 'menu':
            send_enhanced_main_menu(user_id, call.message.message_id)
            bot.answer_callback_query(call.id)
        
        # VS AI Menu
        elif action == 'vs' and len(data_parts) > 2 and data_parts[1] == 'ai' and data_parts[2] == 'menu':
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton(f"{EMOJI_EASY} Easy", callback_data="ai_easy"),
                InlineKeyboardButton(f"{EMOJI_MEDIUM} Medium", callback_data="ai_medium")
            )
            markup.add(
                InlineKeyboardButton(f"{EMOJI_HARD} Hard", callback_data="ai_hard"),
                InlineKeyboardButton(f"{EMOJI_IMPOSSIBLE} Impossible", callback_data="ai_impossible")
            )
            markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu"))
            
            text = "🤖 Choose AI Difficulty\n\n"
            text += "🟢 Easy - Random moves\n"
            text += "🟡 Medium - Sometimes smart\n"
            text += "🔴 Hard - Always optimal\n"
            text += "💀 Impossible - Perfect play"
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # VS Friend Menu
        elif action == 'vs' and len(data_parts) > 2 and data_parts[1] == 'friend' and data_parts[2] == 'menu':
            game_id = str(uuid.uuid4())[:8]
            games[game_id] = {
                'game_id': game_id,
                'players': [user_id],
                'message_ids': {user_id: call.message.message_id},
                'game_mode': 'friend_dm',
                'created_at': time.time(),
                'start_time': time.time()
            }
            
            bot_username = bot.get_me().username
            share_link = f"https://t.me/{bot_username}?start={game_id}"
            
            text = f"👥 Waiting for a Friend...\n\n"
            text += f"Share this link with a friend to play:\n"
            text += f"`{share_link}`\n\n"
            text += f"⏰ This invitation expires in 10 minutes."
            
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(f"{EMOJI_REFRESH} New Invitation", callback_data="vs_friend_menu"),
                InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu")
            )
            
            safe_edit_message(user_id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id, "🔗 Invitation created! Share the link with a friend.")
        
        # AI Difficulty Selection
        elif action == 'ai':
            if len(data_parts) > 1:
                difficulty = data_parts[1]
                game_id = str(uuid.uuid4())[:8]
                
                games[game_id] = {
                    'game_id': game_id,
                    'chat_id': user_id,
                    'message_ids': {user_id: call.message.message_id},
                    'players': [user_id, bot.get_me().id],
                    'player_symbols': {user_id: PLAYER_X, bot.get_me().id: PLAYER_O},
                    'board': [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)],
                    'turn': user_id,
                    'is_over': False,
                    'game_mode': 'vs_ai',
                    'difficulty': difficulty,
                    'move_history': [],
                    'hints_used': {user_id: 0},
                    'empty_symbol': '⬜',
                    'created_at': time.time(),
                    'start_time': time.time()
                }
                
                bot.answer_callback_query(call.id, f"🤖 Started game vs {difficulty.title()} AI!")
                update_game_state(game_id)
        
        # Rematch AI
        elif action == 'rematch' and len(data_parts) > 2 and data_parts[1] == 'ai':
            difficulty = data_parts[2]
            game_id = str(uuid.uuid4())[:8]
            
            games[game_id] = {
                'game_id': game_id,
                'chat_id': user_id,
                'message_ids': {user_id: call.message.message_id},
                'players': [user_id, bot.get_me().id],
                'player_symbols': {user_id: PLAYER_X, bot.get_me().id: PLAYER_O},
                'board': [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)],
                'turn': user_id,
                'is_over': False,
                'game_mode': 'vs_ai',
                'difficulty': difficulty,
                'move_history': [],
                'hints_used': {user_id: 0},
                'empty_symbol': '⬜',
                'created_at': time.time(),
                'start_time': time.time()
            }
            
            bot.answer_callback_query(call.id, f"🔁 New game vs {difficulty.title()} AI!")
            update_game_state(game_id)
        
        # Game Moves
        elif action == 'move':
            game_id = data_parts[1]
            r, c = int(data_parts[2]), int(data_parts[3])
            
            if game_id not in games:
                bot.answer_callback_query(call.id, "❌ This game has ended!", show_alert=True)
                return

            game = games[game_id]
            if user_id != game['turn']:
                bot.answer_callback_query(call.id, "❌ It's not your turn!")
                return
            if game['board'][r][c] != EMPTY:
                bot.answer_callback_query(call.id, "❌ This spot is already taken!")
                return

            # Make the move
            game['board'][r][c] = game['player_symbols'][user_id]
            game.setdefault('move_history', []).append((user_id, r, c, time.time()))
            
            # Check for win
            if check_win(game['board'], game['player_symbols'][user_id]):
                end_game(game_id, winner_id=user_id)
                bot.answer_callback_query(call.id, "🎉 You won!")
                return
            
            # Check for draw
            if is_board_full(game['board']):
                end_game(game_id, is_draw=True)
                bot.answer_callback_query(call.id, "🤝 It's a draw!")
                return

            # Switch turn
            game['turn'] = game['players'][1] if user_id == game['players'][0] else game['players'][0]

            # Handle AI move if it's an AI game
            if game['game_mode'] == 'vs_ai' and game['turn'] == bot.get_me().id:
                difficulty = game.get('difficulty', 'easy')
                ai = AdvancedAI(difficulty)
                ai_move = ai.get_move(game['board'], PLAYER_O)
                
                if ai_move != (-1, -1):
                    game['board'][ai_move[0]][ai_move[1]] = PLAYER_O
                    game['move_history'].append(('AI', ai_move[0], ai_move[1], time.time()))

                    if check_win(game['board'], PLAYER_O):
                        end_game(game_id, winner_id=bot.get_me().id)
                        bot.answer_callback_query(call.id, "🤖 AI wins!")
                        return
                    elif is_board_full(game['board']):
                        end_game(game_id, is_draw=True)
                        bot.answer_callback_query(call.id, "🤝 It's a draw!")
                        return
                    else:
                        game['turn'] = user_id

            update_game_state(game_id)
            bot.answer_callback_query(call.id, "✅ Move made!")
        
        # Game Hints
        elif action == 'hint':
            game_id = data_parts[1]
            if game_id not in games:
                bot.answer_callback_query(call.id, "❌ Game not found!")
                return
            
            game = games[game_id]
            hints_used = game.setdefault('hints_used', {}).get(user_id, 0)
            
            if hints_used >= 3:
                bot.answer_callback_query(call.id, "❌ No more hints available! (3/3 used)")
                return
            
            ai = AdvancedAI('hard')
            hint_move = ai.get_move(game['board'], game['player_symbols'][user_id])
            
            if hint_move != (-1, -1):
                game['hints_used'][user_id] = hints_used + 1
                remaining = 3 - game['hints_used'][user_id]
                bot.answer_callback_query(call.id, 
                    f"💡 Try row {hint_move[0]+1}, column {hint_move[1]+1}! ({remaining} hints left)")
            else:
                bot.answer_callback_query(call.id, "❌ No hints available!")
        
        # Game Undo
        elif action == 'undo':
            game_id = data_parts[1]
            if game_id not in games:
                bot.answer_callback_query(call.id, "❌ Game not found!")
                return
            
            game = games[game_id]
            move_history = game.get('move_history', [])
            
            if len(move_history) < 2:
                bot.answer_callback_query(call.id, "❌ Not enough moves to undo!")
                return
            
            # Undo last two moves
            for _ in range(2):
                if move_history:
                    _, r, c, _ = move_history.pop()
                    game['board'][r][c] = EMPTY
            
            # Reset turn to current player
            game['turn'] = user_id
            update_game_state(game_id)
            bot.answer_callback_query(call.id, "↩️ Last moves undone!")
        
        # Game Resign
        elif action == 'resign':
            game_id = data_parts[1]
            if game_id not in games:
                bot.answer_callback_query(call.id, "❌ This game has ended!", show_alert=True)
                return
            
            end_game(game_id, resigned_id=user_id)
            bot.answer_callback_query(call.id, "🏳️ You have resigned!")
        
        # Quick Match System
        elif action == 'quick' and len(data_parts) > 1 and data_parts[1] == 'match':
            # Try to find a match immediately
            opponent_id = find_quick_match(user_id)
            
            if opponent_id:
                # Create game between matched players
                game_id = str(uuid.uuid4())[:8]
                
                games[game_id] = {
                    'game_id': game_id,
                    'players': [user_id, opponent_id],
                    'player_symbols': {user_id: PLAYER_X, opponent_id: PLAYER_O},
                    'board': [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)],
                    'turn': user_id,
                    'is_over': False,
                    'game_mode': 'quick_match',
                    'message_ids': {},
                    'move_history': [],
                    'hints_used': {user_id: 0, opponent_id: 0},
                    'empty_symbol': '⬜',
                    'created_at': time.time(),
                    'start_time': time.time()
                }
                
                # Send game to both players
                for player_id in [user_id, opponent_id]:
                    if player_id == user_id:
                        games[game_id]['message_ids'][player_id] = call.message.message_id
                        safe_edit_message(call.message.chat.id, call.message.message_id,
                                        f"⚔️ Quick Match Found!\n\nOpponent: {get_user_name(opponent_id)}" + WATERMARK)
                    else:
                        try:
                            msg = bot.send_message(player_id, f"⚔️ Quick Match Found!\n\nOpponent: {get_user_name(user_id)}" + WATERMARK)
                            games[game_id]['message_ids'][player_id] = msg.message_id
                        except Exception as e:
                            print(f"Error sending quick match message to {player_id}: {e}")
                
                # Update game state
                update_game_state(game_id)
                bot.answer_callback_query(call.id, "⚔️ Match found! Game starting...")
            else:
                # Add to queue and wait
                add_to_quick_match_queue(user_id)
                
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton(f"❌ Cancel Search", callback_data="cancel_quick_match"),
                    InlineKeyboardButton(f"{EMOJI_REFRESH} Refresh", callback_data="quick_match")
                )
                
                text = f"⚔️ Searching for Opponent...\n\n"
                text += f"Players in queue: {len(quick_match_queue)}\n"
                text += f"⏳ Please wait while we find you a match!"
                
                safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
                bot.answer_callback_query(call.id, "🔍 Searching for opponent...")
        
        # Cancel Quick Match
        elif action == 'cancel' and len(data_parts) > 2 and data_parts[1] == 'quick' and data_parts[2] == 'match':
            if remove_from_quick_match_queue(user_id):
                send_enhanced_main_menu(user_id, call.message.message_id)
                bot.answer_callback_query(call.id, "❌ Quick match search cancelled")
            else:
                bot.answer_callback_query(call.id, "❌ You're not in the queue!")
        
        # Tournament Menu
        elif action == 'tournament' and len(data_parts) > 1 and data_parts[1] == 'menu':
            active_tournaments = tournament_manager.get_active_tournaments()
            
            text = f"🏟️ Tournament Center\n\n"
            
            if user_id in ADMIN_IDS:
                text += f"{EMOJI_CROWN} Admin Access Enabled\n\n"
            
            text += f"🎯 Active Tournaments: {len(active_tournaments)}\n"
            text += f"🏆 Your Tournament Wins: {get_user_stats(user_id).get('tournament_wins', 0) if get_user_stats(user_id) else 0}"
            
            markup = InlineKeyboardMarkup(row_width=2)
            
            if user_id in ADMIN_IDS:
                markup.add(InlineKeyboardButton(f"{EMOJI_CROWN} Create Tournament", callback_data="create_tournament"))
            
            markup.add(
                InlineKeyboardButton(f"🎯 Join Tournament", callback_data="join_tournament"),
                InlineKeyboardButton(f"📋 Active Tournaments", callback_data="list_tournaments")
            )
            markup.add(
                InlineKeyboardButton(f"🏆 My Tournaments", callback_data="my_tournaments"),
                InlineKeyboardButton(f"📊 Tournament History", callback_data="tournament_history")
            )
            markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu"))
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # Create Tournament (Admin Only)
        elif action == 'create' and len(data_parts) > 1 and data_parts[1] == 'tournament':
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "❌ Only admins can create tournaments!", show_alert=True)
                return
            
            user_input_state[user_id] = {'state': 'tournament_name'}
            
            text = f"{EMOJI_CROWN} Create New Tournament\n\n"
            text += f"Please enter the tournament name (3-50 characters):"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("❌ Cancel", callback_data="tournament_menu"))
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id, "📝 Please type the tournament name...")
        
        # Tournament Players Selection
        elif action == 'tournament' and len(data_parts) > 2 and data_parts[1] == 'players':
            max_players = int(data_parts[2])
            user_input_state[user_id]['max_players'] = max_players
            user_input_state[user_id]['state'] = 'tournament_prize'
            
            text = f"🏟️ Tournament Setup\n\n"
            text += f"Name: {user_input_state[user_id]['tournament_name']}\n"
            text += f"Max Players: {max_players}\n\n"
            text += f"Enter the prize description (optional, or type 'Glory'):"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🏆 Use 'Glory'", callback_data="tournament_prize_glory"))
            markup.add(InlineKeyboardButton("❌ Cancel", callback_data="tournament_menu"))
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id, "🏆 Enter prize description...")
        
        # Tournament Prize Glory
        elif action == 'tournament' and len(data_parts) > 2 and data_parts[1] == 'prize' and data_parts[2] == 'glory':
            # Simulate message with "Glory" as prize
            class MockMessage:
                def __init__(self, text):
                    self.text = text
                    self.from_user = call.from_user
            
            handle_tournament_prize(MockMessage("Glory"))
            bot.answer_callback_query(call.id)
        
        # Join Tournament
        elif action == 'join' and len(data_parts) > 1 and data_parts[1] == 'tournament':
            user_input_state[user_id] = {'state': 'join_tournament'}
            
            text = f"🎯 Join Tournament\n\n"
            text += f"Please enter the tournament ID:"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("❌ Cancel", callback_data="tournament_menu"))
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id, "🆔 Please type the tournament ID...")
        
        # List Active Tournaments
        elif action == 'list' and len(data_parts) > 1 and data_parts[1] == 'tournaments':
            active_tournaments = tournament_manager.get_active_tournaments()
            
            if not active_tournaments:
                text = f"📋 Active Tournaments\n\nNo active tournaments at the moment.\n\n"
                if user_id in ADMIN_IDS:
                    text += f"As an admin, you can create new tournaments!"
                else:
                    text += f"Check back later or ask an admin to create one!"
                
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="tournament_menu"))
            else:
                text = f"📋 Active Tournaments ({len(active_tournaments)})\n\n"
                markup = InlineKeyboardMarkup(row_width=1)
                
                for tournament in active_tournaments[:5]:  # Show max 5
                    status_emoji = "⏳" if tournament['status'] == 'waiting' else "🔥"
                    creator_name = get_user_name(tournament['creator'])
                    
                    button_text = f"{status_emoji} {tournament['name']} ({tournament['current_players']}/{tournament['max_players']}) - {creator_name}"
                    markup.add(InlineKeyboardButton(button_text, callback_data=f"view_tournament_{tournament['id']}"))
                
                markup.add(
                    InlineKeyboardButton(f"🔄 Refresh", callback_data="list_tournaments"),
                    InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="tournament_menu")
                )
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # View Tournament
        elif action == 'view' and len(data_parts) > 2 and data_parts[1] == 'tournament':
            tournament_id = data_parts[2]
            tournament = tournament_manager.get_tournament_info(tournament_id)
            
            if not tournament:
                bot.answer_callback_query(call.id, "❌ Tournament not found!")
                return
            
            text = f"🏟️ {tournament['name']}\n\n"
            text += f"🆔 ID: {tournament_id}\n"
            text += f"👑 Creator: {get_user_name(tournament['creator'])}\n"
            text += f"👥 Players: {len(tournament['participants'])}/{tournament['max_players']}\n"
            text += f"📊 Status: {tournament['status'].title()}\n"
            text += f"🏆 Prize: {tournament.get('prize_pool', 'Glory')}\n\n"
            
            if tournament['status'] == 'waiting':
                text += f"Participants:\n"
                for i, participant_id in enumerate(tournament['participants'], 1):
                    text += f"{i}. {get_user_name(participant_id)}\n"
            elif tournament['status'] == 'active':
                text += f"🔥 Tournament in progress!\n"
                text += f"Current Round: {tournament.get('current_round', 1)}"
            
            markup = InlineKeyboardMarkup()
            
            if tournament['status'] == 'waiting':
                if user_id not in tournament['participants']:
                    markup.add(InlineKeyboardButton(f"🎯 Join Tournament", callback_data=f"join_tournament_direct_{tournament_id}"))
                
                if user_id == tournament['creator'] or user_id in ADMIN_IDS:
                    if len(tournament['participants']) >= 2:
                        markup.add(InlineKeyboardButton(f"🚀 Start Tournament", callback_data=f"start_tournament_{tournament_id}"))
            
            markup.add(
                InlineKeyboardButton(f"🔄 Refresh", callback_data=f"view_tournament_{tournament_id}"),
                InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="tournament_menu")
            )
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # Join Tournament Direct
        elif action == 'join' and len(data_parts) > 3 and data_parts[1] == 'tournament' and data_parts[2] == 'direct':
            tournament_id = data_parts[3]
            success, msg = tournament_manager.join_tournament(tournament_id, user_id)
            
            if success:
                bot.answer_callback_query(call.id, f"✅ {msg}")
                # Refresh tournament view
                handle_enhanced_callback(type('obj', (object,), {'data': f'view_tournament_{tournament_id}', 'id': call.id, 'from_user': call.from_user, 'message': call.message})())
            else:
                bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        
        # Start Tournament
        elif action == 'start' and len(data_parts) > 2 and data_parts[1] == 'tournament':
            tournament_id = data_parts[2]
            success, msg = tournament_manager.start_tournament(tournament_id, user_id)
            
            if success:
                bot.answer_callback_query(call.id, f"🚀 {msg}")
                # Refresh tournament view
                handle_enhanced_callback(type('obj', (object,), {'data': f'view_tournament_{tournament_id}', 'id': call.id, 'from_user': call.from_user, 'message': call.message})())
            else:
                bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        
        # Spectate System
        elif action == 'spectate':
            if len(data_parts) == 1:  # Main spectate menu
                active_games = get_spectatable_games()
                
                if not active_games:
                    text = f"👁️ Spectate Games\n\nNo active games to spectate right now.\nCheck back later!"
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu"))
                else:
                    text = f"👁️ Active Games ({len(active_games)} available)\n\n"
                    markup = InlineKeyboardMarkup(row_width=1)
                    
                    for game in active_games[:5]:  # Show max 5 games
                        players_text = " vs ".join(game['players'])
                        spectator_text = f" ({game['spectators']} watching)" if game['spectators'] > 0 else ""
                        
                        markup.add(InlineKeyboardButton(
                            f"👁️ {players_text}{spectator_text}",
                            callback_data=f"spectate_game_{game['id']}"
                        ))
                    
                    markup.add(
                        InlineKeyboardButton(f"🔄 Refresh", callback_data="spectate"),
                        InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu")
                    )
                
                safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
                bot.answer_callback_query(call.id)
            
            elif len(data_parts) > 2 and data_parts[1] == 'game':  # Spectate specific game
                game_id = data_parts[2]
                
                if game_id not in games:
                    bot.answer_callback_query(call.id, "❌ Game not found or ended!")
                    return
                
                game = games[game_id]
                if game.get('game_mode') == 'vs_ai':
                    bot.answer_callback_query(call.id, "❌ Cannot spectate AI games!")
                    return
                
                # Add user as spectator
                add_spectator(game_id, user_id)
                
                # Create spectator view
                spectator_text = get_spectator_status_text(game) + WATERMARK
                spectator_markup = create_spectator_board_markup(game, user_id)
                
                # Store spectator message ID
                if 'spectator_messages' not in game:
                    game['spectator_messages'] = {}
                game['spectator_messages'][user_id] = call.message.message_id
                
                safe_edit_message(call.message.chat.id, call.message.message_id, spectator_text, spectator_markup)
                bot.answer_callback_query(call.id, "👁️ Now spectating this game!")
            
            elif len(data_parts) > 2 and data_parts[1] == 'refresh':  # Refresh spectator view
                game_id = data_parts[2]
                
                if game_id not in games:
                    bot.answer_callback_query(call.id, "❌ Game ended!")
                    # Return to spectate menu
                    handle_enhanced_callback(type('obj', (object,), {'data': 'spectate', 'id': call.id, 'from_user': call.from_user, 'message': call.message})())
                    return
                
                game = games[game_id]
                spectator_text = get_spectator_status_text(game) + WATERMARK
                spectator_markup = create_spectator_board_markup(game, user_id)
                
                safe_edit_message(call.message.chat.id, call.message.message_id, spectator_text, spectator_markup)
                bot.answer_callback_query(call.id, "🔄 Refreshed!")
        
        # Stop Spectating
        elif action == 'stop' and len(data_parts) > 2 and data_parts[1] == 'spectate':
            game_id = data_parts[2]
            remove_spectator(game_id, user_id)
            
            # Return to spectate menu
            handle_enhanced_callback(type('obj', (object,), {'data': 'spectate', 'id': call.id, 'from_user': call.from_user, 'message': call.message})())
            bot.answer_callback_query(call.id, "❌ Stopped spectating")
        
        # Spectate View (non-interactive)
        elif action == 'spectate' and len(data_parts) > 2 and data_parts[1] == 'view':
            bot.answer_callback_query(call.id, "👁️ You're spectating - you can't make moves!")
        
        # Game History
        elif action == 'history':
            history = get_game_history(user_id, 10)
            
            if not history:
                text = f"📜 Game History\n\nNo games played yet!\nStart playing to see your history here."
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu"))
            else:
                text = f"📜 Game History (Last 10 games)\n\n"
                
                for i, game_record in enumerate(history, 1):
                    # Unpack the game record properly
                    if len(game_record) >= 9:
                        game_id, p1_id, p2_id, winner_id, game_mode, duration, moves, board_state, created_at = game_record[:9]
                        
                        opponent_id = p2_id if p1_id == user_id else p1_id
                        opponent_name = "AI" if opponent_id == bot.get_me().id else get_user_name(opponent_id)
                        
                        if winner_id == user_id:
                            result = "🎉 Won"
                        elif winner_id is None:
                            result = "🤝 Draw"
                        else:
                            result = "❌ Lost"
                        
                        text += f"`{i}.` vs {opponent_name} - {result}\n"
                        text += f"   ⏱️ {duration}s | 📊 {moves} moves | {game_mode}\n\n"
                
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton(f"🔄 Refresh", callback_data="history")
                )
                markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu"))
            
            safe_edit_message(call.message.chat.id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # Statistics Menu
        elif action == 'stats' and len(data_parts) > 1 and data_parts[1] == 'menu':
            stats = get_user_stats(user_id) or {}
            total = stats.get('total_games', 0)
            win_rate = (stats.get('wins', 0) / total * 100) if total > 0 else 0
            
            text = f"📊 Your Statistics\n\n"
            text += f"✅ Wins: `{stats.get('wins', 0)}`\n"
            text += f"❌ Losses: `{stats.get('losses', 0)}`\n"
            text += f"🤝 Draws: `{stats.get('draws', 0)}`\n"
            text += f"📈 Win Rate: `{win_rate:.1f}%`\n\n"
            text += f"🔥 Current Streak: `{stats.get('current_streak', 0)} wins`\n"
            text += f"🏆 Longest Streak: `{stats.get('longest_streak', 0)} wins`\n\n"
            text += f"🤖 vs AI: {stats.get('ai_wins', 0)}W-{stats.get('ai_losses', 0)}L\n"
            text += f"🏟️ Tournament Wins: {stats.get('tournament_wins', 0)}"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu"))
            
            safe_edit_message(user_id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # Settings Menu
        elif action == 'settings' and len(data_parts) > 1 and data_parts[1] == 'menu':
            stats = get_user_stats(user_id) or {}
            current_theme = stats.get('theme', 'classic')
            
            text = f"⚙️ Settings\n\n"
            text += f"👤 Name: {get_user_name(user_id)}\n"
            text += f"🎨 Theme: {current_theme.title()}\n"
            text += f"🏅 Achievements: {len(json.loads(stats.get('achievements', '[]')))}"
            
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton(f"{EMOJI_NAME} Change Name", callback_data="change_name"),
                InlineKeyboardButton(f"{EMOJI_THEMES} Change Theme", callback_data="change_theme"),
                InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu")
            )
            
            safe_edit_message(user_id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # Change Theme
        elif action == 'change' and len(data_parts) > 1 and data_parts[1] == 'theme':
            markup = InlineKeyboardMarkup(row_width=2)
            for theme_name, theme_data in THEMES.items():
                markup.add(InlineKeyboardButton(
                    f"{theme_data['x']}{theme_data['o']} {theme_name.title()}", 
                    callback_data=f"set_theme_{theme_name}"
                ))
            markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="settings_menu"))
            
            text = "🎨 Choose Theme\n\nSelect your preferred game theme:"
            safe_edit_message(user_id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # Set Theme
        elif action == 'set' and len(data_parts) > 2 and data_parts[1] == 'theme':
            theme_name = data_parts[2]
            if theme_name in THEMES:
                update_user_stats(user_id, theme=theme_name)
                bot.answer_callback_query(call.id, f"🎨 Theme changed to {theme_name.title()}!")
                
                # Go back to settings
                stats = get_user_stats(user_id) or {}
                current_theme = stats.get('theme', 'classic')
                
                text = f"⚙️ Settings\n\n"
                text += f"👤 Name: {get_user_name(user_id)}\n"
                text += f"🎨 Theme: {current_theme.title()}\n"
                text += f"🏅 Achievements: {len(json.loads(stats.get('achievements', '[]')))}"
                
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton(f"{EMOJI_NAME} Change Name", callback_data="change_name"),
                    InlineKeyboardButton(f"{EMOJI_THEMES} Change Theme", callback_data="change_theme"),
                    InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu")
                )
                
                safe_edit_message(user_id, call.message.message_id, text + WATERMARK, markup)
        
        # Achievements
        elif action == 'achievements':
            stats = get_user_stats(user_id) or {}
            user_achievements = json.loads(stats.get('achievements', '[]'))
            
            # Define all achievements
            all_achievements = [
                {'id': 'first_win', 'name': 'First Victory', 'desc': 'Win your first game', 'icon': '🥇'},
                {'id': 'streak_5', 'name': 'Streak Master', 'desc': 'Win 5 games in a row', 'icon': '🔥'},
                {'id': 'ai_destroyer', 'name': 'AI Destroyer', 'desc': 'Beat the AI 10 times', 'icon': '🤖💥'},
                {'id': 'social_player', 'name': 'Social Player', 'desc': 'Play 25 games with friends', 'icon': '👥'},
                {'id': 'veteran', 'name': 'Veteran', 'desc': 'Play 100 total games', 'icon': '🎖️'},
                {'id': 'unbeatable', 'name': 'Unbeatable', 'desc': 'Win 10 games in a row', 'icon': '🛡️'},
                {'id': 'tournament_champion', 'name': 'Tournament Champion', 'desc': 'Win a tournament', 'icon': '🏆'},
            ]
            
            text = "🏅 Your Achievements\n\n"
            unlocked_count = 0
            
            for ach in all_achievements:
                if ach['id'] in user_achievements:
                    text += f"✅ {ach['icon']} {ach['name']}\n   {ach['desc']}\n\n"
                    unlocked_count += 1
                else:
                    text += f"🔒 {ach['name']}\n   {ach['desc']}\n\n"
            
            text += f"📊 Progress: {unlocked_count}/{len(all_achievements)} unlocked"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(f"{EMOJI_BACK} Back", callback_data="main_menu"))
            
            safe_edit_message(user_id, call.message.message_id, text + WATERMARK, markup)
            bot.answer_callback_query(call.id)
        
        # Coming soon features
        elif action in ['my', 'change'] and len(data_parts) > 1:
            if data_parts[1] in ['tournaments', 'name'] or (action == 'tournament' and data_parts[1] == 'history'):
                bot.answer_callback_query(call.id, "🚧 This feature is coming soon! Stay tuned for updates.")
        
        else:
            bot.answer_callback_query(call.id, "🚧 Feature coming soon!")

    except Exception as e:
        print(f"Error in callback handler: {e}, data: {call.data}")
        bot.answer_callback_query(call.id, "❌ An error occurred. Please try again.")

# -------------------- HELPER FUNCTIONS --------------------
def check_win(board, player):
    # Check rows, columns, and diagonals
    for i in range(BOARD_SIZE):
        if all(board[i][j] == player for j in range(BOARD_SIZE)):
            return True
        if all(board[j][i] == player for j in range(BOARD_SIZE)):
            return True
    
    if all(board[i][i] == player for i in range(BOARD_SIZE)):
        return True
    if all(board[i][BOARD_SIZE - 1 - i] == player for i in range(BOARD_SIZE)):
        return True
    
    return False

def is_board_full(board):
    return all(cell != EMPTY for row in board for cell in row)

# -------------------- INITIALIZATION AND STARTUP --------------------
def main():
    print("🚀 Initializing Advanced Tic-Tac-Toe Bot...")
    
    # Initialize database
    init_database()
    print("✅ Database initialized")
    
    # Start bot
    print("🎮 Advanced Tic-Tac-Toe Bot is now running!")
    print("Features: AI opponents, Quick Match, Game History, Themes, Tournaments, and more!")
    print(f"👑 Admin ID: {ADMIN_IDS[0]}")
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        time.sleep(15)
        main()  # Restart on error

if __name__ == '__main__':

    main()


