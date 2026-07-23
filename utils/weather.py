import random
import math
from typing import List, Dict, Any, Tuple

def lerp_color(hex1: str, hex2: str, t: float) -> str:
    """Linearly interpolates between two hex colors."""
    try:
        h1 = hex1.lstrip('#')
        h2 = hex2.lstrip('#')
        
        # Default fallback if formats are invalid
        if len(h1) != 6 or len(h2) != 6:
            return hex1
            
        r1, g1, b1 = int(h1[0:2], 16), int(h1[2:4], 16), int(h1[4:6], 16)
        r2, g2, b2 = int(h2[0:2], 16), int(h2[2:4], 16), int(h2[4:6], 16)
        
        r = max(0, min(255, int(r1 + (r2 - r1) * t)))
        g = max(0, min(255, int(g1 + (g2 - g1) * t)))
        b = max(0, min(255, int(b1 + (b2 - b1) * t)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex1

class WeatherThemeManager:
    """Manages weather parameters, color palettes, and physics particles for backgrounds."""
    def __init__(self):
        self.weather_modes = ["morning", "sunny", "evening", "night", "rain", "storm", "fog", "snow"]
        self.current_weather = "night"
        self.target_weather = "night"
        self.transition_t = 1.0  # 1.0 means fully transitioned
        self.transition_speed = 0.05  # Steps per tick (20fps tick in main UI)
        
        # Color definitions for UI elements
        # Palettes contain keys: [bg_gradient_start, bg_gradient_end, border_highlight, primary_neon, text_color]
        self.palettes = {
            "morning": {
                "bg_start": "#1e1035", "bg_end": "#321d54",
                "border": "#ff7597", "accent": "#ff9ebb", "text": "#ffffff"
            },
            "sunny": {
                "bg_start": "#0a1c3a", "bg_end": "#173b75",
                "border": "#00f5ff", "accent": "#ffd700", "text": "#ffffff"
            },
            "evening": {
                "bg_start": "#2a0845", "bg_end": "#6441a5",
                "border": "#ff007f", "accent": "#ff8c00", "text": "#ffffff"
            },
            "night": {
                "bg_start": "#030308", "bg_end": "#0b0c16",
                "border": "#1b1836", "accent": "#00f5ff", "text": "#ffffff"
            },
            "rain": {
                "bg_start": "#06060c", "bg_end": "#101424",
                "border": "#ff007f", "accent": "#00f5ff", "text": "#cbd5e1"
            },
            "storm": {
                "bg_start": "#030306", "bg_end": "#0a0a0f",
                "border": "#7d12ff", "accent": "#ffff00", "text": "#94a3b8"
            },
            "fog": {
                "bg_start": "#0f1115", "bg_end": "#1c1f26",
                "border": "#475569", "accent": "#a1a1aa", "text": "#e4e4e7"
            },
            "snow": {
                "bg_start": "#0b132b", "bg_end": "#1c2541",
                "border": "#38bdf8", "accent": "#ffffff", "text": "#ffffff"
            }
        }
        
        # Particle arrays
        self.particles: List[Dict[str, Any]] = []
        self.lightning_flash = 0.0  # Ambient flash brightness for Storm weather

    def set_weather(self, mode: str) -> None:
        """Trigger smooth fade transition to target weather mode."""
        if mode in self.weather_modes and mode != self.target_weather:
            self.target_weather = mode
            self.transition_t = 0.0

    def update(self, w: int, h: int, speed_mph: float) -> None:
        """Update transitions and particle physics states."""
        # 1. Update Transition Fade Interpolation
        if self.transition_t < 1.0:
            self.transition_t = min(1.0, self.transition_t + self.transition_speed)
            if self.transition_t >= 1.0:
                self.current_weather = self.target_weather

        # 2. Update Lightning Flashes for Storm Mode
        if self.target_weather == "storm" or self.current_weather == "storm":
            if self.lightning_flash > 0.0:
                self.lightning_flash = max(0.0, self.lightning_flash - 0.12)
            elif random.random() < 0.015:  # 1.5% chance per tick to trigger flash
                self.lightning_flash = 1.0

        # 3. Spawn and update ambient environment particles based on target mode
        self._update_particles(w, h, speed_mph)

    def get_color(self, key: str) -> str:
        """Gets current color, smoothly blending during active fade transitions."""
        c_curr = self.palettes[self.current_weather][key]
        c_targ = self.palettes[self.target_weather][key]
        if self.transition_t >= 1.0:
            return c_targ
        return lerp_color(c_curr, c_targ, self.transition_t)

    def _update_particles(self, w: int, h: int, speed_mph: float) -> None:
        # Determine particle limit and spawn rate based on weather
        target_count = 15
        if self.target_weather in ["rain", "snow", "storm"]:
            target_count = 35
        elif self.target_weather == "fog":
            target_count = 10
            
        # Prune dead particles
        self.particles = [p for p in self.particles if p["y"] < h + 20 and p["x"] > -20 and p["x"] < w + 20]
        
        # Spawn to maintain count
        while len(self.particles) < target_count:
            # Random initial position
            px = random.uniform(0, w)
            py = random.uniform(-50, h) if not self.particles else random.uniform(-50, 0)
            
            # Select particle type based on target weather
            if self.target_weather == "snow":
                self.particles.append({
                    "x": px, "y": py,
                    "vx": random.uniform(-0.5, 0.5), "vy": random.uniform(1.2, 2.5),
                    "size": random.uniform(2.0, 5.0), "color": "#FFFFFF", "type": "snow"
                })
            elif self.target_weather in ["rain", "storm"]:
                self.particles.append({
                    "x": px, "y": py,
                    "vx": -1.5, "vy": random.uniform(8.0, 15.0),
                    "size": random.uniform(1.0, 2.5), "color": "#78a5c2" if self.target_weather == "rain" else "#cbd5e1",
                    "type": "rain"
                })
            elif self.target_weather == "fog":
                self.particles.append({
                    "x": px, "y": py,
                    "vx": random.uniform(-0.3, 0.3), "vy": random.uniform(0.2, 0.6),
                    "size": random.uniform(40.0, 80.0), "color": "#334155", "type": "fog"
                })
            elif self.target_weather == "morning":
                # Floating pinkish dust/leaves particles
                self.particles.append({
                    "x": px, "y": py,
                    "vx": random.uniform(-0.5, 0.8), "vy": random.uniform(0.6, 1.4),
                    "size": random.uniform(3.0, 6.0), "color": random.choice(["#ff7597", "#fca5a5", "#fde047"]),
                    "type": "leaf"
                })
            else:  # Night or general ambient stars
                self.particles.append({
                    "x": px, "y": py,
                    "vx": 0.0, "vy": random.uniform(0.05, 0.2),
                    "size": random.uniform(1.0, 2.5), "color": random.choice(["#ffffff", "#e0f2fe", "#00f5ff"]),
                    "type": "star"
                })

        # Update particle physics step
        speed_modifier = 1.0 + (speed_mph / 30.0)
        for p in self.particles:
            if p["type"] == "rain":
                p["y"] += p["vy"] * speed_modifier
                p["x"] += p["vx"]
            elif p["type"] == "snow":
                p["y"] += p["vy"] * speed_modifier * 0.7
                p["x"] += p["vx"] + math.sin(p["y"] / 15.0) * 0.3  # sway
            elif p["type"] == "fog":
                p["y"] += p["vy"]
                p["x"] += p["vx"]
            elif p["type"] == "leaf":
                p["y"] += p["vy"] * speed_modifier * 0.8
                p["x"] += p["vx"] + math.sin(p["y"] / 10.0) * 0.4
            else:  # Stars / floating dust
                p["y"] += p["vy"] * speed_modifier * 0.2
                if p["y"] > h:
                    p["y"] = -10.0

    def draw(self, canvas: Any, w: int, h: int) -> None:
        """Renders ambient textures onto the back canvas."""
        # 1. Draw lightning flash overlays (Storm Mode)
        if self.lightning_flash > 0.0:
            flash_opacity = int(self.lightning_flash * 255)
            # Draw flash rectangle
            canvas.create_rectangle(0, 0, w, h, fill="#ffffff", outline="")
            return

        # 2. Draw particle shapes
        for p in self.particles:
            x, y, sz = p["x"], p["y"], p["size"]
            
            if p["type"] == "rain":
                # Draw streak lines
                canvas.create_line(x, y, x - 2, y + 8, fill=p["color"], width=1)
            elif p["type"] in ["snow", "leaf"]:
                # Draw circular flakes/leaves
                canvas.create_oval(x - sz/2, y - sz/2, x + sz/2, y + sz/2, fill=p["color"], outline="")
            elif p["type"] == "fog":
                # Draw fog bounds (large soft blocks using canvas stipples if supported, or just light filled circles)
                # To prevent performance lags, draw fewer large soft ovals
                # On Windows, stippling can cause severe GUI lag. Use outline instead.
                import platform
                if platform.system() == "Windows":
                    canvas.create_oval(x - sz, y - sz, x + sz, y + sz, fill="", outline=p["color"], width=1)
                else:
                    canvas.create_oval(x - sz, y - sz, x + sz, y + sz, fill=p["color"], outline="", stipple="gray12")
            else:  # Stars
                canvas.create_oval(x, y, x + sz, y + sz, fill=p["color"], outline="")

# Global manager instance
weather_manager = WeatherThemeManager()
