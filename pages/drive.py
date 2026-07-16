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
from utils.theme_manager import get_theme_colors

class DriveScreen(ctk.CTkFrame):
    """Refactored Driving Simulator screen wrapping retro racing game and camera HUD."""
    def __init__(
        self,
        parent: Any,
        user_data: Dict[str, Any],
        on_screenshot_callback: Any,
        on_record_toggle_callback: Any,
        on_fullscreen_callback: Any,
        on_game_callback: Any,
        on_start_callback: Any,
        on_stop_callback: Any,
        on_calibrate_callback: Any
    ):
        super().__init__(parent, corner_radius=15, fg_color="transparent")
        self.user_data = user_data
        self.on_screenshot = on_screenshot_callback
        self.on_record_toggle = on_record_toggle_callback
        self.on_fullscreen = on_fullscreen_callback
        self.on_game = on_game_callback
        self.on_start = on_start_callback
        self.on_stop = on_stop_callback
        self.on_calibrate = on_calibrate_callback
        
        # State
        self.recording_active = False
        self.session_start_time: Optional[float] = None
        self.steering_history: List[float] = [0.0] * 60
        self.log_messages: List[str] = []
        self.hud_cards: Dict[str, ctk.CTkFrame] = {}
        self.current_fps = 30.0
        
        self.setup_ui()

    def setup_ui(self) -> None:
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        self.immersive_active = False

        # ==========================================
        # 1. TOP BAR HUD (☰ VisionDrive AI | Weather | Session Time | Time)
        # ==========================================
        self.top_bar = ctk.CTkFrame(self, fg_color="#0a0a0f", height=45, corner_radius=10, border_width=1, border_color=colors["border"])
        self.top_bar.pack(side="top", fill="x", pady=(0, 10))
        self.top_bar.pack_propagate(False)

        # Hamburger Button
        self.hamburger_btn = ctk.CTkButton(
            self.top_bar, text="☰", width=30, height=30, fg_color="transparent", hover_color="#12121e",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFFFFF", command=self.on_hamburger_click,
            cursor="hand2"
        )
        self.hamburger_btn.pack(side="left", padx=10, pady=7)

        # Title Label
        self.top_title = ctk.CTkLabel(
            self.top_bar, text="VISIONDRIVE AI - FOCUS MODE",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            text_color=colors["accent"]
        )
        self.top_title.pack(side="left", padx=5)

        # Right-side indicators
        indicators_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        indicators_frame.pack(side="right", padx=15, pady=5)

        self.top_weather_lbl = ctk.CTkLabel(indicators_frame, text="WEATHER: SUNNY", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=colors["secondary"])
        self.top_weather_lbl.pack(side="left", padx=15)

        self.top_session_lbl = ctk.CTkLabel(indicators_frame, text="TIME: --:--", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#F1C40F")
        self.top_session_lbl.pack(side="left", padx=15)

        self.top_fps_lbl = ctk.CTkLabel(indicators_frame, text="SIGNAL: 100% | 30 FPS", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#00FF66")
        self.top_fps_lbl.pack(side="left", padx=15)

        self.top_time_lbl = ctk.CTkLabel(indicators_frame, text="00:00:00", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#FFFFFF")
        self.top_time_lbl.pack(side="left", padx=15)

        # Start live digital clock thread loop
        self.update_top_clock()

        # ==========================================
        # 2. MIDDLE VIEWPORT AREA (Game Frame & Webcam Frame)
        # ==========================================
        self.middle_row = ctk.CTkFrame(self, fg_color="transparent")
        self.middle_row.pack(side="top", fill="both", expand=True)

        # Game Frame Card (Left side)
        self.game_card = ctk.CTkFrame(self.middle_row, fg_color="#0f0f1b", border_width=1, border_color=colors["border"], corner_radius=12)
        self.game_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        from ui.game import RetroRacingGame
        self.game_widget = RetroRacingGame(self.game_card)
        self.game_widget.pack(fill="both", expand=True, padx=10, pady=10)

        # Camera Frame Card (Right side)
        self.cam_card = ctk.CTkFrame(self.middle_row, fg_color="#0f0f1b", border_width=1, border_color=colors["border"], corner_radius=12, height=330, width=440)
        self.cam_card.pack(side="right", fill="both", expand=True, padx=(5, 0))
        self.cam_card.pack_propagate(False)

        # Live Feed Label centered inside cam_card
        self.video_wrapper = self.cam_card  # Keep compatibility with existing calibration/video wrapper code
        self.video_label = ctk.CTkLabel(
            self.cam_card, text="CAMERA INACTIVE\n\nClick 'START CAMERA' or calibration wizard to begin.",
            font=ctk.CTkFont(family="Outfit", size=11, weight="bold"),
            text_color="#888888",
            wraplength=250
        )
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)

        # Calibration overlay banner (invisible by default)
        self.calib_overlay = ctk.CTkFrame(self.cam_card, fg_color="#0a0a0f", corner_radius=8, border_width=1, border_color=colors["border"])
        self.calib_instruction = ctk.CTkLabel(
            self.calib_overlay, text="Calibration Instructions",
            font=ctk.CTkFont(family="Outfit", size=14, weight="bold"),
            text_color=colors["accent"]
        )
        self.calib_instruction.pack(fill="x", padx=15, pady=(15, 5))
        self.calib_progress = ctk.CTkProgressBar(self.calib_overlay, progress_color=colors["accent"], fg_color="#121216")
        self.calib_progress.set(0)
        self.calib_progress.pack(fill="x", padx=25, pady=(5, 15))

        # ==========================================
        # 3. BOTTOM CONTROL DOCK (Clean Horizontal Buttons)
        # ==========================================
        self.bottom_dock = ctk.CTkFrame(self, fg_color="#0a0a0f", height=60, corner_radius=12, border_width=1, border_color=colors["border"])
        self.bottom_dock.pack(side="top", fill="x", pady=5)
        self.bottom_dock.pack_propagate(False)
        self.bottom_dock.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        self.bottom_dock.grid_rowconfigure(0, weight=1)

        self.game_btn = ctk.CTkButton(
            self.bottom_dock, text="▶ START GAME", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color="#00FF66", border_width=1, border_color="#1b1836",
            command=self.resume_game, cursor="hand2"
        )
        self.game_btn.grid(row=0, column=0, sticky="nsew", padx=6, pady=10)

        self.pause_btn = ctk.CTkButton(
            self.bottom_dock, text="⏸ PAUSE GAME", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color=colors["accent"], border_width=1, border_color="#1b1836",
            command=self.pause_game, cursor="hand2"
        )
        self.pause_btn.grid(row=0, column=1, sticky="nsew", padx=6, pady=10)

        self.start_btn = ctk.CTkButton(
            self.bottom_dock, text="🟢 START CAMERA", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color="#00FF66", border_width=1, border_color="#1b1836",
            command=self.on_start, cursor="hand2"
        )
        self.start_btn.grid(row=0, column=2, sticky="nsew", padx=6, pady=10)

        self.stop_btn = ctk.CTkButton(
            self.bottom_dock, text="🔴 STOP CAMERA", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color="#FF007F", border_width=1, border_color="#1b1836",
            command=self.on_stop, cursor="hand2"
        )
        self.stop_btn.grid(row=0, column=3, sticky="nsew", padx=6, pady=10)

        self.calib_btn = ctk.CTkButton(
            self.bottom_dock, text="🔧 CALIBRATE", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color="#00F5FF", border_width=1, border_color="#1b1836",
            command=self.on_calibrate, cursor="hand2"
        )
        self.calib_btn.grid(row=0, column=4, sticky="nsew", padx=6, pady=10)

        self.screenshot_btn = ctk.CTkButton(
            self.bottom_dock, text="📸 SNAPSHOT", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color=colors["accent"], border_width=1, border_color="#1b1836",
            command=self.on_screenshot, cursor="hand2"
        )
        self.screenshot_btn.grid(row=0, column=5, sticky="nsew", padx=6, pady=10)

        self.fullscreen_btn = ctk.CTkButton(
            self.bottom_dock, text="🖥 IMMERSIVE", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color=colors["accent"], border_width=1, border_color="#1b1836",
            command=self.toggle_immersive_mode, cursor="hand2"
        )
        self.fullscreen_btn.grid(row=0, column=6, sticky="nsew", padx=6, pady=10)

        self.record_btn = ctk.CTkButton(
            self.bottom_dock, text="⏺ RECORD", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#121216", hover_color="#C0392B", border_width=1, border_color="#1b1836",
            command=self.on_record_toggle, cursor="hand2"
        )
        self.record_btn.grid(row=0, column=7, sticky="nsew", padx=6, pady=10)

        # ==========================================
        # 4. TELEMETRY DASHBOARD (Streamlined Bottom Panels)
        # ==========================================
        self.telemetry_dock = ctk.CTkFrame(self, fg_color="#0a0a0f", height=120, corner_radius=12, border_width=1, border_color=colors["border"])
        self.telemetry_dock.pack(side="top", fill="x", pady=(5, 0))
        self.telemetry_dock.pack_propagate(False)
        self.telemetry_dock.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        self.telemetry_dock.grid_rowconfigure(0, weight=1)

        # A. Speedometer Instrument Canvas
        self.hud_canvas = ctk.CTkCanvas(self.telemetry_dock, width=240, height=120, bg="#0a0a0f", highlightthickness=0)
        self.hud_canvas.grid(row=0, column=0, padx=6, pady=2, sticky="nsew")

        # B. Accelerator Card
        accel_card = ctk.CTkFrame(self.telemetry_dock, fg_color="#0f0f1b", corner_radius=10, border_color=colors["border"], border_width=1)
        accel_card.grid(row=0, column=1, padx=6, pady=10, sticky="nsew")
        accel_card.grid_propagate(False)
        
        lbl_accel_title = ctk.CTkLabel(accel_card, text="ACCELERATOR", font=ctk.CTkFont(size=9, weight="bold"), text_color="#5a5a66")
        lbl_accel_title.pack(anchor="w", padx=10, pady=(10, 2))
        self.lbl_accel_val = ctk.CTkLabel(accel_card, text="OFF", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#2ECC71")
        self.lbl_accel_val.pack(anchor="w", padx=10, pady=2)
        self.accel_pbar = ctk.CTkProgressBar(accel_card, progress_color="#00FF66", fg_color="#161622", height=6, corner_radius=3)
        self.accel_pbar.pack(fill="x", padx=10, pady=(2, 6))
        self.accel_pbar.set(0.0)

        # C. Brake Card
        brake_card = ctk.CTkFrame(self.telemetry_dock, fg_color="#0f0f1b", corner_radius=10, border_color=colors["border"], border_width=1)
        brake_card.grid(row=0, column=2, padx=6, pady=10, sticky="nsew")
        brake_card.grid_propagate(False)
        
        lbl_brake_title = ctk.CTkLabel(brake_card, text="BRAKE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#5a5a66")
        lbl_brake_title.pack(anchor="w", padx=10, pady=(10, 2))
        self.lbl_brake_val = ctk.CTkLabel(brake_card, text="OFF", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#E74C3C")
        self.lbl_brake_val.pack(anchor="w", padx=10, pady=2)
        self.brake_pbar = ctk.CTkProgressBar(brake_card, progress_color="#FF007F", fg_color="#161622", height=6, corner_radius=3)
        self.brake_pbar.pack(fill="x", padx=10, pady=(2, 6))
        self.brake_pbar.set(0.0)

        # D. Active Gesture Card
        gest_card = ctk.CTkFrame(self.telemetry_dock, fg_color="#0f0f1b", corner_radius=10, border_color=colors["border"], border_width=1)
        gest_card.grid(row=0, column=3, padx=6, pady=10, sticky="nsew")
        gest_card.grid_propagate(False)
        
        lbl_gest_title = ctk.CTkLabel(gest_card, text="ACTIVE GESTURE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#5a5a66")
        lbl_gest_title.pack(anchor="w", padx=10, pady=(10, 5))
        self.lbl_gest_val = ctk.CTkLabel(gest_card, text="Neutral", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color=colors["secondary"])
        self.lbl_gest_val.pack(anchor="w", padx=10, pady=2)

        # E. FPS Card
        fps_card = ctk.CTkFrame(self.telemetry_dock, fg_color="#0f0f1b", corner_radius=10, border_color=colors["border"], border_width=1)
        fps_card.grid(row=0, column=4, padx=6, pady=10, sticky="nsew")
        fps_card.grid_propagate(False)
        
        lbl_fps_title = ctk.CTkLabel(fps_card, text="LOOP FRAME RATE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#5a5a66")
        lbl_fps_title.pack(anchor="w", padx=10, pady=(10, 5))
        self.lbl_fps_val = ctk.CTkLabel(fps_card, text="30 FPS", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color="#F1C40F")
        self.lbl_fps_val.pack(anchor="w", padx=10, pady=2)

        # F. Steering Wheel Vector Canvas
        self.wheel_canvas = ctk.CTkCanvas(self.telemetry_dock, width=240, height=120, bg="#0a0a0f", highlightthickness=0)
        self.wheel_canvas.grid(row=0, column=5, padx=6, pady=2, sticky="nsew")

        # Map to HUD widgets dictionary for backend updates compatibility
        self.hud_widgets = {
            "ACCELERATOR": self.lbl_accel_val,
            "ACCELERATOR_BAR": self.accel_pbar,
            "BRAKE": self.lbl_brake_val,
            "BRAKE_BAR": self.brake_pbar,
            "GESTURE": self.lbl_gest_val,
            "SESSION TIME": self.top_session_lbl,
            "FPS": self.lbl_fps_val
        }
        self.hud_cards = {}  # Compatibility empty dictionary

        # Clean logs textbox frame (invisible dummy logger for error prevention)
        self.log_textbox = ctk.CTkTextbox(self, height=1)
        self.log_textbox.pack_forget()

    def _add_hud_card(self, parent: Any, title: str, value: str, row: int, col: int, color: str, border_color: str) -> None:
        card = ctk.CTkFrame(parent, fg_color="#0a0a0f", corner_radius=10, border_color=border_color, border_width=1, height=80)
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
        canvas = self.hud_canvas
        canvas.delete("all")
        
        w, h = 240, 120
        cx, cy = w / 2, h / 2 + 5
        r = 40
        
        rpm = (speed / 120.0) * 8000.0 + 1000.0
        if rpm > 9000: rpm = 9000
        
        if speed <= 1.0:
            gear_text = "R" if (braking or handbrake) else "N"
        elif speed < 20.0: gear_text = "1"
        elif speed < 40.0: gear_text = "2"
        elif speed < 60.0: gear_text = "3"
        elif speed < 80.0: gear_text = "4"
        elif speed < 100.0: gear_text = "5"
        else: gear_text = "6"
            
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=-45, extent=270, style="arc", outline="#1b1836", width=6)
        
        rpm_ratio = (rpm - 1000) / 8000.0
        extent = 270.0 * rpm_ratio
        
        if rpm >= 7500.0:
            arc_color = "#FF007F" if int(time.time() * 8) % 2 == 0 else "#FF3366"
        else:
            arc_color = "#00FF66" if rpm_ratio < 0.6 else "#00F5FF"
            
        if extent > 0.1:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=225, extent=-extent, style="arc", outline=arc_color, width=7)
            
        canvas.create_text(cx, cy - 8, text=gear_text, font=("Outfit", 22, "bold"), fill=arc_color)
        canvas.create_text(cx, cy + 15, text=f"{int(speed)}", font=("Outfit", 16, "bold"), fill="#FFFFFF")
        canvas.create_text(cx, cy + 27, text="MPH", font=("Outfit", 7, "bold"), fill="#5a5a66")
        
        canvas.create_text(cx - r - 15, cy + 18, text="1K", font=("Consolas", 7), fill="#5a5a66")
        canvas.create_text(cx + r + 15, cy + 18, text="9K", font=("Consolas", 7), fill="#5a5a66")

    def _draw_vector_wheel(self, angle_deg: float) -> None:
        canvas = self.wheel_canvas
        canvas.delete("all")
        
        cx, cy = 120, 60
        sx, sy = 0.0, 0.0
        if abs(angle_deg) > 22.0:
            sx = random.uniform(-1.5, 1.5)
            sy = random.uniform(-1.5, 1.5)
            
        cx += sx
        cy += sy
        r = 52
        
        angle_rad = math.radians(-angle_deg)
        
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        theme_accent = colors["accent"]
        theme_border = colors["border"]
        
        canvas.create_oval(cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6, outline="#050508", width=12)
        
        if abs(angle_deg) > 10.0:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=90 - angle_deg - 30, extent=60, style="arc", outline=theme_accent, width=8, stipple="gray25")
        
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#1b1836", width=8)
        
        extent_angle = min(360.0, abs(angle_deg) * 3.0)
        start_angle = 90 - angle_deg
        if extent_angle > 5.0:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=start_angle, extent=extent_angle if angle_deg < 0 else -extent_angle, style="arc", outline=theme_accent, width=8)
            
        canvas.create_oval(cx - 16, cy - 16, cx + 16, cy + 16, fill="#0a0a0f", outline=theme_border, width=3)
        canvas.create_text(cx, cy, text="VD", font=("Outfit", 8, "bold"), fill=theme_accent)
        
        spoke_angles = [angle_rad + math.pi / 2, angle_rad + 7 * math.pi / 6, angle_rad + 11 * math.pi / 6]
        for sa in spoke_angles:
            x_end = cx + (r - 6) * math.cos(sa)
            y_end = cy + (r - 6) * math.sin(sa)
            canvas.create_line(cx, cy, x_end, y_end, fill="#121216", width=6)
            canvas.create_line(cx, cy, x_end, y_end, fill="#383a48", width=2)
            
        center_a = angle_rad - math.pi / 2
        cx_top = cx + r * math.cos(center_a)
        cy_top = cy + r * math.sin(center_a)
        canvas.create_oval(cx_top - 5, cy_top - 5, cx_top + 5, cy_top + 5, fill=theme_border, outline="#ffffff", width=1.5)
        canvas.create_text(cx, cy + 22, text=f"{int(angle_deg)}°", font=("Consolas", 9, "bold"), fill="#FFFFFF")

    def _draw_graph(self) -> None:
        if not hasattr(self, "graph_canvas") or self.graph_canvas is None:
            return
        canvas = self.graph_canvas
        canvas.delete("all")
        
        w, h = 280, 85
        ch = h / 2
        
        canvas.create_line(0, ch, w, ch, fill="#1b1836", dash=(4, 4))
        canvas.create_line(0, ch - 25, w, ch - 25, fill="#0c0c16")
        canvas.create_line(0, ch + 25, w, ch + 25, fill="#0c0c16")
        
        points = []
        num_points = len(self.steering_history)
        dx = w / (num_points - 1)
        
        for i, val in enumerate(self.steering_history):
            x = i * dx
            y_offset = (val / 45.0) * 28.0
            y = ch - y_offset
            points.append((x, y))
            
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i+1]
            
            avg_val = abs(self.steering_history[i] + self.steering_history[i+1]) / 2.0
            if avg_val > 22.0:
                color = "#FF007F"
            elif avg_val > 8.0:
                color = "#00F5FF"
            else:
                color = "#00FF66"
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
        self.current_fps = fps
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        theme_border = colors["border"]
        
        # Configure layout borders dynamically
        if hasattr(self, "top_bar") and self.top_bar:
            self.top_bar.configure(border_color=theme_border)
        if hasattr(self, "game_card") and self.game_card:
            self.game_card.configure(border_color=theme_border)
        if hasattr(self, "cam_card") and self.cam_card:
            self.cam_card.configure(border_color=theme_border)
        if hasattr(self, "bottom_dock") and self.bottom_dock:
            self.bottom_dock.configure(border_color=theme_border)
        if hasattr(self, "telemetry_dock") and self.telemetry_dock:
            self.telemetry_dock.configure(border_color=theme_border)
        if hasattr(self, "calib_overlay") and self.calib_overlay:
            self.calib_overlay.configure(border_color=theme_border)
            
        # Update top HUD status bar labels
        if hasattr(self, "top_weather_lbl") and self.top_weather_lbl:
            weather_text = "SUNNY"
            if hasattr(self, "game_widget") and hasattr(self.game_widget, "current_weather"):
                weather_text = self.game_widget.current_weather.upper()
            self.top_weather_lbl.configure(text=f"WEATHER: {weather_text}")
        if hasattr(self, "top_fps_lbl") and self.top_fps_lbl:
            self.top_fps_lbl.configure(text=f"SIGNAL: 100% | {int(fps)} FPS")
        if "FPS" in self.hud_widgets:
            self.hud_widgets["FPS"].configure(text=f"{int(fps)} FPS")
            
        speed_mph = self.game_widget.speed_mph if hasattr(self, "game_widget") else 0.0
        self._draw_hud_dial(speed_mph, accelerating, braking, handbrake)
        
        self.steering_history.append(steering_angle)
        if len(self.steering_history) > 60:
            self.steering_history.pop(0)
        self._draw_graph()
        self._draw_vector_wheel(steering_angle)

        accel_text = "ACTIVE" if accelerating else "OFF"
        self.hud_widgets["ACCELERATOR"].configure(text=accel_text)
        if "ACCELERATOR_BAR" in self.hud_widgets:
            self.hud_widgets["ACCELERATOR_BAR"].set(1.0 if accelerating else 0.0)
        
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

        gest_display = f"{gesture_name} ({int(confidence * 100)}%)"
        self.hud_widgets["GESTURE"].configure(text=gest_display)

        if self.session_start_time is not None:
            elapsed = int(time.time() - self.session_start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.hud_widgets["SESSION TIME"].configure(text=f"{mins:02d}:{secs:02d}")

    def update_video_feed(self, processed_frame: cv2.Mat) -> None:
        draw_frame = processed_frame.copy()
        fh, fw = draw_frame.shape[:2]
        
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        # Cyan / Accent corner brackets
        bracket_len = 15
        color = (255, 245, 0)
        cv2.line(draw_frame, (10, 10), (10 + bracket_len, 10), color, 2)
        cv2.line(draw_frame, (10, 10), (10, 10 + bracket_len), color, 2)
        cv2.line(draw_frame, (fw - 10, 10), (fw - 10 - bracket_len, 10), color, 2)
        cv2.line(draw_frame, (fw - 10, 10), (fw - 10, 10 + bracket_len), color, 2)
        cv2.line(draw_frame, (10, fh - 10), (10 + bracket_len, fh - 10), color, 2)
        cv2.line(draw_frame, (10, fh - 10), (10, fh - 10 - bracket_len), color, 2)
        cv2.line(draw_frame, (fw - 10, fh - 10), (fw - 10 - bracket_len, fh - 10), color, 2)
        cv2.line(draw_frame, (fw - 10, fh - 10), (fw - 10, fh - 10 - bracket_len), color, 2)
        
        if self.recording_active and int(time.time() * 2) % 2 == 0:
            cv2.circle(draw_frame, (25, 25), 6, (0, 0, 255), -1)
            cv2.putText(draw_frame, "REC", (38, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            
        fps_text = f"SIGNAL: 100% | FPS: {int(self.current_fps)}"
        cv2.putText(draw_frame, fps_text, (fw - 150, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 245, 0), 1, cv2.LINE_AA)
        
        rgb_img = cv2.cvtColor(draw_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(400, 300))
        self.video_label.configure(image=ctk_img, text="")
        self.video_label.image = ctk_img

    def show_calibration_overlay(self, step: int, progress: float, instructions: str) -> None:
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        if step > 0 and step < 4:
            self.calib_overlay.place(relx=0.5, rely=0.85, anchor="center", relwidth=0.85)
            self.calib_instruction.configure(text=f"Calibration Step {step}: {instructions}", text_color=colors["accent"])
            self.calib_progress.configure(progress_color=colors["accent"])
            self.calib_progress.set(progress)
        elif step == 4:
            self.calib_instruction.configure(text=instructions, text_color=colors["accent"])
            self.calib_progress.set(1.0)
            self.calib_overlay.place(relx=0.5, rely=0.85, anchor="center", relwidth=0.85)
        else:
            self.calib_overlay.place_forget()

    def set_recording_state(self, active: bool) -> None:
        self.recording_active = active
        if active:
            self.record_btn.configure(text="● RECORDING", fg_color="#C0392B", hover_color="#962D22")
            self.add_log_message("SYSTEM: Video recording started.")
        else:
            self.record_btn.configure(text="⏺ RECORD SESSION", fg_color="#121216", hover_color="#C0392B")
            self.add_log_message("SYSTEM: Video recording stopped and saved.")

    def add_log_message(self, message: str) -> None:
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
        game = self.game_widget
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        if game.game_over:
            game.reset_game()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color=colors["accent"], hover_color=colors["accent"], text_color="#FFFFFF")
            self.add_log_message("GAME: Retro Racing Game Restarted.")
            return

        if not game.game_started:
            game.start_game()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color=colors["accent"], hover_color=colors["accent"], text_color="#FFFFFF")
            self.add_log_message("GAME: Retro Racing Game Started.")
        elif game.game_running:
            game.stop_game()
            self.game_btn.configure(text="▶ RESUME GAME", fg_color="#00FF66", hover_color="#00CC52", text_color="#0A0A0F")
            self.add_log_message("GAME: Retro Racing Game Paused.")
        else:
            game.game_running = True
            game.game_loop()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color=colors["accent"], hover_color=colors["accent"], text_color="#FFFFFF")
            self.add_log_message("GAME: Retro Racing Game Resumed.")
        
        if self.on_game is not None:
            try: self.on_game()
            except: pass
        
    def reset_view(self) -> None:
        self.video_label.configure(image="", text="CAMERA INACTIVE\n\nClick 'START SYSTEM' in Settings or calibration wizard to begin.")
        self.video_label.image = None
        self.hud_widgets["GESTURE"].configure(text="Neutral")
        self.hud_widgets["ACCELERATOR"].configure(text="OFF")
        self.hud_widgets["BRAKE"].configure(text="OFF")
        self.stop_session_timer()
        self.steering_history = [0.0] * 60
        self._draw_graph()
        self._draw_vector_wheel(0.0)
        
        self.game_widget.stop_game()
        self.game_widget.game_started = False
        self.game_widget._draw_splash()
        self.game_btn.configure(text="🎮 START GAME", fg_color="#121216", hover_color="#3498DB")

    def set_system_state(self, running: bool) -> None:
        """Toggles enabling states of the start/stop/calibrate buttons directly on the driving dashboard."""
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.calib_btn.configure(state="disabled")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.calib_btn.configure(state="normal")

    def on_hamburger_click(self) -> None:
        """Invokes master window to collapse/expand sidebar."""
        try:
            self.winfo_toplevel().toggle_sidebar()
        except Exception as e:
            logger.error(f"Failed to toggle sidebar: {e}")

    def update_top_clock(self) -> None:
        """Triggers periodic digital clock update on the Top HUD bar."""
        if hasattr(self, "top_time_lbl") and self.top_time_lbl.winfo_exists():
            self.top_time_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
            self.after(1000, self.update_top_clock)

    def resume_game(self) -> None:
        """Starts or resumes retro racing loop."""
        game = self.game_widget
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        if game.game_over:
            game.reset_game()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color=colors["accent"], hover_color=colors["accent"], text_color="#FFFFFF")
            self.add_log_message("GAME: Restarted.")
            return
            
        if not game.game_started:
            game.start_game()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color=colors["accent"], hover_color=colors["accent"], text_color="#FFFFFF")
            self.add_log_message("GAME: Started.")
        elif not game.game_running:
            game.game_running = True
            game.game_loop()
            self.game_btn.configure(text="⏸ PAUSE GAME", fg_color=colors["accent"], hover_color=colors["accent"], text_color="#FFFFFF")
            self.add_log_message("GAME: Resumed.")

    def pause_game(self) -> None:
        """Pauses retro racing loop."""
        game = self.game_widget
        if game.game_started and game.game_running:
            game.stop_game()
            self.game_btn.configure(text="▶ RESUME GAME", fg_color="#00FF66", hover_color="#00CC52", text_color="#0A0A0F")
            self.add_log_message("GAME: Paused.")

    def toggle_immersive_mode(self) -> None:
        """Toggles Driving Immersive Focus Mode (Hides sidebars, buttons, panels)."""
        app = self.winfo_toplevel()
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        if not getattr(self, "immersive_active", False):
            # Enter Immersive Mode!
            self.immersive_active = True
            
            # 1. Hide global sidebar
            try: app.sidebar_frame.pack_forget()
            except: pass
            
            # 2. Hide Drive Top Bar & Controls Dock
            self.top_bar.pack_forget()
            self.bottom_dock.pack_forget()
            
            # 3. Add keyboard escape listener
            app.bind("<Escape>", self._on_exit_immersive)
            self.add_log_message("SYSTEM: Focus Mode Active. Press ESC to exit.")
        else:
            # Exit Immersive Mode!
            self.immersive_active = False
            
            # 1. Restore global sidebar (keep collapsed for Drive page)
            try:
                app.sidebar_frame.pack(side="left", fill="y", padx=(10, 0), pady=10)
                app.set_sidebar_state(True)
            except: pass
            
            # 2. Restore Top Bar & Controls Dock
            self.top_bar.pack(side="top", fill="x", pady=(0, 10))
            self.middle_row.pack_forget()
            self.middle_row.pack(side="top", fill="both", expand=True)
            
            self.bottom_dock.pack(side="top", fill="x", pady=5)
            self.telemetry_dock.pack_forget()
            self.telemetry_dock.pack(side="top", fill="x", pady=(5, 0))
            
            # 3. Unbind escape
            app.unbind("<Escape>")
            self.add_log_message("SYSTEM: Focus Mode Deactivated.")

    def _on_exit_immersive(self, event: Any = None) -> None:
        if getattr(self, "immersive_active", False):
            self.toggle_immersive_mode()
