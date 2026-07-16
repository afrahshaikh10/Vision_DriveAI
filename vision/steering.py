import math
from typing import Dict, List, Tuple, Optional, Any
from utils.logger import logger
from utils.math_utils import MovingAverage, calculate_angle, map_value, get_hand_center, DoubleExponentialFilter

class SteeringController:
    """Calculates steering angle and classifies steering states from hand tracking data."""
    def __init__(self, dead_zone: float = 5.0, smoothing_amount: int = 5, sensitivity: float = 1.0):
        self.dead_zone = dead_zone
        self.sensitivity = sensitivity
        self.smoother = MovingAverage(window_size=smoothing_amount)
        
        # Calibration bounds (default values, overwritten by calibration config)
        self.neutral_angle = 0.0
        self.max_left_angle = -30.0
        self.max_right_angle = 30.0
        
        self.current_raw_angle = 0.0
        self.current_smoothed_angle = 0.0
        self.current_state = "Straight"
        self.double_smoother = DoubleExponentialFilter(alpha=0.4, beta=0.2)

    def update_settings(self, dead_zone: float, smoothing_amount: int, sensitivity: float) -> None:
        """Dynamically updates steering settings."""
        self.dead_zone = dead_zone
        self.sensitivity = sensitivity
        self.smoother.set_window_size(smoothing_amount)
        # Adapt double exponential filter alpha and beta dynamically
        alpha = max(0.15, min(0.85, 2.0 / (smoothing_amount + 1.0)))
        self.double_smoother.alpha = alpha
        self.double_smoother.beta = alpha * 0.5

    def update_calibration(self, calibration_data: Dict[str, Any]) -> None:
        """Loads calibration parameters."""
        self.neutral_angle = calibration_data.get("neutral_angle", 0.0)
        self.max_left_angle = calibration_data.get("max_left_angle", -30.0)
        self.max_right_angle = calibration_data.get("max_right_angle", 30.0)
        logger.info(f"Steering calibration updated: Neutral={self.neutral_angle}, MaxLeft={self.max_left_angle}, MaxRight={self.max_right_angle}")

    def calculate_steering(self, hands_data: List[Dict[str, Any]]) -> Tuple[float, float, str]:
        """
        Calculates and smooths steering angle using the line connecting two hands.
        Returns:
            - raw_angle: Unfiltered angle relative to neutral
            - smoothed_angle: Moving-average filtered angle
            - steering_state: 'Hard Left', 'Left', 'Slight Left', 'Straight', etc.
        """
        if len(hands_data) < 2:
            # Not enough hands, steer straight or return current smoothed
            # For gameplay safety, if hands disappear, decay steering to 0
            self.current_raw_angle = 0.0
            self.current_smoothed_angle = self.double_smoother.filter(0.0)
            self.current_state = "Straight"
            return self.current_raw_angle, self.current_smoothed_angle, self.current_state

        # Identify visual left and visual right hands based on x-coordinate
        sorted_hands = sorted(hands_data, key=lambda h: h["bbox"][0])  # Sort by xmin
        left_hand = sorted_hands[0]
        right_hand = sorted_hands[1]

        # Calculate hand centers (average of all landmarks)
        left_center = get_hand_center(left_hand["landmarks"])
        right_center = get_hand_center(right_hand["landmarks"])

        # Calculate angle of the line connecting left and right hand centers
        # We invert the angle so that a clockwise tilt (right hand higher, left hand lower)
        # corresponds to a positive angle (Right Turn).
        raw_angle = calculate_angle(left_center, right_center)
        
        # Adjust by neutral calibration offset
        calibrated_angle = raw_angle - self.neutral_angle
        
        # Apply steering sensitivity factor
        calibrated_angle *= self.sensitivity
        
        # Update raw and smoothed values
        self.current_raw_angle = calibrated_angle
        self.current_smoothed_angle = self.double_smoother.filter(calibrated_angle)
        
        # Classify steering state
        self.current_state = self._classify_steering(self.current_smoothed_angle)
        
        return self.current_raw_angle, self.current_smoothed_angle, self.current_state

    def _classify_steering(self, angle: float) -> str:
        """Maps an angle into discrete steering states using calibration limits."""
        abs_angle = abs(angle)
        
        # Check dead zone
        if abs_angle <= self.dead_zone:
            return "Straight"

        # Determine limits based on direction
        is_right = angle > 0
        limit = self.max_right_angle if is_right else abs(self.max_left_angle)
        
        # Ensure limit is positive and non-zero
        limit = max(10.0, limit)
        
        # Segment boundaries
        slight_threshold = limit * 0.33
        hard_threshold = limit * 0.70

        if abs_angle <= slight_threshold:
            return "Slight Right" if is_right else "Slight Left"
        elif abs_angle <= hard_threshold:
            return "Right" if is_right else "Left"
        else:
            return "Hard Right" if is_right else "Hard Left"
            
    def get_steering_percentage(self) -> float:
        """Returns the current steering angle as a percentage from -100 (Hard Left) to +100 (Hard Right)."""
        angle = self.current_smoothed_angle
        if angle >= 0:
            limit = max(1.0, self.max_right_angle)
            pct = (angle / limit) * 100.0
        else:
            limit = max(1.0, abs(self.max_left_angle))
            pct = (angle / limit) * 100.0
        return max(-100.0, min(100.0, pct))
