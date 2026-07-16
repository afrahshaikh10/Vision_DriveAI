import customtkinter as ctk
from typing import Any, Dict
from utils.db import db
from utils.theme_manager import get_theme_colors

class ProfileScreen(ctk.CTkFrame):
    """Driver Profile screen summarizing gaming records and unlocked badges."""
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
            text="👤 DRIVER PROFILE",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Grid splits: Left Profile Card, Right detailed stats
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)
        
        # 1. Left side Profile Card
        profile_card = ctk.CTkFrame(split, fg_color="#0f0f1b", border_color=colors["border"], border_width=1, corner_radius=15, width=280)
        profile_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        profile_card.grid_propagate(False)
        
        avatar_emoji = "🏎️"
        avatar_name = "Pro Racer"
        avatar_id = self.user_data.get("avatar", "avatar_1")
        if avatar_id == "avatar_2":
            avatar_emoji, avatar_name = "🚀", "Space Pilot"
        elif avatar_id == "avatar_3":
            avatar_emoji, avatar_name = "🛸", "Cyber Driver"
        elif avatar_id == "avatar_4":
            avatar_emoji, avatar_name = "⚡", "Electro Pilot"
            
        avatar_lbl = ctk.CTkLabel(profile_card, text=avatar_emoji, font=ctk.CTkFont(size=56))
        avatar_lbl.pack(pady=(30, 5))
        
        username_lbl = ctk.CTkLabel(profile_card, text=self.user_data.get("name", "Driver").upper(), font=ctk.CTkFont(family="Outfit", size=18, weight="bold"), text_color="#FFFFFF")
        username_lbl.pack(pady=2)
        
        avatar_title = ctk.CTkLabel(profile_card, text=avatar_name, font=ctk.CTkFont(size=11), text_color="#888888")
        avatar_title.pack(pady=(0, 15))
        
        # Level / Progression
        lvl = self.user_data.get("level", 1)
        rank_name = self.get_rank_name(lvl)
        
        rank_lbl = ctk.CTkLabel(profile_card, text=rank_name.upper(), font=ctk.CTkFont(family="Outfit", size=12, weight="bold"), text_color=colors["accent"])
        rank_lbl.pack(pady=4)
        
        lvl_desc = ctk.CTkLabel(profile_card, text=f"Level {lvl} Simulator Pilot", font=ctk.CTkFont(size=10), text_color="#888888")
        lvl_desc.pack(pady=(0, 20))
        
        # Balance details
        bal_frame = ctk.CTkFrame(profile_card, fg_color="#12121e", corner_radius=8, height=60)
        bal_frame.pack(fill="x", padx=25, pady=5)
        bal_frame.pack_propagate(False)
        bal_frame.grid_columnconfigure((0, 1), weight=1)
        
        coins_lbl = ctk.CTkLabel(bal_frame, text=f"💰 Coins\n{self.user_data.get('coins', 0)}", font=ctk.CTkFont(size=10, weight="bold"), text_color="#F1C40F")
        coins_lbl.grid(row=0, column=0, pady=8)
        
        xp_lbl = ctk.CTkLabel(bal_frame, text=f"⭐ XP\n{self.user_data.get('xp', 0)}", font=ctk.CTkFont(size=10, weight="bold"), text_color=colors["secondary"])
        xp_lbl.grid(row=0, column=1, pady=8)
        
        # 2. Right side detailed statistics
        stats_scroll = ctk.CTkScrollableFrame(split, fg_color="transparent")
        stats_scroll.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        sessions = db.get_sessions(self.user_data["id"])
        total_runs = len(sessions)
        
        avg_score = 0
        total_duration = 0
        avg_smoothness = 0.0
        avg_reaction = 0.65
        
        if total_runs > 0:
            avg_score = int(sum(s["score"] for s in sessions) / total_runs)
            total_duration = sum(s["duration_sec"] for s in sessions)
            avg_smoothness = sum(s["smoothness"] for s in sessions) / total_runs
            avg_reaction = sum(s["reaction_time_sec"] for s in sessions) / total_runs
            
        stats_box = ctk.CTkFrame(stats_scroll, fg_color="#0a0a0f", border_width=1, border_color="#1b1836", corner_radius=12)
        stats_box.pack(fill="both", expand=True, ipady=15)
        
        sb_title = ctk.CTkLabel(stats_box, text="📈 HISTORICAL DRIVING STATISTICS", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#FFFFFF")
        sb_title.pack(anchor="w", padx=20, pady=(20, 15))
        
        metrics = [
            ("Simulator Runs Completed", f"{total_runs} games"),
            ("Estimated Time Behind Wheel", f"{total_duration // 60}m {total_duration % 60}s"),
            ("Average Drive Session Score", f"{avg_score} / 100"),
            ("Mean Steering Smoothness Accuracy", f"{avg_smoothness:.1f}%"),
            ("Mean Gesture Obstacle Evasion Time", f"{avg_reaction:.2f} seconds"),
            ("Achievements Unlocked Count", f"{self.get_unlocked_ach_count()} / {len(db.get_achievements())}")
        ]
        
        for label, val in metrics:
            row = ctk.CTkFrame(stats_box, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            
            lbl = ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11), text_color="#888888")
            lbl.pack(side="left")
            
            val_lbl = ctk.CTkLabel(row, text=val, font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color=colors["secondary"])
            val_lbl.pack(side="right")
            
            hr = ctk.CTkFrame(stats_box, fg_color="#12121e", height=1)
            hr.pack(fill="x", padx=15, pady=2)

    def get_rank_name(self, level: int) -> str:
        ranks = ["Beginner", "Learner", "Driver", "Professional", "Expert", "Elite", "Champion", "Legend", "Grand Master"]
        idx = min(len(ranks) - 1, (level - 1) // 2)
        return ranks[idx]

    def get_unlocked_ach_count(self) -> int:
        ach = db.get_achievements()
        return sum(1 for a in ach if a["unlocked"] == 1)
