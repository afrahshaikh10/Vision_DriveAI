import customtkinter as ctk
from typing import Callable, Dict, Any, List, Optional
from utils.logger import logger
from vision.camera import Camera
from utils.theme_manager import get_theme_colors

class SettingsScreen(ctk.CTkFrame):
    """Full-screen Settings page wrapping webcam setups, key bindings and calibration controls."""
    def __init__(
        self,
        parent: Any,
        user_data: Dict[str, Any],
        config_manager: Any,
        on_save_callback: Callable[[Dict[str, Any]], None],
        on_start_callback: Callable[[], None],
        on_stop_callback: Callable[[], None],
        on_calibrate_callback: Callable[[], None],
        on_weather_change_callback: Optional[Callable[[str], None]] = None
    ):
        super().__init__(parent, fg_color="transparent")
        self.user_data = user_data
        self.config_manager = config_manager
        self.on_save_callback = on_save_callback
        self.on_start_callback = on_start_callback
        self.on_stop_callback = on_stop_callback
        self.on_calibrate_callback = on_calibrate_callback
        self.on_weather_change_callback = on_weather_change_callback
        
        self.setup_ui()

    def setup_ui(self) -> None:
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        # Header Title
        header = ctk.CTkLabel(
            self,
            text="⚙️ SYSTEM CONFIGURATION SETTINGS",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        desc = ctk.CTkLabel(
            self,
            text="Adjust camera sources, steering response formulas, gesture bounds, and key maps.",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        # Split layout: Left column for slider configs, Right column for bindings & control buttons
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=1)
        split.grid_rowconfigure(0, weight=1)
        
        left_col = ctk.CTkScrollableFrame(split, fg_color="#0a0a0f", border_width=1, border_color="#1b1836", corner_radius=12)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        right_col = ctk.CTkScrollableFrame(split, fg_color="#0a0a0f", border_width=1, border_color="#1b1836", corner_radius=12)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # --- LEFT COLUMN: TELEMETRY & CV PARAMS ---
        # 1. Camera Selector
        cam_label = ctk.CTkLabel(left_col, text="ACTIVE CAMERA SOURCE:", font=ctk.CTkFont(family="Outfit", size=12, weight="bold"), text_color=colors["secondary"])
        cam_label.pack(anchor="w", pady=(15, 2), padx=15)
        
        available_cams = Camera.get_available_cameras()
        cam_options = [f"Camera {i}" for i in available_cams]
        if not cam_options:
            cam_options = ["Camera 0 (Default)"]
            
        current_cam_idx = self.config_manager.get("camera_id", 0)
        default_cam = f"Camera {current_cam_idx}"
        if default_cam not in cam_options:
            default_cam = cam_options[0]

        self.cam_dropdown = ctk.CTkOptionMenu(
            left_col, values=cam_options,
            button_color=colors["accent"], button_hover_color=colors["secondary"],
            fg_color="#12121e", dropdown_fg_color="#1E1E24", dropdown_hover_color="#2D2D35",
            cursor="hand2"
        )
        self.cam_dropdown.set(default_cam)
        self.cam_dropdown.pack(fill="x", padx=15, pady=(0, 15))

        # 2. Sliders
        self.sens_label = ctk.CTkLabel(left_col, text="Steering Sensitivity: 1.0", font=ctk.CTkFont(size=11), text_color="#FFFFFF")
        self.sens_label.pack(anchor="w", padx=15)
        self.sens_slider = ctk.CTkSlider(
            left_col, from_=0.5, to=3.0, number_of_steps=25,
            command=self._on_sens_change, progress_color=colors["accent"], button_color=colors["accent"], button_hover_color=colors["secondary"],
            cursor="hand2"
        )
        self.sens_slider.set(self.config_manager.get("steering_sensitivity", 1.0))
        self.sens_slider.pack(fill="x", padx=15, pady=(0, 15))

        self.dead_label = ctk.CTkLabel(left_col, text="Dead Zone: 5.0 deg", font=ctk.CTkFont(size=11), text_color="#FFFFFF")
        self.dead_label.pack(anchor="w", padx=15)
        self.dead_slider = ctk.CTkSlider(
            left_col, from_=0.0, to=20.0, number_of_steps=20,
            command=self._on_dead_change, progress_color=colors["accent"], button_color=colors["accent"], button_hover_color=colors["secondary"],
            cursor="hand2"
        )
        self.dead_slider.set(self.config_manager.get("steering_dead_zone", 5.0))
        self.dead_slider.pack(fill="x", padx=15, pady=(0, 15))

        self.conf_label = ctk.CTkLabel(left_col, text="Gesture Confidence: 70%", font=ctk.CTkFont(size=11), text_color="#FFFFFF")
        self.conf_label.pack(anchor="w", padx=15)
        self.conf_slider = ctk.CTkSlider(
            left_col, from_=0.4, to=0.95, number_of_steps=11,
            command=self._on_conf_change, progress_color=colors["accent"], button_color=colors["accent"], button_hover_color=colors["secondary"],
            cursor="hand2"
        )
        self.conf_slider.set(self.config_manager.get("min_detection_confidence", 0.7))
        self.conf_slider.pack(fill="x", padx=15, pady=(0, 15))

        self.smooth_label = ctk.CTkLabel(left_col, text="Smoothing Window: 5 frames", font=ctk.CTkFont(size=11), text_color="#FFFFFF")
        self.smooth_label.pack(anchor="w", padx=15)
        self.smooth_slider = ctk.CTkSlider(
            left_col, from_=1.0, to=15.0, number_of_steps=14,
            command=self._on_smooth_change, progress_color=colors["accent"], button_color=colors["accent"], button_hover_color=colors["secondary"],
            cursor="hand2"
        )
        self.smooth_slider.set(self.config_manager.get("smoothing_amount", 5))
        self.smooth_slider.pack(fill="x", padx=15, pady=(0, 15))

        self.fps_label = ctk.CTkLabel(left_col, text="Max FPS Limit: 30", font=ctk.CTkFont(size=11), text_color="#FFFFFF")
        self.fps_label.pack(anchor="w", padx=15)
        self.fps_slider = ctk.CTkSlider(
            left_col, from_=15.0, to=60.0, number_of_steps=9,
            command=self._on_fps_change, progress_color=colors["accent"], button_color=colors["accent"], button_hover_color=colors["secondary"],
            cursor="hand2"
        )
        self.fps_slider.set(self.config_manager.get("fps_limit", 30))
        self.fps_slider.pack(fill="x", padx=15, pady=(0, 15))

        # --- RIGHT COLUMN: BINDINGS & ACTIONS ---
        # 1. Weather dropdown
        weather_label = ctk.CTkLabel(right_col, text="AMBIENT WEATHER OVERRIDE:", font=ctk.CTkFont(family="Outfit", size=12, weight="bold"), text_color=colors["secondary"])
        weather_label.pack(anchor="w", pady=(15, 2), padx=15)
        
        # Get unlocked weather list from database
        from utils.db import db
        fresh_user = db.get_user_by_id(self.user_data["id"])
        if fresh_user:
            self.user_data = fresh_user
            
        unlocked_weather_str = self.user_data.get("unlocked_weather", "morning,sunny,evening")
        unlocked_weathers = [w.strip() for w in unlocked_weather_str.split(",") if w.strip()]
        
        weather_options = ["morning", "sunny", "evening", "night", "rain", "storm", "fog", "snow"]
        weather_options = [w for w in weather_options if w in unlocked_weathers]
        if not weather_options:
            weather_options = ["morning", "sunny", "evening"]
            
        self.weather_dropdown = ctk.CTkOptionMenu(
            right_col, values=weather_options,
            button_color=colors["accent"], button_hover_color=colors["secondary"],
            fg_color="#12121e", dropdown_fg_color="#1E1E24", dropdown_hover_color="#2D2D35",
            command=self._on_weather_change,
            cursor="hand2"
        )
        # Default dropdown selection to the first available unlocked option
        default_weather = weather_options[0] if "sunny" not in weather_options else "sunny"
        self.weather_dropdown.set(default_weather)
        self.weather_dropdown.pack(fill="x", padx=15, pady=(0, 15))

        # 2. Key Bindings
        kb_title = ctk.CTkLabel(right_col, text="KEYBOARD MAP EMULATION:", font=ctk.CTkFont(family="Outfit", size=12, weight="bold"), text_color=colors["secondary"])
        kb_title.pack(anchor="w", padx=15, pady=(5, 5))

        self.accel_key_dropdown = self._create_key_dropdown(right_col, "Accelerate", "accelerate", colors)
        self.brake_key_dropdown = self._create_key_dropdown(right_col, "Brake/Reverse", "brake", colors)
        self.left_key_dropdown = self._create_key_dropdown(right_col, "Steer Left", "left", colors)
        self.right_key_dropdown = self._create_key_dropdown(right_col, "Steer Right", "right", colors)
        self.handbrake_key_dropdown = self._create_key_dropdown(right_col, "Handbrake", "handbrake", colors)
        self.boost_key_dropdown = self._create_key_dropdown(right_col, "Nitro Boost", "boost", colors)

        # 3. Action Buttons
        btn_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(20, 10))

        self.start_btn = ctk.CTkButton(
            btn_frame, text="START WEBCAM SYSTEM", fg_color="#00FF66", hover_color="#00CC52", text_color="#0A0A0F",
            font=ctk.CTkFont(weight="bold"), height=36, command=self.on_start_callback, cursor="hand2"
        )
        self.start_btn.pack(fill="x", pady=4)

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="STOP WEBCAM SYSTEM", fg_color="#FF007F", hover_color="#CC0066",
            font=ctk.CTkFont(weight="bold"), height=36, state="disabled", command=self.on_stop_callback, cursor="hand2"
        )
        self.stop_btn.pack(fill="x", pady=4)

        self.calib_btn = ctk.CTkButton(
            btn_frame, text="RUN CALIBRATION WIZARD", fg_color="#00F5FF", hover_color="#00C4CC", text_color="#0A0A0F",
            font=ctk.CTkFont(weight="bold"), height=36, command=self.on_calibrate_callback, cursor="hand2"
        )
        self.calib_btn.pack(fill="x", pady=4)

        self.save_btn = ctk.CTkButton(
            btn_frame, text="SAVE SETTINGS CONFIG", fg_color="#F39C12", hover_color="#D35400",
            font=ctk.CTkFont(weight="bold"), height=36, command=self.save_settings, cursor="hand2"
        )
        self.save_btn.pack(fill="x", pady=4)

        # Initial label triggers
        self._on_sens_change(self.sens_slider.get())
        self._on_dead_change(self.dead_slider.get())
        self._on_conf_change(self.conf_slider.get())
        self._on_smooth_change(self.smooth_slider.get())
        self._on_fps_change(self.fps_slider.get())

    def _create_key_dropdown(self, parent: Any, label_text: str, config_key: str, colors: dict) -> ctk.CTkOptionMenu:
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", padx=15, pady=3)
        
        lbl = ctk.CTkLabel(row_frame, text=label_text, font=ctk.CTkFont(size=11), width=100, anchor="w", text_color="#888888")
        lbl.pack(side="left")
        
        keys_list = ["up", "down", "left", "right", "space", "w", "s", "a", "d", "shift", "ctrl"]
        default_val = "shift" if config_key == "boost" else "space"
        current_binding = self.config_manager.get("key_bindings", {}).get(config_key, default_val)
        if current_binding not in keys_list:
            keys_list.append(current_binding)
            
        dropdown = ctk.CTkOptionMenu(
            row_frame, values=keys_list, width=120, height=24,
            fg_color="#12121e", button_color=colors["accent"], button_hover_color=colors["secondary"],
            cursor="hand2"
        )
        dropdown.set(current_binding)
        dropdown.pack(side="right")
        return dropdown

    def _on_sens_change(self, val: float) -> None:
        self.sens_label.configure(text=f"Steering Sensitivity: {val:.2f}")

    def _on_dead_change(self, val: float) -> None:
        self.dead_label.configure(text=f"Dead Zone: {val:.1f} deg")

    def _on_conf_change(self, val: float) -> None:
        self.conf_label.configure(text=f"Gesture Confidence: {int(val * 100)}%")

    def _on_smooth_change(self, val: float) -> None:
        self.smooth_label.configure(text=f"Smoothing Window: {int(val)} frames")

    def _on_fps_change(self, val: float) -> None:
        self.fps_label.configure(text=f"Max FPS Limit: {int(val)}")

    def _on_weather_change(self, val: str) -> None:
        from utils.weather import weather_manager
        weather_manager.set_weather(val)
        if self.on_weather_change_callback:
            self.on_weather_change_callback(val)

    def set_system_state(self, running: bool) -> None:
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.calib_btn.configure(state="disabled")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.calib_btn.configure(state="normal")

    def save_settings(self) -> None:
        cam_str = self.cam_dropdown.get()
        try:
            cam_id = int(cam_str.replace("Camera ", "").split()[0])
        except Exception:
            cam_id = 0
            
        updated_settings = {
            "camera_id": cam_id,
            "steering_sensitivity": round(self.sens_slider.get(), 2),
            "steering_dead_zone": round(self.dead_slider.get(), 1),
            "min_detection_confidence": round(self.conf_slider.get(), 2),
            "min_tracking_confidence": round(self.conf_slider.get(), 2),
            "smoothing_amount": int(self.smooth_slider.get()),
            "fps_limit": int(self.fps_slider.get()),
            "key_bindings": {
                "accelerate": self.accel_key_dropdown.get(),
                "brake": self.brake_key_dropdown.get(),
                "left": self.left_key_dropdown.get(),
                "right": self.right_key_dropdown.get(),
                "handbrake": self.handbrake_key_dropdown.get(),
                "boost": self.boost_key_dropdown.get()
            }
        }
        self.on_save_callback(updated_settings)
