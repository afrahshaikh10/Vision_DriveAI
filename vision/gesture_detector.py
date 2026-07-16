import time
from typing import Dict, List, Tuple, Any, Optional
from utils.logger import logger
from utils.math_utils import calculate_distance

# MediaPipe Finger landmark indices
# Format: (TIP, DIP, PIP, MCP)
FINGER_INDEX_MAP = {
    "index": (8, 7, 6, 5),
    "middle": (12, 11, 10, 9),
    "ring": (16, 15, 14, 13),
    "pinky": (20, 19, 18, 17)
}

class GestureDetector:
    """Detects gestures like Open Palm, Fist, Hands Close, and Thumbs Down to drive controls."""
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        
        # State tracking for sustained gestures (e.g., handbrake duration)
        self.fist_start_time: Optional[float] = None
        self.thumbs_down_start_time: Optional[float] = None
        
        self.neutral_distance = 200.0  # From config, calibrated

    def update_settings(self, confidence_threshold: float, neutral_distance: float) -> None:
        self.confidence_threshold = confidence_threshold
        self.neutral_distance = neutral_distance

    def detect_gestures(self, hands_data: List[Dict[str, Any]]) -> Tuple[bool, bool, bool, List[str]]:
        """
        Processes hands coordinates to classify gestures.
        Returns:
            - accelerate: bool (Open Palm or Raised Hand)
            - brake: bool (Fist or Hands Close Together)
            - handbrake: bool (Sustained fist > 2s or Thumbs Down)
            - debug_info: List of string labels describing the current hand states
        """
        accelerate = False
        brake = False
        handbrake = False
        debug_info = []
        
        num_hands = len(hands_data)
        
        # 1. Evaluate individual hand gestures
        hand_states = {}
        for hand in hands_data:
            label = hand["label"] # "Left" or "Right"
            landmarks = hand["landmarks"]
            
            is_open = self._is_open_palm(landmarks)
            is_fist = self._is_fist(landmarks)
            is_thumbs_down = self._is_thumbs_down(landmarks)
            
            if is_open:
                hand_states[label] = "Open Palm"
            elif is_thumbs_down:
                hand_states[label] = "Thumbs Down"
            elif is_fist:
                hand_states[label] = "Fist"
            else:
                hand_states[label] = "Neutral"
                
            debug_info.append(f"{label}: {hand_states[label]}")

        # 2. Check Acceleration (Closed Fist on any hand, simulating steering grip)
        # We classify as Accelerate if at least one hand is a "Fist"
        if any(state == "Fist" for state in hand_states.values()):
            accelerate = True

        # Check if right hand is raised significantly above left hand (another acceleration gesture)
        if num_hands == 2:
            sorted_hands = sorted(hands_data, key=lambda h: h["bbox"][0]) # visual left, visual right
            left_y = self._get_hand_center_y(sorted_hands[0]["landmarks"])
            right_y = self._get_hand_center_y(sorted_hands[1]["landmarks"])
            # Remember pixel Y increases downwards, so a higher hand has smaller Y
            # If right hand is higher by more than 100 pixels, trigger accelerate
            if left_y - right_y > 100:
                accelerate = True
                debug_info.append("Right Hand Raised")

        # 3. Check Braking (Open Palm on any hand, simulating letting go, or hands close together)
        if any(state == "Open Palm" for state in hand_states.values()):
            brake = True

        if num_hands == 2:
            # Calculate distance between hands
            sorted_hands = sorted(hands_data, key=lambda h: h["bbox"][0])
            left_center = self._get_hand_center(sorted_hands[0]["landmarks"])
            right_center = self._get_hand_center(sorted_hands[1]["landmarks"])
            dist = calculate_distance(left_center, right_center)
            
            # If hands are close together (e.g. less than 40% of neutral calibrated distance or 120 pixels)
            close_threshold = max(100.0, self.neutral_distance * 0.45)
            if dist < close_threshold:
                brake = True
                debug_info.append(f"Hands Close ({int(dist)}px)")

        # 4. Check Handbrake (Thumbs down, or Fist held for 2 seconds)
        # Thumbs down
        if any(state == "Thumbs Down" for state in hand_states.values()):
            if self.thumbs_down_start_time is None:
                self.thumbs_down_start_time = time.time()
            # Thumbs down triggers handbrake instantly
            handbrake = True
        else:
            self.thumbs_down_start_time = None



        # Don't accelerate if braking
        if brake or handbrake:
            accelerate = False

        return accelerate, brake, handbrake, debug_info

    def _is_open_palm(self, landmarks: List[Tuple[int, int]]) -> bool:
        """Determines if the hand is an open palm (all fingers extended)."""
        # Count extended fingers
        extended_count = 0
        
        # Check standard 4 fingers
        for finger, indices in FINGER_INDEX_MAP.items():
            tip, _, pip, _ = indices
            # Y coordinate of TIP is smaller than PIP
            if landmarks[tip][1] < landmarks[pip][1]:
                extended_count += 1
                
        # Check thumb (distance between thumb tip and index MCP is large when extended)
        # Landmark 4: Thumb Tip, Landmark 5: Index MCP, Landmark 2: Thumb MCP
        thumb_tip = landmarks[4]
        index_mcp = landmarks[5]
        thumb_mcp = landmarks[2]
        
        # Average distance between thumb tip and index MCP when folded vs extended
        dist_thumb = calculate_distance(thumb_tip, index_mcp)
        dist_mcp = calculate_distance(thumb_mcp, index_mcp)
        
        if dist_thumb > dist_mcp * 1.3:
            extended_count += 1
            
        return extended_count >= 4

    def _is_fist(self, landmarks: List[Tuple[int, int]]) -> bool:
        """Determines if the hand is a closed fist (fingers folded)."""
        folded_count = 0
        
        # Check standard 4 fingers
        for finger, indices in FINGER_INDEX_MAP.items():
            tip, _, pip, mcp = indices
            # Y coordinate of TIP is larger than PIP
            if landmarks[tip][1] > landmarks[pip][1]:
                folded_count += 1
                
        # Check thumb
        thumb_tip = landmarks[4]
        index_mcp = landmarks[5]
        thumb_mcp = landmarks[2]
        
        dist_thumb = calculate_distance(thumb_tip, index_mcp)
        dist_mcp = calculate_distance(thumb_mcp, index_mcp)
        
        if dist_thumb <= dist_mcp * 1.1:
            folded_count += 1
            
        return folded_count >= 4

    def _is_thumbs_down(self, landmarks: List[Tuple[int, int]]) -> bool:
        """Detects a thumbs-down gesture (thumb pointing down, other fingers folded)."""
        # Other fingers must be folded (fist-like)
        folded_count = 0
        for finger, indices in FINGER_INDEX_MAP.items():
            tip, _, pip, _ = indices
            if landmarks[tip][1] > landmarks[pip][1]:
                folded_count += 1
                
        if folded_count < 3:
            return False
            
        # Thumb TIP (4) Y must be larger than Thumb MCP (2) Y (pointing downwards)
        thumb_tip_y = landmarks[4][1]
        thumb_mcp_y = landmarks[2][1]
        wrist_y = landmarks[0][1]
        
        # Also thumb should be extended (dist from index MCP)
        dist_thumb_tip = calculate_distance(landmarks[4], landmarks[5])
        dist_mcp = calculate_distance(landmarks[2], landmarks[5])
        
        return thumb_tip_y > thumb_mcp_y and dist_thumb_tip > dist_mcp * 1.2

    def _get_hand_center_y(self, landmarks: List[Tuple[int, int]]) -> float:
        """Returns average Y of hand landmarks."""
        ys = [lm[1] for lm in landmarks]
        return sum(ys) / len(ys)

    def _get_hand_center(self, landmarks: List[Tuple[int, int]]) -> Tuple[float, float]:
        """Returns average (X, Y) of hand landmarks."""
        xs = [lm[0] for lm in landmarks]
        ys = [lm[1] for lm in landmarks]
        return sum(xs) / len(xs), sum(ys) / len(ys)
