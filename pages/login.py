import customtkinter as ctk
from typing import Optional, Dict, Any, List
from utils.db import db

class LoginScreen(ctk.CTkFrame):
    """Modern full-screen login and registration page with a game-launcher theme."""
    def __init__(self, parent: Any, on_login_success: callable):
        super().__init__(parent, fg_color="#080810")
        self.on_login_success = on_login_success
        
        self.is_register_mode = False
        self.selected_avatar = "avatar_1"
        self.avatars = {
            "avatar_1": "🏎️ Pro Racer",
            "avatar_2": "🚀 Space Pilot",
            "avatar_3": "🛸 Cyber Driver",
            "avatar_4": "⚡ Electro Pilot"
        }
        
        self.setup_ui()

    def setup_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Main Glassmorphic Wrapper Card
        self.card = ctk.CTkFrame(
            self, 
            fg_color="#0f0f1b", 
            border_color="#FF007F", 
            border_width=1, 
            corner_radius=20,
            width=400,
            height=580
        )
        self.card.grid(row=0, column=0, sticky="")
        self.card.grid_propagate(False)
        
        # Header / Title
        self.header_label = ctk.CTkLabel(
            self.card,
            text="SIGN IN",
            font=ctk.CTkFont(family="Outfit", size=26, weight="bold"),
            text_color="#FFFFFF"
        )
        self.header_label.pack(pady=(35, 10))
        
        self.desc_label = ctk.CTkLabel(
            self.card,
            text="Access your VisionDrive AI driver profile",
            font=ctk.CTkFont(family="Outfit", size=11),
            text_color="#888888"
        )
        self.desc_label.pack(pady=(0, 25))
        
        # Username Entry
        self.username_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="Enter Player Name",
            width=300,
            height=40,
            fg_color="#12121e",
            border_color="#1b1836",
            text_color="#FFFFFF",
            placeholder_text_color="#5a5a66"
        )
        self.username_entry.pack(pady=8)
        
        # Password Entry
        self.password_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="Enter Password",
            show="*",
            width=300,
            height=40,
            fg_color="#12121e",
            border_color="#1b1836",
            text_color="#FFFFFF",
            placeholder_text_color="#5a5a66"
        )
        self.password_entry.pack(pady=8)
        
        # Avatar Dropdown (hidden in login mode, shown in register mode)
        self.avatar_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.avatar_label = ctk.CTkLabel(self.avatar_frame, text="Select Avatar:", font=ctk.CTkFont(size=11), text_color="#888888")
        self.avatar_label.pack(side="left", padx=5)
        self.avatar_menu = ctk.CTkOptionMenu(
            self.avatar_frame,
            values=list(self.avatars.values()),
            command=self._on_avatar_select,
            button_color="#FF007F",
            button_hover_color="#CC0066",
            fg_color="#12121e"
        )
        self.avatar_menu.pack(side="right", padx=5)
        self.avatar_menu.set(self.avatars["avatar_1"])
        
        # Options row (Remember Me / Forgot Password)
        self.options_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.options_frame.pack(pady=12, fill="x", padx=50)
        
        self.remember_cb = ctk.CTkCheckBox(
            self.options_frame, 
            text="Remember Me", 
            font=ctk.CTkFont(size=10),
            checkbox_width=16,
            checkbox_height=16,
            border_width=1,
            fg_color="#FF007F",
            hover_color="#CC0066",
            text_color="#888888"
        )
        self.remember_cb.pack(side="left")
        
        self.forgot_lbl = ctk.CTkLabel(
            self.options_frame,
            text="Forgot Password?",
            font=ctk.CTkFont(size=10, underline=True),
            text_color="#00F5FF",
            cursor="hand2"
        )
        self.forgot_lbl.pack(side="right")
        self.forgot_lbl.bind("<Button-1>", self._on_forgot_password)
        
        # Status message label
        self.status_lbl = ctk.CTkLabel(
            self.card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#FF007F"
        )
        self.status_lbl.pack(pady=5)
        
        # Main Submit Button
        self.submit_btn = ctk.CTkButton(
            self.card,
            text="LOG IN",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            width=300,
            height=40,
            fg_color="#FF007F",
            hover_color="#CC0066",
            command=self._on_submit_click
        )
        self.submit_btn.pack(pady=10)
        
        # Guest Login Button
        self.guest_btn = ctk.CTkButton(
            self.card,
            text="CONTINUE AS GUEST",
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            width=300,
            height=36,
            fg_color="#12121e",
            border_color="#1b1836",
            border_width=1,
            hover_color="#00F5FF",
            text_color="#00F5FF",
            command=self._on_guest_click
        )
        self.guest_btn.pack(pady=5)
        
        # Google Sign-In (UI Only)
        self.google_btn = ctk.CTkButton(
            self.card,
            text="SIGN IN WITH GOOGLE",
            font=ctk.CTkFont(family="Outfit", size=11),
            width=300,
            height=30,
            fg_color="#050508",
            border_color="#1b1836",
            border_width=1,
            hover_color="#888888",
            text_color="#888888",
            command=self._on_google_click
        )
        self.google_btn.pack(pady=5)
        
        # Toggle mode row
        self.toggle_mode_lbl = ctk.CTkLabel(
            self.card,
            text="Don't have an account? Sign Up",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            cursor="hand2"
        )
        self.toggle_mode_lbl.pack(pady=(15, 10))
        self.toggle_mode_lbl.bind("<Button-1>", self._toggle_login_mode)

    def _toggle_login_mode(self, event: Any = None) -> None:
        self.is_register_mode = not self.is_register_mode
        self.status_lbl.configure(text="")
        
        if self.is_register_mode:
            self.header_label.configure(text="REGISTER")
            self.desc_label.configure(text="Create a new VisionDrive AI profile")
            self.submit_btn.configure(text="CREATE ACCOUNT")
            self.toggle_mode_lbl.configure(text="Already have an account? Sign In")
            self.avatar_frame.pack(pady=5, fill="x", padx=50, before=self.options_frame)
            self.options_frame.pack_forget()
        else:
            self.header_label.configure(text="SIGN IN")
            self.desc_label.configure(text="Access your VisionDrive AI driver profile")
            self.submit_btn.configure(text="LOG IN")
            self.toggle_mode_lbl.configure(text="Don't have an account? Sign Up")
            self.avatar_frame.pack_forget()
            self.options_frame.pack(pady=12, fill="x", padx=50, before=self.status_lbl)

    def _on_avatar_select(self, val: str) -> None:
        for k, v in self.avatars.items():
            if v == val:
                self.selected_avatar = k
                break

    def _on_forgot_password(self, event: Any) -> None:
        self.status_lbl.configure(text="Hint: Default guest account is available.", text_color="#00F5FF")

    def _on_google_click(self) -> None:
        self.status_lbl.configure(text="Google Login is simulated (UI Only).", text_color="#F1C40F")

    def _on_guest_click(self) -> None:
        # Load Guest account from DB
        guest = db.get_user_by_id(1)
        if guest:
            self.on_login_success(guest)
        else:
            self.status_lbl.configure(text="Guest Account DB Error", text_color="#FF007F")

    def _on_submit_click(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username:
            self.status_lbl.configure(text="Please enter player name.", text_color="#FF007F")
            return
            
        if self.is_register_mode:
            # Register user
            if db.register_user(username, password, self.selected_avatar):
                self.status_lbl.configure(text="Account created! Logging in...", text_color="#00FF66")
                # Auto log in
                user = db.authenticate_user(username, password)
                if user:
                    self.after(800, lambda: self.on_login_success(user))
            else:
                self.status_lbl.configure(text="Player name already taken.", text_color="#FF007F")
        else:
            # Log in
            user = db.authenticate_user(username, password)
            if user:
                self.status_lbl.configure(text="Login successful!", text_color="#00FF66")
                self.after(500, lambda: self.on_login_success(user))
            else:
                self.status_lbl.configure(text="Invalid credentials.", text_color="#FF007F")
