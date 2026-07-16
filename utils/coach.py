import time
import threading
import queue
import random
from typing import Optional, Tuple
from utils.logger import logger

# Thread-safe vocal playback queue
speech_queue = queue.Queue()
tts_engine = None

def tts_worker():
    global tts_engine
    try:
        import pyttsx3
        tts_engine = pyttsx3.init()
        # Set speech rate a bit faster for F1 race engineer vibe
        tts_engine.setProperty('rate', 165)
    except Exception as e:
        logger.warning(f"Voice Coach Audio disabled: pyttsx3 not available or failed: {e}")
        return
        
    while True:
        try:
            msg = speech_queue.get()
            if msg is None:
                break
            tts_engine.say(msg)
            tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"Voice Coach play error: {e}")
        finally:
            speech_queue.task_done()

# Start background speech thread
speech_thread = threading.Thread(target=tts_worker, name="VoiceCoachThread", daemon=True)
speech_thread.start()

class DrivingCoach:
    """Evaluates live steering derivatives, lane alignment, and brakes to output alerts."""
    def __init__(self):
        self.last_feedback_time = 0.0
        self.cooldown = 4.0  # seconds between speech feedbacks to avoid spam
        
        # Buffers for evaluation
        self.jitter_ticks = 0
        self.lane_alignment_ticks = 0
        
    def evaluate_tick(self, steering_angle: float, delta_angle: float, speed: float, player_x: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Analyzes telemetry and returns:
          - text_msg: Alert to display on screen (HUD)
          - speech_msg: Speech text to read in background
        """
        now = time.time()
        
        # 1. Steering Jitter Check
        if abs(delta_angle) > 9.0:
            self.jitter_ticks += 1
        else:
            self.jitter_ticks = max(0, self.jitter_ticks - 1)
            
        if self.jitter_ticks >= 20:  # held jittery steering for ~400ms
            self.jitter_ticks = 0
            if now - self.last_feedback_time >= self.cooldown:
                self.last_feedback_time = now
                return "⚠️ STABILIZE STEERING - RELAX GRIP!", "Relax your grip, stabilize steering."
                
        # 2. Perfect Lane Alignment Praise
        # Standard lane centers: 80, 140, 200, 260
        p_center = player_x + 12.5
        lane_centers = [80.0, 140.0, 200.0, 260.0]
        min_offset = min(abs(p_center - lc) for lc in lane_centers)
        is_aligned = min_offset <= 12.0
        
        if is_aligned and speed > 20.0:
            self.lane_alignment_ticks += 1
        else:
            self.lane_alignment_ticks = 0
            
        if self.lane_alignment_ticks >= 120:  # centered for ~2.5 seconds
            self.lane_alignment_ticks = 0
            if now - self.last_feedback_time >= self.cooldown:
                self.last_feedback_time = now
                return "🏆 PERFECT LANE DISCIPLINE!", "Excellent lane discipline."
                
        # 3. Overspeeding warning on curves
        if speed > 85.0 and abs(steering_angle) > 15.0:
            if now - self.last_feedback_time >= self.cooldown:
                self.last_feedback_time = now
                return "⚠️ SLOW DOWN ON TURNS!", "Slow down on turns."
                
        return None, None

    def trigger_dodge_feedback(self) -> Tuple[str, str]:
        """Called when obstacle is evaded."""
        self.last_feedback_time = time.time()
        feedbacks = [
            ("🔥 PERFECT EVASION!", "Nice dodge."),
            ("⚡ INCREDIBLE REFLEXES!", "Incredible reflexes!"),
            ("🚀 UNTOUCHABLE!", "You're untouchable!"),
            ("💎 SMOOTH EVASION!", "Beautifully avoided."),
            ("🎯 PRECISE DODGE!", "Precise dodge. Keep it up!"),
            ("⭐ GODLIKE REFLEXES!", "Godlike reflexes!"),
            ("🌟 ABSOLUTE CONTROL!", "Absolute control!"),
            ("🏎️ RACING PRO!", "Superb reaction time!"),
            ("⚡ INSTINCTIVE EVASION!", "Great reaction!"),
            ("🔥 FLAWLESS DODGE!", "Perfect evasion, nice job!")
        ]
        return random.choice(feedbacks)

    def trigger_crash_feedback(self) -> Tuple[str, str]:
        """Called when collision occurs."""
        self.last_feedback_time = time.time()
        return "💥 CRASH DETECTED - HEAVY COLLISION!", "Crash detected."

    def speak(self, phrase: str) -> None:
        """Enqueues phrase to speech thread."""
        speech_queue.put(phrase)

# Global Coach Instance
driving_coach = DrivingCoach()
