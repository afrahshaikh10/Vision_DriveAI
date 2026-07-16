import sqlite3
import os
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from utils.logger import logger

class DatabaseManager:
    """Manages the local SQLite database for session tracking, achievements, and calibration history."""
    def __init__(self, db_path: str = "visiondrive.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def initialize_db(self) -> None:
        """Creates tables if they do not exist, runs migrations, and pre-populates default achievements."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 1. Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Upgrade Users Table schema
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if "password" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN password TEXT DEFAULT ''")
            if "xp" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
            if "coins" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0")
            if "level" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1")
            if "active_theme" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN active_theme TEXT DEFAULT 'cyberpunk'")
            if "unlocked_themes" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN unlocked_themes TEXT DEFAULT 'cyberpunk'")
            if "avatar" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT 'avatar_1'")
            if "current_license" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN current_license TEXT DEFAULT 'License D'")
            if "unlocked_weather" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN unlocked_weather TEXT DEFAULT 'morning,sunny,evening'")
            if "daily_goal_text" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_text TEXT DEFAULT ''")
            if "daily_goal_type" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_type TEXT DEFAULT ''")
            if "daily_goal_progress" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_progress INTEGER DEFAULT 0")
            if "daily_goal_target" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_target INTEGER DEFAULT 0")
            if "daily_goal_completed" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_completed INTEGER DEFAULT 0")
            if "daily_goal_xp" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_xp INTEGER DEFAULT 0")
            if "daily_goal_coins" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_coins INTEGER DEFAULT 0")
            if "daily_goal_date" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_goal_date TEXT DEFAULT ''")
            
            # 2. Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_time TEXT NOT NULL,
                    duration_sec INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    smoothness REAL NOT NULL,
                    reaction_time_sec REAL NOT NULL,
                    lane_discipline REAL NOT NULL,
                    efficiency REAL NOT NULL,
                    false_gestures_count INTEGER NOT NULL
                )
            """)
            
            # Upgrade Sessions Table schema (user_id relation)
            cursor.execute("PRAGMA table_info(sessions)")
            session_columns = [row[1] for row in cursor.fetchall()]
            if "user_id" not in session_columns:
                cursor.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER DEFAULT 1")
            
            # 3. Achievements Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    unlocked INTEGER DEFAULT 0,
                    unlocked_at TEXT
                )
            """)
            
            # 4. Calibration Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_time TEXT NOT NULL,
                    neutral_angle REAL NOT NULL,
                    max_left_angle REAL NOT NULL,
                    max_right_angle REAL NOT NULL,
                    neutral_distance REAL NOT NULL
                )
            """)
            
            # 5. Challenges Progress Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challenges_progress (
                    user_id INTEGER,
                    challenge_id INTEGER,
                    best_score INTEGER DEFAULT 0,
                    stars INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, challenge_id)
                )
            """)
            
            conn.commit()
            self._prepopulate_achievements()
            
            # Prepopulate a default guest user (user_id=1)
            cursor.execute("SELECT id FROM users WHERE id = 1")
            if not cursor.fetchone():
                date_str = time.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO users (id, name, password, created_at, xp, coins, level, active_theme, unlocked_themes, avatar)
                    VALUES (1, 'Guest Player', '', ?, 0, 100, 1, 'cyberpunk', 'cyberpunk', 'avatar_1')
                """, (date_str,))
                conn.commit()
                
            logger.info("Database initialized and upgraded successfully.")
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}")

    def _prepopulate_achievements(self) -> None:
        """Seeds default achievements into database if empty."""
        default_achievements = [
            ("Perfect Driver", "Drive for 2 minutes without crashing."),
            ("Gesture Master", "Use all hand gestures at least once in a session."),
            ("Smooth Operator", "Achieve a steering smoothness score of 90% or higher."),
            ("Safe Driver", "Achieve a driving efficiency of 95% or higher."),
            ("Night Rider", "Complete a session in Night Mode."),
            ("Precision King", "Dodge 15 obstacles in a single session."),
            ("First Drive", "Complete your first simulator drive session."),
            ("Smooth Driver", "Achieve a steering smoothness score of 85% or higher."),
            ("Perfect Brake", "Successfully use hand gestures to apply brakes."),
            ("Reaction King", "Evade an obstacle with a reaction time under 0.4 seconds."),
            ("Rain Master", "Complete a driving session in a rainy weather theme."),
            ("AI Driver", "Drive with maximum hand gesture confidence."),
            ("100 Games", "Complete 100 simulator drive sessions."),
            ("1000 Gestures", "Execute 1000 total gestures."),
            ("Legend", "Unlock all other driver achievements.")
        ]
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            for name, desc in default_achievements:
                cursor.execute("""
                    INSERT OR IGNORE INTO achievements (name, description, unlocked)
                    VALUES (?, ?, 0)
                """, (name, desc))
            conn.commit()
        except Exception as e:
            logger.error(f"Error seeding achievements: {e}")

    def save_session(
        self,
        duration: int,
        score: int,
        smoothness: float,
        reaction_time: float,
        lane_discipline: float,
        efficiency: float,
        false_gestures: int,
        user_id: int = 1
    ) -> bool:
        """Saves a driving run session."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            date_str = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO sessions (date_time, duration_sec, score, smoothness, reaction_time_sec, lane_discipline, efficiency, false_gestures_count, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, duration, score, smoothness, reaction_time, lane_discipline, efficiency, false_gestures, user_id))
            conn.commit()
            logger.info(f"Saved session with score {score} for user {user_id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def get_sessions(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns all recorded sessions, optionally filtered by user_id, in reverse chronological order."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("SELECT * FROM sessions WHERE user_id = ? ORDER BY id DESC", (user_id,))
            else:
                cursor.execute("SELECT * FROM sessions ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}")
            return []

    def get_achievements(self) -> List[Dict[str, Any]]:
        """Returns all achievements."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM achievements")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching achievements: {e}")
            return []

    def unlock_achievement(self, name: str) -> bool:
        """Unlocks an achievement by name."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Check if already unlocked
            cursor.execute("SELECT unlocked FROM achievements WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row and row["unlocked"] == 1:
                return False  # Already unlocked
                
            date_str = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE achievements
                SET unlocked = 1, unlocked_at = ?
                WHERE name = ?
            """, (date_str, name))
            conn.commit()
            logger.info(f"ACHIEVEMENT UNLOCKED: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unlock achievement {name}: {e}")
            return False

    def save_calibration(self, neutral_ang: float, left_ang: float, right_ang: float, dist: float) -> bool:
        """Saves dynamic hand calibration parameters to database log."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            date_str = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO calibration_history (date_time, neutral_angle, max_left_angle, max_right_angle, neutral_distance)
                VALUES (?, ?, ?, ?, ?)
            """, (date_str, neutral_ang, left_ang, right_ang, dist))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to log calibration history: {e}")
            return False

    # --- USER AUTHENTICATION & PROGRESSION METHODS ---
    def authenticate_user(self, name: str, password: str) -> Optional[Dict[str, Any]]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE name = ? AND password = ?", (name, password))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to authenticate user: {e}")
            return None

    def register_user(self, name: str, password: str, avatar: str = "avatar_1") -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            date_str = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO users (name, password, created_at, xp, coins, level, active_theme, unlocked_themes, avatar)
                VALUES (?, ?, ?, 0, 100, 1, 'cyberpunk', 'cyberpunk', ?)
            """, (name, password, date_str, avatar))
            conn.commit()
            logger.info(f"Registered new user: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register user {name}: {e}")
            return False

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def add_xp_coins(self, user_id: int, xp_amount: int, coins_amount: int) -> Tuple[int, int, int]:
        """Adds XP and Coins, performs level up calculations. Returns (new_level, new_xp, new_coins)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT level, xp, coins FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return (1, 0, 0)
                
            level, xp, coins = row["level"], row["xp"], row["coins"]
            xp += xp_amount
            coins += coins_amount
            
            # Level up calculation (e.g. 500 XP * level per level)
            while xp >= level * 500:
                xp -= level * 500
                level += 1
                
            cursor.execute("UPDATE users SET level = ?, xp = ?, coins = ? WHERE id = ?", (level, xp, coins, user_id))
            conn.commit()
            return (level, xp, coins)
        except Exception as e:
            logger.error(f"Failed to update user progression: {e}")
            return (1, 0, 0)

    def get_challenge_progress(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM challenges_progress WHERE user_id = ?", (user_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get challenge progress: {e}")
            return []

    def save_challenge_progress(self, user_id: int, challenge_id: int, score: int, stars: int, completed: int = 1) -> None:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Get existing score/stars
            cursor.execute("SELECT best_score, stars FROM challenges_progress WHERE user_id = ? AND challenge_id = ?", (user_id, challenge_id))
            row = cursor.fetchone()
            if row:
                new_score = max(row["best_score"], score)
                new_stars = max(row["stars"], stars)
                cursor.execute("""
                    UPDATE challenges_progress
                    SET best_score = ?, stars = ?, completed = ?
                    WHERE user_id = ? AND challenge_id = ?
                """, (new_score, new_stars, completed, user_id, challenge_id))
            else:
                cursor.execute("""
                    INSERT INTO challenges_progress (user_id, challenge_id, best_score, stars, completed)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, challenge_id, score, stars, completed))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save challenge progress: {e}")

    def get_user_themes(self, user_id: int) -> Tuple[str, List[str]]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT active_theme, unlocked_themes FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                unlocked = [t.strip() for t in row["unlocked_themes"].split(",") if t.strip()]
                return row["active_theme"], unlocked
            return "cyberpunk", ["cyberpunk"]
        except Exception as e:
            logger.error(f"Failed to get themes: {e}")
            return "cyberpunk", ["cyberpunk"]

    def unlock_theme(self, user_id: int, theme_name: str, cost: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT coins, unlocked_themes FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False
            coins = row["coins"]
            unlocked = [t.strip() for t in row["unlocked_themes"].split(",") if t.strip()]
            if theme_name in unlocked:
                return True
            if coins < cost:
                return False
                
            new_coins = coins - cost
            unlocked.append(theme_name)
            unlocked_str = ",".join(unlocked)
            cursor.execute("UPDATE users SET coins = ?, unlocked_themes = ? WHERE id = ?", (new_coins, unlocked_str, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to unlock theme: {e}")
            return False

    def equip_theme(self, user_id: int, theme_name: str) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT unlocked_themes FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False
            unlocked = [t.strip() for t in row["unlocked_themes"].split(",") if t.strip()]
            if theme_name not in unlocked:
                return False
            cursor.execute("UPDATE users SET active_theme = ? WHERE id = ?", (theme_name, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to equip theme: {e}")
            return False
    def get_license_info(self, user_id: int) -> Dict[str, Any]:
        """Calculates current license progression statistics for driver overview and HUD display."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT current_license, xp, coins, name FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                return {}
                
            lic_name = user["current_license"]
            xp = user["xp"]
            
            # Map licenses to challenges
            license_challenges = {
                "License D": [1, 2],
                "License C": [3, 4],
                "License B": [5, 6],
                "License A": [7, 8],
                "International License": [9],
                "Master License": [10]
            }
            
            xp_requirements = {
                "License D": 500,
                "License C": 1200,
                "License B": 2200,
                "License A": 3500,
                "International License": 5000,
                "Master License": 99999
            }
            
            target_ids = license_challenges.get(lic_name, [1, 2])
            target_xp = xp_requirements.get(lic_name, 500)
            
            # Get completed challenges count for this user in this license tier
            cursor.execute(
                f"SELECT challenge_id FROM challenges_progress WHERE user_id = ? AND completed = 1 AND challenge_id IN ({','.join('?' * len(target_ids))})",
                [user_id] + target_ids
            )
            completed_ids = [row[0] for row in cursor.fetchall()]
            completed_cnt = len(completed_ids)
            total_cnt = len(target_ids)
            remaining_cnt = total_cnt - completed_cnt
            
            progress_pct = int((completed_cnt / total_cnt) * 100) if total_cnt > 0 else 0
            
            return {
                "license_name": lic_name,
                "progress_pct": progress_pct,
                "completed_challenges": completed_cnt,
                "remaining_challenges": remaining_cnt,
                "current_xp": xp,
                "xp_required": target_xp,
                "coins": user["coins"],
                "name": user["name"]
            }
        except Exception as e:
            logger.error(f"Failed to get license info: {e}")
            return {}

    def check_license_unlocks(self, user_id: int) -> List[str]:
        """Evaluates completed challenges and upgrades license tier and unlocks content automatically."""
        unlock_notifications = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT current_license, unlocked_themes, unlocked_weather FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                return []
                
            lic_name = user["current_license"]
            unlocked_themes = [t.strip() for t in user["unlocked_themes"].split(",") if t.strip()]
            unlocked_weather = [w.strip() for w in user["unlocked_weather"].split(",") if w.strip()]
            
            license_challenges = {
                "License D": [1, 2],
                "License C": [3, 4],
                "License B": [5, 6],
                "License A": [7, 8],
                "International License": [9],
                "Master License": [10]
            }
            
            target_ids = license_challenges.get(lic_name, [])
            if not target_ids:
                return []
                
            # Get completed count
            cursor.execute(
                f"SELECT COUNT(*) FROM challenges_progress WHERE user_id = ? AND completed = 1 AND challenge_id IN ({','.join('?' * len(target_ids))})",
                [user_id] + target_ids
            )
            completed_cnt = cursor.fetchone()[0]
            
            if completed_cnt >= len(target_ids):
                # License completed! Upgrade to next rank
                license_upgrades = {
                    "License D": ("License C", "sunny", "blue", "First Drive"),
                    "License C": ("License B", "night", "night", "Night Rider"),
                    "License B": ("License A", "rain", "rain", "Rain Master"),
                    "License A": ("International License", "fog", "glass", "Safe Driver"),
                    "International License": ("Master License", "storm", "future", "Gesture Master"),
                    "Master License": ("Master License", "snow", "neon", "Legend")
                }
                
                if lic_name in license_upgrades:
                    next_lic, weather_unlock, theme_unlock, ach_unlock = license_upgrades[lic_name]
                    
                    # Update license if it's a new rank
                    if next_lic != lic_name:
                        cursor.execute("UPDATE users SET current_license = ? WHERE id = ?", (next_lic, user_id))
                        unlock_notifications.append(f"🎖️ LICENSED UPGRADED: Welcome to {next_lic}!")
                    
                    # Unlock weather mode
                    if weather_unlock not in unlocked_weather:
                        unlocked_weather.append(weather_unlock)
                        cursor.execute("UPDATE users SET unlocked_weather = ? WHERE id = ?", (",".join(unlocked_weather), user_id))
                        unlock_notifications.append(f"☀ WEATHER UNLOCKED: {weather_unlock.upper()} Weather mode!")
                        
                    # Unlock theme
                    if theme_unlock not in unlocked_themes:
                        unlocked_themes.append(theme_unlock)
                        cursor.execute("UPDATE users SET unlocked_themes = ? WHERE id = ?", (",".join(unlocked_themes), user_id))
                        unlock_notifications.append(f"🏎️ THEME UNLOCKED: {theme_unlock.upper()} Theme equipped in Garage!")
                        
                    # Unlock achievement
                    self.unlock_achievement(ach_unlock)
                    unlock_notifications.append(f"🏆 ACHIEVEMENT UNLOCKED: {ach_unlock}!")
                    
                    conn.commit()
            return unlock_notifications
        except Exception as e:
            logger.error(f"Failed to check license progression: {e}")
            return []

    def generate_daily_goal(self, user_id: int, force: bool = False) -> None:
        """Generates a random daily training goal if the day has changed."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT daily_goal_date FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            today = time.strftime("%Y-%m-%d")
            if row and row["daily_goal_date"] == today and not force:
                return # Already generated for today
                
            goals = [
                {"type": "challenges", "text": "Complete 2 Challenges", "target": 2, "xp": 100, "coins": 50},
                {"type": "accuracy", "text": "Maintain Steering Accuracy >90%", "target": 90, "xp": 150, "coins": 75},
                {"type": "duration", "text": "Drive for 10 Minutes", "target": 600, "xp": 120, "coins": 60},
                {"type": "brakes", "text": "Perfect Brake 15 Times", "target": 15, "xp": 100, "coins": 50}
            ]
            
            selected = random.choice(goals)
            cursor.execute("""
                UPDATE users
                SET daily_goal_text = ?,
                    daily_goal_type = ?,
                    daily_goal_progress = 0,
                    daily_goal_target = ?,
                    daily_goal_completed = 0,
                    daily_goal_xp = ?,
                    daily_goal_coins = ?,
                    daily_goal_date = ?
                WHERE id = ?
            """, (selected["text"], selected["type"], selected["target"], selected["xp"], selected["coins"], today, user_id))
            conn.commit()
            logger.info(f"Daily Goal generated for user {user_id}: {selected['text']}")
        except Exception as e:
            logger.error(f"Failed to generate daily goal: {e}")

    def update_daily_goal_progress(self, user_id: int, goal_type: str, increment: int) -> Tuple[bool, int, int, str]:
        """Increments daily goal counts, triggers rewards if goal thresholds are met."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT daily_goal_type, daily_goal_progress, daily_goal_target, daily_goal_completed, daily_goal_text, daily_goal_xp, daily_goal_coins
                FROM users WHERE id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if not row or row["daily_goal_completed"] == 1:
                return False, 0, 0, ""
                
            if row["daily_goal_type"] != goal_type:
                return False, 0, 0, ""
                
            target = row["daily_goal_target"]
            completed = 0
            
            if goal_type == "accuracy":
                if increment >= target:
                    new_progress = target
                    completed = 1
                else:
                    new_progress = max(row["daily_goal_progress"], increment)
            else:
                new_progress = row["daily_goal_progress"] + increment
                if new_progress >= target:
                    new_progress = target
                    completed = 1
                    
            cursor.execute("""
                UPDATE users
                SET daily_goal_progress = ?, daily_goal_completed = ?
                WHERE id = ?
            """, (new_progress, completed, user_id))
            
            if completed == 1:
                self.add_xp_coins(user_id, row["daily_goal_xp"], row["daily_goal_coins"])
                conn.commit()
                return True, row["daily_goal_xp"], row["daily_goal_coins"], row["daily_goal_text"]
                
            conn.commit()
            return False, 0, 0, ""
        except Exception as e:
            logger.error(f"Failed to update daily goal: {e}")
            return False, 0, 0, ""

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

# Global instance
db = DatabaseManager()
