from typing import Dict, List, Tuple, Any, Optional
from utils.logger import logger
from utils.math_utils import calculate_angle, calculate_distance, get_hand_center

class CalibrationWizard:
    """Manages the step-by-step calibration sequence for steering angles and hand distance."""
    def __init__(self):
        self.current_step = 0  # 0: Idle, 1: Neutral, 2: Max Left, 3: Max Right, 4: Ready to Save
        
        # Temp buffers for averaging during calibration
        self.step_samples: List[Tuple[float, float]] = [] # stores (angle, distance)
        
        # Final calibrated values
        self.neutral_angle = 0.0
        self.neutral_distance = 200.0
        self.max_left_angle = -30.0
        self.max_right_angle = 30.0

    def start(self) -> None:
        """Starts/restarts the calibration sequence."""
        self.current_step = 1
        self.step_samples.clear()
        logger.info("Calibration sequence started. Step 1: Place hands in Neutral position.")

    def get_instructions(self) -> str:
        """Returns description text for the current step."""
        if self.current_step == 0:
            return "Press 'Start Calibration' to begin."
        elif self.current_step == 1:
            return "Step 1: Place both hands naturally at a comfortable level distance. Keep them level (horizontal)."
        elif self.current_step == 2:
            return "Step 2: Turn your hands fully to the LEFT (simulating full steering turn)."
        elif self.current_step == 3:
            return "Step 3: Turn your hands fully to the RIGHT (simulating full steering turn)."
        elif self.current_step == 4:
            return "Calibration complete! Press 'Save' to apply settings."
        return "Unknown Step"

    def record_frame(self, hands_data: List[Dict[str, Any]]) -> bool:
        """
        Records the current frame values for the active calibration step.
        Returns:
            - True if enough frames/samples are collected, indicating readiness to advance.
        """
        if self.current_step not in [1, 2, 3] or len(hands_data) < 2:
            return False

        # Identify visual left and right hands
        sorted_hands = sorted(hands_data, key=lambda h: h["bbox"][0])
        left_hand = sorted_hands[0]
        right_hand = sorted_hands[1]

        # Calculate hand centers
        left_center = get_hand_center(left_hand["landmarks"])
        right_center = get_hand_center(right_hand["landmarks"])

        # Calculate angle (inverted so right turn = positive)
        angle = -calculate_angle(left_center, right_center)
        distance = calculate_distance(left_center, right_center)

        self.step_samples.append((angle, distance))
        
        # We collect 15 samples to average out noise
        return len(self.step_samples) >= 15

    def process_step(self) -> None:
        """Averages the collected samples for the current step and moves to next."""
        if not self.step_samples:
            logger.warning(f"No samples collected for step {self.current_step}")
            return

        avg_angle = sum(s[0] for s in self.step_samples) / len(self.step_samples)
        avg_distance = sum(s[1] for s in self.step_samples) / len(self.step_samples)

        if self.current_step == 1:
            self.neutral_angle = avg_angle
            self.neutral_distance = avg_distance
            logger.info(f"Neutral calibrated: Angle={self.neutral_angle:.2f}, Distance={self.neutral_distance:.2f}")
            self.current_step = 2
            
        elif self.current_step == 2:
            # Angle relative to neutral
            self.max_left_angle = avg_angle - self.neutral_angle
            logger.info(f"Max Left calibrated: Rel Angle={self.max_left_angle:.2f}")
            self.current_step = 3
            
        elif self.current_step == 3:
            # Angle relative to neutral
            self.max_right_angle = avg_angle - self.neutral_angle
            logger.info(f"Max Right calibrated: Rel Angle={self.max_right_angle:.2f}")
            self.current_step = 4

        self.step_samples.clear()

    def get_results(self) -> Dict[str, Any]:
        """Returns the calibration dictionary."""
        # Sanity check limits to avoid division by zero or inverse steering
        left = self.max_left_angle if self.max_left_angle < -5.0 else -30.0
        right = self.max_right_angle if self.max_right_angle > 5.0 else 30.0
        
        return {
            "neutral_angle": self.neutral_angle,
            "max_left_angle": left,
            "max_right_angle": right,
            "neutral_distance": self.neutral_distance,
            "calibrated": True
        }

    def reset(self) -> None:
        """Resets calibration wizard state."""
        self.current_step = 0
        self.step_samples.clear()


