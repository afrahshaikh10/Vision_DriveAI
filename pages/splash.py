import customtkinter as ctk
import time
import math

class SplashScreen(ctk.CTkFrame):
    """Sleek splash screen with neon animations showing system initialization steps."""
    def __init__(self, parent: ctk.CTk, on_loaded_callback: callable):
        super().__init__(parent, fg_color="#080810")
        self.on_loaded = on_loaded_callback
        
        # State
        self.loading_step = 0
        self.pulse_phase = 0.0
        
        self.setup_ui()
        self.animate_logo()
        self.run_initialization_sequence()

    def setup_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Content Box
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="")
        
        # Pulsing logo
        self.logo_label = ctk.CTkLabel(
            self.container, 
            text="VISIONDRIVE AI", 
            font=ctk.CTkFont(family="Outfit", size=48, weight="bold"),
            text_color="#FF007F"
        )
        self.logo_label.pack(pady=(0, 5))
        
        self.subtitle_label = ctk.CTkLabel(
            self.container,
            text="AI GESTURE CONTROLLED RACING SIMULATOR",
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            text_color="#00F5FF"
        )
        self.subtitle_label.pack(pady=(0, 40))
        
        # Loader
        self.status_label = ctk.CTkLabel(
            self.container,
            text="Initializing AI Engine...",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#888888"
        )
        self.status_label.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(
            self.container, 
            width=300, 
            height=6, 
            progress_color="#FF007F", 
            fg_color="#12121e"
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(pady=10)

    def animate_logo(self) -> None:
        """Pulsates the color/glowing effect of the title."""
        if not self.winfo_exists():
            return
            
        self.pulse_phase += 0.1
        # Interpolate neon pink to cyber cyan
        factor = (math.sin(self.pulse_phase) + 1.0) / 2.0
        
        # Hex interpolation between #FF007F and #00F5FF
        r = int(255 * (1.0 - factor) + 0 * factor)
        g = int(0 * (1.0 - factor) + 245 * factor)
        b = int(127 * (1.0 - factor) + 255 * factor)
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        
        self.logo_label.configure(text_color=hex_color)
        self.after(50, self.animate_logo)

    def run_initialization_sequence(self) -> None:
        """Cycles through boot checkmarks."""
        steps = [
            (0.15, "Initializing AI Configurations...", 400),
            (0.40, "Detecting Webcam Input...", 600),
            (0.70, "Loading Gesture Engine Models...", 800),
            (0.95, "Checking Calibration Database...", 500),
            (1.00, "Ready! Launching Simulator Dashboard...", 400)
        ]
        
        if self.loading_step < len(steps):
            progress, text, delay = steps[self.loading_step]
            self.progress_bar.set(progress)
            self.status_label.configure(text=text)
            self.loading_step += 1
            self.after(delay, self.run_initialization_sequence)
        else:
            # Done loading, call parent callback
            self.on_loaded()
