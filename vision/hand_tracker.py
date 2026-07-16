import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from utils.logger import logger

class HandTracker:
    """Uses MediaPipe to track hands, extract landmarks, labels, and bounding boxes."""
    def __init__(self, min_detection_confidence: float = 0.7, min_tracking_confidence: float = 0.7):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def set_confidences(self, detection_conf: float, tracking_conf: float) -> None:
        """Allows dynamic adjustment of detection and tracking confidences."""
        # Re-initialize MediaPipe Hands if settings change
        self.hands.close()
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf
        )

    def process_frame(self, frame: cv2.Mat) -> Tuple[cv2.Mat, List[Dict[str, Any]]]:
        """
        Processes a BGR video frame to detect hands.
        Returns:
            - The original/annotated frame (for preview)
            - A list of dicts containing parsed hand details.
        """
        h, w, _ = frame.shape
        # Convert the frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.hands.process(rgb_frame)
        hands_data = []

        if results.multi_hand_landmarks and results.multi_handedness:
            # Sort or match handedness with landmarks
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                handedness = results.multi_handedness[idx]
                label = handedness.classification[0].label  # "Left" or "Right"
                score = handedness.classification[0].score
                
                # Extract pixel coordinates
                landmarks_px = []
                landmarks_z = []
                x_coords = []
                y_coords = []
                
                for lm in hand_landmarks.landmark:
                    px_x = int(lm.x * w)
                    px_y = int(lm.y * h)
                    landmarks_px.append((px_x, px_y))
                    landmarks_z.append(lm.z)
                    x_coords.append(px_x)
                    y_coords.append(px_y)
                
                # Calculate Bounding Box
                xmin, xmax = min(x_coords), max(x_coords)
                ymin, ymax = min(y_coords), max(y_coords)
                # Pad bounding box slightly
                padding = 15
                xmin = max(0, xmin - padding)
                ymin = max(0, ymin - padding)
                xmax = min(w, xmax + padding)
                ymax = min(h, ymax + padding)
                
                hands_data.append({
                    "label": label,  # MediaPipe is mirrored internally
                    "score": score,
                    "landmarks": landmarks_px,
                    "landmarks_z": landmarks_z,
                    "bbox": (xmin, ymin, xmax, ymax),
                    "raw_landmarks": hand_landmarks
                })

        return frame, hands_data

    def draw_overlays(self, frame: cv2.Mat, hands_data: List[Dict[str, Any]]) -> cv2.Mat:
        """Draws skeletons, landmarks, labels, bounding boxes, hand centers, and steering vectors."""
        import math
        from utils.math_utils import get_hand_center
        
        annotated_frame = frame.copy()
        h, w, _ = frame.shape
        
        # Calculate tracking quality
        hand_count = len(hands_data)
        if hand_count == 2:
            avg_score = sum(h["score"] for h in hands_data) / 2.0
            quality = "EXCELLENT" if avg_score > 0.8 else "GOOD"
            quality_color = (0, 255, 102)  # Neon Green
        elif hand_count == 1:
            quality = "MODERATE"
            quality_color = (0, 245, 255)  # Neon Cyan
        else:
            quality = "INACTIVE"
            quality_color = (127, 127, 127)  # Gray
            
        # Draw Top HUD bar with glassmorphism style outline
        cv2.rectangle(annotated_frame, (10, 10), (w - 10, 35), (20, 20, 26), -1)
        cv2.rectangle(annotated_frame, (10, 10), (w - 10, 35), (80, 80, 100), 1)
        
        cv2.putText(
            annotated_frame, f"TRACKING STATUS: {quality}", (20, 27),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, quality_color, 1, cv2.LINE_AA
        )
        
        # Hand Centers buffer
        centers = []
        
        for hand in hands_data:
            # Bounding box
            xmin, ymin, xmax, ymax = hand["bbox"]
            label = hand["label"]
            score = hand["score"]
            
            # Use futuristic green/cyan styling for dark dashboard feel
            color = (0, 255, 102) if label == "Right" else (255, 0, 127)
            
            # Bounding box corner-style draw
            length = 20
            thickness = 3
            cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), color, 1)
            # Corner accents
            cv2.line(annotated_frame, (xmin, ymin), (xmin + length, ymin), color, thickness)
            cv2.line(annotated_frame, (xmin, ymin), (xmin, ymin + length), color, thickness)
            cv2.line(annotated_frame, (xmax, ymin), (xmax - length, ymin), color, thickness)
            cv2.line(annotated_frame, (xmax, ymin), (xmax, ymin + length), color, thickness)
            cv2.line(annotated_frame, (xmin, ymax), (xmin + length, ymax), color, thickness)
            cv2.line(annotated_frame, (xmin, ymax), (xmin, ymax - length), color, thickness)
            cv2.line(annotated_frame, (xmax, ymax), (xmax - length, ymax), color, thickness)
            cv2.line(annotated_frame, (xmax, ymax), (xmax, ymax - length), color, thickness)

            # Draw Hand skeleton using MediaPipe drawing utils
            self.mp_drawing.draw_landmarks(
                annotated_frame,
                hand["raw_landmarks"],
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )
            
            # Calculate hand center
            cx, cy = get_hand_center(hand["landmarks"])
            cx_int, cy_int = int(cx), int(cy)
            centers.append((cx, cy))
            
            # Draw glowing center point
            cv2.circle(annotated_frame, (cx_int, cy_int), 8, color, -1)
            cv2.circle(annotated_frame, (cx_int, cy_int), 10, (255, 255, 255), 1)
            
            # Label
            txt = f"{label} ({int(score * 100)}%)"
            cv2.putText(
                annotated_frame, txt, (xmin, ymin - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA
            )
            
        # Draw steering vectors if two hands are tracked
        if len(centers) == 2:
            # Sort visual left to right
            centers_sorted = sorted(centers, key=lambda p: p[0])
            c1, c2 = centers_sorted[0], centers_sorted[1]
            p1 = (int(c1[0]), int(c1[1]))
            p2 = (int(c2[0]), int(c2[1]))
            
            # Connecting Vector Line
            cv2.line(annotated_frame, p1, p2, (0, 245, 255), 2, cv2.LINE_AA) # neon cyan
            
            # Draw Midpoint
            mx, my = int((p1[0] + p2[0]) / 2), int((p1[1] + p2[1]) / 2)
            cv2.circle(annotated_frame, (mx, my), 5, (255, 0, 127), -1) # neon pink
            
            # Draw tilt angle vector
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            angle = -math.degrees(math.atan2(dy, dx))
            cv2.putText(
                annotated_frame, f"STEER VECTOR: {angle:+.1f} deg", (mx - 75, my - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA
            )
            
        return annotated_frame

    def close(self) -> None:
        """Closes the MediaPipe Hands object."""
        self.hands.close()
