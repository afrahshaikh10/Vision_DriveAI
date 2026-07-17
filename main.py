import os
import cv2
import time
import threading
import queue
import tkinter as tk
from datetime import datetime
import customtkinter as ctk
from PIL import Image
from typing import Optional, Dict, Any, List

# Custom Module Imports
from utils.logger import logger
from utils.config import ConfigManager
from utils.math_utils import calculate_distance
from utils.db import db
from utils.theme_manager import get_theme_colors
from vision.camera import Camera
from vision.hand_tracker import HandTracker
from vision.steering import SteeringController
from vision.gesture_detector import GestureDetector
from vision.calibration import CalibrationWizard
from controllers.keyboard_controller import KeyboardController

class ToolTip:
    def __init__(self, widget, text, app):
        self.widget = widget
        self.text = text
        self.app = app
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if not getattr(self.app, "sidebar_collapsed", False) or not self.text:
            return
        if self.tooltip_window:
            return
        
        x = self.widget.winfo_rootx() + 75
        y = self.widget.winfo_rooty() + 5
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        theme = self.app.logged_in_user.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        border_col = colors["border"]
        
        inner_frame = tk.Frame(tw, bg="#0f0f1b", highlightthickness=1, highlightbackground=border_col)
        inner_frame.pack()
        
        label = tk.Label(
            inner_frame, text=self.text, justify='left',
            background="#0f0f1b", foreground="#FFFFFF",
            font=("Outfit", 9, "bold"), padx=8, pady=4
        )
        label.pack()

    def hide_tooltip(self, event=None):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            try:
                tw.destroy()
            except Exception:
                pass

# Custom Pages
from pages.splash import SplashScreen
from pages.login import LoginScreen
from pages.dashboard import HomeDashboardScreen
from pages.drive import DriveScreen
from pages.challenges import ChallengesScreen
from pages.career import CareerScreen
from pages.achievements import AchievementsScreen
from pages.analytics import AnalyticsScreen
from pages.garage import GarageScreen
from pages.leaderboard import LeaderboardScreen
from pages.profile import ProfileScreen
from pages.settings import SettingsScreen

# Configure App Styling
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VisionDriveAIApp(ctk.CTk):
    """Main Application coordinating system workers, user profile progression and multi-page views."""
    def __init__(self):
        super().__init__()
        
        self.title("VisionDrive AI - Gesture Controlled Racing Simulator")
        self.geometry("1280x680")
        self.resizable(True, True)
        self.configure(fg_color="#080810")

        # Initialize configurations
        self.config_manager = ConfigManager()
        
        # Load directories
        self.screenshots_dir = "screenshots"
        self.recordings_dir = "recordings"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.recordings_dir, exist_ok=True)

        # CV Pipeline Components
        self.camera: Optional[Camera] = None
        self.hand_tracker = HandTracker(
            min_detection_confidence=self.config_manager.get("min_detection_confidence", 0.7),
            min_tracking_confidence=self.config_manager.get("min_tracking_confidence", 0.7)
        )
        self.steering_controller = SteeringController(
            dead_zone=self.config_manager.get("steering_dead_zone", 5.0),
            smoothing_amount=self.config_manager.get("smoothing_amount", 5),
            sensitivity=self.config_manager.get("steering_sensitivity", 1.0)
        )
        # Load saved calibration values into steering controller
        self.steering_controller.update_calibration(self.config_manager.get("calibration", {}))
        
        self.gesture_detector = GestureDetector(
            confidence_threshold=self.config_manager.get("min_detection_confidence", 0.7)
        )
        self.gesture_detector.update_settings(
            confidence_threshold=self.config_manager.get("min_detection_confidence", 0.7),
            neutral_distance=self.config_manager.get("calibration", {}).get("neutral_distance", 200.0)
        )
        
        self.calibration_wizard = CalibrationWizard()
        self.keyboard_controller = KeyboardController(
            key_bindings=self.config_manager.get("key_bindings", {})
        )

        # Threading States
        self.system_running = False
        self.log_queue = queue.Queue()
        self.vision_thread: Optional[threading.Thread] = None
        self.frame_lock = threading.Lock()
        self.sidebar_collapsed = False
        self.sidebar_width = 230
        
        # Latest frame and telemetry data passed to GUI
        self.latest_display_frame: Optional[cv2.Mat] = None
        self.latest_telemetry: Dict[str, Any] = {
            "steering_angle": 0.0,
            "steering_state": "Straight",
            "accelerating": False,
            "braking": False,
            "handbrake": False,
            "fps": 0.0,
            "gestures": []
        }

        # Video Recording
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording_active = False
        self.fullscreen_active = False

        # Session & Multi-User State
        self.logged_in_user: Optional[Dict[str, Any]] = None
        self.current_page_name: Optional[str] = None
        self.active_challenge: Optional[Dict[str, Any]] = None
        self.log_messages_history: List[str] = []

        # Background particles canvas (weather backing overlay)
        self.bg_canvas = ctk.CTkCanvas(self, bg="#030308", highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # Start with Splash Screen
        self.splash = SplashScreen(self, on_loaded_callback=self.show_login_screen)
        self.splash.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start GUI polling loop
        self.gui_update_loop()

    def show_login_screen(self) -> None:
        """Invoked once splash loading tasks complete."""
        if hasattr(self, "splash") and self.splash:
            try:
                self.splash.place_forget()
                self.splash.destroy()
            except Exception:
                pass
            self.splash = None
            
        self.login_screen = LoginScreen(self, on_login_success=self.show_main_app)
        self.login_screen.place(x=0, y=0, relwidth=1.0, relheight=1.0)

    def show_main_app(self, user_data: Dict[str, Any]) -> None:
        """Sets up the sidebar navigation framework post-authentication."""
        self.logged_in_user = user_data
        
        if hasattr(self, "login_screen") and self.login_screen:
            try:
                self.login_screen.place_forget()
                self.login_screen.destroy()
            except Exception:
                pass
            self.login_screen = None

        # Build Main Frame structure
        self.main_split = ctk.CTkFrame(self, fg_color="transparent")
        self.main_split.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        theme = self.logged_in_user.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)

        # Left Sidebar Navigation
        self.sidebar_frame = ctk.CTkFrame(self.main_split, fg_color="#0a0a0f", width=230, border_width=1, border_color=colors["border"])
        self.sidebar_frame.pack(side="left", fill="y", padx=(10, 0), pady=10)
        self.sidebar_frame.pack_propagate(False)

        # Sidebar Title
        self.logo = ctk.CTkLabel(
            self.sidebar_frame, text="VISIONDRIVE AI",
            font=ctk.CTkFont(family="Outfit", size=20, weight="bold"),
            text_color=colors["border"]
        )
        self.logo.pack(pady=(20, 10))

        # Status Pill
        self.status_pill = ctk.CTkLabel(
            self.sidebar_frame, text="● OFFLINE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#888888"
        )
        self.status_pill.pack(pady=(0, 15))

        # Mini Profile card in sidebar
        self.mini_profile = ctk.CTkFrame(self.sidebar_frame, fg_color="#12121e", height=65, corner_radius=10)
        self.mini_profile.pack(fill="x", padx=15, pady=(0, 15))
        self.mini_profile.pack_propagate(False)

        self.lbl_profile_name = ctk.CTkLabel(self.mini_profile, text=self.logged_in_user.get("name", "Player").upper(), font=ctk.CTkFont(family="Outfit", size=11, weight="bold"))
        self.lbl_profile_name.pack(anchor="w", padx=10, pady=(6, 1))

        self.lbl_profile_level = ctk.CTkLabel(self.mini_profile, text=f"LVL {self.logged_in_user.get('level', 1)} | 💰 {self.logged_in_user.get('coins', 0)}", font=ctk.CTkFont(size=9), text_color=colors["secondary"])
        self.lbl_profile_level.pack(anchor="w", padx=10, pady=(1, 6))

        # Scrollable sidebar buttons
        self.btn_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.btn_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.nav_buttons = {}
        self.nav_item_labels = {}
        nav_items = [
            ("dashboard", "🏠 DASHBOARD"),
            ("drive", "🎮 DRIVE MODE"),
            ("challenges", "🎯 CHALLENGES"),
            ("career", "📈 CAREER PATH"),
            ("achievements", "🏆 ACHIEVEMENTS"),
            ("analytics", "📊 ANALYTICS"),
            ("garage", "🏎️ THEME GARAGE"),
            ("leaderboard", "👑 LEADERBOARDS"),
            ("profile", "👤 MY PROFILE"),
            ("settings", "⚙️ SETTINGS"),
            ("logout", "🚪 LOGOUT")
        ]

        for p_name, label in nav_items:
            # Extract first char as icon, remaining as description text
            icon = label[0]
            text = label[2:]
            self.nav_item_labels[p_name] = (icon, text)
            
            btn = ctk.CTkButton(
                self.btn_scroll, text=label, anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="transparent", text_color="#888888", hover_color="#12121e",
                command=lambda p=p_name: self.switch_page(p),
                cursor="hand2"
            )
            btn.pack(fill="x", pady=2, ipady=4)
            self.nav_buttons[p_name] = btn
            
            # Attach custom tooltip
            ToolTip(btn, text, self)

        # Right Content Container
        self.content_container = ctk.CTkFrame(self.main_split, fg_color="transparent")
        self.content_container.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Default Page
        self.switch_page("dashboard")

    def toggle_sidebar(self) -> None:
        """Toggles sidebar collapse/expand state."""
        collapsed = not getattr(self, "sidebar_collapsed", False)
        self.set_sidebar_state(collapsed)

    def set_sidebar_state(self, collapsed: bool) -> None:
        """Sets the sidebar to collapsed or expanded, applying appropriate layouts and width changes."""
        if collapsed == getattr(self, "sidebar_collapsed", False):
            return
            
        self.sidebar_collapsed = collapsed
        theme = self.logged_in_user.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        if collapsed:
            # 1. Unpack header widgets to hide text
            self.logo.pack_forget()
            self.status_pill.pack_forget()
            self.mini_profile.pack_forget()
            
            # 2. Update navigation buttons to display icons only (centered)
            for p_name, btn in self.nav_buttons.items():
                icon, _ = self.nav_item_labels[p_name]
                btn.configure(text=icon, anchor="center")
                
            # 3. Animate width shrinking
            self.animate_sidebar(70)
        else:
            # 1. Restore navigation buttons text
            for p_name, btn in self.nav_buttons.items():
                icon, text = self.nav_item_labels[p_name]
                btn.configure(text=f"{icon} {text}", anchor="w")
                
            # 2. Repack header widgets in the correct order
            self.logo.pack(pady=(20, 10))
            self.status_pill.pack(pady=(0, 15))
            self.mini_profile.pack(fill="x", padx=15, pady=(0, 15))
            self.btn_scroll.pack_forget()
            self.btn_scroll.pack(fill="both", expand=True, padx=5, pady=5)
            
            # 3. Animate width expanding
            self.animate_sidebar(230)

    def animate_sidebar(self, target_width: int) -> None:
        """Smoothly resizes sidebar width via increments/decrements (approx 250ms total)."""
        if not hasattr(self, "sidebar_frame") or not self.sidebar_frame:
            return
            
        current_width = getattr(self, "sidebar_width", 230)
        if current_width == target_width:
            return
            
        step = 15
        diff = target_width - current_width
        if abs(diff) <= step:
            new_width = target_width
        else:
            new_width = current_width + (step if diff > 0 else -step)
            
        self.sidebar_width = new_width
        self.sidebar_frame.configure(width=new_width)
        if hasattr(self, "btn_scroll") and self.btn_scroll:
            self.btn_scroll.configure(width=max(40, new_width - 15))
        
        if new_width != target_width:
            self.after(15, lambda: self.animate_sidebar(target_width))

    def switch_page(self, page_name: str) -> None:
        """Destroys current page view and instantiates the selected dashboard module."""
        if page_name == "logout":
            self.logout()
            return

        # Clean up existing page
        if hasattr(self, "current_page_widget") and self.current_page_widget:
            # If leaving Drive Mode, safely stop cameras/recordings
            if self.current_page_name == "drive":
                self.stop_system()
            self.current_page_widget.pack_forget()
            self.current_page_widget.destroy()

        self.current_page_name = page_name
        
        # Handle automatic sidebar collapse for Drive Mode
        self.set_sidebar_state(page_name == "drive")
        
        theme = self.logged_in_user.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)

        # Update mini profile levels/coins on screen
        fresh_user = db.get_user_by_id(self.logged_in_user["id"])
        if fresh_user:
            self.logged_in_user = fresh_user
            self.lbl_profile_level.configure(text=f"LVL {fresh_user['level']} | 💰 {fresh_user['coins']}")

        # Highlight sidebar buttons
        for name, btn in self.nav_buttons.items():
            if name == page_name:
                btn.configure(fg_color=colors["accent"], hover_color=colors["secondary"], text_color="#080810" if theme != "minimal" else "#000000")
            else:
                btn.configure(fg_color="transparent", hover_color="#12121e", text_color="#888888")

        # Instantiate new widget page inside container
        if page_name == "dashboard":
            self.current_page_widget = HomeDashboardScreen(self.content_container, self.logged_in_user, self.switch_page)
        elif page_name == "drive":
            self.current_page_widget = DriveScreen(
                self.content_container, self.logged_in_user,
                on_screenshot_callback=self.take_screenshot,
                on_record_toggle_callback=self.toggle_recording,
                on_fullscreen_callback=self.toggle_fullscreen,
                on_game_callback=None,
                on_start_callback=self.start_system,
                on_stop_callback=self.stop_system,
                on_calibrate_callback=self.start_calibration
            )
            # Synchronize webcam start/stop button states immediately
            self.current_page_widget.set_system_state(self.system_running)
            
            # Propagate active challenge if loaded
            if self.active_challenge:
                self.current_page_widget.game_widget.active_challenge = self.active_challenge
                self.current_page_widget.game_widget.user_data = self.logged_in_user
                self.current_page_widget.game_widget.current_weather = self.active_challenge["weather"]
                # Clear active challenge reference so it only runs once
                self.active_challenge = None
            else:
                self.current_page_widget.game_widget.user_data = self.logged_in_user
        elif page_name == "challenges":
            self.current_page_widget = ChallengesScreen(self.content_container, self.logged_in_user, self.launch_challenge)
        elif page_name == "career":
            self.current_page_widget = CareerScreen(self.content_container, self.logged_in_user)
        elif page_name == "achievements":
            self.current_page_widget = AchievementsScreen(self.content_container, self.logged_in_user)
        elif page_name == "analytics":
            self.current_page_widget = AnalyticsScreen(self.content_container, self.logged_in_user)
        elif page_name == "garage":
            self.current_page_widget = GarageScreen(self.content_container, self.logged_in_user, self.on_theme_changed)
        elif page_name == "leaderboard":
            self.current_page_widget = LeaderboardScreen(self.content_container, self.logged_in_user)
        elif page_name == "profile":
            self.current_page_widget = ProfileScreen(self.content_container, self.logged_in_user)
        elif page_name == "settings":
            self.current_page_widget = SettingsScreen(
                self.content_container, self.logged_in_user, self.config_manager,
                on_save_callback=self.save_settings,
                on_start_callback=self.start_system,
                on_stop_callback=self.stop_system,
                on_calibrate_callback=self.start_calibration,
                on_weather_change_callback=self.change_weather_theme
            )
            self.current_page_widget.set_system_state(self.system_running)

        self.current_page_widget.pack(fill="both", expand=True)
        self.update_idletasks()
        logger.info(f"DEBUG switch_page: current_page={page_name}")
        logger.info(f"DEBUG: main_split size={self.main_split.winfo_width()}x{self.main_split.winfo_height()}")
        logger.info(f"DEBUG: sidebar size={self.sidebar_frame.winfo_width()}x{self.sidebar_frame.winfo_height()}")
        logger.info(f"DEBUG: content_container size={self.content_container.winfo_width()}x{self.content_container.winfo_height()}")
        logger.info(f"DEBUG: current_page_widget size={self.current_page_widget.winfo_width()}x{self.current_page_widget.winfo_height()}")

    def launch_challenge(self, challenge: Dict[str, Any]) -> None:
        """Triggered from challenges selector page. Preserves challenge dict targets."""
        self.active_challenge = challenge
        self.switch_page("drive")
        # Automatically trigger webcam start
        self.start_system()
        # Automatically trigger game loop
        self.after(500, self.current_page_widget.toggle_game_state)
        self.add_log_message(f"CHALLENGE LOADED: {challenge['name']} (Score Target: {challenge['target_score']})")

    def on_theme_changed(self, theme_name: str) -> None:
        """Instantly repaints borders and font highlights matching newly equipped items."""
        colors = get_theme_colors(theme_name)
        self.logo.configure(text_color=colors["border"])
        self.sidebar_frame.configure(border_color=colors["border"])
        self.status_pill.configure(text_color=colors["secondary"])
        self.lbl_profile_level.configure(text_color=colors["secondary"])
        
        # Repaint nav buttons highlights
        for name, btn in self.nav_buttons.items():
            if name == self.current_page_name:
                btn.configure(fg_color=colors["accent"], hover_color=colors["secondary"], text_color="#080810" if theme_name != "minimal" else "#000000")
            else:
                btn.configure(fg_color="transparent", hover_color="#12121e", text_color="#888888")

    def logout(self) -> None:
        """Re-initializes context and drops navigation splits."""
        self.stop_system()
        self.logged_in_user = None
        self.current_page_name = None
        
        if hasattr(self, "main_split") and self.main_split:
            try:
                self.main_split.place_forget()
                self.main_split.destroy()
            except Exception:
                pass
            self.main_split = None
        
        self.show_login_screen()

    def start_system(self) -> None:
        if self.system_running:
            return
            
        cam_id = self.config_manager.get("camera_id", 0)
        self.camera = Camera(camera_id=cam_id)
        
        logger.info(f"Starting camera source {cam_id}...")
        if not self.camera.start():
            ctk.CTkMessagebox(
                title="Camera Error",
                message=f"Could not open Camera Index {cam_id}.\nPlease verify connections and try again.",
                icon="warning"
            )
            return

        self.system_running = True
        self.camera_start_time = time.time()
        if hasattr(self, "warned_no_feed"):
            delattr(self, "warned_no_feed")
            
        self.status_pill.configure(text="● ONLINE", text_color="#2ECC71")
        if hasattr(self, "current_page_widget") and hasattr(self.current_page_widget, "set_system_state"):
            self.current_page_widget.set_system_state(True)
        if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
            self.current_page_widget.start_session_timer()

        # Update controller confidence values
        self.hand_tracker.set_confidences(
            self.config_manager.get("min_detection_confidence", 0.7),
            self.config_manager.get("min_tracking_confidence", 0.7)
        )
        
        self.vision_thread = threading.Thread(target=self.vision_worker_loop, name="VisionWorker", daemon=True)
        self.vision_thread.start()

    def stop_system(self) -> None:
        if not self.system_running:
            return
            
        logger.info("Stopping VisionDrive System...")
        self.system_running = False
        
        if self.vision_thread is not None:
            self.vision_thread.join(timeout=1.0)
            self.vision_thread = None

        if self.camera is not None:
            self.camera.stop()
            self.camera = None

        if self.recording_active:
            self.stop_recording()

        self.keyboard_controller.release_all()
        
        self.status_pill.configure(text="● OFFLINE", text_color="#888888")
        if hasattr(self, "current_page_widget") and hasattr(self.current_page_widget, "set_system_state"):
            self.current_page_widget.set_system_state(False)
        if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
            self.current_page_widget.reset_view()
            
        self.calibration_wizard.reset()
        logger.info("VisionDrive System Stopped.")

    def add_log_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] >>> {message}"
        self.log_messages_history.append(formatted)
        if len(self.log_messages_history) > 20:
            self.log_messages_history.pop(0)
            
        if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
            self.current_page_widget.add_log_message(message)

    def log_message(self, message: str) -> None:
        """Thread-safe queues logger called by CV pipeline."""
        self.log_queue.put(message)

    def save_settings(self, settings: Dict[str, Any]) -> None:
        self.config_manager.update_multiple(settings)
        self.steering_controller.update_settings(
            dead_zone=settings["steering_dead_zone"],
            smoothing_amount=settings["smoothing_amount"],
            sensitivity=settings["steering_sensitivity"]
        )
        self.gesture_detector.update_settings(
            confidence_threshold=settings["min_detection_confidence"],
            neutral_distance=self.config_manager.get("calibration", {}).get("neutral_distance", 200.0)
        )
        self.keyboard_controller.update_bindings(settings["key_bindings"])
        self.hand_tracker.set_confidences(
            settings["min_detection_confidence"],
            settings["min_detection_confidence"]
        )

        if self.system_running and self.camera and self.camera.camera_id != settings["camera_id"]:
            logger.info("Camera source index updated. Rebooting camera...")
            self.camera.change_camera(settings["camera_id"])
            self.camera_start_time = time.time()
            if hasattr(self, "warned_no_feed"):
                delattr(self, "warned_no_feed")
            
        self.add_log_message("SYSTEM: Settings updated successfully.")

    def start_calibration(self) -> None:
        if not self.system_running:
            self.start_system()
            if not self.system_running:
                return

        self.calibration_wizard.start()
        # Route to drive page to show overlay calibration UI
        self.switch_page("drive")
        self.add_log_message("SYSTEM: Calibration wizard loaded.")

    def take_screenshot(self) -> None:
        with self.frame_lock:
            frame = self.latest_display_frame.copy() if self.latest_display_frame is not None else None
            
        if frame is not None:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.screenshots_dir, f"screenshot_{now_str}.png")
            cv2.imwrite(filename, frame)
            self.add_log_message(f"SNAPSHOT: Saved to {filename}")
        else:
            self.add_log_message("SNAPSHOT: Error - Camera thread offline.")

    def toggle_recording(self) -> None:
        if not self.system_running:
            self.add_log_message("RECORD: System offline.")
            return

        if not self.recording_active:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.recordings_dir, f"recording_{now_str}.avi")
            w = self.camera.actual_width if self.camera else 640
            h = self.camera.actual_height if self.camera else 480
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.video_writer = cv2.VideoWriter(filename, fourcc, 15.0, (w, h))
            self.recording_active = True
            if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
                self.current_page_widget.set_recording_state(True)
        else:
            self.stop_recording()

    def stop_recording(self) -> None:
        self.recording_active = False
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
        if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
            self.current_page_widget.set_recording_state(False)

    def toggle_fullscreen(self) -> None:
        self.fullscreen_active = not self.fullscreen_active
        self.attributes("-fullscreen", self.fullscreen_active)
        self.add_log_message(f"SYSTEM: Fullscreen set to {self.fullscreen_active}.")

    def vision_worker_loop(self) -> None:
        while self.system_running:
            loop_start = time.time()
            if self.camera is None:
                time.sleep(0.01)
                continue
                
            frame = self.camera.get_frame()
            if frame is None:
                time.sleep(0.005)
                continue

            frame = cv2.flip(frame, 1)
            frame, hands_data = self.hand_tracker.process_frame(frame)
            frame_annotated = self.hand_tracker.draw_overlays(frame, hands_data)

            # 1. Calibration Wizard Handling
            calib_step = self.calibration_wizard.current_step
            if calib_step > 0:
                finished_step_sampling = self.calibration_wizard.record_frame(hands_data)
                samples_collected = len(self.calibration_wizard.step_samples)
                progress = min(1.0, samples_collected / 15.0)
                inst = self.calibration_wizard.get_instructions()
                
                if finished_step_sampling:
                    self.calibration_wizard.process_step()
                    next_step = self.calibration_wizard.current_step
                    
                    if next_step == 4:
                        results = self.calibration_wizard.get_results()
                        self.config_manager.set("calibration", results)
                        self.steering_controller.update_calibration(results)
                        self.gesture_detector.update_settings(
                            confidence_threshold=self.config_manager.get("min_detection_confidence", 0.7),
                            neutral_distance=results["neutral_distance"]
                        )
                        self.log_message("CALIBRATION: Saved successfully!")
                        time.sleep(1.0)
                        self.calibration_wizard.reset()
                    else:
                        self.log_message(f"CALIBRATION: Step {calib_step} complete.")
                
                self.keyboard_controller.release_all()
                with self.frame_lock:
                    self.latest_display_frame = frame_annotated
                    self.latest_telemetry = {
                        "steering_angle": 0.0,
                        "steering_state": "Calibrating",
                        "accelerating": False,
                        "braking": False,
                        "handbrake": False,
                        "fps": self.camera.fps if self.camera else 0.0,
                        "calibration_overlay": (calib_step, progress, inst)
                    }

            # 2. Gameplay Mode Handling
            else:
                raw_ang, smoothed_ang, steer_state = self.steering_controller.calculate_steering(hands_data)
                accel, brake, handbrake, boost, gest_info = self.gesture_detector.detect_gestures(hands_data)
                self.keyboard_controller.update_controls(accel, brake, handbrake, boost, steer_state)
                
                # Dynamic check if user is currently playing game
                if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
                    game = self.current_page_widget.game_widget
                    if game.game_started and not game.game_over:
                        from utils.analytics import analytics_tracker
                        analytics_tracker.log_tick(
                            steering_angle=smoothed_ang,
                            accel=accel,
                            brake=brake,
                            player_x=game.player_x
                        )
                        
                        from utils.coach import driving_coach
                        prev_angle = self.latest_telemetry.get("steering_angle", 0.0)
                        delta_angle = smoothed_ang - prev_angle
                        text, speech = driving_coach.evaluate_tick(
                            steering_angle=smoothed_ang,
                            delta_angle=delta_angle,
                            speed=game.speed_mph,
                            player_x=game.player_x
                        )
                        if text and speech:
                            game.trigger_coach_alert(text)
                            self.log_message(f"COACH: {text}")
                            driving_coach.speak(speech)
                
                for info in gest_info:
                    if "Fist" in info or "Palm" in info or "Close" in info or "Thumb" in info:
                         self.log_message(f"GESTURE: {info}")
                
                if steer_state != self.keyboard_controller.last_steering_state:
                    self.log_message(f"STEERING: {steer_state} ({int(smoothed_ang)}°)")
 
                conf_val = sum(h["score"] for h in hands_data) / len(hands_data) if hands_data else 0.0
                gest_name = "Neutral"
                if handbrake: gest_name = "ThumbsDown (HB)"
                elif boost: gest_name = "ThumbsUp (BST)"
                elif brake: gest_name = "Open Palm (BRK)"
                elif accel: gest_name = "Closed Fist (ACC)"
 
                with self.frame_lock:
                    self.latest_display_frame = frame_annotated
                    self.latest_telemetry = {
                        "steering_angle": smoothed_ang,
                        "steering_state": steer_state,
                        "accelerating": accel,
                        "braking": brake,
                        "handbrake": handbrake,
                        "boost": boost,
                        "fps": self.camera.fps if self.camera else 0.0,
                        "calibration_overlay": (0, 0.0, ""),
                        "gesture_name": gest_name,
                        "confidence": conf_val
                    }

            if self.recording_active and self.video_writer is not None:
                self.video_writer.write(frame_annotated)

            fps_limit = self.config_manager.get("fps_limit", 30)
            target_delay = 1.0 / fps_limit
            elapsed = time.time() - loop_start
            sleep_time = target_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def gui_update_loop(self) -> None:
        """GUI rendering and synchronization loop (30 FPS limit)."""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.add_log_message(msg)
            except Exception:
                break

        # Weather Manager tick updates
        from utils.weather import weather_manager
        speed_mph = 0.0
        if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
            speed_mph = self.current_page_widget.game_widget.speed_mph
            
        weather_manager.update(w=self.winfo_width(), h=self.winfo_height(), speed_mph=speed_mph)
        
        # Repaint dynamic weather backgrounds
        if hasattr(self, "bg_canvas") and self.bg_canvas is not None:
            self.bg_canvas.delete("all")
            c_start = weather_manager.get_color("bg_start")
            self.bg_canvas.create_rectangle(0, 0, self.winfo_width(), self.winfo_height(), fill=c_start, outline="")
            weather_manager.draw(self.bg_canvas, self.winfo_width(), self.winfo_height())

        # Update Drive Mode HUD layouts if showing
        if self.current_page_name == "drive" and hasattr(self, "current_page_widget") and self.current_page_widget:
            game = self.current_page_widget.game_widget
            if game.game_started and game.game_over:
                self.current_page_widget.game_btn.configure(text="🎮 RESTART GAME", fg_color="#00FF66", hover_color="#00CC52", text_color="#0A0A0F")
                
            if self.system_running:
                with self.frame_lock:
                    frame = self.latest_display_frame.copy() if self.latest_display_frame is not None else None
                    telemetry = self.latest_telemetry.copy()
                    
                if frame is not None:
                    self.status_pill.configure(text="● ONLINE", text_color="#2ECC71")
                    self.current_page_widget.update_video_feed(frame)
                    self.current_page_widget.update_telemetry(
                        steering_angle=telemetry["steering_angle"],
                        steering_state=telemetry["steering_state"],
                        accelerating=telemetry["accelerating"],
                        braking=telemetry["braking"],
                        handbrake=telemetry["handbrake"],
                        fps=telemetry["fps"],
                        gesture_name=telemetry.get("gesture_name", "Neutral"),
                        confidence=telemetry.get("confidence", 0.0),
                        raw_frame=frame
                    )
                    calib_data = telemetry.get("calibration_overlay", (0, 0.0, ""))
                    self.current_page_widget.show_calibration_overlay(*calib_data)
                else:
                    if hasattr(self, "camera_start_time") and time.time() - self.camera_start_time > 3.0:
                        self.status_pill.configure(text="● NO FEED", text_color="#FF9900")
                        if not hasattr(self, "warned_no_feed"):
                            self.warned_no_feed = True
                            self.add_log_message("WARNING: Camera index grab timeout.")
                            self.current_page_widget.video_label.configure(
                                image="",
                                text="⚠️ NO WEBCAM FEED DETECTED\n\nCheck inputs or calibration wizards."
                            )

        # Loop timing
        self.after(33, self.gui_update_loop)

    def change_weather_theme(self, weather_mode: str) -> None:
        game_weather_map = {
            "morning": "day",
            "sunny": "day",
            "evening": "day",
            "night": "night",
            "rain": "rain",
            "storm": "rain",
            "fog": "fog",
            "snow": "rain"
        }
        target_weather = game_weather_map.get(weather_mode, "night")
        if self.current_page_name == "drive" and hasattr(self, "current_page_widget"):
            self.current_page_widget.game_widget.current_weather = target_weather

    def on_close(self) -> None:
        logger.info("Closing application...")
        self.stop_system()
        self.destroy()

if __name__ == "__main__":
    app = VisionDriveAIApp()
    app.mainloop()
