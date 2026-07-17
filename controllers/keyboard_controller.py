from typing import Dict, Set, Any
from pynput.keyboard import Key, Controller
from utils.logger import logger

class KeyboardController:
    """Simulates keyboard inputs for game control based on steering and gesture states."""
    def __init__(self, key_bindings: Dict[str, str]):
        self.keyboard = Controller()
        self.bindings = key_bindings
        
        # Track currently pressed virtual keys to avoid duplicate keydown spam
        self.pressed_keys: Set[Any] = set()
        
        # Track steering state
        self.last_steering_state = "Straight"
        self.frame_count = 0
        
        logger.info("KeyboardController initialized.")

    def update_bindings(self, key_bindings: Dict[str, str]) -> None:
        """Updates the key bindings mapping."""
        self.release_all()
        self.bindings = key_bindings
        logger.info(f"Keyboard bindings updated: {self.bindings}")

    def update_controls(self, accelerate: bool, brake: bool, handbrake: bool, boost: bool, steering_state: str) -> None:
        """
        Translates gesture decisions and steering states into keyboard presses/releases.
        """
        # 1. Handle Acceleration (Up key equivalent)
        accel_key = self._resolve_key(self.bindings.get("accelerate", "up"))
        if accelerate:
            self._press(accel_key)
        else:
            self._release(accel_key)

        # 1b. Handle Boost (Shift key equivalent)
        boost_key = self._resolve_key(self.bindings.get("boost", "shift"))
        if boost:
            self._press(boost_key)
        else:
            self._release(boost_key)

        # 2. Handle Braking (Down key equivalent)
        brake_key = self._resolve_key(self.bindings.get("brake", "down"))
        if brake:
            self._press(brake_key)
        else:
            self._release(brake_key)

        # 3. Handle Handbrake (Space key equivalent)
        handbrake_key = self._resolve_key(self.bindings.get("handbrake", "space"))
        if handbrake:
            self._press(handbrake_key)
        else:
            self._release(handbrake_key)

        # 4. Handle Steering (Left / Right keys equivalent)
        self.frame_count += 1
        left_key = self._resolve_key(self.bindings.get("left", "left"))
        right_key = self._resolve_key(self.bindings.get("right", "right"))

        # Implement pulsed duty-cycle key emulation to allow analog-like control precision
        # Hard: 100% active frames
        # Medium: 66% active frames (2 out of 3)
        # Slight: 33% active frames (1 out of 3)
        press_left = False
        press_right = False
        
        if steering_state == "Hard Left":
            press_left = True
        elif steering_state == "Left":
            press_left = (self.frame_count % 3 != 0)
        elif steering_state == "Slight Left":
            press_left = (self.frame_count % 3 == 0)
            
        if steering_state == "Hard Right":
            press_right = True
        elif steering_state == "Right":
            press_right = (self.frame_count % 3 != 0)
        elif steering_state == "Slight Right":
            press_right = (self.frame_count % 3 == 0)

        if press_left:
            self._release(right_key)
            self._press(left_key)
        elif press_right:
            self._release(left_key)
            self._press(right_key)
        else:
            self._release(left_key)
            self._release(right_key)

        self.last_steering_state = steering_state

    def release_all(self) -> None:
        """Releases all keys currently registered as pressed."""
        if not self.pressed_keys:
            return
            
        logger.info(f"Releasing all keys: {self.pressed_keys}")
        # Copy to avoid Set modification during iteration
        for key in list(self.pressed_keys):
            try:
                self.keyboard.release(key)
            except Exception as e:
                logger.error(f"Error releasing key {key}: {e}")
        self.pressed_keys.clear()

    def _resolve_key(self, key_str: str) -> Any:
        """Converts string name of key from config to pynput Key or character."""
        key_str = key_str.lower().strip()
        
        special_keys = {
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
            "space": Key.space,
            "enter": Key.enter,
            "shift": Key.shift,
            "ctrl": Key.ctrl,
            "alt": Key.alt,
            "tab": Key.tab,
            "esc": Key.esc
        }
        
        if key_str in special_keys:
            return special_keys[key_str]
        
        # If it is a character, return it directly
        if len(key_str) == 1:
            return key_str
            
        # Default fallback
        return Key.space

    def _press(self, key: Any) -> None:
        """Internal helper to press a key if it is not already pressed."""
        if key not in self.pressed_keys:
            try:
                self.keyboard.press(key)
                self.pressed_keys.add(key)
            except Exception as e:
                logger.error(f"Failed to press key {key}: {e}")

    def _release(self, key: Any) -> None:
        """Internal helper to release a key if it is currently pressed."""
        if key in self.pressed_keys:
            try:
                self.keyboard.release(key)
                self.pressed_keys.remove(key)
            except Exception as e:
                logger.error(f"Failed to release key {key}: {e}")
        elif isinstance(key, Key):
            # Safe redundant release for special keys to ensure no sticky controls
            try:
                self.keyboard.release(key)
            except:
                pass
