import random
import math
import time
import customtkinter as ctk
from typing import List, Tuple, Dict, Any, Optional
from utils.logger import logger

class RetroRacingGame(ctk.CTkFrame):
    """A built-in 2D retro racing mini-game that is embedded directly into the main dashboard."""
    def __init__(self, parent: Any):
        # Initialize as a frame
        super().__init__(parent, corner_radius=15, fg_color="#1E1E24", border_color="#2D2D35", border_width=2)
        
        # Game State Variables
        self.game_started = False
        self.game_running = False
        self.game_over = False
        self.score = 0
        self.high_score = 0
        self.speed_mph = 0.0
        self.target_speed_mph = 0.0
        
        # Player position
        self.player_x = 180.0  # Range: 50 to 350
        self.player_y = 390.0
        self.player_width = 25
        self.player_height = 42
        
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

        # Screen shake state
        self.shake_remaining = 0
        self.shake_intensity = 0.0

        # Weather & Particle systems
        self.weather_modes = ["day", "night", "rain", "fog"]
        self.current_weather = "night"
        self.rain_drops: List[Dict[str, Any]] = []
        self.explosion_particles: List[Dict[str, Any]] = []

        # Driving Coach status overlays
        self.coach_message = ""
        self.coach_timer = 0
        
        self.setup_ui()
        
        # Schedule keyboard binding once mapped
        self.after(500, self.bind_controls)

    def setup_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Canvas viewport size: 360 x 450
        self.canvas = ctk.CTkCanvas(self, bg="#0d0b1e", width=360, height=450, highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        
        # Draw initial splash screen
        self._draw_splash()

    def _scale_canvas_to_fit(self) -> None:
        """Scales all vectors dynamically to fill the actual canvas dimensions."""
        w_canvas = self.canvas.winfo_width()
        h_canvas = self.canvas.winfo_height()
        
        # If not laid out yet, keep default scale
        if w_canvas < 100 or h_canvas < 100:
            return
            
        scale_x = w_canvas / 360.0
        scale_y = h_canvas / 450.0
        
        # Use native canvas scale method to scale everything relative to (0,0)
        self.canvas.scale("all", 0, 0, scale_x, scale_y)

    def bind_controls(self) -> None:
        """Binds controls to the main root application window."""
        try:
            toplevel = self.winfo_toplevel()
            toplevel.bind("<KeyPress>", self._on_key_press, add="+")
            toplevel.bind("<KeyRelease>", self._on_key_release, add="+")
            logger.info("Game keyboard bindings hooked to main window successfully.")
        except Exception as e:
            logger.error(f"Failed to bind game controls to root: {e}")

    def _on_key_press(self, event: Any) -> None:
        k = event.keysym.lower()
        if k == "left":
            self.keys_pressed["left"] = True
        elif k == "right":
            self.keys_pressed["right"] = True
        elif k == "up":
            self.keys_pressed["up"] = True
        elif k == "down":
            self.keys_pressed["down"] = True
        elif k == "space" or k == "spacebar":
            self.keys_pressed["space"] = True
            if self.game_over and self.game_started:
                self.reset_game()
        elif "shift" in k:
            self.keys_pressed["shift"] = True

    def _on_key_release(self, event: Any) -> None:
        k = event.keysym.lower()
        if k == "left":
            self.keys_pressed["left"] = False
        elif k == "right":
            self.keys_pressed["right"] = False
        elif k == "up":
            self.keys_pressed["up"] = False
        elif k == "down":
            self.keys_pressed["down"] = False
        elif k == "space" or k == "spacebar":
            self.keys_pressed["space"] = False
        elif "shift" in k:
            self.keys_pressed["shift"] = False
            if self.game_over and self.game_started:
                self.reset_game()
            elif not self.game_started:
                self.start_game()

    def start_game(self) -> None:
        """Starts the game loop."""
        self.game_started = True
        self.reset_game()
        if not self.game_running:
            self.game_running = True
            self.game_loop()

    def stop_game(self) -> None:
        """Pauses the game execution loop."""
        self.game_running = False

    def reset_game(self) -> None:
        """Restarts/Resets active play coordinates."""
        self.game_over = False
        self.score = 0
        self.speed_mph = 0.0
        self.target_speed_mph = 45.0
        self.player_x = 180.0
        self.obstacles.clear()
        self.obstacle_counter = 0
        self.shake_remaining = 0
        self.shake_intensity = 0.0
        self.current_weather = random.choice(self.weather_modes)
        self.brakes_count = 0
        self.was_braking = False
        
        # Reset analytics tracker
        from utils.analytics import analytics_tracker
        analytics_tracker.reset()
        
        # Spawn rain particles
        self.rain_drops.clear()
        for _ in range(40):
            self.rain_drops.append({
                "x": random.uniform(0, 360),
                "y": random.uniform(0, 450),
                "speed": random.uniform(8.0, 14.0)
            })
        self.explosion_particles.clear()
        
        for key in self.keys_pressed:
            self.keys_pressed[key] = False

    def trigger_screen_shake(self, frames: int, intensity: float) -> None:
        self.shake_remaining = frames
        self.shake_intensity = intensity

    def game_loop(self) -> None:
        """Core visual rendering update loop running at 50Hz."""
        if not self.game_running:
            return

        if self.game_started and not self.game_over:
            # Increment brakes count on state transition
            is_currently_braking = self.keys_pressed["space"] or self.keys_pressed["down"]
            if is_currently_braking and not getattr(self, "was_braking", False):
                self.brakes_count = getattr(self, "brakes_count", 0) + 1
            self.was_braking = is_currently_braking

            # 1. Update Speed
            if self.keys_pressed["space"]: # Handbrake slows down vehicle
                self.target_speed_mph = 0.0
                accel_coeff = 0.35 # High deceleration coeff for instant braking
            elif self.keys_pressed["shift"]: # Nitro boost speed up
                self.target_speed_mph = 120.0
                accel_coeff = 0.15
            elif self.keys_pressed["up"]: # Accelerating
                self.target_speed_mph = 80.0
                accel_coeff = 0.12
            elif self.keys_pressed["down"]: # Braking
                self.target_speed_mph = 0.0
                accel_coeff = 0.22
            else: # Cruise
                self.target_speed_mph = 40.0
                accel_coeff = 0.10

            self.speed_mph += (self.target_speed_mph - self.speed_mph) * accel_coeff

            # 2. Update Steering Lateral Movement
            steer_speed = 5.0
            if self.keys_pressed["left"]:
                self.player_x -= steer_speed
            if self.keys_pressed["right"]:
                self.player_x += steer_speed
                
            self.player_x = max(50.0, min(310.0 - self.player_width, self.player_x))

            # 3. Score
            if self.speed_mph > 5.0:
                score_factor = 2 if self.keys_pressed["space"] else 1
                self.score += int((self.speed_mph / 15.0) * score_factor)

            # 4. Scroll markings
            scroll_dy = (self.speed_mph / 10.0) * 1.5
            for idx in range(len(self.road_markings)):
                self.road_markings[idx] += scroll_dy
                if self.road_markings[idx] > 450.0:
                    self.road_markings[idx] = -30.0

            # 5. Spawning
            self.spawn_timer += 1
            spawn_interval = max(40, int(110 - (self.speed_mph / 2.0)))
            if self.spawn_timer >= spawn_interval:
                self.spawn_timer = 0
                self._spawn_obstacle()

            # Move and update rain drops
            if self.current_weather == "rain":
                for drop in self.rain_drops:
                    drop["y"] += drop["speed"] + (self.speed_mph / 8.0)
                    drop["x"] -= 1.5  # wind tilt
                    if drop["y"] > 450.0:
                        drop["y"] = -10.0
                        drop["x"] = random.uniform(0, 400)

            # Move obstacles and execute Traffic AI lateral steering
            for obs in list(self.obstacles):
                if obs.get("changing_lane", False):
                    target_x = obs["target_lane_x"]
                    dx_steer = target_x - obs["x"]
                    if abs(dx_steer) < 3.0:
                        obs["x"] = target_x
                        obs["changing_lane"] = False
                    else:
                        obs["x"] += 3.0 if dx_steer > 0 else -3.0
                else:
                    # AI decision: lane shift if another obstacle is in front
                    car_in_front = False
                    for other in self.obstacles:
                        if other != obs and abs(other["x"] - obs["x"]) < 20.0 and other["y"] > obs["y"] and other["y"] - obs["y"] < 130.0:
                            car_in_front = True
                            break
                    if car_in_front and random.random() < 0.15:
                        current_lane_idx = [80.0, 140.0, 200.0, 260.0].index(obs["x"])
                        possible_lanes = []
                        if current_lane_idx > 0:
                            possible_lanes.append([80.0, 140.0, 200.0, 260.0][current_lane_idx - 1])
                        if current_lane_idx < 3:
                            possible_lanes.append([80.0, 140.0, 200.0, 260.0][current_lane_idx + 1])
                        if possible_lanes:
                            obs["changing_lane"] = True
                            obs["target_lane_x"] = random.choice(possible_lanes)

                obs["y"] += scroll_dy + obs["speed_offset"]
                if self._check_collision(obs):
                    self.handle_crash()
                if obs["y"] > 480.0:
                    # Notify successful dodge
                    from utils.analytics import analytics_tracker
                    analytics_tracker.log_obstacle_dodge(obs["id"])
                    
                    # Trigger dodge coaching feedback
                    from utils.coach import driving_coach
                    text, speech = driving_coach.trigger_dodge_feedback()
                    self.trigger_coach_alert(text)
                    driving_coach.speak(speech)
                    
                    self.obstacles.remove(obs)

        # Always update crash explosion particles (even during Game Over state)
        for part in list(self.explosion_particles):
            part["x"] += part["vx"]
            part["y"] += part["vy"]
            part["size"] -= 0.25
            if part["size"] <= 0:
                self.explosion_particles.remove(part)

        # Render
        self._draw_scene()
        
        # Reschedule loop
        self.after(30, self.game_loop)

    def _spawn_obstacle(self) -> None:
        lanes = [80.0, 140.0, 200.0, 260.0]
        x_start = random.choice(lanes)
        self.obstacle_counter += 1
        obs = {
            "id": self.obstacle_counter,
            "x": x_start,
            "y": -50.0,
            "width": 25,
            "height": 42,
            "speed_offset": random.uniform(1.0, 2.5),
            "color": random.choice(["#3498DB", "#9B59B6", "#E67E22", "#E74C3C", "#1ABC9C"])
        }
        self.obstacles.append(obs)
        from utils.analytics import analytics_tracker
        analytics_tracker.log_obstacle_spawn(obs["id"])

    def _check_collision(self, obs: Dict[str, Any]) -> bool:
        px1 = self.player_x
        px2 = self.player_x + self.player_width
        py1 = self.player_y
        py2 = self.player_y + self.player_height

        ox1 = obs["x"]
        ox2 = obs["x"] + obs["width"]
        oy1 = obs["y"]
        oy2 = obs["y"] + obs["height"]

        margin = 3
        return not (px2 - margin < ox1 or px1 + margin > ox2 or py2 - margin < oy1 or py1 + margin > oy2)

    def handle_crash(self) -> None:
        if not self.game_over:
            self.game_over = True
            self.trigger_screen_shake(16, 9.0)
            if self.score > self.high_score:
                self.high_score = self.score
                
            # Save session logs to SQLite database via analytics tracker
            from utils.analytics import analytics_tracker
            from utils.db import db
            uid = 1
            if hasattr(self, "user_data") and self.user_data:
                uid = self.user_data.get("id", 1)
            metrics = analytics_tracker.save_session_to_db(self.score, self.current_weather, user_id=uid)
            
            # Progress daily goals with session telemetry
            dur_val = int(metrics.get("duration", 0))
            smooth_val = int(metrics.get("smoothness", 0))
            brk_val = getattr(self, "brakes_count", 0)
            
            for g_type, val in [("duration", dur_val), ("brakes", brk_val), ("accuracy", smooth_val)]:
                done, r_xp, r_coins, r_text = db.update_daily_goal_progress(uid, g_type, val)
                if done:
                    self.trigger_coach_alert(f"🎁 DAILY GOAL MET: {r_text}! +{r_xp} XP / +{r_coins} Coins")
            
            # Check challenge completion
            if hasattr(self, "active_challenge") and self.active_challenge:
                chal = self.active_challenge
                target = chal.get("target_score", 200)
                if self.score >= target:
                    stars = 1
                    if self.score >= target * 1.5:
                        stars = 3
                    elif self.score >= target * 1.2:
                        stars = 2
                    db.save_challenge_progress(uid, chal["id"], self.score, stars, completed=1)
                    
                    # Progress daily goal challenges completion count
                    done, r_xp, r_coins, r_text = db.update_daily_goal_progress(uid, "challenges", 1)
                    if done:
                        self.trigger_coach_alert(f"🎁 DAILY GOAL MET: {r_text}! +{r_xp} XP / +{r_coins} Coins")
                    
                    # Award rewards (XP/coins)
                    lvl_new, xp_new, coins_new = db.add_xp_coins(uid, chal["reward_xp"], chal["reward_coins"])
                    if hasattr(self, "user_data") and self.user_data:
                        self.user_data["xp"] = xp_new
                        self.user_data["coins"] = coins_new
                        self.user_data["level"] = lvl_new
                        
                    self.trigger_coach_alert(f"🏆 CHALLENGE PASSED! +{chal['reward_xp']} XP")
                    
                    # Check and process license upgrades and unlocked rewards
                    unlocks = db.check_license_unlocks(uid)
                    for note in unlocks:
                        self.trigger_coach_alert(note)
                else:
                    self.trigger_coach_alert(f"❌ CHALLENGE FAILED (Need {target} pts)")
            
            # If achievements were unlocked, notify coach/event logs
            if "unlocked_achievements" in metrics and metrics["unlocked_achievements"]:
                # Trigger a sequence or display first unlocked achievement
                for ach in metrics["unlocked_achievements"]:
                    self.trigger_coach_alert(f"🏆 UNLOCKED: {ach}!")
            
            # Trigger crash coaching feedback
            from utils.coach import driving_coach
            text, speech = driving_coach.trigger_crash_feedback()
            self.trigger_coach_alert(text)
            driving_coach.speak(speech)
                
            # Spawn crash explosion particles
            px = self.player_x + self.player_width / 2.0
            py = self.player_y + self.player_height / 2.0
            for _ in range(25):
                angle = random.uniform(0, 2.0 * math.pi)
                speed = random.uniform(3.0, 8.0)
                self.explosion_particles.append({
                    "x": px,
                    "y": py,
                    "vx": speed * math.cos(angle),
                    "vy": speed * math.sin(angle),
                    "color": random.choice(["#FF007F", "#FF9900", "#FFFF00", "#00F5FF"]),
                    "size": random.uniform(3.5, 7.0)
                })

    def _draw_splash(self) -> None:
        self.canvas.delete("all")
        w, h = 360, 450
        
        # Draw background grid
        self.canvas.create_rectangle(0, 0, w, h, fill="#0d0b1e", outline="")
        for y in range(0, h, 40):
            self.canvas.create_line(0, y, w, y, fill="#1b1836", width=1)
        for x in range(0, w, 40):
            self.canvas.create_line(x, 0, x, h, fill="#1b1836", width=1)
            
        # Title
        self.canvas.create_text(
            w/2, 45, text="VISIONDRIVE ARCADE",
            font=("Outfit", 20, "bold"), fill="#FF007F"
        )
        self.canvas.create_text(
            w/2, 70, text="Hand Tracking Simulator",
            font=("Outfit", 11, "bold"), fill="#00F5FF"
        )

        # Instructions Panel (Glass-style box)
        self.canvas.create_rectangle(20, 100, w - 20, 365, fill="#12121e", outline="#1b1836", width=2)
        
        self.canvas.create_text(
            w/2, 120, text="--- HOW TO PLAY ---",
            font=("Outfit", 12, "bold"), fill="#FF007F"
        )
        
        rules = [
            ("👐 Neutral Hands", "Steer Straight"),
            ("🔄 Tilt Hands Left/Right", "Steer Vehicle"),
            ("✊ Closed Fist", "Accelerate (Speed up)"),
            ("🖐 Open Palm", "Brake / Slow Down"),
            ("👎 Thumbs Down", "Handbrake (Stop Vehicle)"),
            ("⌨ Shift Key", "Turbo Boost (120 MPH)")
        ]
        
        start_y = 150
        for desc, action in rules:
            self.canvas.create_text(
                40, start_y, text=desc,
                font=("Outfit", 10, "bold"), fill="#00F5FF", anchor="w"
            )
            self.canvas.create_text(
                190, start_y, text=f"➔ {action}",
                font=("Outfit", 9), fill="#CCCCCC", anchor="w"
            )
            start_y += 32
            
        self.canvas.create_text(
            w/2, 400, text="Click 'START GAME' or press SPACE to begin!",
            font=("Outfit", 11, "bold"), fill="#00FF66"
        )
        self._scale_canvas_to_fit()

    def _draw_scene(self) -> None:
        if not self.game_started:
            self._draw_splash()
            return
            
        self.canvas.delete("all")
        w, h = 360, 450
        
        # Apply screen shake offsets
        dx, dy = 0.0, 0.0
        if self.shake_remaining > 0:
            self.shake_remaining -= 1
            dx = random.uniform(-self.shake_intensity, self.shake_intensity)
            dy = random.uniform(-self.shake_intensity, self.shake_intensity)
            
        # Draw background base sky
        if self.current_weather == "day":
            sky_color = "#1e1035"  # Sunset dark violet
            horizon_color = "#e55b7c"  # sunset warm pink
        elif self.current_weather == "rain":
            sky_color = "#0a0a14"  # Very dark rainy sky
            horizon_color = "#1a233a"
        elif self.current_weather == "fog":
            sky_color = "#1a1c1e"
            horizon_color = "#2d3238"
        else:  # Night Mode
            sky_color = "#030308"  # Cyberpunk night pitch black
            horizon_color = "#080b20"
            
        self.canvas.create_rectangle(0 + dx, 0 + dy, w + dx, h + dy, fill="#0d0b1e", outline="")
        
        # Draw Horizon Sky area (from y=0 to y=120)
        self.canvas.create_rectangle(0 + dx, 0 + dy, w + dx, 120 + dy, fill=sky_color, outline="")
        
        # Draw stars in Night Mode
        if self.current_weather == "night":
            random.seed(42) # keeps stars static
            for _ in range(15):
                sx = random.randint(0, w)
                sy = random.randint(0, 95)
                self.canvas.create_oval(sx + dx, sy + dy, sx + 2 + dx, sy + 2 + dy, fill="#FFFFFF", outline="")
            random.seed() # reset seed
            
        # Draw horizon line glow gradient
        self.canvas.create_rectangle(0 + dx, 110 + dy, w + dx, 120 + dy, fill=horizon_color, outline="")

        # Draw Parallax Background Skyline (buildings)
        # Shift amount is proportional to steering deviation
        parallax_shift = -(self.player_x - 180.0) * 0.25
        building_widths = [30, 45, 25, 50, 35, 60]
        building_heights = [60, 85, 45, 75, 55, 80]
        building_colors = ["#16132b", "#1a1638", "#121021", "#1d193d", "#151226", "#1c183a"]
        
        bx = -50 + parallax_shift
        idx = 0
        while bx < w + 50:
            bw = building_widths[idx % len(building_widths)]
            bh = building_heights[idx % len(building_heights)]
            bc = building_colors[idx % len(building_colors)]
            
            # Draw skyscraper with stylized neon outlines
            self.canvas.create_rectangle(bx + dx, 120 - bh + dy, bx + bw + dx, 120 + dy, fill=bc, outline="#00f5ff" if idx % 2 == 0 else "#ff007f", width=1)
            
            bx += bw + 15
            idx += 1

        # Draw main asphalt roadbed (starts at y=120 horizon down to bottom)
        road_left = 50.0
        road_right = 310.0
        self.canvas.create_rectangle(road_left + dx, 120 + dy, road_right + dx, h + dy, fill="#101014", outline="")
        
        # Draw dynamic horizontal grid lines on shoulders
        grid_fill = building_colors[0]
        for my in self.road_markings:
            if my >= 120.0:
                self.canvas.create_line(0 + dx, my + dy, 50 + dx, my + dy, fill=grid_fill, width=1)
                self.canvas.create_line(310 + dx, my + dy, w + dx, my + dy, fill=grid_fill, width=1)
            
        # Draw static vertical grid lines on shoulders (clipped to horizon y=120)
        self.canvas.create_line(15 + dx, 120 + dy, 15 + dx, h + dy, fill=grid_fill, width=1)
        self.canvas.create_line(30 + dx, 120 + dy, 30 + dx, h + dy, fill=grid_fill, width=1)
        self.canvas.create_line(330 + dx, 120 + dy, 330 + dx, h + dy, fill=grid_fill, width=1)
        self.canvas.create_line(345 + dx, 120 + dy, 345 + dx, h + dy, fill=grid_fill, width=1)
        
        # Draw scrolling neon pink & cyan curbstones at road borders (horizon clipped)
        curb_h = 50.0
        offset_y = self.road_markings[0] % curb_h
        y_cursor = 120.0 + ((offset_y - 120.0) % curb_h)
        
        curb_w = 4
        index = 0
        while y_cursor < h + curb_h:
            color1 = "#FF007F" if index % 2 == 0 else "#00F5FF"  # Pink/Cyan alternation
            color2 = "#00F5FF" if index % 2 == 0 else "#FF007F"
            
            # Crop top of first curbstone to horizon
            top_y = max(120.0, y_cursor)
            if top_y < h:
                self.canvas.create_rectangle(road_left - curb_w + dx, top_y + dy, road_left + dx, y_cursor + curb_h + dy, fill=color1, outline="")
                self.canvas.create_rectangle(road_right + dx, top_y + dy, road_right + curb_w + dx, y_cursor + curb_h + dy, fill=color2, outline="")
            
            y_cursor += curb_h
            index += 1

        # Draw road dashed center line markings (neon green)
        lane_w = 4
        cx = 180.0
        for my in self.road_markings:
            if my >= 120.0:
                self.canvas.create_rectangle(cx - lane_w/2 + dx, my + dy, cx + lane_w/2 + dx, min(h, my + 45) + dy, fill="#00FF66", outline="")

        # Draw Obstacle Cars (clipped to horizon y=120)
        for obs in self.obstacles:
            if obs["y"] + obs["height"] < 120.0:
                continue
            ox, oy = obs["x"] + dx, obs["y"] + dy
            ow, oh = obs["width"], obs["height"]
            
            # Crop top
            draw_oy = max(120.0, oy)
            draw_oh = oh - (draw_oy - oy)
            
            # Draw obstacle car body rectangle
            self.canvas.create_rectangle(ox, draw_oy, ox + ow, draw_oy + draw_oh, fill=obs["color"], outline="#FFFFFF", width=1)
            # Tires
            tw, th = 5, 10
            if oy + 4 >= 120.0:
                self.canvas.create_rectangle(ox - tw, oy + 4, ox, oy + 4 + th, fill="#08080a", outline="")
                self.canvas.create_rectangle(ox + ow, oy + 4, ox + ow + tw, oy + 4 + th, fill="#08080a", outline="")
            if oy + oh - 13 >= 120.0:
                self.canvas.create_rectangle(ox - tw, oy + oh - 13, ox, oy + oh - 13 + th, fill="#08080a", outline="")
                self.canvas.create_rectangle(ox + ow, oy + oh - 13, ox + ow + tw, oy + oh - 13 + th, fill="#08080a", outline="")
            
            # Windshield
            if oy + 10 >= 120.0:
                self.canvas.create_rectangle(ox + 3, oy + 10, ox + ow - 3, oy + 18, fill="#1B1E22", outline="")
            
            # Brake Lights
            if oy + oh - 3 >= 120.0:
                self.canvas.create_rectangle(ox + 2, oy + oh - 3, ox + 6, oy + oh, fill="#E74C3C", outline="")
                self.canvas.create_rectangle(ox + ow - 6, oy + oh - 3, ox + ow - 2, oy + oh, fill="#E74C3C", outline="")

        # Draw Player Car
        px, py = self.player_x + dx, self.player_y + dy
        pw, ph = self.player_width, self.player_height
        
        # Color based on state
        car_body_color = "#FF4B4B" # Standard Red
        if self.keys_pressed["shift"]:
            car_body_color = "#F39C12" # Golden Orange Nitro
            
            # Speed streaks (Nitro lines)
            for _ in range(5):
                sx = random.randint(int(px - 15), int(px + pw + 15))
                sy = random.randint(int(py), int(py + ph))
                slen = random.randint(15, 30)
                self.canvas.create_line(sx, sy, sx, sy + slen, fill="#FF9900", width=1)

        # Shadow underneath
        self.canvas.create_oval(px - 5, py + ph - 8, px + pw + 5, py + ph + 4, fill="#050508", outline="")

        # Wheels
        tw, th = 5, 10
        self.canvas.create_rectangle(px - tw, py + 4, px, py + 4 + th, fill="#0F0F0F", outline="")
        self.canvas.create_rectangle(px + pw, py + 4, px + pw + tw, py + 4 + th, fill="#0F0F0F", outline="")
        self.canvas.create_rectangle(px - tw, py + ph - 13, px, py + ph - 13 + th, fill="#0F0F0F", outline="")
        self.canvas.create_rectangle(px + pw, py + ph - 13, px + pw + tw, py + ph - 13 + th, fill="#0F0F0F", outline="")

        # Car Body Shape
        self.canvas.create_rectangle(px, py, px + pw, py + ph, fill=car_body_color, outline="#FFFFFF", width=1.5)
        # Windshield
        self.canvas.create_rectangle(px + 3, py + 10, px + pw - 3, py + 18, fill="#00FFFF", outline="")
        # Spoiler
        self.canvas.create_rectangle(px - 2, py + ph - 3, px + pw + 2, py + ph, fill="#111111", outline="")
        
        # Headlights (Simple visual circles)
        self.canvas.create_oval(px + 2, py + 2, px + 6, py + 6, fill="#FFFF99", outline="")
        self.canvas.create_oval(px + pw - 6, py + 2, px + pw - 2, py + 6, fill="#FFFF99", outline="")

        # Nitro flame drawing if holding shift
        if self.keys_pressed["shift"] and not self.game_over:
            flame_len = random.randint(12, 25)
            self.canvas.create_polygon(
                px + pw/2 - 4, py + ph,
                px + pw/2 + 4, py + ph,
                px + pw/2, py + ph + flame_len,
                fill="#FF9900", outline="#FFCC00"
            )

        # Draw weather overlays (Rain)
        if self.current_weather == "rain":
            for drop in self.rain_drops:
                self.canvas.create_line(drop["x"] + dx, drop["y"] + dy, drop["x"] - 2 + dx, drop["y"] + 6 + dy, fill="#5a7a9a", width=1)

        # Render Explosion Particles upon crash
        for part in self.explosion_particles:
            self.canvas.create_oval(
                part["x"] - part["size"] + dx, part["y"] - part["size"] + dy,
                part["x"] + part["size"] + dx, part["y"] + part["size"] + dy,
                fill=part["color"], outline=""
            )

        # Draw Arcade HUD overlays directly on top of the road canvas
        # Banner for current weather theme
        weather_names = {"day": "DAY SUNRISE", "night": "NIGHT RIDER", "rain": "NEON STORM", "fog": "TOKYO FOG"}
        self.canvas.create_text(
            180, 45, text=weather_names.get(self.current_weather, "NIGHT RIDER"),
            font=("Outfit", 8, "bold"), fill="#00F5FF", anchor="center"
        )
        
        # Speedometer (top-left)
        self.canvas.create_text(
            55, 20, text=f"SPEED: {int(self.speed_mph)} MPH",
            font=("Consolas", 10, "bold"), fill="#FF007F", anchor="w"
        )
        # Score (top-right)
        self.canvas.create_text(
            305, 20, text=f"SCORE: {self.score:05d}",
            font=("Consolas", 10, "bold"), fill="#00FF66", anchor="e"
        )
        # Best Score (top-center)
        self.canvas.create_text(
            180, 20, text=f"BEST: {self.high_score:05d}",
            font=("Consolas", 10, "bold"), fill="#F1C40F", anchor="center"
        )

        # Draw Game Over Banner
        if self.game_over:
            # Let the explosion particles animate by not drawing overlay for first 12 frames
            if len(self.explosion_particles) < 12:
                # Dark semi-transparent overlay
                self.canvas.create_rectangle(0, 0, w, h, fill="#0c0c0f", outline="")
                
                # Banner text
                self.canvas.create_text(
                    w/2 + dx, 55 + dy, text="GAME OVER",
                    font=("Outfit", 20, "bold"), fill="#FF007F"
                )
                
                # Fetch metrics from analytics
                from utils.analytics import analytics_tracker
                m = analytics_tracker.compute_metrics()
                
                # Draw Box outline
                self.canvas.create_rectangle(30, 95, w - 30, 345, fill="#12121e", outline="#1b1836", width=2)
                
                self.canvas.create_text(
                    w/2, 115, text="AI SESSION DRIVING REPORT",
                    font=("Outfit", 12, "bold"), fill="#FF007F"
                )
                
                stats = [
                    ("🎮 Arcade Score", f"{self.score:05d}"),
                    ("🏆 Driving Score", f"{m['score']}/100"),
                    ("⚡ Smoothness", f"{int(m['smoothness'])}%"),
                    ("⏱ Reaction Time", f"{m['reaction_time']:.2f}s"),
                    ("🛣 Lane Discipline", f"{int(m['lane_discipline'])}%"),
                    ("⛽ Driving Efficiency", f"{int(m['efficiency'])}%")
                ]
                
                sy = 150
                for label, val in stats:
                    self.canvas.create_text(
                        50, sy, text=label,
                        font=("Outfit", 10, "bold"), fill="#00F5FF", anchor="w"
                    )
                    vcolor = "#00FF66" if "Score" in label else "#FFFFFF"
                    self.canvas.create_text(
                        210, sy, text=f"➔ {val}",
                        font=("Outfit", 10, "bold"), fill=vcolor, anchor="w"
                    )
                    sy += 30
                
                self.canvas.create_text(
                    w/2 + dx, 385 + dy, text="Press SPACE or click RESTART to drive again",
                    font=("Outfit", 10, "bold"), fill="#FFFFFF"
                )

        # Draw Real-Time Driving Coach Warning/Praise Banner
        if self.coach_timer > 0:
            self.coach_timer -= 1
            # Draw semi-transparent dark box with neon cyan outline
            self.canvas.create_rectangle(30 + dx, 335 + dy, w - 30 + dx, 368 + dy, fill="#0a0a0f", outline="#00F5FF", width=1.5)
            self.canvas.create_text(
                w/2 + dx, 351 + dy, text=self.coach_message,
                font=("Outfit", 10, "bold"),
                fill="#FF007F" if "⚠️" in self.coach_message or "💥" in self.coach_message else "#00FF66"
            )
        self._scale_canvas_to_fit()

    def trigger_coach_alert(self, text: str) -> None:
        """Triggers a fading on-screen coach alert banner."""
        self.coach_message = text
        self.coach_timer = 90  # display for ~1.8 seconds (90 frames * 20ms)
