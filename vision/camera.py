import os
import cv2
import threading
import time
from typing import Tuple, Optional, List
from utils.logger import logger

class Camera:
    """Manages webcam access and frame acquisition using a dedicated background thread."""
    def __init__(self, camera_id: int = 0, width: int = 640, height: int = 480):
        self.camera_id = camera_id
        self.desired_width = width
        self.desired_height = height
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        
        # Performance metrics
        self.fps = 0.0
        self.frame_count = 0
        self.start_time = time.time()
        self.actual_width = 0
        self.actual_height = 0

    def start(self) -> bool:
        """Starts the background frame grabber thread."""
        if self.running:
            return True

        # Try starting with DirectShow backend for Windows stability
        self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            logger.warning(f"DirectShow camera initialization failed for index {self.camera_id}. Falling back to default backend...")
            self.cap = cv2.VideoCapture(self.camera_id)
            
        if not self.cap.isOpened():
            logger.error(f"Cannot open camera with ID {self.camera_id}")
            self.cap = None
            return False

        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.desired_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.desired_height)
        
        self.actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Camera started. Resolution set to: {self.actual_width}x{self.actual_height}")

        self.running = True
        self.frame = None
        self.frame_count = 0
        self.start_time = time.time()
        
        self.thread = threading.Thread(target=self._update, name="CameraThread", daemon=True)
        self.thread.start()
        return True

    def _update(self) -> None:
        """Internal loop to read frames in the background thread."""
        while self.running:
            if self.cap is None:
                break
                
            ret, frame = self.cap.read()
            if ret:
                # Store the frame thread-safely
                with self.lock:
                    self.frame = frame
                
                # Calculate FPS
                self.frame_count += 1
                now = time.time()
                elapsed = now - self.start_time
                if elapsed >= 1.0:
                    self.fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.start_time = now
            else:
                if not hasattr(self, "last_grab_warn") or time.time() - self.last_grab_warn > 5.0:
                    self.last_grab_warn = time.time()
                    logger.warning("Failed to grab camera frame")
                time.sleep(0.02)

    def get_frame(self) -> Optional[cv2.Mat]:
        """Returns the latest frame retrieved by the background thread."""
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            return None

    def stop(self) -> None:
        """Stops the camera thread and releases resources."""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
            
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        logger.info("Camera resources released.")

    def change_camera(self, camera_id: int) -> bool:
        """Dynamically switches camera sources."""
        logger.info(f"Switching camera to ID {camera_id}")
        self.stop()
        self.camera_id = camera_id
        return self.start()

    @staticmethod
    def get_available_cameras(max_to_test: int = 5) -> List[int]:
        """Helper to scan and find active camera indices on the system."""
        available = []
        for i in range(max_to_test):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
