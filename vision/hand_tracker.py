import cv2
import os
import math
import urllib.request
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from utils.logger import logger
import mediapipe as mp

# Define MediaPipe Hand skeleton connection pairs
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index finger
    (5, 9), (9, 10), (10, 11), (11, 12),    # Middle finger
    (9, 13), (13, 14), (14, 15), (15, 16),  # Ring finger
    (13, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (0, 17), (5, 9)                         # Palm connections
]

class HandTracker:
    """Uses MediaPipe to track hands, extract landmarks, labels, and bounding boxes.
    Supports both legacy mediapipe.solutions and modern mediapipe.tasks HandLandmarker for Python 3.13+.
    """
    def __init__(self, min_detection_confidence: float = 0.7, min_tracking_confidence: float = 0.7):
        self.use_legacy = hasattr(mp, "solutions") and hasattr(mp.solutions, "hands")
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        
        if self.use_legacy:
            logger.info("Initializing HandTracker with legacy mediapipe.solutions...")
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
            
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
        else:
            logger.info("Initializing HandTracker with modern MediaPipe Tasks API (HandLandmarker)...")
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            # Ensure model file exists locally
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
            os.makedirs(models_dir, exist_ok=True)
            model_path = os.path.join(models_dir, "hand_landmarker.task")

            if not os.path.exists(model_path):
                # Also check root directory
                root_model_path = os.path.join(os.getcwd(), "hand_landmarker.task")
                if os.path.exists(root_model_path):
                    model_path = root_model_path
                else:
                    logger.info(f"Downloading hand_landmarker.task model to {model_path}...")
                    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
                    try:
                        urllib.request.urlretrieve(url, model_path)
                        logger.info("Model download complete.")
                    except Exception as e:
                        logger.error(f"Failed to download hand_landmarker.task: {e}")
                        raise

            self.model_path = model_path
            self._init_tasks_landmarker(min_detection_confidence, min_tracking_confidence)

    def _init_tasks_landmarker(self, detection_conf: float, tracking_conf: float) -> None:
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=self.model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=detection_conf,
            min_hand_presence_confidence=tracking_conf,
            min_tracking_confidence=tracking_conf
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def set_confidences(self, detection_conf: float, tracking_conf: float) -> None:
        """Allows dynamic adjustment of detection and tracking confidences."""
        self.min_detection_confidence = detection_conf
        self.min_tracking_confidence = tracking_conf

        if self.use_legacy:
            self.hands.close()
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=detection_conf,
                min_tracking_confidence=tracking_conf
            )
        else:
            if hasattr(self, "landmarker") and self.landmarker:
                self.landmarker.close()
            self._init_tasks_landmarker(detection_conf, tracking_conf)

    def process_frame(self, frame: cv2.Mat) -> Tuple[cv2.Mat, List[Dict[str, Any]]]:
        """
        Processes a BGR video frame to detect hands.
        Returns:
            - The original frame
            - A list of dicts containing parsed hand details.
        """
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands_data = []

        if self.use_legacy:
            results = self.hands.process(rgb_frame)
            if results.multi_hand_landmarks and results.multi_handedness:
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    handedness = results.multi_handedness[idx]
                    label = handedness.classification[0].label  # "Left" or "Right"
                    score = handedness.classification[0].score

                    landmarks_px = []
                    landmarks_z = []
                    x_coords, y_coords = [], []

                    for lm in hand_landmarks.landmark:
                        px_x = int(lm.x * w)
                        px_y = int(lm.y * h)
                        landmarks_px.append((px_x, px_y))
                        landmarks_z.append(lm.z)
                        x_coords.append(px_x)
                        y_coords.append(px_y)

                    xmin, xmax = min(x_coords), max(x_coords)
                    ymin, ymax = min(y_coords), max(y_coords)
                    padding = 15
                    xmin = max(0, xmin - padding)
                    ymin = max(0, ymin - padding)
                    xmax = min(w, xmax + padding)
                    ymax = min(h, ymax + padding)

                    hands_data.append({
                        "label": label,
                        "score": score,
                        "landmarks": landmarks_px,
                        "landmarks_z": landmarks_z,
                        "bbox": (xmin, ymin, xmax, ymax),
                        "raw_landmarks": hand_landmarks
                    })
        else:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = self.landmarker.detect(mp_image)

            if results.hand_landmarks and results.handedness:
                for idx, landmarks_list in enumerate(results.hand_landmarks):
                    handedness_cat = results.handedness[idx][0]
                    # Tasks API handedness returns "Left" or "Right"
                    label = handedness_cat.category_name or handedness_cat.display_name or "Right"
                    score = handedness_cat.score

                    landmarks_px = []
                    landmarks_z = []
                    x_coords, y_coords = [], []

                    for lm in landmarks_list:
                        px_x = int(lm.x * w)
                        px_y = int(lm.y * h)
                        landmarks_px.append((px_x, px_y))
                        landmarks_z.append(lm.z)
                        x_coords.append(px_x)
                        y_coords.append(px_y)

                    xmin, xmax = min(x_coords), max(x_coords)
                    ymin, ymax = min(y_coords), max(y_coords)
                    padding = 15
                    xmin = max(0, xmin - padding)
                    ymin = max(0, ymin - padding)
                    xmax = min(w, xmax + padding)
                    ymax = min(h, ymax + padding)

                    hands_data.append({
                        "label": label,
                        "score": score,
                        "landmarks": landmarks_px,
                        "landmarks_z": landmarks_z,
                        "bbox": (xmin, ymin, xmax, ymax),
                        "raw_landmarks": landmarks_list
                    })

        return frame, hands_data

    def draw_overlays(self, frame: cv2.Mat, hands_data: List[Dict[str, Any]]) -> cv2.Mat:
        """Draws skeletons, landmarks, labels, bounding boxes, hand centers, and steering vectors."""
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
            xmin, ymin, xmax, ymax = hand["bbox"]
            label = hand["label"]
            score = hand["score"]
            landmarks = hand["landmarks"]
            
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

            # Draw Hand skeleton
            if self.use_legacy and hasattr(self, "mp_drawing"):
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    hand["raw_landmarks"],
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
            else:
                # Custom high-contrast landmark skeleton rendering
                for p1_idx, p2_idx in HAND_CONNECTIONS:
                    if p1_idx < len(landmarks) and p2_idx < len(landmarks):
                        cv2.line(annotated_frame, landmarks[p1_idx], landmarks[p2_idx], color, 2, cv2.LINE_AA)

                for px, py in landmarks:
                    cv2.circle(annotated_frame, (px, py), 4, (255, 255, 255), -1)
                    cv2.circle(annotated_frame, (px, py), 5, color, 1, cv2.LINE_AA)
            
            # Calculate hand center
            cx, cy = get_hand_center(landmarks)
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
        """Closes the MediaPipe object."""
        if self.use_legacy and hasattr(self, "hands"):
            self.hands.close()
        elif hasattr(self, "landmarker") and self.landmarker:
            self.landmarker.close()

