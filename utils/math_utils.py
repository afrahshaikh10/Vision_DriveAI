import math
import numpy as np
from typing import List, Tuple

class MovingAverage:
    """A moving average filter to smooth values and reduce jitter."""
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.values: List[float] = []

    def update(self, new_value: float) -> float:
        """Adds a new value and returns the current average."""
        self.values.append(new_value)
        if len(self.values) > self.window_size:
            self.values.pop(0)
        return sum(self.values) / len(self.values)

    def reset(self) -> None:
        """Resets the filter memory."""
        self.values.clear()

    def set_window_size(self, size: int) -> None:
        """Changes the window size and adjusts history if needed."""
        self.window_size = max(1, size)
        while len(self.values) > self.window_size:
            self.values.pop(0)

def calculate_angle(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Calculates the angle in degrees between the line connecting two points and the horizontal line.
    p1: Left point (typically Left Hand)
    p2: Right point (typically Right Hand)
    Returns: angle in degrees, where 0 is horizontal, negative is counter-clockwise (left turn),
             positive is clockwise (right turn).
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    
    # Calculate angle in radians and convert to degrees
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    return angle_deg

def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculates the Euclidean distance between two 2D points."""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def map_value(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Clamps and maps a value from an input range to an output range."""
    if in_min == in_max:
        return out_min
    
    # Clamp value within input range
    clamped_val = max(min(value, max(in_min, in_max)), min(in_min, in_max))
    
    # Linear interpolation formula
    return out_min + (float(clamped_val - in_min) / float(in_max - in_min)) * (out_max - out_min)

def get_hand_center(landmarks: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Calculates the center of mass (X, Y) of the hand landmarks."""
    if not landmarks:
        return 0.0, 0.0
    xs = [lm[0] for lm in landmarks]
    ys = [lm[1] for lm in landmarks]
    return sum(xs) / len(xs), sum(ys) / len(ys)

class DoubleExponentialFilter:
    """Double Exponential Smoothing filter to remove high-frequency hand jitter without introducing lag."""
    def __init__(self, alpha: float = 0.45, beta: float = 0.25):
        self.alpha = alpha
        self.beta = beta
        self.s = None
        self.b = 0.0

    def filter(self, x: float) -> float:
        if self.s is None:
            self.s = x
            self.b = 0.0
            return x
        
        last_s = self.s
        last_b = self.b
        
        self.s = self.alpha * x + (1.0 - self.alpha) * (last_s + last_b)
        self.b = self.beta * (self.s - last_s) + (1.0 - self.beta) * last_b
        
        return self.s

    def reset(self) -> None:
        self.s = None
        self.b = 0.0
