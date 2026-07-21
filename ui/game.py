import random
import math
import time
import os
import pygame
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk
from typing import List, Tuple, Dict, Any, Optional
from utils.logger import logger
from utils.sound_manager import sound_manager

class RetroRacingGame(ctk.CTkFrame):
    """A high-performance arcade racing game component powered by a Pygame Off-Screen Surface Engine,
    featuring perspective road projection, sprite rendering, sky modes, parallax layers, and particle effects."""
    
    def __init__(self, parent: Any):
        super().__init__(parent, corner_radius=15, fg_color="#1E1E24", border_color="#2D2D35", border_width=2)
        
        # Base virtual canvas resolution
        self.vw = 360
        self.vh = 450

        # Pygame Off-Screen Surface & Fonts Initialization
        pygame.init()
        self.pg_surface = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
        self._init_fonts()

        # Game State Variables
        self.game_started = False
        self.game_running = False
        self.game_over = False
        self.score = 0
        self.high_score = 0
        self.speed_mph = 0.0
        self.target_speed_mph = 0.0
        
        # Player position & animation physics
        self.player_x = 180.0  # Range: 50 to 350
        self.player_y = 390.0
        self.player_width = 28
        self.player_height = 46
        self.car_tilt = 0.0    # Visual chassis tilt angle
        self.wheel_angle = 0.0 # Rotating wheel animation angle
        
        # Inputs states
        self.keys_pressed = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "space": False,
            "shift": False
        }
        
        # Track items
        self.obstacles: List[Dict[str, Any]] = []
        self.road_markings: List[float] = [0.0, 100.0, 200.0, 300.0, 400.0]
        self.spawn_timer = 0
        self.obstacle_counter = 0

        # Environment & Roadside Elements (Trees, Lights, Clouds)
        self.weather_modes = ["day", "sunset", "night", "rain", "fog"]
        self.current_weather = "night"
        
        self.clouds: List[Dict[str, Any]] = []
        self._init_clouds()
        
        self.roadside_objects: List[Dict[str, Any]] = []
        self.roadside_timer = 0

        # Screen shake state
        self.shake_remaining = 0
        self.shake_intensity = 0.0

        # Particle systems
        self.rain_drops: List[Dict[str, Any]] = []
        self.rain_splashes: List[Dict[str, Any]] = []
        self.tire_smoke: List[Dict[str, Any]] = []
        self.nitro_sparks: List[Dict[str, Any]] = []
        self.explosion_particles: List[Dict[str, Any]] = []

        # Driving Coach status overlays
        self.coach_message = ""
        self.coach_timer = 0
        
        # Canvas PhotoImage Cache
        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self.canvas_img_id: Optional[int] = None
        
        # Generate Procedural Sprites
        self._generate_sprites()

        self.setup_ui()
        self.after(500, self.bind_controls)

    def _init_fonts(self) -> None:
        """Initializes Pygame fonts with fallback fonts."""
        try:
            self.font_title = pygame.font.SysFont("Impact", 22)
            self.font_hud = pygame.font.SysFont("Trebuchet MS", 11, bold=True)
            self.font_hud_sm = pygame.font.SysFont("Trebuchet MS", 9, bold=True)
            self.font_stat = pygame.font.SysFont("Consolas", 10, bold=True)
        except Exception:
            self.font_title = pygame.font.Font(None, 24)
            self.font_hud = pygame.font.Font(None, 14)
            self.font_hud_sm = pygame.font.Font(None, 11)
            self.font_stat = pygame.font.Font(None, 12)

    def _init_clouds(self) -> None:
        self.clouds.clear()
        for _ in range(6):
            self.clouds.append({
                "x": random.uniform(-20, self.vw + 20),
                "y": random.uniform(5, 75),
                "scale": random.uniform(0.6, 1.3),
                "speed": random.uniform(0.15, 0.45)
            })

    def _generate_sprites(self) -> None:
        """Generates crisp procedural arcade sprites for sports cars, buses, semi-trucks, trees, and streetlights."""
        self.sprites = {}

        # 1. Player Supercar Sprite (Red/Gold, sleek aerodynamic chassis)
        car_surf = pygame.Surface((32, 52), pygame.SRCALPHA)
        # Shadow
        pygame.draw.ellipse(car_surf, (5, 5, 10, 140), (2, 38, 28, 12))
        # Tires
        pygame.draw.rect(car_surf, (20, 20, 25), (0, 6, 6, 12), border_radius=2)
        pygame.draw.rect(car_surf, (20, 20, 25), (26, 6, 6, 12), border_radius=2)
        pygame.draw.rect(car_surf, (20, 20, 25), (0, 34, 6, 12), border_radius=2)
        pygame.draw.rect(car_surf, (20, 20, 25), (26, 34, 6, 12), border_radius=2)
        # Body Shell
        pygame.draw.rect(car_surf, (230, 40, 40), (4, 2, 24, 46), border_radius=6)
        # Hood lines & Carbon accent
        pygame.draw.polygon(car_surf, (180, 20, 20), [(10, 4), (22, 4), (18, 16), (14, 16)])
        # Roof & Cabin Windshield
        pygame.draw.polygon(car_surf, (20, 30, 45), [(7, 14), (25, 14), (22, 28), (10, 28)])
        pygame.draw.polygon(car_surf, (60, 180, 230, 160), [(8, 15), (24, 15), (22, 21), (10, 21)]) # Reflection
        # Headlights (Gold glow)
        pygame.draw.circle(car_surf, (255, 240, 150), (7, 4), 2)
        pygame.draw.circle(car_surf, (255, 240, 150), (25, 4), 2)
        # Rear Spoiler
        pygame.draw.rect(car_surf, (30, 30, 35), (3, 45, 26, 4), border_radius=1)
        # Brake Lights
        pygame.draw.rect(car_surf, (255, 30, 30), (5, 44, 4, 2))
        pygame.draw.rect(car_surf, (255, 30, 30), (23, 44, 4, 2))
        self.sprites["player_car"] = car_surf

        # Nitro Variant Player Car Body (Golden Orange)
        nitro_car = car_surf.copy()
        pygame.draw.rect(nitro_car, (255, 140, 0), (4, 2, 24, 46), border_radius=6)
        pygame.draw.polygon(nitro_car, (200, 100, 0), [(10, 4), (22, 4), (18, 16), (14, 16)])
        self.sprites["player_nitro"] = nitro_car

        # 2. AI Traffic Car Sprites (5 Colors/Styles)
        ai_colors = [
            ("#3498DB", (52, 152, 219)),  # Cyan Sports Sedan
            ("#9B59B6", (155, 89, 182)),  # Purple Coupe
            ("#E67E22", (230, 126, 34)),  # Orange Muscle Car
            ("#E74C3C", (231, 76, 60)),   # Red Hatchback
            ("#1ABC9C", (26, 188, 156))   # Emerald SUV
        ]
        self.sprites["ai_cars"] = []
        for name, rgb in ai_colors:
            ai_s = pygame.Surface((30, 48), pygame.SRCALPHA)
            # Tires
            pygame.draw.rect(ai_s, (15, 15, 18), (0, 6, 5, 10), border_radius=2)
            pygame.draw.rect(ai_s, (15, 15, 18), (25, 6, 5, 10), border_radius=2)
            pygame.draw.rect(ai_s, (15, 15, 18), (0, 32, 5, 10), border_radius=2)
            pygame.draw.rect(ai_s, (15, 15, 18), (25, 32, 5, 10), border_radius=2)
            # Body
            pygame.draw.rect(ai_s, rgb, (3, 2, 24, 44), border_radius=5)
            pygame.draw.rect(ai_s, (int(rgb[0]*0.7), int(rgb[1]*0.7), int(rgb[2]*0.7)), (6, 4, 18, 12), border_radius=3)
            # Windshield & Windows
            pygame.draw.polygon(ai_s, (30, 35, 45), [(6, 14), (24, 14), (21, 26), (9, 26)])
            # Taillights
            pygame.draw.rect(ai_s, (240, 40, 40), (4, 43, 5, 2))
            pygame.draw.rect(ai_s, (240, 40, 40), (21, 43, 5, 2))
            self.sprites["ai_cars"].append(ai_s)

        # 3. City Bus Sprite (Yellow Body, Long Chassis)
        bus_s = pygame.Surface((34, 74), pygame.SRCALPHA)
        # Double Tires
        pygame.draw.rect(bus_s, (15, 15, 18), (0, 10, 5, 14), border_radius=2)
        pygame.draw.rect(bus_s, (15, 15, 18), (29, 10, 5, 14), border_radius=2)
        pygame.draw.rect(bus_s, (15, 15, 18), (0, 48, 5, 12), border_radius=2)
        pygame.draw.rect(bus_s, (15, 15, 18), (29, 48, 5, 12), border_radius=2)
        pygame.draw.rect(bus_s, (15, 15, 18), (0, 58, 5, 12), border_radius=2)
        pygame.draw.rect(bus_s, (15, 15, 18), (29, 58, 5, 12), border_radius=2)
        # Body (Yellow City Bus)
        pygame.draw.rect(bus_s, (245, 180, 20), (3, 2, 28, 70), border_radius=6)
        # Roof Vents
        pygame.draw.rect(bus_s, (210, 150, 15), (8, 4, 18, 10), border_radius=3)
        pygame.draw.rect(bus_s, (210, 150, 15), (8, 30, 18, 12), border_radius=3)
        # Windshield
        pygame.draw.rect(bus_s, (30, 40, 55), (6, 16, 22, 10), border_radius=2)
        # Side Windows
        for wy in range(28, 62, 8):
            pygame.draw.rect(bus_s, (40, 50, 65), (4, wy, 4, 6))
            pygame.draw.rect(bus_s, (40, 50, 65), (26, wy, 4, 6))
        # Rear Taillights
        pygame.draw.rect(bus_s, (255, 30, 30), (5, 69, 6, 2))
        pygame.draw.rect(bus_s, (255, 30, 30), (23, 69, 6, 2))
        self.sprites["bus"] = bus_s

        # 4. Heavy Cargo Semi-Truck Sprite (Silver Cargo Container + Red Tractor)
        truck_s = pygame.Surface((36, 84), pygame.SRCALPHA)
        # Trailer Container Body
        pygame.draw.rect(truck_s, (220, 225, 230), (3, 2, 30, 60), border_radius=4)
        for ly in range(6, 58, 6):
            pygame.draw.line(truck_s, (180, 185, 195), (5, ly), (31, ly), 1)
        # Red Tractor Cab
        pygame.draw.rect(truck_s, (210, 35, 35), (4, 62, 28, 20), border_radius=5)
        # Cab Windshield
        pygame.draw.rect(truck_s, (25, 35, 50), (8, 65, 20, 8), border_radius=2)
        # Mirrors
        pygame.draw.rect(truck_s, (180, 180, 190), (0, 66, 4, 6), border_radius=1)
        pygame.draw.rect(truck_s, (180, 180, 190), (32, 66, 4, 6), border_radius=1)
        # Taillights
        pygame.draw.rect(truck_s, (240, 20, 20), (5, 60, 6, 2))
        pygame.draw.rect(truck_s, (240, 20, 20), (25, 60, 6, 2))
        self.sprites["truck"] = truck_s

        # 5. Pine Tree Sprite
        tree_s = pygame.Surface((28, 44), pygame.SRCALPHA)
        pygame.draw.rect(tree_s, (90, 55, 30), (11, 32, 6, 12)) # Trunk
        pygame.draw.polygon(tree_s, (25, 110, 50), [(14, 0), (2, 18), (26, 18)])
        pygame.draw.polygon(tree_s, (35, 145, 65), [(14, 10), (4, 28), (24, 28)])
        pygame.draw.polygon(tree_s, (45, 175, 80), [(14, 20), (6, 36), (22, 36)])
        self.sprites["tree"] = tree_s

        # 6. Street Light Sprite
        light_s = pygame.Surface((20, 50), pygame.SRCALPHA)
        pygame.draw.rect(light_s, (140, 145, 160), (8, 6, 4, 44))
        pygame.draw.rect(light_s, (180, 185, 200), (4, 2, 12, 5), border_radius=2)
        pygame.draw.circle(light_s, (255, 255, 180), (10, 7), 3)
        self.sprites["light_pole"] = light_s

    def setup_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = ctk.CTkCanvas(self, bg="#0d0b1e", width=self.vw, height=self.vh, highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        
        self._draw_splash()

    def bind_controls(self) -> None:
        try:
            toplevel = self.winfo_toplevel()
            toplevel.bind("<KeyPress>", self._on_key_press, add="+")
            toplevel.bind("<KeyRelease>", self._on_key_release, add="+")
            logger.info("Game keyboard bindings hooked to main window successfully.")
        except Exception as e:
            logger.error(f"Failed to bind game controls to root: {e}")

    def _on_key_press(self, event: Any) -> None:
        k = event.keysym.lower()
        if k in ("left", "a"):
            self.keys_pressed["left"] = True
        elif k in ("right", "d"):
            self.keys_pressed["right"] = True
        elif k in ("up", "w"):
            self.keys_pressed["up"] = True
        elif k in ("down", "s"):
            self.keys_pressed["down"] = True
        elif k in ("space", "spacebar"):
            self.keys_pressed["space"] = True
            if self.game_over and self.game_started:
                self.reset_game()
        elif "shift" in k:
            self.keys_pressed["shift"] = True

    def _on_key_release(self, event: Any) -> None:
        k = event.keysym.lower()
        if k in ("left", "a"):
            self.keys_pressed["left"] = False
        elif k in ("right", "d"):
            self.keys_pressed["right"] = False
        elif k in ("up", "w"):
            self.keys_pressed["up"] = False
        elif k in ("down", "s"):
            self.keys_pressed["down"] = False
        elif k in ("space", "spacebar"):
            self.keys_pressed["space"] = False
        elif "shift" in k:
            self.keys_pressed["shift"] = False
            if self.game_over and self.game_started:
                self.reset_game()
            elif not self.game_started:
                self.start_game()

    def start_game(self) -> None:
        self.game_started = True
        self.reset_game()
        if not self.game_running:
            self.game_running = True
            self.game_loop()

    def stop_game(self) -> None:
        self.game_running = False
        sound_manager.stop_all()

    def reset_game(self) -> None:
        self.game_over = False
        self.score = 0
        self.speed_mph = 0.0
        self.target_speed_mph = 45.0
        self.player_x = 180.0
        self.car_tilt = 0.0
        self.obstacles.clear()
        self.obstacle_counter = 0
        self.shake_remaining = 0
        self.shake_intensity = 0.0
        self.current_weather = random.choice(self.weather_modes)
        self.brakes_count = 0
        self.was_braking = False
        self.session_start_time = time.time()
        
        from utils.analytics import analytics_tracker
        analytics_tracker.reset()
        
        # Init rain drops
        self.rain_drops.clear()
        for _ in range(50):
            self.rain_drops.append({
                "x": random.uniform(0, self.vw),
                "y": random.uniform(0, self.vh),
                "speed": random.uniform(9.0, 16.0)
            })
        self.rain_splashes.clear()
        self.tire_smoke.clear()
        self.nitro_sparks.clear()
        self.explosion_particles.clear()
        
        # Init roadside objects
        self.roadside_objects.clear()
        for y_pos in [130, 190, 260, 340, 420]:
            self.roadside_objects.append({
                "y": float(y_pos),
                "side": "left",
                "type": "tree"
            })
            self.roadside_objects.append({
                "y": float(y_pos + 30),
                "side": "right",
                "type": "light_pole" if random.random() < 0.5 else "tree"
            })
        
        for key in self.keys_pressed:
            self.keys_pressed[key] = False

    def trigger_screen_shake(self, frames: int, intensity: float) -> None:
        self.shake_remaining = frames
        self.shake_intensity = intensity

    def game_loop(self) -> None:
        if not self.game_running:
            return

        if self.game_started and not self.game_over:
            is_currently_braking = self.keys_pressed["space"] or self.keys_pressed["down"]
            if is_currently_braking and not getattr(self, "was_braking", False):
                self.brakes_count = getattr(self, "brakes_count", 0) + 1
                sound_manager.play_screech()
            self.was_braking = is_currently_braking

            # 1. Update Speed
            if self.keys_pressed["space"]:
                self.target_speed_mph = 0.0
                accel_coeff = 0.35
            elif self.keys_pressed["shift"]:
                self.target_speed_mph = 140.0
                accel_coeff = 0.15
                sound_manager.play_nitro()
            elif self.keys_pressed["up"]:
                self.target_speed_mph = 80.0
                accel_coeff = 0.12
            elif self.keys_pressed["down"]:
                self.target_speed_mph = 0.0
                accel_coeff = 0.22
            else:
                self.target_speed_mph = 40.0
                accel_coeff = 0.10

            self.speed_mph += (self.target_speed_mph - self.speed_mph) * accel_coeff
            sound_manager.update_engine_sound(self.speed_mph, self.keys_pressed["up"])

            # 2. Update Steering Lateral Movement & Chassis Tilt
            steer_speed = 5.5
            target_tilt = 0.0
            if self.keys_pressed["left"]:
                self.player_x -= steer_speed
                target_tilt = -7.0
            if self.keys_pressed["right"]:
                self.player_x += steer_speed
                target_tilt = 7.0
                
            self.player_x = max(50.0, min(310.0 - self.player_width, self.player_x))
            self.car_tilt += (target_tilt - self.car_tilt) * 0.3
            self.wheel_angle = (self.wheel_angle + self.speed_mph * 0.2) % 360.0

            # 3. Score
            if self.speed_mph > 5.0:
                score_factor = 2 if self.keys_pressed["space"] else 1
                self.score += int((self.speed_mph / 15.0) * score_factor)

            # 4. Scroll Road Markings & Roadside Scenery
            scroll_dy = (self.speed_mph / 10.0) * 1.5
            for idx in range(len(self.road_markings)):
                self.road_markings[idx] += scroll_dy
                if self.road_markings[idx] > self.vh:
                    self.road_markings[idx] = 110.0

            for r_obj in self.roadside_objects:
                r_obj["y"] += scroll_dy
                if r_obj["y"] > self.vh + 30:
                    r_obj["y"] = 120.0
                    r_obj["side"] = "left" if random.random() < 0.5 else "right"
                    r_obj["type"] = "light_pole" if random.random() < 0.4 else "tree"

            # 5. Cloud Parallax Drift
            for cloud in self.clouds:
                cloud["x"] += cloud["speed"] + (self.speed_mph / 100.0)
                if cloud["x"] > self.vw + 40:
                    cloud["x"] = -40.0
                    cloud["y"] = random.uniform(5, 75)

            # 6. Particle Systems Updates
            if self.keys_pressed["shift"] and self.speed_mph > 20.0:
                px = self.player_x + self.player_width / 2.0
                py = self.player_y + self.player_height
                for _ in range(3):
                    self.nitro_sparks.append({
                        "x": px + random.uniform(-6, 6),
                        "y": py,
                        "vx": random.uniform(-1.5, 1.5),
                        "vy": random.uniform(4.0, 9.0),
                        "life": 1.0,
                        "color": random.choice([(255, 140, 0), (255, 220, 0), (0, 245, 255)])
                    })

            for p in list(self.nitro_sparks):
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["life"] -= 0.08
                if p["life"] <= 0:
                    self.nitro_sparks.remove(p)

            # Tire Smoke during brake or sharp turns
            if (self.keys_pressed["space"] or abs(self.car_tilt) > 4.0) and self.speed_mph > 15.0:
                px = self.player_x + self.player_width / 2.0
                py = self.player_y + self.player_height - 5
                for side in [-10, 10]:
                    self.tire_smoke.append({
                        "x": px + side + random.uniform(-2, 2),
                        "y": py,
                        "size": random.uniform(3.0, 6.0),
                        "alpha": 180
                    })

            for sm in list(self.tire_smoke):
                sm["y"] += scroll_dy * 0.5
                sm["size"] += 0.35
                sm["alpha"] -= 12
                if sm["alpha"] <= 0:
                    self.tire_smoke.remove(sm)

            # Rain Drops & Splashes
            if self.current_weather == "rain":
                for drop in self.rain_drops:
                    drop["y"] += drop["speed"] + (self.speed_mph / 8.0)
                    drop["x"] -= 1.5
                    if drop["y"] > self.vh:
                        if random.random() < 0.25:
                            self.rain_splashes.append({
                                "x": drop["x"],
                                "y": self.vh - random.uniform(5, 150),
                                "radius": 1.0,
                                "alpha": 200
                            })
                        drop["y"] = -10.0
                        drop["x"] = random.uniform(0, self.vw + 50)

                for sp in list(self.rain_splashes):
                    sp["radius"] += 0.5
                    sp["alpha"] -= 20
                    if sp["alpha"] <= 0:
                        self.rain_splashes.remove(sp)

            # 7. Dynamic Progressive Traffic Spawning & Lane Movement
            self.spawn_timer += 1
            elapsed_sec = time.time() - getattr(self, "session_start_time", time.time())
            
            if elapsed_sec < 5.0:  # Warmup Phase (0-5s): Easy, low density
                spawn_interval = max(55, int(120 - (self.speed_mph / 2.0)))
            elif elapsed_sec < 25.0: # Ramping Phase (5-25s): Progressive traffic build-up
                time_factor = 1.0 + ((elapsed_sec - 5.0) / 15.0)
                spawn_interval = max(24, int((105 - (self.speed_mph / 2.0)) / time_factor))
            else: # Extreme Rush Hour Phase (>25s): High density, fast spawns
                time_factor = min(3.2, 2.33 + ((elapsed_sec - 25.0) / 20.0))
                spawn_interval = max(16, int((90 - (self.speed_mph / 2.0)) / time_factor))

            if self.spawn_timer >= spawn_interval:
                self.spawn_timer = 0
                self._spawn_obstacle()

            for obs in list(self.obstacles):
                if obs.get("changing_lane", False):
                    target_f = obs["target_lane_frac"]
                    df = target_f - obs["lane_frac"]
                    if abs(df) < 0.02:
                        obs["lane_frac"] = target_f
                        obs["changing_lane"] = False
                    else:
                        obs["lane_frac"] += 0.02 if df > 0 else -0.02
                else:
                    car_in_front = False
                    for other in self.obstacles:
                        if other != obs and abs(other["lane_frac"] - obs["lane_frac"]) < 0.1 and other["y"] > obs["y"] and other["y"] - obs["y"] < 130.0:
                            car_in_front = True
                            break
                    if car_in_front and random.random() < 0.12:
                        lane_options = [0.15, 0.38, 0.62, 0.85]
                        curr_idx = min(range(len(lane_options)), key=lambda i: abs(lane_options[i] - obs["lane_frac"]))
                        possible = []
                        if curr_idx > 0:
                            possible.append(lane_options[curr_idx - 1])
                        if curr_idx < len(lane_options) - 1:
                            possible.append(lane_options[curr_idx + 1])
                        if possible:
                            obs["changing_lane"] = True
                            obs["target_lane_frac"] = random.choice(possible)

                obs["y"] += scroll_dy + obs["speed_offset"]
                if self._check_collision(obs):
                    self.handle_crash()
                if obs["y"] > self.vh + 40:
                    from utils.analytics import analytics_tracker
                    analytics_tracker.log_obstacle_dodge(obs["id"])
                    
                    from utils.coach import driving_coach
                    text, speech = driving_coach.trigger_dodge_feedback()
                    self.trigger_coach_alert(text)
                    driving_coach.speak(speech)
                    sound_manager.play_dodge()
                    
                    self.obstacles.remove(obs)

        # Crash Shrapnel Particles
        for part in list(self.explosion_particles):
            part["x"] += part["vx"]
            part["y"] += part["vy"]
            part["size"] -= 0.22
            if part["size"] <= 0:
                self.explosion_particles.remove(part)

        # Render Pygame Scene & Blit to Canvas
        self._draw_scene()
        self.after(25, self.game_loop)

    def _spawn_obstacle(self) -> None:
        elapsed_sec = time.time() - getattr(self, "session_start_time", time.time())
        lane_fracs = [0.15, 0.38, 0.62, 0.85]

        # Determine simultaneous wave spawns based on elapsed survival time
        if elapsed_sec < 6.0:
            num_spawns = 1
        elif elapsed_sec < 18.0:
            num_spawns = 2 if random.random() < 0.25 else 1
        elif elapsed_sec < 35.0:
            num_spawns = 2 if random.random() < 0.55 else 1
        else: # Intense Rush Hour (>35s)
            r = random.random()
            if r < 0.22:
                num_spawns = 3  # 3 cars across 4 lanes (leaves 1 open dodge gap!)
            elif r < 0.70:
                num_spawns = 2
            else:
                num_spawns = 1

        selected_lanes = random.sample(lane_fracs, k=num_spawns)

        for l_frac in selected_lanes:
            self.obstacle_counter += 1

            # Pick vehicle type: 60% Sports Car/SUV, 20% City Bus, 20% Heavy Semi-Truck
            r_type = random.random()
            if r_type < 0.20:
                veh_type = "bus"
                base_w, base_h = 34, 74
                speed_off = random.uniform(0.8, 1.8)
                sprite_obj = self.sprites["bus"]
            elif r_type < 0.40:
                veh_type = "truck"
                base_w, base_h = 36, 84
                speed_off = random.uniform(0.7, 1.6)
                sprite_obj = self.sprites["truck"]
            else:
                veh_type = "car"
                base_w, base_h = 30, 48
                speed_off = random.uniform(1.4, 2.8)
                sprite_obj = self.sprites["ai_cars"][random.randint(0, len(self.sprites["ai_cars"]) - 1)]

            obs = {
                "id": self.obstacle_counter,
                "lane_frac": l_frac,
                "target_lane_frac": l_frac,
                "y": 120.0,
                "base_width": base_w,
                "base_height": base_h,
                "speed_offset": speed_off,
                "veh_type": veh_type,
                "sprite": sprite_obj,
                "changing_lane": False
            }
            self.obstacles.append(obs)
            from utils.analytics import analytics_tracker
            analytics_tracker.log_obstacle_spawn(obs["id"])

    def _check_collision(self, obs: Dict[str, Any]) -> bool:
        horizon_y = 120.0
        road_top_w = 140.0
        road_bot_w = 280.0
        cx = self.vw / 2.0

        oy = obs["y"]
        if oy < horizon_y + 40:
            return False

        t_ratio = max(0.0, min(1.0, (oy - horizon_y) / (self.vh - horizon_y)))
        scale = 0.40 + 0.60 * t_ratio
        w_at_y = road_top_w + (road_bot_w - road_top_w) * t_ratio
        road_left = cx - w_at_y / 2.0

        scaled_w = obs["base_width"] * scale
        scaled_h = obs["base_height"] * scale
        ox = road_left + obs["lane_frac"] * w_at_y - scaled_w / 2.0

        px1 = self.player_x
        px2 = self.player_x + self.player_width
        py1 = self.player_y
        py2 = self.player_y + self.player_height

        ox1 = ox
        ox2 = ox + scaled_w
        oy1 = oy
        oy2 = oy + scaled_h

        margin = 4
        return not (px2 - margin < ox1 or px1 + margin > ox2 or py2 - margin < oy1 or py1 + margin > oy2)

    def handle_crash(self) -> None:
        if not self.game_over:
            self.game_over = True
            self.trigger_screen_shake(18, 10.0)
            sound_manager.play_crash()
            
            if self.score > self.high_score:
                self.high_score = self.score
                
            from utils.analytics import analytics_tracker
            from utils.db import db
            uid = self.user_data.get("id", 1) if hasattr(self, "user_data") and self.user_data else 1
            metrics = analytics_tracker.save_session_to_db(self.score, self.current_weather, user_id=uid)
            
            dur_val = int(metrics.get("duration", 0))
            smooth_val = int(metrics.get("smoothness", 0))
            brk_val = getattr(self, "brakes_count", 0)
            
            for g_type, val in [("duration", dur_val), ("brakes", brk_val), ("accuracy", smooth_val)]:
                done, r_xp, r_coins, r_text = db.update_daily_goal_progress(uid, g_type, val)
                if done:
                    self.trigger_coach_alert(f"🎁 DAILY GOAL MET: {r_text}! +{r_xp} XP / +{r_coins} Coins")
            
            if hasattr(self, "active_challenge") and self.active_challenge:
                chal = self.active_challenge
                target = chal.get("target_score", 200)
                if self.score >= target:
                    stars = 3 if self.score >= target * 1.5 else (2 if self.score >= target * 1.2 else 1)
                    db.save_challenge_progress(uid, chal["id"], self.score, stars, completed=1)
                    db.update_daily_goal_progress(uid, "challenges", 1)
                    lvl_new, xp_new, coins_new = db.add_xp_coins(uid, chal["reward_xp"], chal["reward_coins"])
                    if hasattr(self, "user_data") and self.user_data:
                        self.user_data["xp"] = xp_new
                        self.user_data["coins"] = coins_new
                        self.user_data["level"] = lvl_new
                    self.trigger_coach_alert(f"🏆 CHALLENGE PASSED! +{chal['reward_xp']} XP")
                else:
                    self.trigger_coach_alert(f"❌ CHALLENGE FAILED (Need {target} pts)")
            
            from utils.coach import driving_coach
            text, speech = driving_coach.trigger_crash_feedback()
            self.trigger_coach_alert(text)
            driving_coach.speak(speech)
                
            # Metallic Shrapnel & Flame Explosion Particles
            px = self.player_x + self.player_width / 2.0
            py = self.player_y + self.player_height / 2.0
            for _ in range(35):
                angle = random.uniform(0, 2.0 * math.pi)
                speed = random.uniform(4.0, 9.5)
                self.explosion_particles.append({
                    "x": px,
                    "y": py,
                    "vx": speed * math.cos(angle),
                    "vy": speed * math.sin(angle),
                    "color": random.choice([(255, 50, 50), (255, 160, 0), (255, 240, 0), (0, 245, 255), (200, 200, 200)]),
                    "size": random.uniform(3.5, 7.5)
                })

    def _draw_splash(self) -> None:
        """Renders the arcade splash screen on Pygame surface."""
        self.pg_surface.fill((13, 11, 30))
        
        # Grid lines
        for y in range(0, self.vh, 35):
            pygame.draw.line(self.pg_surface, (27, 24, 54), (0, y), (self.vw, y), 1)
        for x in range(0, self.vw, 35):
            pygame.draw.line(self.pg_surface, (27, 24, 54), (x, 0), (x, self.vh), 1)
            
        # Title text
        t_txt = self.font_title.render("VISIONDRIVE ARCADE", True, (255, 0, 127))
        sub_txt = self.font_hud.render("Hand Tracking Simulator Engine", True, (0, 245, 255))
        self.pg_surface.blit(t_txt, (self.vw//2 - t_txt.get_width()//2, 35))
        self.pg_surface.blit(sub_txt, (self.vw//2 - sub_txt.get_width()//2, 65))

        # How to play Glass Box
        pygame.draw.rect(self.pg_surface, (18, 18, 30), (20, 95, self.vw - 40, 275), border_radius=10)
        pygame.draw.rect(self.pg_surface, (27, 24, 54), (20, 95, self.vw - 40, 275), width=2, border_radius=10)
        
        h_txt = self.font_hud.render("--- HOW TO PLAY ---", True, (255, 0, 127))
        self.pg_surface.blit(h_txt, (self.vw//2 - h_txt.get_width()//2, 110))
        
        rules = [
            ("👐 Neutral Hands", "Steer Straight"),
            ("🔄 Tilt Hands Left/Right", "Steer Vehicle"),
            ("✊ Closed Fist", "Accelerate (80 MPH)"),
            ("👍 Thumbs Up", "Turbo Boost (140 MPH)"),
            ("🖐 Open Palm", "Brake / Slow Down"),
            ("👎 Thumbs Down", "Handbrake (Stop Vehicle)")
        ]
        
        start_y = 140
        for desc, action in rules:
            d_s = self.font_stat.render(desc, True, (0, 245, 255))
            a_s = self.font_stat.render(f"-> {action}", True, (200, 200, 200))
            self.pg_surface.blit(d_s, (35, start_y))
            self.pg_surface.blit(a_s, (190, start_y))
            start_y += 32
            
        strt_txt = self.font_hud.render("Click 'START GAME' or press SPACE to begin!", True, (0, 255, 102))
        self.pg_surface.blit(strt_txt, (self.vw//2 - strt_txt.get_width()//2, 395))

        self._render_pg_to_canvas()

    def _draw_scene(self) -> None:
        if not self.game_started:
            self._draw_splash()
            return

        # Screen shake offset
        dx, dy = 0.0, 0.0
        if self.shake_remaining > 0:
            self.shake_remaining -= 1
            dx = random.uniform(-self.shake_intensity, self.shake_intensity)
            dy = random.uniform(-self.shake_intensity, self.shake_intensity)

        # 1. Sky & Atmosphere Background Gradient
        horizon_y = 120.0
        if self.current_weather == "day":
            sky_top, sky_bot = (30, 140, 220), (230, 240, 255)
        elif self.current_weather == "sunset":
            sky_top, sky_bot = (45, 20, 70), (245, 110, 140)
        elif self.current_weather == "rain":
            sky_top, sky_bot = (10, 12, 22), (30, 40, 60)
        elif self.current_weather == "fog":
            sky_top, sky_bot = (25, 28, 35), (75, 85, 95)
        else:  # Night
            sky_top, sky_bot = (3, 3, 10), (12, 18, 45)

        # Draw Sky Gradient
        for y in range(int(horizon_y)):
            r = sky_top[0] + (sky_bot[0] - sky_top[0]) * (y / horizon_y)
            g = sky_top[1] + (sky_bot[1] - sky_top[1]) * (y / horizon_y)
            b = sky_top[2] + (sky_bot[2] - sky_top[2]) * (y / horizon_y)
            pygame.draw.line(self.pg_surface, (int(r), int(g), int(b)), (0, y + dy), (self.vw, y + dy))

        # Stars in Night Mode
        if self.current_weather == "night":
            random.seed(42)
            for _ in range(25):
                sx = random.randint(0, self.vw)
                sy = random.randint(0, 95)
                brightness = random.randint(180, 255)
                pygame.draw.circle(self.pg_surface, (brightness, brightness, brightness), (int(sx + dx), int(sy + dy)), 1)
            random.seed()

        # Moon / Sun in Sky
        if self.current_weather == "night":
            pygame.draw.circle(self.pg_surface, (240, 245, 255), (300, 35), 14)
            pygame.draw.circle(self.pg_surface, (12, 18, 45), (294, 31), 12) # Moon crescent
        elif self.current_weather in ("day", "sunset"):
            sun_color = (255, 240, 150) if self.current_weather == "day" else (255, 120, 60)
            pygame.draw.circle(self.pg_surface, sun_color, (280, 45), 18)

        # Volumetric Clouds
        for cloud in self.clouds:
            cx_c, cy_c, scale = cloud["x"] + dx, cloud["y"] + dy, cloud["scale"]
            c_color = (240, 240, 250, 160) if self.current_weather != "night" else (40, 50, 70, 140)
            c_surf = pygame.Surface((int(60 * scale), int(30 * scale)), pygame.SRCALPHA)
            pygame.draw.ellipse(c_surf, c_color, (0, int(10*scale), int(60*scale), int(20*scale)))
            pygame.draw.circle(c_surf, c_color, (int(20*scale), int(15*scale)), int(14*scale))
            pygame.draw.circle(c_surf, c_color, (int(35*scale), int(12*scale)), int(16*scale))
            self.pg_surface.blit(c_surf, (cx_c, cy_c))

        # Distant Parallax Mountain Silhouette
        parallax_shift = -(self.player_x - 180.0) * 0.2
        mtn_pts = [
            (0, horizon_y),
            (30 + parallax_shift, 75),
            (80 + parallax_shift, 105),
            (140 + parallax_shift, 65),
            (210 + parallax_shift, 95),
            (280 + parallax_shift, 55),
            (340 + parallax_shift, 90),
            (self.vw, horizon_y)
        ]
        mtn_color = (15, 20, 35) if self.current_weather == "night" else (40, 45, 65)
        pygame.draw.polygon(self.pg_surface, mtn_color, mtn_pts)

        # 2. Pseudo-3D Perspective Road Projection
        road_top_w = 140.0
        road_bot_w = 280.0
        cx = self.vw / 2.0 + dx
        
        p_top_left = (cx - road_top_w/2.0, horizon_y + dy)
        p_top_right = (cx + road_top_w/2.0, horizon_y + dy)
        p_bot_left = (cx - road_bot_w/2.0, self.vh + dy)
        p_bot_right = (cx + road_bot_w/2.0, self.vh + dy)

        # Off-road Grass Shoulders
        pygame.draw.rect(self.pg_surface, (18, 50, 25), (0, horizon_y, self.vw, self.vh - horizon_y))

        # Main Asphalt Road Poly
        pygame.draw.polygon(self.pg_surface, (35, 38, 45), [p_top_left, p_top_right, p_bot_right, p_bot_left])

        # Perspective Striped Curbstones & Lane Lines
        curb_h = 40.0
        offset_y = self.road_markings[0] % curb_h
        y_cursor = horizon_y + ((offset_y - horizon_y) % curb_h)
        
        idx = 0
        while y_cursor < self.vh:
            t_ratio = (y_cursor - horizon_y) / (self.vh - horizon_y)
            w_at_y = road_top_w + (road_bot_w - road_top_w) * t_ratio
            x_left = cx - w_at_y / 2.0
            x_right = cx + w_at_y / 2.0

            curb_color = (255, 40, 90) if idx % 2 == 0 else (0, 245, 255)
            if self.current_weather == "day":
                curb_color = (230, 40, 40) if idx % 2 == 0 else (240, 240, 240)

            # Curb lines
            pygame.draw.line(self.pg_surface, curb_color, (x_left, y_cursor), (x_left - 6 * t_ratio, y_cursor + 20 * t_ratio), int(3 * t_ratio + 1))
            pygame.draw.line(self.pg_surface, curb_color, (x_right, y_cursor), (x_right + 6 * t_ratio, y_cursor + 20 * t_ratio), int(3 * t_ratio + 1))
            
            y_cursor += curb_h * (0.6 + 0.4 * t_ratio)
            idx += 1

        # Perspective Center & Multi-Lane Dashes
        lane_color = (0, 255, 120) if self.current_weather == "night" else (255, 220, 0)
        for my in self.road_markings:
            if my >= horizon_y:
                t_ratio = (my - horizon_y) / (self.vh - horizon_y)
                w_at_y = road_top_w + (road_bot_w - road_top_w) * t_ratio
                road_left = cx - w_at_y / 2.0
                
                lw = max(2, int(5 * t_ratio))
                lh = max(4, int(22 * t_ratio))
                # 3 lane lines separating 4 lanes
                for l_frac in [0.27, 0.50, 0.73]:
                    lx = road_left + l_frac * w_at_y
                    pygame.draw.rect(self.pg_surface, lane_color, (lx - lw//2, my + dy, lw, lh))

        # 3. Roadside Scenery (Trees & Streetlights with depth scale)
        for r_obj in sorted(self.roadside_objects, key=lambda o: o["y"]):
            ry = r_obj["y"] + dy
            if ry < horizon_y:
                continue
            t_ratio = (ry - horizon_y) / (self.vh - horizon_y)
            w_at_y = road_top_w + (road_bot_w - road_top_w) * t_ratio
            
            scale = 0.3 + 0.9 * t_ratio
            if r_obj["side"] == "left":
                rx = cx - w_at_y / 2.0 - 25 * scale
            else:
                rx = cx + w_at_y / 2.0 + 5 * scale
                
            sprite = self.sprites["tree"] if r_obj["type"] == "tree" else self.sprites["light_pole"]
            w_sc, h_sc = int(sprite.get_width() * scale), int(sprite.get_height() * scale)
            scaled_sprite = pygame.transform.scale(sprite, (w_sc, h_sc))
            self.pg_surface.blit(scaled_sprite, (rx, ry - h_sc))

            # Light Cone for Streetlights at Night
            if r_obj["type"] == "light_pole" and self.current_weather in ("night", "rain"):
                light_cone = pygame.Surface((int(40 * scale), int(60 * scale)), pygame.SRCALPHA)
                pygame.draw.polygon(light_cone, (255, 255, 180, 45), [(int(20*scale), 0), (0, int(60*scale)), (int(40*scale), int(60*scale))])
                self.pg_surface.blit(light_cone, (rx - 10 * scale, ry))

        # 4. Obstacle Traffic (Cars, Buses, Trucks) with True Perspective Projection
        for obs in self.obstacles:
            oy = obs["y"] + dy
            if oy + obs["base_height"] < horizon_y:
                continue

            t_ratio = max(0.0, min(1.0, (oy - horizon_y) / (self.vh - horizon_y)))
            scale = 0.40 + 0.60 * t_ratio
            w_at_y = road_top_w + (road_bot_w - road_top_w) * t_ratio
            road_left = cx - w_at_y / 2.0

            scaled_w = int(obs["base_width"] * scale)
            scaled_h = int(obs["base_height"] * scale)
            
            # Position vehicle strictly inside its perspective lane
            ox = road_left + obs["lane_frac"] * w_at_y - scaled_w / 2.0

            scaled_sprite = pygame.transform.scale(obs["sprite"], (scaled_w, scaled_h))

            # Vehicle Shadow
            pygame.draw.ellipse(self.pg_surface, (5, 5, 10, 130), (ox, oy + scaled_h - int(6 * scale), scaled_w, int(10 * scale)))
            self.pg_surface.blit(scaled_sprite, (ox, oy))

        # 5. Tire Smoke Particles
        for sm in self.tire_smoke:
            sm_surf = pygame.Surface((int(sm["size"]*2), int(sm["size"]*2)), pygame.SRCALPHA)
            pygame.draw.circle(sm_surf, (220, 220, 230, max(0, int(sm["alpha"]))), (int(sm["size"]), int(sm["size"])), int(sm["size"]))
            self.pg_surface.blit(sm_surf, (sm["x"] + dx - sm["size"], sm["y"] + dy - sm["size"]))

        # 6. Player Sports Car (With Dynamic Steering Tilt & Wheel Rotation)
        px, py = self.player_x + dx, self.player_y + dy
        p_sprite = self.sprites["player_nitro"] if (self.keys_pressed["shift"] and not self.game_over) else self.sprites["player_car"]
        
        # Apply chassis tilt rotation
        if abs(self.car_tilt) > 0.5:
            rotated_car = pygame.transform.rotate(p_sprite, -self.car_tilt)
            rx = px - (rotated_car.get_width() - self.player_width) / 2.0
            ry = py - (rotated_car.get_height() - self.player_height) / 2.0
            self.pg_surface.blit(rotated_car, (rx, ry))
        else:
            self.pg_surface.blit(p_sprite, (px, py))

        # Headlight Beams in Night/Rain Mode
        if self.current_weather in ("night", "rain", "fog") and not self.game_over:
            beam_surf = pygame.Surface((100, 120), pygame.SRCALPHA)
            pygame.draw.polygon(beam_surf, (255, 240, 180, 50), [(50, 0), (0, 120), (100, 120)])
            self.pg_surface.blit(beam_surf, (px + self.player_width/2.0 - 50, py - 110))

        # 7. Particle Effects (Nitro Flames & Rain Splashes & Crash Shrapnel)
        for p in self.nitro_sparks:
            alpha = int(p["life"] * 255)
            color = p["color"] + (alpha,)
            p_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, color, (3, 3), 3)
            self.pg_surface.blit(p_surf, (p["x"] + dx - 3, p["y"] + dy - 3))

        # Rain Drops & Splashes
        if self.current_weather == "rain":
            for drop in self.rain_drops:
                pygame.draw.line(self.pg_surface, (120, 170, 220, 180), (drop["x"] + dx, drop["y"] + dy), (drop["x"] - 2 + dx, drop["y"] + 8 + dy), 1)
            for sp in self.rain_splashes:
                pygame.draw.circle(self.pg_surface, (160, 200, 240, max(0, int(sp["alpha"]))), (int(sp["x"] + dx), int(sp["y"] + dy)), int(sp["radius"]), 1)

        # Crash Explosion Particles
        for part in self.explosion_particles:
            color = part["color"]
            p_surf = pygame.Surface((int(part["size"]*2), int(part["size"]*2)), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, color, (int(part["size"]), int(part["size"])), int(part["size"]))
            self.pg_surface.blit(p_surf, (part["x"] + dx - part["size"], part["y"] + dy - part["size"]))

        # 8. Modern Arcade HUD Overlays
        # Weather Banner
        weather_names = {"day": "DAY SUNRISE", "sunset": "SUNSET COAST", "night": "NIGHT RIDER", "rain": "NEON STORM", "fog": "TOKYO FOG"}
        w_txt = self.font_hud_sm.render(weather_names.get(self.current_weather, "NIGHT RIDER"), True, (0, 245, 255))
        self.pg_surface.blit(w_txt, (self.vw//2 - w_txt.get_width()//2, 38))

        # Speedometer (top-left)
        sp_txt = self.font_stat.render(f"SPEED: {int(self.speed_mph)} MPH", True, (255, 0, 127))
        self.pg_surface.blit(sp_txt, (15, 16))

        # Best Score (top-center)
        hi_txt = self.font_stat.render(f"BEST: {self.high_score:05d}", True, (241, 196, 15))
        self.pg_surface.blit(hi_txt, (self.vw//2 - hi_txt.get_width()//2, 16))

        # Current Score (top-right)
        sc_txt = self.font_stat.render(f"SCORE: {self.score:05d}", True, (0, 255, 102))
        self.pg_surface.blit(sc_txt, (self.vw - sc_txt.get_width() - 15, 16))

        # Driving Coach Alert Banner Overlay
        if self.coach_timer > 0:
            self.coach_timer -= 1
            pygame.draw.rect(self.pg_surface, (10, 10, 20), (30 + dx, 335 + dy, self.vw - 60, 34), border_radius=6)
            pygame.draw.rect(self.pg_surface, (0, 245, 255), (30 + dx, 335 + dy, self.vw - 60, 34), width=1, border_radius=6)
            c_color = (255, 0, 127) if ("⚠️" in self.coach_message or "💥" in self.coach_message) else (0, 255, 102)
            c_txt = self.font_hud_sm.render(self.coach_message, True, c_color)
            self.pg_surface.blit(c_txt, (self.vw//2 - c_txt.get_width()//2 + dx, 345 + dy))

        # Game Over Banner Overlay
        if self.game_over and len(self.explosion_particles) < 15:
            overlay_s = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
            overlay_s.fill((10, 10, 15, 220))
            self.pg_surface.blit(overlay_s, (0, 0))

            go_txt = self.font_title.render("GAME OVER", True, (255, 0, 127))
            self.pg_surface.blit(go_txt, (self.vw//2 - go_txt.get_width()//2 + dx, 50 + dy))

            pygame.draw.rect(self.pg_surface, (18, 18, 30), (30, 95, self.vw - 60, 245), border_radius=10)
            pygame.draw.rect(self.pg_surface, (27, 24, 54), (30, 95, self.vw - 60, 245), width=2, border_radius=10)

            from utils.analytics import analytics_tracker
            m = analytics_tracker.compute_metrics()
            
            rep_txt = self.font_hud.render("AI SESSION DRIVING REPORT", True, (255, 0, 127))
            self.pg_surface.blit(rep_txt, (self.vw//2 - rep_txt.get_width()//2, 110))

            stats = [
                ("🎮 Arcade Score", f"{self.score:05d}"),
                ("🏆 Driving Score", f"{m['score']}/100"),
                ("⚡ Smoothness", f"{int(m['smoothness'])}%"),
                ("⏱ Reaction Time", f"{m['reaction_time']:.2f}s"),
                ("🛣 Lane Discipline", f"{int(m['lane_discipline'])}%"),
                ("⛽ Driving Efficiency", f"{int(m['efficiency'])}%")
            ]

            sy = 142
            for label, val in stats:
                lbl_s = self.font_hud_sm.render(label, True, (0, 245, 255))
                val_s = self.font_hud_sm.render(f"-> {val}", True, (0, 255, 102) if "Score" in label else (240, 240, 240))
                self.pg_surface.blit(lbl_s, (45, sy))
                self.pg_surface.blit(val_s, (205, sy))
                sy += 28

            rst_txt = self.font_hud_sm.render("Press SPACE or click RESTART to drive again", True, (255, 255, 255))
            self.pg_surface.blit(rst_txt, (self.vw//2 - rst_txt.get_width()//2 + dx, 385 + dy))

        self._render_pg_to_canvas()

    def _render_pg_to_canvas(self) -> None:
        """Converts Pygame surface buffer to PIL Image and updates CustomTkinter Canvas."""
        try:
            if not self.winfo_exists():
                return
            raw_data = pygame.image.tostring(self.pg_surface, "RGBA")
            pil_img = Image.frombytes("RGBA", (self.vw, self.vh), raw_data)
            
            cw = max(100, self.canvas.winfo_width())
            ch = max(100, self.canvas.winfo_height())
            if cw != self.vw or ch != self.vh:
                pil_img = pil_img.resize((cw, ch), Image.Resampling.BILINEAR)

            self.tk_image = ImageTk.PhotoImage(pil_img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
        except Exception as e:
            logger.debug(f"Error converting Pygame surface to canvas: {e}")
            
    def trigger_coach_alert(self, text: str) -> None:
        self.coach_message = text
        self.coach_timer = 90
