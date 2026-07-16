import customtkinter as ctk
from typing import Any, Dict, List
from utils.db import db
from utils.theme_manager import get_theme_colors

CHALLENGES = [
    {"id": 1, "name": "Learning Steering", "difficulty": "Easy", "reward_xp": 100, "reward_coins": 50, "weather": "day", "target_score": 200, "desc": "Practice basic lane control and steering.", "est_time": "1 Min"},
    {"id": 2, "name": "Steering Accuracy", "difficulty": "Easy", "reward_xp": 150, "reward_coins": 75, "weather": "day", "target_score": 400, "desc": "Maintain lane centering discipline.", "est_time": "2 Min"},
    {"id": 3, "name": "Brake Master", "difficulty": "Medium", "reward_xp": 200, "reward_coins": 100, "weather": "day", "target_score": 600, "desc": "Evade obstacles using palm gesture brakes.", "est_time": "2 Min"},
    {"id": 4, "name": "Reaction Test", "difficulty": "Medium", "reward_xp": 250, "reward_coins": 125, "weather": "day", "target_score": 800, "desc": "Dodge fast obstacles with quick reaction times.", "est_time": "3 Min"},
    {"id": 5, "name": "Highway Survival", "difficulty": "Medium", "reward_xp": 300, "reward_coins": 150, "weather": "day", "target_score": 1000, "desc": "Survive the busy highway traffic lanes.", "est_time": "3 Min"},
    {"id": 6, "name": "Night Driver", "difficulty": "Hard", "reward_xp": 350, "reward_coins": 175, "weather": "night", "target_score": 1200, "desc": "Navigate traffic in dark night conditions.", "est_time": "4 Min"},
    {"id": 7, "name": "Rain Challenge", "difficulty": "Hard", "reward_xp": 400, "reward_coins": 200, "weather": "rain", "target_score": 1400, "desc": "Control your vehicle through heavy downpours.", "est_time": "4 Min"},
    {"id": 8, "name": "Fog Driver", "difficulty": "Hard", "reward_xp": 450, "reward_coins": 225, "weather": "fog", "target_score": 1600, "desc": "Drive safely in low-visibility dense fog.", "est_time": "4 Min"},
    {"id": 9, "name": "Obstacle Rush", "difficulty": "Expert", "reward_xp": 500, "reward_coins": 250, "weather": "night", "target_score": 2000, "desc": "Dodge waves of oncoming obstacles.", "est_time": "5 Min"},
    {"id": 10, "name": "Master Driver Test", "difficulty": "Expert", "reward_xp": 1000, "reward_coins": 500, "weather": "rain", "target_score": 3000, "desc": "The ultimate highway storm survival test.", "est_time": "5 Min"}
]

class ChallengesScreen(ctk.CTkFrame):
    """Sleek Challenge Mode page displaying 10 challenges with stars and progression logs."""
    def __init__(self, parent: Any, user_data: Dict[str, Any], start_challenge_callback: callable):
        super().__init__(parent, fg_color="transparent")
        self.user_data = user_data
        self.start_challenge = start_challenge_callback
        
        self.setup_ui()

    def setup_ui(self) -> None:
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        # Title Header
        header = ctk.CTkLabel(
            self,
            text="🎯 TRAINING CHALLENGES",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        desc = ctk.CTkLabel(
            self,
            text="Complete driver challenges to earn XP, coins, and unlock new simulation levels.",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        # Scrollable grid of challenges
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        scroll.grid_columnconfigure((0, 1), weight=1)
        
        # Load progress from DB
        progress = db.get_challenge_progress(self.user_data["id"])
        prog_map = {p["challenge_id"]: p for p in progress}
        
        # Check unlock status of challenges based on current license
        lic_name = self.user_data.get("current_license", "License D")
        license_tiers = ["License D", "License C", "License B", "License A", "International License", "Master License"]
        lic_index = license_tiers.index(lic_name) if lic_name in license_tiers else 0
        
        def is_challenge_unlocked(c_id: int) -> bool:
            if c_id in [1, 2]:
                required_idx = 0  # License D
            elif c_id in [3, 4]:
                required_idx = 1  # License C
            elif c_id in [5, 6]:
                required_idx = 2  # License B
            elif c_id in [7, 8]:
                required_idx = 3  # License A
            elif c_id == 9:
                required_idx = 4  # International License
            elif c_id == 10:
                required_idx = 5  # Master License
            else:
                required_idx = 0
            return lic_index >= required_idx

        for idx, chal in enumerate(CHALLENGES):
            row = idx // 2
            col = idx % 2
            
            c_id = chal["id"]
            is_unlocked = is_challenge_unlocked(c_id)
            
            chal_prog = prog_map.get(c_id, {"best_score": 0, "stars": 0, "completed": 0})
            best_score = chal_prog["best_score"]
            completion_pct = 100 if chal_prog["completed"] == 1 else 0
            
            # Card styling
            bg_col = "#0f0f1b" if is_unlocked else "#06060c"
            border_col = colors["border"] if is_unlocked else "#1b1836"
            
            card = ctk.CTkFrame(
                scroll,
                fg_color=bg_col,
                border_color=border_col,
                border_width=1,
                corner_radius=12,
                height=180
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            card.grid_propagate(False)
            
            # Title
            title_text = f"LEVEL {c_id}: {chal['name'].upper()}"
            title_lbl = ctk.CTkLabel(card, text=title_text, font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#FFFFFF" if is_unlocked else "#5a5a66")
            title_lbl.pack(anchor="w", padx=15, pady=(10, 1))
            
            # Row 1: Difficulty (★ to ★★★★★) & Reward (XP + Coins)
            meta_frame1 = ctk.CTkFrame(card, fg_color="transparent")
            meta_frame1.pack(fill="x", padx=15, pady=1)
            
            diff_stars = "★☆☆☆☆"
            diff_color = "#00FF66"
            if chal["difficulty"] == "Medium":
                diff_stars = "★★★☆☆"
                diff_color = "#F1C40F"
            elif chal["difficulty"] == "Hard":
                diff_stars = "★★★★☆"
                diff_color = "#FF007F"
            elif chal["difficulty"] == "Expert":
                diff_stars = "★★★★★"
                diff_color = "#E82127"
                
            diff_lbl = ctk.CTkLabel(meta_frame1, text=f"Difficulty: {diff_stars}", font=ctk.CTkFont(size=10, weight="bold"), text_color=diff_color if is_unlocked else "#5a5a66")
            diff_lbl.pack(side="left")
            
            reward_lbl = ctk.CTkLabel(meta_frame1, text=f"🎁 {chal['reward_xp']} XP + {chal['reward_coins']} Coins", font=ctk.CTkFont(size=10, weight="bold"), text_color="#FFFFFF" if is_unlocked else "#5a5a66")
            reward_lbl.pack(side="right")
            
            # Row 2: Est. Time & Completion %
            meta_frame2 = ctk.CTkFrame(card, fg_color="transparent")
            meta_frame2.pack(fill="x", padx=15, pady=1)
            
            time_lbl = ctk.CTkLabel(meta_frame2, text=f"⏱️ Est. Time: {chal['est_time']}", font=ctk.CTkFont(size=10), text_color="#888888" if is_unlocked else "#44444c")
            time_lbl.pack(side="left")
            
            comp_lbl = ctk.CTkLabel(meta_frame2, text=f"Completion: {completion_pct}%", font=ctk.CTkFont(size=10), text_color="#888888" if is_unlocked else "#44444c")
            comp_lbl.pack(side="right")
            
            # Row 3: Best Score
            stats_frame = ctk.CTkFrame(card, fg_color="transparent")
            stats_frame.pack(fill="x", padx=15, pady=2)
            
            score_lbl = ctk.CTkLabel(stats_frame, text=f"🏆 Best Score: {best_score} pts", font=ctk.CTkFont(size=10), text_color=colors["secondary"] if is_unlocked else "#44444c")
            score_lbl.pack(side="left")
            
            # Buttons / Labels
            action_frame = ctk.CTkFrame(card, fg_color="transparent")
            action_frame.pack(fill="x", padx=15, pady=(8, 10))
            
            if is_unlocked:
                if completion_pct == 100:
                    comp_badge = ctk.CTkLabel(action_frame, text="✓ COMPLETED", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00FF66")
                    comp_badge.pack(side="left")
                    
                    retry_btn = ctk.CTkButton(
                        action_frame,
                        text="RETRY",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        fg_color="#12121e",
                        hover_color=colors["accent"],
                        border_color="#1b1836",
                        border_width=1,
                        width=70,
                        height=24,
                        command=lambda c=chal: self.start_challenge(c)
                    )
                    retry_btn.pack(side="right")
                else:
                    start_btn = ctk.CTkButton(
                        action_frame,
                        text="START",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        fg_color=colors["accent"],
                        hover_color=colors["secondary"],
                        text_color="#080810" if theme != "minimal" else "#000000",
                        width=80,
                        height=24,
                        command=lambda c=chal: self.start_challenge(c)
                    )
                    start_btn.pack(side="right")
            else:
                lock_lbl = ctk.CTkLabel(action_frame, text="🔒 LOCKED", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#FF4B4B")
                lock_lbl.pack(side="right")
