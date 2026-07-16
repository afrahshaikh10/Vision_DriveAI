import customtkinter as ctk
import time
from typing import Any, Dict, List
from utils.db import db
from utils.theme_manager import get_theme_colors

class HomeDashboardScreen(ctk.CTkFrame):
    """Modern home dashboard displaying player level, progression, news, and stats summary."""
    def __init__(self, parent: Any, user_data: Dict[str, Any], navigate_callback: callable):
        super().__init__(parent, fg_color="transparent")
        self.user_data = user_data
        self.navigate = navigate_callback
        
        self.setup_ui()

    def setup_ui(self) -> None:
        self.grid_columnconfigure(0, weight=2) # Left: Profile, quick actions, news
        self.grid_columnconfigure(1, weight=1) # Right: Stats, weather, daily rewards
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT SIDE COLUMN ---
        left_col = ctk.CTkFrame(self, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=10)
        
        # Ensure daily goal is generated
        db.generate_daily_goal(self.user_data["id"])
        
        # Load fresh user data
        fresh_user = db.get_user_by_id(self.user_data["id"])
        if fresh_user:
            self.user_data = fresh_user
            
        lic_info = db.get_license_info(self.user_data["id"])
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)

        # 1. Welcome / Driver Overview Card
        welcome_card = ctk.CTkFrame(
            left_col, 
            fg_color="#0f0f1b", 
            border_color=colors["border"], 
            border_width=1, 
            corner_radius=15
        )
        welcome_card.pack(fill="x", pady=(0, 10), ipady=12)
        
        # Header: Good Morning, {name} ☀
        welcome_lbl = ctk.CTkLabel(
            welcome_card,
            text=f"Good Morning, {self.user_data.get('name', 'Driver')} ☀",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        welcome_lbl.pack(anchor="w", padx=20, pady=(15, 5))
        
        # Grid of Driver Stats
        stats_subgrid = ctk.CTkFrame(welcome_card, fg_color="transparent")
        stats_subgrid.pack(fill="x", padx=20, pady=5)
        stats_subgrid.columnconfigure((0, 1), weight=1)
        
        lic_val = lic_info.get("license_name", "License D")
        rank_val = self.get_rank_name(self.user_data.get("level", 1))
        
        from utils.weather import weather_manager
        weather_val = weather_manager.current_weather.upper()
        
        lic_lbl = ctk.CTkLabel(
            stats_subgrid, 
            text=f"🎖️ LICENSE: {lic_val}  |  🏆 RANK: {rank_val}", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color=colors["secondary"],
            anchor="w"
        )
        lic_lbl.grid(row=0, column=0, sticky="w")
        
        env_lbl = ctk.CTkLabel(
            stats_subgrid, 
            text=f"☁️ WEATHER: {weather_val}  |  💰 COINS: {self.user_data.get('coins', 0)}", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color="#F1C40F",
            anchor="e"
        )
        env_lbl.grid(row=0, column=1, sticky="e")
        
        # XP Level progression
        current_xp = lic_info.get("current_xp", 0)
        xp_required = lic_info.get("xp_required", 500)
        prog = min(1.0, current_xp / xp_required) if xp_required > 0 else 0
        
        prog_frame = ctk.CTkFrame(welcome_card, fg_color="transparent")
        prog_frame.pack(fill="x", padx=20, pady=(10, 2))
        
        lvl_lbl = ctk.CTkLabel(prog_frame, text=f"XP PROGRESSION TO NEXT LICENSE", font=ctk.CTkFont(family="Outfit", size=10, weight="bold"), text_color="#FFFFFF")
        lvl_lbl.pack(side="left")
        
        xp_lbl = ctk.CTkLabel(prog_frame, text=f"{current_xp} / {xp_required} XP", font=ctk.CTkFont(size=10), text_color="#888888")
        xp_lbl.pack(side="right")
        
        xp_bar = ctk.CTkProgressBar(welcome_card, progress_color=colors["accent"], fg_color="#12121e", height=8, corner_radius=4)
        xp_bar.pack(fill="x", padx=20, pady=(0, 10))
        xp_bar.set(prog)
        
        # Today's Goals (Daily Goals)
        goal_text = self.user_data.get("daily_goal_text", "No goal generated.")
        goal_target = self.user_data.get("daily_goal_target", 1)
        goal_progress = self.user_data.get("daily_goal_progress", 0)
        goal_completed = self.user_data.get("daily_goal_completed", 0)
        goal_xp = self.user_data.get("daily_goal_xp", 100)
        goal_coins = self.user_data.get("daily_goal_coins", 50)
        
        goal_frame = ctk.CTkFrame(welcome_card, fg_color="#12121e", corner_radius=10, border_color="#1b1836", border_width=1)
        goal_frame.pack(fill="x", padx=20, pady=(5, 5), ipady=6)
        
        goal_title_lbl = ctk.CTkLabel(goal_frame, text="🎯 TODAY'S GOAL", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color=colors["accent"])
        goal_title_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        
        if goal_completed == 1:
            goal_status_text = f"{goal_text}  (✓ COMPLETED)"
            status_color = "#00FF66"
        else:
            goal_status_text = f"{goal_text}  ({goal_progress} / {goal_target})"
            status_color = "#FFFFFF"
            
        goal_desc_lbl = ctk.CTkLabel(goal_frame, text=goal_status_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color)
        goal_desc_lbl.pack(anchor="w", padx=15)
        
        reward_txt = f"Reward: +{goal_xp} XP / +{goal_coins} Coins"
        goal_reward_lbl = ctk.CTkLabel(goal_frame, text=reward_txt, font=ctk.CTkFont(size=10), text_color="#888888")
        goal_reward_lbl.pack(anchor="w", padx=15, pady=(2, 5))
        
        # Next Unlock
        unlock_descriptions = {
            "License D": "Sunny Weather, Blue Theme, Challenge Pack 2, 'First Driver' Achievement",
            "License C": "Night Weather, Midnight Theme, Challenge Pack 3",
            "License B": "Rainy Weather, Wet Asphalt Theme, Challenge Pack 4",
            "License A": "Foggy Weather, Glassmorphism Theme, Challenge Pack 5",
            "International License": "Stormy Weather, Future Tech Theme",
            "Master License": "All unlocks complete!"
        }
        next_unlock_desc = unlock_descriptions.get(lic_val, "All unlocks complete!")
        
        unlock_frame = ctk.CTkFrame(welcome_card, fg_color="transparent")
        unlock_frame.pack(fill="x", padx=20, pady=(5, 0))
        
        unlock_icon_lbl = ctk.CTkLabel(unlock_frame, text="🔑 NEXT UNLOCK:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#888888")
        unlock_icon_lbl.pack(side="left")
        
        unlock_desc_lbl = ctk.CTkLabel(unlock_frame, text=next_unlock_desc, font=ctk.CTkFont(size=10, weight="bold"), text_color=colors["secondary"], wraplength=200, justify="left")
        unlock_desc_lbl.pack(side="left", padx=5)

        # 2. Main Quick-Actions Cards Row
        actions_grid = ctk.CTkFrame(left_col, fg_color="transparent")
        actions_grid.pack(fill="x", pady=5)
        actions_grid.columnconfigure((0, 1), weight=1)
        
        # Drive Card
        drive_action = ctk.CTkFrame(actions_grid, fg_color="#0f0f1b", border_color="#1b1836", border_width=1, corner_radius=10, height=110)
        drive_action.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        drive_action.grid_propagate(False)
        
        da_title = ctk.CTkLabel(drive_action, text="⚡ SIMULATOR SETUP", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#00FF66")
        da_title.pack(anchor="w", padx=15, pady=(12, 2))
        da_desc = ctk.CTkLabel(drive_action, text="Start camera calibration or drive freely.", font=ctk.CTkFont(size=10), text_color="#888888")
        da_desc.pack(anchor="w", padx=15)
        da_btn = ctk.CTkButton(drive_action, text="QUICK LAUNCH", width=120, height=24, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#00FF66", hover_color="#00CC52", text_color="#080810", command=lambda: self.navigate("drive"))
        da_btn.pack(anchor="w", padx=15, pady=(12, 10))
        
        # Challenge Card
        chal_action = ctk.CTkFrame(actions_grid, fg_color="#0f0f1b", border_color="#1b1836", border_width=1, corner_radius=10, height=110)
        chal_action.grid(row=0, column=1, padx=(5, 0), sticky="nsew")
        chal_action.grid_propagate(False)
        
        ca_title = ctk.CTkLabel(chal_action, text="🎯 TODAY'S CHALLENGE", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#FF007F")
        ca_title.pack(anchor="w", padx=15, pady=(12, 2))
        ca_desc = ctk.CTkLabel(chal_action, text="Level 1: Learning Steering - 100 XP.", font=ctk.CTkFont(size=10), text_color="#888888")
        ca_desc.pack(anchor="w", padx=15)
        ca_btn = ctk.CTkButton(chal_action, text="ACCEPT CHALLENGE", width=140, height=24, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#FF007F", hover_color="#CC0066", command=lambda: self.navigate("challenges"))
        ca_btn.pack(anchor="w", padx=15, pady=(12, 10))
        
        # 3. News / Activity Feed
        news_frame = ctk.CTkFrame(left_col, fg_color="#0f0f1b", border_color="#1b1836", border_width=1, corner_radius=12)
        news_frame.pack(fill="both", expand=True, pady=10)
        
        news_title = ctk.CTkLabel(news_frame, text="📰 SIMULATOR DAILY NEWS & UPDATES", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#FFFFFF")
        news_title.pack(anchor="w", padx=15, pady=(12, 10))
        
        news_list = [
            ("⚡ VisionDrive AI Launcher Refactor Active!", "You are now running on our game-launcher architecture! Unlock profile leveling, custom garage UI themes, and 10 dynamic challenges."),
            ("🏆 Global Leaderboards Open", "Compare steering precision and reactions against players globally. Complete perfect evasions in Highway Survival mode to top the charts!"),
            ("🚗 Cyberpunk Garage Theme Available", "Redeem your simulator coins in the Garage page to unlock neon color designs and custom weather backdrops.")
        ]
        
        for header, body in news_list:
            item_box = ctk.CTkFrame(news_frame, fg_color="#12121e", corner_radius=8)
            item_box.pack(fill="x", padx=15, pady=4, ipady=8)
            
            n_hdr = ctk.CTkLabel(item_box, text=header, font=ctk.CTkFont(size=11, weight="bold"), text_color="#00F5FF")
            n_hdr.pack(anchor="w", padx=12, pady=(6, 1))
            
            n_bdy = ctk.CTkLabel(item_box, text=body, font=ctk.CTkFont(size=10), text_color="#888888", wraplength=480, justify="left")
            n_bdy.pack(anchor="w", padx=12, pady=(1, 6))

        # --- RIGHT SIDE COLUMN ---
        right_col = ctk.CTkFrame(self, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=10)
        
        # 1. Profile / Stats Summary
        stats_frame = ctk.CTkFrame(right_col, fg_color="#0f0f1b", border_color="#1b1836", border_width=1, corner_radius=15)
        stats_frame.pack(fill="x", pady=(0, 10), ipady=10)
        
        sf_title = ctk.CTkLabel(stats_frame, text="📊 PERFORMANCE SUMMARY", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#FFFFFF")
        sf_title.pack(anchor="w", padx=15, pady=(15, 8))
        
        sessions = db.get_sessions(self.user_data["id"])
        total_runs = len(sessions)
        avg_score = 0
        max_score = 0
        if total_runs > 0:
            avg_score = int(sum(s["score"] for s in sessions) / total_runs)
            max_score = max(s["score"] for s in sessions)
            
        stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15)
        stats_grid.columnconfigure((0, 1), weight=1)
        
        self._add_dash_stat(stats_grid, "TOTAL RUNS", str(total_runs), 0, 0, "#00F5FF")
        self._add_dash_stat(stats_grid, "AVG SCORE", f"{avg_score}", 0, 1, "#00FF66")
        self._add_dash_stat(stats_grid, "HIGH SCORE", str(max_score), 1, 0, "#FF007F")
        self._add_dash_stat(stats_grid, "ACHIEVEMENTS", f"{self.get_unlocked_achievements_count()}", 1, 1, "#F1C40F")

        # 2. Simulator Weather Card
        weather_frame = ctk.CTkFrame(right_col, fg_color="#0f0f1b", border_color="#1b1836", border_width=1, corner_radius=15)
        weather_frame.pack(fill="x", pady=5, ipady=8)
        
        wf_title = ctk.CTkLabel(weather_frame, text="☁️ SIMULATOR ENVIRONMENT WEATHER", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#FFFFFF")
        wf_title.pack(anchor="w", padx=15, pady=(12, 2))
        
        from utils.weather import weather_manager
        current_weather = weather_manager.current_weather.upper()
        wf_state = ctk.CTkLabel(weather_frame, text=f"Current: {current_weather}", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), text_color="#00F5FF")
        wf_state.pack(anchor="w", padx=15, pady=(2, 6))
        
        wf_btn = ctk.CTkButton(weather_frame, text="Garage & Weather Settings", width=160, height=24, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#12121e", border_color="#1b1836", border_width=1, hover_color="#00F5FF", command=lambda: self.navigate("garage"))
        wf_btn.pack(anchor="w", padx=15, pady=5)

        # 3. Daily rewards / Progression claim
        rewards_frame = ctk.CTkFrame(right_col, fg_color="#0f0f1b", border_color="#1b1836", border_width=1, corner_radius=15)
        rewards_frame.pack(fill="both", expand=True, pady=(10, 0), ipady=10)
        
        rf_title = ctk.CTkLabel(rewards_frame, text="🎁 DAILY TRAINING REWARDS", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#FFFFFF")
        rf_title.pack(anchor="w", padx=15, pady=(15, 4))
        
        rf_desc = ctk.CTkLabel(rewards_frame, text="Claim your daily coin reward to spend in the Garage theme shop.", font=ctk.CTkFont(size=10), text_color="#888888", wraplength=200)
        rf_desc.pack(anchor="w", padx=15, pady=(0, 10))
        
        self.reward_btn = ctk.CTkButton(
            rewards_frame, 
            text="CLAIM 50 COINS", 
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            fg_color="#F1C40F", 
            hover_color="#D4AC0D", 
            text_color="#080810",
            command=self._claim_daily_rewards
        )
        self.reward_btn.pack(padx=15, pady=5, fill="x")
        
        self.reward_status = ctk.CTkLabel(rewards_frame, text="", font=ctk.CTkFont(size=10), text_color="#00FF66")
        self.reward_status.pack(pady=2)

    def _add_dash_stat(self, parent: Any, label: str, value: str, row: int, col: int, color: str) -> None:
        card = ctk.CTkFrame(parent, fg_color="#12121e", height=60, corner_radius=8)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        card.grid_propagate(False)
        
        lbl_lbl = ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=8, weight="bold"), text_color="#5a5a66")
        lbl_lbl.pack(anchor="w", padx=8, pady=(6, 0))
        
        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(family="Outfit", size=14, weight="bold"), text_color=color)
        lbl_val.pack(anchor="w", padx=8, pady=(0, 4))

    def get_rank_name(self, level: int) -> str:
        ranks = ["Beginner", "Learner", "Driver", "Professional", "Expert", "Elite", "Champion", "Legend", "Grand Master"]
        idx = min(len(ranks) - 1, (level - 1) // 2)
        return ranks[idx]

    def get_unlocked_achievements_count(self) -> int:
        ach = db.get_achievements()
        return sum(1 for a in ach if a["unlocked"] == 1)

    def _claim_daily_rewards(self) -> None:
        # Give 50 coins to player
        lvl, xp, coins = db.add_xp_coins(self.user_data["id"], 0, 50)
        self.user_data["coins"] = coins
        self.reward_btn.configure(state="disabled", text="CLAIMED")
        self.reward_status.configure(text="+50 Coins added to profile!")
        # Trigger update of home screen coins count
        self.setup_ui()
