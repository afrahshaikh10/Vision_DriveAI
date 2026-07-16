import time
import math
import cv2
import os
import random
from PIL import Image
import customtkinter as ctk
from typing import Optional, List, Tuple, Dict, Any
from utils.logger import logger
from datetime import datetime

class DashboardPanel(ctk.CTkFrame):
    """Main Dashboard for VisionDrive AI. Displays video, HUD, animated wheel, and logs."""
    def __init__(
        self,
        parent: Any,
        on_screenshot_callback: Any,
        on_record_toggle_callback: Any,
        on_fullscreen_callback: Any,
        on_game_callback: Any
    ):
        super().__init__(parent, corner_radius=15, fg_color="transparent")
        self.on_screenshot = on_screenshot_callback
        self.on_record_toggle = on_record_toggle_callback
        self.on_fullscreen = on_fullscreen_callback
        self.on_game = on_game_callback
        
        # State
        self.recording_active = False
        self.session_start_time: Optional[float] = None
        self.steering_history: List[float] = [0.0] * 60  # Graph points
        self.log_messages: List[str] = []
        self.hud_cards: Dict[str, ctk.CTkFrame] = {}
        self.current_fps = 30.0
        
        self.setup_ui()

    def setup_ui(self) -> None:
        # Configure Grid
        self.grid_columnconfigure(0, weight=3) # Left side: Video & controls
        self.grid_columnconfigure(1, weight=1) # Right side: Telemetry, Wheel, Graph, Logs
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # LEFT AREA: VIDEO & ACTION BAR
        # ==========================================
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        left_frame.grid_rowconfigure(0, weight=5) # Game & Video Feeds Row
        left_frame.grid_rowconfigure(1, weight=1) # Action buttons
        
        # Grid splits: column 0 = Game, column 1 = Video Preview
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_columnconfigure(1, weight=1)

        # 1. Embedded Retro Racing Game (Left side of dashboard viewport)
        from ui.game import RetroRacingGame
        self.game_widget = RetroRacingGame(left_frame)
        self.game_widget.grid(row=0, column=0, sticky="n", padx=(0, 5), pady=(0, 10))

        # 2. Video Frame Wrapper (Right side of dashboard viewport)
        self.video_wrapper = ctk.CTkFrame(left_frame, fg_color="#0a0a0f", corner_radius=12, border_width=1, border_color="#FF007F")
        self.video_wrapper.grid(row=0, column=1, sticky="n", padx=(5, 0), pady=(0, 10))
        self.video_wrapper.grid_rowconfigure(0, weight=1)
        self.video_wrapper.grid_columnconfigure(0, weight=1)

        # Live Feed Label
        self.video_label = ctk.CTkLabel(
            self.video_wrapper, text="CAMERA INACTIVE\n\nPress 'Start System' in the control panel to launch tracking feed.",
            font=ctk.CTkFont(family="Outfit", size=11, weight="bold"),
            text_color="#888888",
            wraplength=250
        )
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Calibration overlay banner (invisible by default)
        self.calib_overlay = ctk.CTkFrame(self.video_wrapper, fg_color="#0a0a0f", corner_radius=8, border_width=1, border_color="#FF007F")
        self.calib_instruction = ctk.CTkLabel(
            self.calib_overlay, text="Calibration Instructions",
            font=ctk.CTkFont(family="Outfit", size=14, weight="bold"),
            text_color="#FF4B4B"
        )
        self.calib_instruction.pack(fill="x", padx=15, pady=(15, 5))
        self.calib_progress = ctk.CTkProgressBar(self.calib_overlay, progress_color="#FF007F", fg_color="#121216")
        self.calib_progress.set(0)
        self.calib_progress.pack(fill="x", padx=25, pady=(5, 15))

        # Bottom Action Buttons Bar
        self.action_bar = ctk.CTkFrame(left_frame, fg_color="#0a0a0f", height=60, corner_radius=12, border_width=1, border_color="#FF007F")
        self.action_bar.grid(row=1, column=0, sticky="nsew")
        self.action_bar.grid_propagate(False)

        # Buttons
        self.screenshot_btn = ctk.CTkButton(
            self.action_bar, text="📸 SCREENSHOT", width=120, fg_color="#121216", hover_color="#FF007F", border_width=1, border_color="#1b1836",
            command=self.on_screenshot, cursor="hand2"
        )
        self.screenshot_btn.pack(side="left", padx=15, pady=15)

        self.record_btn = ctk.CTkButton(
            self.action_bar, text="⏺ RECORD SESSION", width=130, fg_color="#121216", hover_color="#C0392B", border_width=1, border_color="#1b1836",
            command=self.on_record_toggle, cursor="hand2"
        )
        self.record_btn.pack(side="left", padx=5, pady=15)

        self.game_btn = ctk.CTkButton(
            self.action_bar, text="🎮 START GAME", width=120, fg_color="#121216", hover_color="#FF007F", border_width=1, border_color="#1b1836",
            command=self.toggle_game_state, cursor="hand2"
        )
        self.game_btn.pack(side="left", padx=5, pady=15)

        self.fullscreen_btn = ctk.CTkButton(
            self.action_bar, text="🖥 FULLSCREEN", width=110, fg_color="#121216", hover_color="#FF007F", border_width=1, border_color="#1b1836",
            command=self.on_fullscreen, cursor="hand2"
        )
        self.fullscreen_btn.pack(side="right", padx=15, pady=15)

        # ==========================================
        # RIGHT AREA: METRICS & VISUAL TELEMETRY
        # ==========================================
        self.right_frame = ctk.CTkFrame(self, fg_color="#0a0a0f", corner_radius=15, border_color="#FF007F", border_width=1)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # 1. Telemetry HUD Cards
        hud_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        hud_frame.pack(fill="x", padx=15, pady=(15, 10))
        hud_frame.grid_columnconfigure((0, 1), weight=1)

        # Status Cards helper
        self.hud_widgets = {}
        self._add_hud_card(hud_frame, "ACCELERATOR", "OFF", 0, 0, color="#2ECC71")
        self._add_hud_card(hud_frame, "BRAKE", "OFF", 0, 1, color="#E74C3C")
        self._add_hud_card(hud_frame, "GESTURE", "Neutral", 1, 0, color="#00F5FF")
        self._add_hud_card(hud_frame, "SESSION TIME", "00:00", 1, 1, color="#F1C40F")

        # 2. RPM, Speedometer, Gear Vector Cluster
        hud_title = ctk.CTkLabel(self.right_frame, text="INSTRUMENT CLUSTER", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="#888888")
        hud_title.pack(pady=(8, 0))
        
        self.hud_canvas = ctk.CTkCanvas(self.right_frame, width=280, height=125, bg="#0a0a0f", highlightthickness=0)
        self.hud_canvas.pack(pady=5)
        self._draw_hud_dial(0.0, False, False, False)

        # 3. Dynamic Vector Steering Wheel
        wheel_title = ctk.CTkLabel(self.right_frame, text="STEERING WHEEL GEOMETRY", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="#888888")
        wheel_title.pack(pady=(5, 0))
        
        self.wheel_canvas = ctk.CTkCanvas(self.right_frame, width=280, height=130, bg="#0a0a0f", highlightthickness=0)
        self.wheel_canvas.pack(pady=5)
        self._draw_vector_wheel(0.0)

        # 4. Steering Graph Canvas
        graph_title = ctk.CTkLabel(self.right_frame, text="STEERING TELEMETRY GRAPH", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="#888888")
        graph_title.pack(pady=(5, 0))

        self.graph_canvas = ctk.CTkCanvas(self.right_frame, width=280, height=85, bg="#0a0a0f", highlightthickness=0)
        self.graph_canvas.pack(padx=15, pady=5)
        self._draw_graph()

        # 5. Console Log Terminal
        log_title = ctk.CTkLabel(self.right_frame, text="CORE TELEMETRY LOGS", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="#888888")
        log_title.pack(pady=(5, 0))

        self.log_textbox = ctk.CTkTextbox(
            self.right_frame, height=115, font=ctk.CTkFont(family="Consolas", size=9),
            fg_color="#0a0a0f", text_color="#00FF66", border_color="#1b1836", border_width=1
        )
        self.log_textbox.pack(fill="x", padx=15, pady=(5, 15))
        self.log_textbox.configure(state="disabled")

    def _add_hud_card(self, parent: Any, title: str, value: str, row: int, col: int, color: str) -> None:
        # Increase frame height to fit animated neon gauges/meters
        card = ctk.CTkFrame(parent, fg_color="#0a0a0f", corner_radius=10, border_color="#FF007F", border_width=1, height=80)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        card.grid_propagate(False)
        
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9, weight="bold"), text_color="#5a5a66")
        lbl_title.pack(anchor="w", padx=8, pady=(4, 0))
        
        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color=color)
        lbl_val.pack(anchor="w", padx=8, pady=(0, 2))
        
        self.hud_widgets[title] = lbl_val
        self.hud_cards[title] = card
        
        # Add F1 style neon bar indicators
        if title == "ACCELERATOR":
            pbar = ctk.CTkProgressBar(card, progress_color="#00FF66", fg_color="#161622", height=6, corner_radius=3)
            pbar.pack(fill="x", padx=8, pady=(2, 4))
            pbar.set(0.0)
            self.hud_widgets["ACCELERATOR_BAR"] = pbar
        elif title == "BRAKE":
            pbar = ctk.CTkProgressBar(card, progress_color="#FF007F", fg_color="#161622", height=6, corner_radius=3)
            pbar.pack(fill="x", padx=8, pady=(2, 4))
            pbar.set(0.0)
            self.hud_widgets["BRAKE_BAR"] = pbar

    def _draw_hud_dial(self, speed: float, accelerating: bool, braking: bool, handbrake: bool) -> None:
        """Draws a premium F1 radial RPM dial, Gear and Speed numeric layouts on canvas."""
        canvas = self.hud_canvas
        canvas.delete("all")
        
        w, h = 280, 125
        cx, cy = w / 2, h / 2 + 10
        r = 45
        
        # Calculate RPM matching sports car redline ranges (1000 - 9000 RPM)
        # Reaches redline as speed approaches maximum speed 120 mph
        rpm = (speed / 120.0) * 8000.0 + 1000.0
        if rpm > 9000: rpm = 9000
        
        # Calculate Gear index based on speed
        if speed <= 1.0:
            if braking or handbrake:
                gear_text = "R"
            else:
                gear_text = "N"
        elif speed < 20.0:
            gear_text = "1"
        elif speed < 40.0:
            gear_text = "2"
        elif speed < 60.0:
            gear_text = "3"
        elif speed < 80.0:
            gear_text = "4"
        elif speed < 100.0:
            gear_text = "5"
        else:
            gear_text = "6"
            
        # Draw background dial ticks / arc (225 deg to -45 deg)
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=-45, extent=270, style="arc", outline="#1b1836", width=6)
        
        # Draw dynamic filled RPM arc segment
        rpm_ratio = (rpm - 1000) / 8000.0
        extent = 270.0 * rpm_ratio
        
        # Color switches to flashing neon red if redlining
        if rpm >= 7500.0:
            arc_color = "#FF007F" if int(time.time() * 8) % 2 == 0 else "#FF3366"
        else:
            arc_color = "#00FF66" if rpm_ratio < 0.6 else "#00F5FF"
            
        if extent > 0.1:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=225, extent=-extent, style="arc", outline=arc_color, width=7)
            
        # Draw giant Gear character in the middle
        canvas.create_text(cx, cy - 10, text=gear_text, font=("Outfit", 26, "bold"), fill=arc_color)
        
        # Numeric speed readout below gear
        canvas.create_text(cx, cy + 18, text=f"{int(speed)}", font=("Outfit", 18, "bold"), fill="#FFFFFF")
        canvas.create_text(cx, cy + 32, text="MPH", font=("Outfit", 8, "bold"), fill="#5a5a66")
        
        # Draw RPM markings (e.g. x1000 RPM)
        canvas.create_text(cx - r - 20, cy + 20, text="1K", font=("Consolas", 8), fill="#5a5a66")
        canvas.create_text(cx + r + 20, cy + 20, text="9K", font=("Consolas", 8), fill="#5a5a66")

    def _draw_vector_wheel(self, angle_deg: float) -> None:
        """Draws a premium 3D effect racing wheel rotated and shaking on fast turn sweeps."""
        canvas = self.wheel_canvas
        canvas.delete("all")
        
        cx, cy = 140, 65
        
        # Aggressive steering shake trigger (shake coordinates if user steers sharply)
        sx, sy = 0.0, 0.0
        if abs(angle_deg) > 22.0:
            sx = random.uniform(-1.5, 1.5)
            sy = random.uniform(-1.5, 1.5)
            
        cx += sx
        cy += sy
        r = 52
        
        # Convert steering angle to radians
        angle_rad = math.radians(-angle_deg)
        
        # Blend border highlights dynamically based on current weather themes
        from utils.weather import weather_manager
        theme_accent = weather_manager.get_color("accent")
        theme_border = weather_manager.get_color("border")
        
        # Draw outer premium rim shadow
        canvas.create_oval(cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6, outline="#050508", width=12)
        
        # Motion blur trailing arcs when steering aggressively
        if abs(angle_deg) > 10.0:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=90 - angle_deg - 30, extent=60, style="arc", outline=theme_accent, width=8, stipple="gray25")
        
        # Draw leather sports grip (Outer rim)
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#1b1836", width=8)
        
        # Dynamic active lighting glow
        extent_angle = min(360.0, abs(angle_deg) * 3.0)
        start_angle = 90 - angle_deg
        if extent_angle > 5.0:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=start_angle, extent=extent_angle if angle_deg < 0 else -extent_angle, style="arc", outline=theme_accent, width=8)
            
        # Hub center circle
        canvas.create_oval(cx - 16, cy - 16, cx + 16, cy + 16, fill="#0a0a0f", outline=theme_border, width=3)
        canvas.create_text(cx, cy, text="VD", font=("Outfit", 8, "bold"), fill=theme_accent)
        
        # Draw spoke angles
        spoke_angles = [angle_rad + math.pi / 2, angle_rad + 7 * math.pi / 6, angle_rad + 11 * math.pi / 6]
        for sa in spoke_angles:
            x_end = cx + (r - 6) * math.cos(sa)
            y_end = cy + (r - 6) * math.sin(sa)
            canvas.create_line(cx, cy, x_end, y_end, fill="#121216", width=6)
            canvas.create_line(cx, cy, x_end, y_end, fill="#383a48", width=2)
            
        # Centering top marker
        center_a = angle_rad - math.pi / 2
        cx_top = cx + r * math.cos(center_a)
        cy_top = cy + r * math.sin(center_a)
        canvas.create_oval(cx_top - 5, cy_top - 5, cx_top + 5, cy_top + 5, fill=theme_border, outline="#ffffff", width=1.5)

    def _draw_graph(self) -> None:
        """Draws the running history graph of steering angles with custom gradient neon paths."""
        canvas = self.graph_canvas
        canvas.delete("all")
        
        w, h = 280, 85
        ch = h / 2 # Center line (0 degrees)
        
        # Grid lines
        canvas.create_line(0, ch, w, ch, fill="#1b1836", dash=(4, 4)) # zero line
        canvas.create_line(0, ch - 25, w, ch - 25, fill="#0c0c16") # top limit
        canvas.create_line(0, ch + 25, w, ch + 25, fill="#0c0c16") # bottom limit
        
        points = []
        num_points = len(self.steering_history)
        dx = w / (num_points - 1)
        
        for i, val in enumerate(self.steering_history):
            x = i * dx
            y_offset = (val / 45.0) * 28.0
            y = ch - y_offset
            points.append((x, y))
            
        # Draw line segment by segment
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i+1]
            
            # Map neon gradient based on severity of steering angle
            avg_val = abs(self.steering_history[i] + self.steering_history[i+1]) / 2.0
            if avg_val > 22.0:
                color = "#FF007F"  # neon pink for sharp turns
            elif avg_val > 8.0:
                color = "#00F5FF"  # cyan for moderate steering
            else:
                color = "#00FF66"  # green for neutral/straight
            canvas.create_line(x1, y1, x2, y2, fill=color, width=2)

    def update_telemetry(
        self,
        steering_angle: float,
        steering_state: str,
        accelerating: bool,
        braking: bool,
        handbrake: bool,
        fps: float,
        gesture_name: str = "Neutral",
        confidence: float = 0.0,
        raw_frame: Optional[cv2.Mat] = None
    ) -> None:
        """Called periodically by the main application to update all HUD elements."""
        self.current_fps = fps
        # Dynamically recolor dashboard container borders to match active weather managers
        from utils.weather import weather_manager
        theme_border = weather_manager.get_color("border")
        
        self.right_frame.configure(border_color=theme_border)
        self.video_wrapper.configure(border_color=theme_border)
        self.action_bar.configure(border_color=theme_border)
        self.calib_overlay.configure(border_color=theme_border)
        
        for card in self.hud_cards.values():
            card.configure(border_color=theme_border)
            
        # Draw vector dials
        speed_mph = self.game_widget.speed_mph if hasattr(self, "game_widget") else 0.0
        self._draw_hud_dial(speed_mph, accelerating, braking, handbrake)
        
        # Update graph data queue
        self.steering_history.append(steering_angle)
        if len(self.steering_history) > 60:
            self.steering_history.pop(0)
        self._draw_graph()
        self._draw_vector_wheel(steering_angle)

        # 1. Update Accelerator Card
        accel_text = "ACTIVE" if accelerating else "OFF"
        self.hud_widgets["ACCELERATOR"].configure(text=accel_text)
        if "ACCELERATOR_BAR" in self.hud_widgets:
            self.hud_widgets["ACCELERATOR_BAR"].set(1.0 if accelerating else 0.0)
        
        # 2. Update Brake Card
        if handbrake:
            brake_text = "HANDBRAKE"
            self.hud_widgets["BRAKE"].configure(text=brake_text, text_color="#FF007F")
            if "BRAKE_BAR" in self.hud_widgets:
                self.hud_widgets["BRAKE_BAR"].configure(progress_color="#FF007F")
                self.hud_widgets["BRAKE_BAR"].set(1.0)
        elif braking:
            brake_text = "BRAKING"
            self.hud_widgets["BRAKE"].configure(text=brake_text, text_color="#FF4B4B")
            if "BRAKE_BAR" in self.hud_widgets:
                self.hud_widgets["BRAKE_BAR"].configure(progress_color="#FF4B4B")
                self.hud_widgets["BRAKE_BAR"].set(1.0)
        else:
            brake_text = "OFF"
            self.hud_widgets["BRAKE"].configure(text=brake_text, text_color="#5a5a66")
            if "BRAKE_BAR" in self.hud_widgets:
                self.hud_widgets["BRAKE_BAR"].set(0.0)

        # 3. Update Gesture Card
        gest_display = f"{gesture_name} ({int(confidence * 100)}%)"
        self.hud_widgets["GESTURE"].configure(text=gest_display)

        # 4. Update timer
        if self.session_start_time is not None:
            elapsed = int(time.time() - self.session_start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.hud_widgets["SESSION TIME"].configure(text=f"{mins:02d}:{secs:02d}")

    def update_video_feed(self, processed_frame: cv2.Mat) -> None:
        """Converts raw BGR cv2 image to CTkImage and overlays onboard telemetry details."""
        draw_frame = processed_frame.copy()
        fh, fw = draw_frame.shape[:2]
        
        # 1. Onboard Driver HUD Corner Bracket Overlays
        bracket_len = 15
        color = (255, 245, 0) # Cyan (BGR)
        # Top-Left Bracket
        cv2.line(draw_frame, (10, 10), (10 + bracket_len, 10), color, 2)
        cv2.line(draw_frame, (10, 10), (10, 10 + bracket_len), color, 2)
        # Top-Right Bracket
        cv2.line(draw_frame, (fw - 10, 10), (fw - 10 - bracket_len, 10), color, 2)
        cv2.line(draw_frame, (fw - 10, 10), (fw - 10, 10 + bracket_len), color, 2)
        # Bottom-Left Bracket
        cv2.line(draw_frame, (10, fh - 10), (10 + bracket_len, fh - 10), color, 2)
        cv2.line(draw_frame, (10, fh - 10), (10, fh - 10 - bracket_len), color, 2)
        # Bottom-Right Bracket
        cv2.line(draw_frame, (fw - 10, fh - 10), (fw - 10 - bracket_len, fh - 10), color, 2)
        cv2.line(draw_frame, (fw - 10, fh - 10), (fw - 10, fh - 10 - bracket_len), color, 2)
        
        # 2. Blinking Onboard REC overlay
        if self.recording_active and int(time.time() * 2) % 2 == 0:
            cv2.circle(draw_frame, (25, 25), 6, (0, 0, 255), -1) # BGR Red
            cv2.putText(draw_frame, "REC", (38, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            
        # 3. System Signal Status & FPS
        fps_text = f"SIGNAL: 100% | FPS: {int(self.current_fps)}"
        cv2.putText(draw_frame, fps_text, (fw - 150, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 245, 0), 1, cv2.LINE_AA)
        
        rgb_img = cv2.cvtColor(draw_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(320, 240))
        self.video_label.configure(image=ctk_img, text="")
        self.video_label.image = ctk_img

    def show_calibration_overlay(self, step: int, progress: float, instructions: str) -> None:
        """Shows and updates the calibration Wizard HUD widget."""
        if step > 0 and step < 4:
            self.calib_overlay.place(relx=0.5, rely=0.85, anchor="center", relwidth=0.85)
            self.calib_instruction.configure(text=f"Calibration Step {step}: {instructions}")
            self.calib_progress.set(progress)
        elif step == 4:
            self.calib_instruction.configure(text=instructions)
            self.calib_progress.set(1.0)
            self.calib_overlay.place(relx=0.5, rely=0.85, anchor="center", relwidth=0.85)
        else:
            self.calib_overlay.place_forget()

    def set_recording_state(self, active: bool) -> None:
        """Toggles recording status colors on the action bar button."""
        self.recording_active = active
        if active:
            self.record_btn.configure(text="● RECORDING", fg_color="#C0392B", hover_color="#962D22")
            self.add_log_message("SYSTEM: Video recording started.")
        else:
            self.record_btn.configure(text="⏺ RECORD SESSION", fg_color="#2D2D35", hover_color="#C0392B")
            self.add_log_message("SYSTEM: Video recording stopped and saved.")

    def add_log_message(self, message: str) -> None:
        """Appends logs with terminal block cursor style typing effects."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] >>> {message}"
        self.log_messages.append(formatted)
        if len(self.log_messages) > 20:
            self.log_messages.pop(0)
            
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.insert("1.0", "\n".join(self.log_messages) + " █")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_session_timer(self) -> None:
        self.session_start_time = time.time()
        self.hud_widgets["SESSION TIME"].configure(text="00:00")
        self.add_log_message("SYSTEM: Drive Session Started.")

    def stop_session_timer(self) -> None:
        self.session_start_time = None
        self.hud_widgets["SESSION TIME"].configure(text="--:--")
        self.add_log_message("SYSTEM: Drive Session Paused.")

    def toggle_game_state(self) -> None:
        """Toggles the running state of the embedded retro racing game."""
        game = self.game_widget
        
        # If the game is in a crashed state, restart it
        if game.game_over:
            game.reset_game()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color="#FF007F", hover_color="#CC0066", text_color="#FFFFFF")
            self.add_log_message("GAME: Retro Racing Game Restarted.")
            return

        if not game.game_started:
            game.start_game()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color="#FF007F", hover_color="#CC0066", text_color="#FFFFFF")
            self.add_log_message("GAME: Retro Racing Game Started.")
        elif game.game_running:
            game.stop_game()
            self.game_btn.configure(text="▶ RESUME GAME", fg_color="#00FF66", hover_color="#00CC52", text_color="#0A0A0F")
            self.add_log_message("GAME: Retro Racing Game Paused.")
        else:
            game.game_running = True
            game.game_loop()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color="#FF007F", hover_color="#CC0066", text_color="#FFFFFF")
            self.add_log_message("GAME: Retro Racing Game Resumed.")
        
        # Fire callback if mapped
        if self.on_game is not None:
            try:
                self.on_game()
            except:
                pass
        
    def reset_view(self) -> None:
        """Clear labels when video feed is stopped."""
        self.video_label.configure(image="", text="CAMERA INACTIVE\n\nPress 'Start System' in the control panel to launch tracking feed.")
        self.video_label.image = None
        self.hud_widgets["GESTURE"].configure(text="Neutral")
        self.hud_widgets["ACCELERATOR"].configure(text="OFF")
        self.hud_widgets["BRAKE"].configure(text="OFF")
        self.stop_session_timer()
        self.steering_history = [0.0] * 60
        self._draw_graph()
        self._draw_vector_wheel(0.0)
        
        # Stop and reset game widget
        self.game_widget.stop_game()
        self.game_widget.game_started = False
        self.game_widget._draw_splash()
        self.game_btn.configure(text="🎮 START GAME", fg_color="#2D2D35", hover_color="#3498DB")
