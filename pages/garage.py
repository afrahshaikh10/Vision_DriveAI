import customtkinter as ctk
from typing import Any, Dict, List
from utils.db import db
from utils.theme_manager import get_theme_colors

THEME_SHOP = [
    {"name": "cyberpunk", "display": "🏍️ Cyberpunk (Neon)", "price": 0, "desc": "High-contrast neon pink and electric cyan grid design."},
    {"name": "blue", "display": "🔵 Blue Wave (Classic)", "price": 100, "desc": "Clean classic blue styling unlocked via License D progression."},
    {"name": "tesla", "display": "🔋 Tesla (Cyber)", "price": 100, "desc": "Clean gray tones with Tesla signature red accents."},
    {"name": "ferrari", "display": "🏎️ Ferrari (Rosso)", "price": 150, "desc": "Aggressive Italian racing red styling."},
    {"name": "minimal", "display": "⚪ Minimal (Monochrome)", "price": 200, "desc": "Pure stark monochrome design for minimal distractions."},
    {"name": "glass", "display": "💎 Glassmorphism", "price": 300, "desc": "Translucent icy cyan borders and frosted frames."},
    {"name": "night", "display": "🌙 Midnight Cruise", "price": 350, "desc": "Midnight navy blue grids with soft yellow markers."},
    {"name": "rain", "display": "🌧️ Wet Asphalt", "price": 400, "desc": "Deep stormy blue outlines matching rainy road tracks."},
    {"name": "neon", "display": "⚡ Acid Neon Grid", "price": 500, "desc": "Acid green borders with intense purple accents."},
    {"name": "future", "display": "🚀 Future Tech (HUD)", "price": 1000, "desc": "Hologram blue outlines with zero border padding."}
]

class GarageScreen(ctk.CTkFrame):
    """Theme unlock shop where players buy and equip UI styles using coins."""
    def __init__(self, parent: Any, user_data: Dict[str, Any], on_theme_equip_callback: callable):
        super().__init__(parent, fg_color="transparent")
        self.user_data = user_data
        self.on_theme_equip = on_theme_equip_callback
        
        self.setup_ui()

    def setup_ui(self) -> None:
        # Clear existing elements to support live redraws
        for widget in self.winfo_children():
            widget.destroy()
            
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        # Header Title
        header = ctk.CTkLabel(
            self,
            text="🏎️ GARAGE - THEME SHOP",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        coins = self.user_data.get("coins", 0)
        desc = ctk.CTkLabel(
            self,
            text=f"Redeem your driver coins to unlock new launcher styles. Current Balance: 💰 {coins} Coins",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        scroll.grid_columnconfigure((0, 1), weight=1)
        
        # Load themes from DB
        active_theme, unlocked_themes = db.get_user_themes(self.user_data["id"])
        
        # In case guest has not saved values, default cyberpunk is always unlocked
        if "cyberpunk" not in unlocked_themes:
            unlocked_themes.append("cyberpunk")
            
        self.status_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color="#FF007F")
        self.status_lbl.pack(pady=5)
        
        for idx, item in enumerate(THEME_SHOP):
            row = idx // 2
            col = idx % 2
            
            t_name = item["name"]
            is_unlocked = t_name in unlocked_themes
            is_active = t_name == active_theme
            
            # Card style
            card_colors = get_theme_colors(t_name)
            border_col = card_colors["border"] if is_active else ("#1b1836" if is_unlocked else "#0c0c16")
            bg_col = "#0f0f1b" if is_unlocked else "#050508"
            
            card = ctk.CTkFrame(
                scroll,
                fg_color=bg_col,
                border_color=border_col,
                border_width=1 if (is_active or is_unlocked) else 0.5,
                corner_radius=12,
                height=140
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            card.grid_propagate(False)
            
            title_text = item["display"].upper()
            if is_active:
                title_text += " [EQUIPPED]"
                
            title_lbl = ctk.CTkLabel(card, text=title_text, font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color=card_colors["accent"] if is_unlocked else "#5a5a66")
            title_lbl.pack(anchor="w", padx=15, pady=(12, 1))
            
            desc_lbl = ctk.CTkLabel(card, text=item["desc"], font=ctk.CTkFont(size=10), text_color="#888888" if is_unlocked else "#44444c", wraplength=260, justify="left")
            desc_lbl.pack(anchor="w", padx=15, pady=(2, 10))
            
            # Action row
            action_frame = ctk.CTkFrame(card, fg_color="transparent")
            action_frame.pack(fill="x", padx=15, side="bottom", pady=(0, 12))
            
            if is_active:
                status_badge = ctk.CTkLabel(action_frame, text="● ACTIVE THEME", font=ctk.CTkFont(size=10, weight="bold"), text_color="#00FF66")
                status_badge.pack(side="left")
            elif is_unlocked:
                equip_btn = ctk.CTkButton(
                    action_frame,
                    text="EQUIP THEME",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color="#121216",
                    hover_color=card_colors["accent"],
                    border_color="#1b1836",
                    border_width=1,
                    width=100,
                    height=24,
                    command=lambda t=t_name: self._equip_theme(t)
                )
                equip_btn.pack(side="right")
            else:
                price_text = f"💰 {item['price']} COINS"
                buy_btn = ctk.CTkButton(
                    action_frame,
                    text=price_text,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color=card_colors["accent"],
                    hover_color=card_colors["secondary"],
                    text_color="#080810" if t_name != "minimal" else "#000000",
                    width=110,
                    height=24,
                    command=lambda t=t_name, p=item["price"]: self._purchase_theme(t, p)
                )
                buy_btn.pack(side="right")

    def _purchase_theme(self, theme_name: str, price: int) -> None:
        user_id = self.user_data["id"]
        if db.unlock_theme(user_id, theme_name, price):
            # Update local coins cache
            updated_user = db.get_user_by_id(user_id)
            if updated_user:
                self.user_data["coins"] = updated_user["coins"]
            self.status_lbl.configure(text=f"Successfully unlocked {theme_name.upper()} theme!", text_color="#00FF66")
            self.setup_ui()
        else:
            self.status_lbl.configure(text="Insufficient coins to unlock theme.", text_color="#FF007F")

    def _equip_theme(self, theme_name: str) -> None:
        user_id = self.user_data["id"]
        if db.equip_theme(user_id, theme_name):
            self.user_data["active_theme"] = theme_name
            self.status_lbl.configure(text=f"Equipped {theme_name.upper()} theme configuration!", text_color="#00FF66")
            
            # Propagate up to main application to repaint highlights
            self.on_theme_equip(theme_name)
            self.setup_ui()
        else:
            self.status_lbl.configure(text="Error equipping theme.", text_color="#FF007F")
