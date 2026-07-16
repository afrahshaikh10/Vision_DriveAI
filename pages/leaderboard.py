import customtkinter as ctk
import random
from typing import Any, Dict, List
from utils.db import db
from utils.theme_manager import get_theme_colors

MOCK_GLOBAL = [
    {"rank": 1, "name": "SpeedDemon ⚡", "level": 24, "score": 4500, "accuracy": 96.5, "xp": 11800},
    {"rank": 2, "name": "DriftKing 🏎️", "level": 20, "score": 3950, "accuracy": 92.4, "xp": 9500},
    {"rank": 3, "name": "ApexHustler 🚀", "level": 17, "score": 3400, "accuracy": 89.8, "xp": 8200},
    {"rank": 5, "name": "GearShifter ⚙️", "level": 12, "score": 2800, "accuracy": 84.5, "xp": 5600},
    {"rank": 6, "name": "AsphaltPro 🏁", "level": 10, "score": 2550, "accuracy": 81.2, "xp": 4900}
]

class LeaderboardScreen(ctk.CTkFrame):
    """Scoreboard page aggregating global mock profiles and active user high scores."""
    def __init__(self, parent: Any, user_data: Dict[str, Any]):
        super().__init__(parent, fg_color="transparent")
        self.user_data = user_data
        
        self.setup_ui()

    def setup_ui(self) -> None:
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        # Header Title
        header = ctk.CTkLabel(
            self,
            text="🏆 GLOBAL SIMULATOR SCOREBOARD",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        desc = ctk.CTkLabel(
            self,
            text="Global player rankings sorted by highest arcade drive score and lane precision.",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Grid frame
        table_frame = ctk.CTkFrame(scroll, fg_color="#0a0a0f", border_width=1, border_color="#1b1836", corner_radius=12)
        table_frame.pack(fill="both", expand=True, pady=10, ipady=15)
        
        # Columns: Rank, Driver, Level, High Score, Smoothness
        # Table Header
        headers = ["RANK", "DRIVER", "LEVEL", "HIGH SCORE", "ACCURACY"]
        for col_idx, h_text in enumerate(headers):
            lbl = ctk.CTkLabel(
                table_frame,
                text=h_text,
                font=ctk.CTkFont(family="Outfit", size=10, weight="bold"),
                text_color=colors["secondary"]
            )
            lbl.grid(row=0, column=col_idx, padx=15, pady=(15, 10), sticky="w")
            table_frame.grid_columnconfigure(col_idx, weight=1)
            
        # Draw horizontal rule below headers
        hr = ctk.CTkFrame(table_frame, fg_color="#1b1836", height=1)
        hr.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 8))
        
        # Load user high score and smoothness
        sessions = db.get_sessions(self.user_data["id"])
        user_max_score = max(s["score"] for s in sessions) if sessions else 0
        user_avg_smoothness = sum(s["smoothness"] for s in sessions) / len(sessions) if sessions else 0.0
        
        user_row = {
            "rank": 4, # insert as rank 4
            "name": f"{self.user_data.get('name', 'Driver')} (You) 🟢",
            "level": self.user_data.get("level", 1),
            "score": user_max_score,
            "accuracy": round(user_avg_smoothness, 1)
        }
        
        # Merge active user dynamically in list sorted by high score
        all_players = MOCK_GLOBAL.copy()
        all_players.append(user_row)
        all_players = sorted(all_players, key=lambda p: p["score"], reverse=True)
        
        # Re-assign ranks dynamically based on sort order
        for rank_idx, player in enumerate(all_players):
            player["rank"] = rank_idx + 1
            
            # Text formatting
            is_self = "(You)" in player["name"]
            row_bg = "#0f0f1b" if is_self else "transparent"
            
            row_frame = ctk.CTkFrame(table_frame, fg_color=row_bg, corner_radius=6, height=36)
            row_frame.grid(row=rank_idx + 2, column=0, columnspan=5, sticky="ew", padx=8, pady=2)
            row_frame.grid_propagate(False)
            row_frame.grid_columnconfigure((0,1,2,3,4), weight=1)
            
            # Rank
            r_lbl = ctk.CTkLabel(row_frame, text=f"#{player['rank']}", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=colors["accent"] if player['rank'] <= 3 else "#888888")
            r_lbl.grid(row=0, column=0, padx=12, pady=5, sticky="w")
            
            # Name
            n_lbl = ctk.CTkLabel(row_frame, text=player["name"], font=ctk.CTkFont(family="Outfit", size=11, weight="bold" if is_self else "normal"), text_color="#FFFFFF" if is_self else "#D5D5D8")
            n_lbl.grid(row=0, column=1, padx=12, pady=5, sticky="w")
            
            # Level
            l_lbl = ctk.CTkLabel(row_frame, text=f"Lvl {player['level']}", font=ctk.CTkFont(size=11), text_color="#888888")
            l_lbl.grid(row=0, column=2, padx=12, pady=5, sticky="w")
            
            # Score
            s_lbl = ctk.CTkLabel(row_frame, text=f"{player['score']} pts", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#00FF66" if player['score'] > 0 else "#5a5a66")
            s_lbl.grid(row=0, column=3, padx=12, pady=5, sticky="w")
            
            # Accuracy
            a_lbl = ctk.CTkLabel(row_frame, text=f"{player['accuracy']}%", font=ctk.CTkFont(size=11), text_color="#00F5FF" if player['accuracy'] > 0 else "#5a5a66")
            a_lbl.grid(row=0, column=4, padx=12, pady=5, sticky="w")
