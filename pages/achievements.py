import customtkinter as ctk
from typing import Any, Dict
from utils.db import db
from utils.theme_manager import get_theme_colors

class AchievementsScreen(ctk.CTkFrame):
    """Sleek Achievements page showing unlocked badge cards with neon styling."""
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
            text="🏆 DRIVER ACHIEVEMENTS & BADGES",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        desc = ctk.CTkLabel(
            self,
            text="Unlock awards by demonstrating elite steering, braking, and lane discipline.",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        scroll.grid_columnconfigure((0, 1), weight=1)
        
        # Fetch achievements
        achievements = db.get_achievements()
        
        for idx, ach in enumerate(achievements):
            row = idx // 2
            col = idx % 2
            
            unlocked = ach["unlocked"] == 1
            border_col = colors["border"] if unlocked else "#1b1836"
            bg_col = "#0f0f1b" if unlocked else "#050508"
            
            badge_card = ctk.CTkFrame(
                scroll, fg_color=bg_col, border_color=border_col, border_width=1, corner_radius=10, height=90
            )
            badge_card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            badge_card.grid_propagate(False)
            
            status_text = f"🏆 UNLOCKED at {ach['unlocked_at']}" if unlocked else "🔒 LOCKED"
            status_color = "#00FF66" if unlocked else "#5a5a66"
            
            lbl_title = ctk.CTkLabel(badge_card, text=ach["name"].upper(), font=ctk.CTkFont(family="Outfit", size=12, weight="bold"), text_color="#FFFFFF" if unlocked else "#5a5a66")
            lbl_title.pack(anchor="w", padx=12, pady=(8, 0))
            
            lbl_desc = ctk.CTkLabel(badge_card, text=ach["description"], font=ctk.CTkFont(family="Outfit", size=10), text_color="#888888" if unlocked else "#44444c")
            lbl_desc.pack(anchor="w", padx=12, pady=(2, 0))
            
            lbl_status = ctk.CTkLabel(badge_card, text=status_text, font=ctk.CTkFont(family="Consolas", size=9, weight="bold"), text_color=status_color)
            lbl_status.pack(anchor="w", padx=12, pady=(4, 8))
