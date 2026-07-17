import customtkinter as ctk
from typing import Callable, Dict, Any, List, Optional
from utils.logger import logger
from vision.camera import Camera

class SettingsPanel(ctk.CTkFrame):
    """Sidebar Settings panel for VisionDrive AI."""
    def __init__(
        self,
        parent: Any,
        config_manager: Any,
        on_save_callback: Callable[[Dict[str, Any]], None],
        on_start_callback: Callable[[], None],
        on_stop_callback: Callable[[], None],
        on_calibrate_callback: Callable[[], None],
        on_weather_change_callback: Optional[Callable[[str], None]] = None
    ):
        super().__init__(parent, corner_radius=15, fg_color="#0a0a0f", border_width=1, border_color="#FF007F")
        self.config_manager = config_manager
        self.on_save_callback = on_save_callback
        self.on_start_callback = on_start_callback
        self.on_stop_callback = on_stop_callback
        self.on_calibrate_callback = on_calibrate_callback
        self.on_weather_change_callback = on_weather_change_callback
        
        self.setup_ui()

    def setup_ui(self) -> None:
        # Title
        title = ctk.CTkLabel(
            self, text="CONTROL PANEL", 
            font=ctk.CTkFont(family="Outfit", size=20, weight="bold"),
            text_color="#FF007F"
        )
        title.pack(pady=(20, 15), padx=20, anchor="w")

        # Scrollable container for settings
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", width=260, height=450)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # --- CAMERA SELECTOR ---
        cam_label = ctk.CTkLabel(scroll_frame, text="Active Camera Source:", font=ctk.CTkFont(size=12, weight="bold"))
        cam_label.pack(anchor="w", pady=(10, 2), padx=10)
        
        # Scan cameras
        available_cams = Camera.get_available_cameras()
        cam_options = [f"Camera {i}" for i in available_cams]
        if not cam_options:
            cam_options = ["Camera 0 (Default)"]
            
        current_cam_idx = self.config_manager.get("camera_id", 0)
        default_cam = f"Camera {current_cam_idx}"
        if default_cam not in cam_options:
            default_cam = cam_options[0]

        self.cam_dropdown = ctk.CTkOptionMenu(
            scroll_frame, values=cam_options,
            button_color="#FF007F", button_hover_color="#CC0066",
            dropdown_fg_color="#1E1E24", dropdown_hover_color="#2D2D35",
            cursor="hand2"
        )
        self.cam_dropdown.set(default_cam)
        self.cam_dropdown.pack(fill="x", padx=10, pady=(0, 10))

        # --- SENSITIVITY SLIDER ---
        self.sens_label = ctk.CTkLabel(scroll_frame, text="Steering Sensitivity: 1.0", font=ctk.CTkFont(size=12))
        self.sens_label.pack(anchor="w", padx=10)
        self.sens_slider = ctk.CTkSlider(
            scroll_frame, from_=0.5, to=3.0, number_of_steps=25,
            command=self._on_sens_change, progress_color="#FF007F", button_color="#FF007F", button_hover_color="#CC0066",
            cursor="hand2"
        )
        self.sens_slider.set(self.config_manager.get("steering_sensitivity", 1.0))
        self.sens_slider.pack(fill="x", padx=10, pady=(0, 10))

        # --- DEAD ZONE SLIDER ---
        self.dead_label = ctk.CTkLabel(scroll_frame, text="Dead Zone: 5.0 deg", font=ctk.CTkFont(size=12))
        self.dead_label.pack(anchor="w", padx=10)
        self.dead_slider = ctk.CTkSlider(
            scroll_frame, from_=0.0, to=20.0, number_of_steps=20,
            command=self._on_dead_change, progress_color="#FF007F", button_color="#FF007F", button_hover_color="#CC0066",
            cursor="hand2"
        )
        self.dead_slider.set(self.config_manager.get("steering_dead_zone", 5.0))
        self.dead_slider.pack(fill="x", padx=10, pady=(0, 10))

        # --- GESTURE CONFIDENCE SLIDER ---
        self.conf_label = ctk.CTkLabel(scroll_frame, text="Gesture Confidence: 70%", font=ctk.CTkFont(size=12))
        self.conf_label.pack(anchor="w", padx=10)
        self.conf_slider = ctk.CTkSlider(
            scroll_frame, from_=0.4, to=0.95, number_of_steps=11,
            command=self._on_conf_change, progress_color="#FF007F", button_color="#FF007F", button_hover_color="#CC0066",
            cursor="hand2"
        )
        self.conf_slider.set(self.config_manager.get("min_detection_confidence", 0.7))
        self.conf_slider.pack(fill="x", padx=10, pady=(0, 10))

        # --- SMOOTHING WINDOW SLIDER ---
        self.smooth_label = ctk.CTkLabel(scroll_frame, text="Smoothing Window: 5 frames", font=ctk.CTkFont(size=12))
        self.smooth_label.pack(anchor="w", padx=10)
        self.smooth_slider = ctk.CTkSlider(
            scroll_frame, from_=1.0, to=15.0, number_of_steps=14,
            command=self._on_smooth_change, progress_color="#FF007F", button_color="#FF007F", button_hover_color="#CC0066",
            cursor="hand2"
        )
        self.smooth_slider.set(self.config_manager.get("smoothing_amount", 5))
        self.smooth_slider.pack(fill="x", padx=10, pady=(0, 10))

        # --- FPS LIMIT SLIDER ---
        self.fps_label = ctk.CTkLabel(scroll_frame, text="Max FPS Limit: 30", font=ctk.CTkFont(size=12))
        self.fps_label.pack(anchor="w", padx=10)
        self.fps_slider = ctk.CTkSlider(
            scroll_frame, from_=15.0, to=60.0, number_of_steps=9,
            command=self._on_fps_change, progress_color="#FF007F", button_color="#FF007F", button_hover_color="#CC0066",
            cursor="hand2"
        )
        self.fps_slider.set(self.config_manager.get("fps_limit", 30))
        self.fps_slider.pack(fill="x", padx=10, pady=(0, 15))

        # --- WEATHER THEME SELECTOR ---
        weather_label = ctk.CTkLabel(scroll_frame, text="Ambient Weather Mode:", font=ctk.CTkFont(size=12, weight="bold"))
        weather_label.pack(anchor="w", pady=(5, 2), padx=10)
        
        weather_options = ["morning", "sunny", "evening", "night", "rain", "storm", "fog", "snow"]
        self.weather_dropdown = ctk.CTkOptionMenu(
            scroll_frame, values=weather_options,
            button_color="#FF007F", button_hover_color="#CC0066",
            dropdown_fg_color="#1E1E24", dropdown_hover_color="#2D2D35",
            command=self._on_weather_change,
            cursor="hand2"
        )
        self.weather_dropdown.set("night")
        self.weather_dropdown.pack(fill="x", padx=10, pady=(0, 15))

        # --- KEY BINDINGS ---
        kb_title = ctk.CTkLabel(scroll_frame, text="Key Bindings", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FF4B4B")
        kb_title.pack(anchor="w", padx=10, pady=(5, 5))

        # Accelerate Key
        self.accel_key_dropdown = self._create_key_dropdown(scroll_frame, "Accelerate", "accelerate")
        # Brake Key
        self.brake_key_dropdown = self._create_key_dropdown(scroll_frame, "Brake/Reverse", "brake")
        # Left Key
        self.left_key_dropdown = self._create_key_dropdown(scroll_frame, "Steer Left", "left")
        # Right Key
        self.right_key_dropdown = self._create_key_dropdown(scroll_frame, "Steer Right", "right")
        # Handbrake Key
        self.handbrake_key_dropdown = self._create_key_dropdown(scroll_frame, "Handbrake", "handbrake")
        # Boost Key
        self.boost_key_dropdown = self._create_key_dropdown(scroll_frame, "Nitro Boost", "boost")

        # Initial label update triggers
        self._on_sens_change(self.sens_slider.get())
        self._on_dead_change(self.dead_slider.get())
        self._on_conf_change(self.conf_slider.get())
        self._on_smooth_change(self.smooth_slider.get())
        self._on_fps_change(self.fps_slider.get())

        # --- CONTROL BUTTONS SECTION ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", padx=15, pady=20)

        # Start and Stop
        self.start_btn = ctk.CTkButton(
            btn_frame, text="START SYSTEM", fg_color="#00FF66", hover_color="#00CC52", text_color="#0A0A0F",
            font=ctk.CTkFont(weight="bold"), command=self.on_start_callback, cursor="hand2"
        )
        self.start_btn.pack(fill="x", pady=4)

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="STOP SYSTEM", fg_color="#FF007F", hover_color="#CC0066",
            font=ctk.CTkFont(weight="bold"), state="disabled", command=self.on_stop_callback, cursor="hand2"
        )
        self.stop_btn.pack(fill="x", pady=4)

        # Calibration
        self.calib_btn = ctk.CTkButton(
            btn_frame, text="RUN CALIBRATION", fg_color="#00F5FF", hover_color="#00C4CC", text_color="#0A0A0F",
            font=ctk.CTkFont(weight="bold"), command=self.on_calibrate_callback, cursor="hand2"
        )
        self.calib_btn.pack(fill="x", pady=4)

        # Save Button
        self.save_btn = ctk.CTkButton(
            btn_frame, text="SAVE SETTINGS", fg_color="#F39C12", hover_color="#D35400",
            font=ctk.CTkFont(weight="bold"), command=self.save_settings, cursor="hand2"
        )
        self.save_btn.pack(fill="x", pady=(4, 0))

    def _create_key_dropdown(self, parent: Any, label_text: str, config_key: str) -> ctk.CTkOptionMenu:
        """Helper to create a small key binding dropdown."""
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", padx=10, pady=2)
        
        lbl = ctk.CTkLabel(row_frame, text=label_text, font=ctk.CTkFont(size=11), width=100, anchor="w")
        lbl.pack(side="left")
        
        # Standard key options
        keys_list = ["up", "down", "left", "right", "space", "w", "s", "a", "d", "shift", "ctrl"]
        default_val = "shift" if config_key == "boost" else "space"
        current_binding = self.config_manager.get("key_bindings", {}).get(config_key, default_val)
        if current_binding not in keys_list:
            keys_list.append(current_binding)
            
        dropdown = ctk.CTkOptionMenu(
            row_frame, values=keys_list, width=120, height=22,
            fg_color="#2A2A30", button_color="#FF007F", button_hover_color="#CC0066",
            cursor="hand2"
        )
        dropdown.set(current_binding)
        dropdown.pack(side="right")
        return dropdown

    # Slider Value Change Listeners
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
        """Toggles active state of control buttons."""
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.calib_btn.configure(state="disabled")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.calib_btn.configure(state="normal")

    def save_settings(self) -> None:
        """Retrieves values from UI widgets and triggers save callback."""
        # Extract Camera ID from string (e.g. "Camera 1" -> 1)
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
