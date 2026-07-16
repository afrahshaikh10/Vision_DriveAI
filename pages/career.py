import customtkinter as ctk
import math
from typing import Any, Dict, List
from utils.theme_manager import get_theme_colors

class CareerScreen(ctk.CTkFrame):
    """Visualizes the player's progression through simulator ranks (Beginner -> Grand Master)."""
    def __init__(self, parent: Any, user_data: Dict[str, Any]):
        super().__init__(parent, fg_color="transparent")
        self.user_data = user_data
        
        self.ranks = [
            {"name": "Beginner", "lvl_req": 1, "desc": "Start your journey in driving physics."},
            {"name": "Learner", "lvl_req": 3, "desc": "Master basic steering controls."},
            {"name": "Driver", "lvl_req": 5, "desc": "Navigate highways with traffic flow."},
            {"name": "Professional", "lvl_req": 7, "desc": "Engage under adverse conditions."},
            {"name": "Expert", "lvl_req": 9, "desc": "React fast in obstacle rushes."},
            {"name": "Elite", "lvl_req": 11, "desc": "Unlock highest lane discipline precision."},
            {"name": "Champion", "lvl_req": 13, "desc": "Race flawlessly on rain and storm modes."},
            {"name": "Legend", "lvl_req": 15, "desc": "Recognized driver across global tracks."},
            {"name": "Grand Master", "lvl_req": 17, "desc": "Perfect reflexes, absolute simulator legend."}
        ]
        
        self.setup_ui()

    def setup_ui(self) -> None:
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        # Header Title
        header = ctk.CTkLabel(
            self,
            text="🏆 DRIVER CAREER PATHWAY",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        desc = ctk.CTkLabel(
            self,
            text="Gain XP and level up to climb the professional driver rankings.",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        # Canvas for Drawing Career Path Roadmap Line
        self.canvas_width = 800
        self.canvas_height = 420
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        canvas_box = ctk.CTkFrame(scroll, fg_color="#0a0a0f", border_width=1, border_color="#1b1836", corner_radius=15)
        canvas_box.pack(pady=10, fill="both", expand=True)
        
        self.canvas = ctk.CTkCanvas(canvas_box, width=self.canvas_width, height=self.canvas_height, bg="#0a0a0f", highlightthickness=0)
        self.canvas.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.draw_roadmap(colors)

    def draw_roadmap(self, colors: dict) -> None:
        user_level = self.user_data.get("level", 1)
        
        # Grid Coordinates for Nodes (Zig-zag timeline)
        node_coords = [
            (60, 210),   # 1. Beginner
            (140, 100),  # 2. Learner
            (220, 210),  # 3. Driver
            (300, 320),  # 4. Professional
            (380, 210),  # 5. Expert
            (460, 100),  # 6. Elite
            (540, 210),  # 7. Champion
            (620, 320),  # 8. Legend
            (700, 210)   # 9. Grand Master
        ]
        
        # 1. Draw glowing background connecting lines
        for i in range(len(node_coords) - 1):
            x1, y1 = node_coords[i]
            x2, y2 = node_coords[i+1]
            
            req_next = self.ranks[i+1]["lvl_req"]
            unlocked = user_level >= req_next
            
            line_color = colors["accent"] if unlocked else "#1b1836"
            line_w = 4 if unlocked else 2
            
            # Glow backing line
            if unlocked:
                self.canvas.create_line(x1, y1, x2, y2, fill=colors["secondary"], width=line_w + 3, stipple="gray25")
            self.canvas.create_line(x1, y1, x2, y2, fill=line_color, width=line_w)

        # 2. Draw nodes
        for idx, rank in enumerate(self.ranks):
            x, y = node_coords[idx]
            req = rank["lvl_req"]
            is_unlocked = user_level >= req
            is_current = False
            
            # Check if this is the active current rank
            if is_unlocked:
                if idx == len(self.ranks) - 1 or user_level < self.ranks[idx+1]["lvl_req"]:
                    is_current = True
                    
            # Node aesthetics
            r = 16 if is_current else 10
            node_color = colors["accent"] if is_current else (colors["secondary"] if is_unlocked else "#12121e")
            border_color = "#FFFFFF" if is_current else (colors["border"] if is_unlocked else "#1b1836")
            
            # Draw glow circle
            if is_current:
                self.canvas.create_oval(x - r - 6, y - r - 6, x + r + 6, y + r + 6, fill="", outline=colors["secondary"], width=2)
                
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=node_color, outline=border_color, width=2 if is_unlocked else 1)
            
            # Rank label Text
            txt_color = "#FFFFFF" if is_unlocked else "#5a5a66"
            font_w = "bold" if is_current else "normal"
            self.canvas.create_text(x, y - r - 12, text=rank["name"].upper(), font=("Outfit", 9, font_w), fill=txt_color)
            
            # Requirement badge below node
            self.canvas.create_text(x, y + r + 12, text=f"Lvl {req}", font=("Consolas", 8), fill="#888888" if is_unlocked else "#44444c")
            
            # Tooltip details on cursor hover or simple label details in corners
            if is_current:
                # Highlighted details box inside canvas
                self.canvas.create_rectangle(10, 360, 790, 410, fill="#0f0f1b", outline=colors["border"], width=1)
                self.canvas.create_text(400, 385, text=f"CURRENT STATUS: {rank['name'].upper()} (Level {user_level}) - {rank['desc']}", font=("Outfit", 11, "bold"), fill="#00FF66")
