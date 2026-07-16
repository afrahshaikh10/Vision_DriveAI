import time
import math
from typing import List, Tuple, Dict, Any, Optional
from utils.logger import logger
from utils.db import db

class SessionAnalyticsTracker:
    """Tracks live driving telemetry to compute reaction times, steering smoothness, lane discipline, and scores."""
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.start_time = time.time()
        self.last_update_time = time.time()
        
        # Telemetry logs
        self.steering_history: List[float] = []
        self.throttle_ticks = 0
        self.brake_ticks = 0
        self.total_ticks = 0
        
        # Lane discipline tracking
        self.discipline_ticks = 0
        
        # Evasion/Obstacle DODGE tracking
        self.dodge_durations: List[float] = []
        self.spawn_times: Dict[int, float] = {}  # obstacle_id -> spawn_time
        
        # False gesture count
        self.false_gesture_count = 0

    def log_tick(self, steering_angle: float, accel: bool, brake: bool, player_x: float) -> None:
        """Called on every GUI frame to append tracking metrics."""
        self.total_ticks += 1
        self.steering_history.append(steering_angle)
        
        if accel:
            self.throttle_ticks += 1
        if brake:
            self.brake_ticks += 1
            
        # Lane Center Check: standard lanes are centered at 80, 140, 200, 260.
        # Player coordinates range from 50 to 310. Player width is 25, center is player_x + 12.5.
        p_center = player_x + 12.5
        lane_centers = [80.0, 140.0, 200.0, 260.0]
        min_offset = min(abs(p_center - lc) for lc in lane_centers)
        
        # If player center is within 18 pixels of any lane center, count as good discipline
        if min_offset <= 18.0:
            self.discipline_ticks += 1

    def log_obstacle_spawn(self, obstacle_id: int) -> None:
        """Logs the time an obstacle enters the screen."""
        self.spawn_times[obstacle_id] = time.time()

    def log_obstacle_dodge(self, obstacle_id: int) -> None:
        """Logs evasion time delta."""
        if obstacle_id in self.spawn_times:
            spawn_t = self.spawn_times.pop(obstacle_id)
            reaction_time = time.time() - spawn_t
            # Sanity bound: reaction time should be between 0.1s and 4.0s
            if 0.1 <= reaction_time <= 4.0:
                self.dodge_durations.append(reaction_time)

    def log_false_gesture(self) -> None:
        self.false_gesture_count += 1

    def compute_metrics(self) -> Dict[str, Any]:
        """Calculates final summaries for driving report database writes."""
        duration = int(time.time() - self.start_time)
        if duration <= 0:
            duration = 1
            
        # 1. Steering Smoothness (Derivative filter: 100 - average delta angle * factor)
        smoothness = 100.0
        if len(self.steering_history) > 1:
            diffs = [abs(self.steering_history[i] - self.steering_history[i-1]) for i in range(1, len(self.steering_history))]
            avg_diff = sum(diffs) / len(diffs)
            # Standard scale: average tremor deviation of 5 degrees per frame reduces smoothness
            smoothness = max(10.0, min(100.0, 100.0 - (avg_diff * 12.0)))
            
        # 2. Lane Discipline Score
        lane_discipline = 100.0
        if self.total_ticks > 0:
            lane_discipline = (self.discipline_ticks / self.total_ticks) * 100.0
            
        # 3. Reaction Time Evasion
        avg_reaction = 0.65  # Default baseline reaction time in seconds
        if self.dodge_durations:
            avg_reaction = sum(self.dodge_durations) / len(self.dodge_durations)
            
        # Map average reaction to score (0.2s is 100%, 1.5s is 10%)
        reaction_score = max(10.0, min(100.0, 100.0 - ((avg_reaction - 0.2) * 70.0)))
        
        # 4. Braking Efficiency (Ratio of throttle ticks to brake ticks)
        # Cruise efficiency is higher if they avoid locking brakes continuously
        efficiency = 100.0
        if self.throttle_ticks + self.brake_ticks > 0:
            efficiency = (self.throttle_ticks / (self.throttle_ticks + self.brake_ticks)) * 100.0
            # Clip between safe bounds
            efficiency = max(30.0, min(100.0, efficiency))
            
        # 5. Aggregate AI Driving Score (Weighted sum of telemetry categories)
        driving_score = int(
            (smoothness * 0.30) + 
            (lane_discipline * 0.25) + 
            (reaction_score * 0.25) + 
            (efficiency * 0.20)
        )
        # Deduct score slightly for false gestures (1 pt per false gesture, max 15 pt deduction)
        deduction = min(15, self.false_gesture_count)
        driving_score = max(5, driving_score - deduction)

        return {
            "duration": duration,
            "score": driving_score,
            "smoothness": smoothness,
            "reaction_time": avg_reaction,
            "lane_discipline": lane_discipline,
            "efficiency": efficiency,
            "false_gestures": self.false_gesture_count
        }

    def save_session_to_db(self, score_total: int, current_weather: str = "day", user_id: int = 1) -> Dict[str, Any]:
        """Saves telemetry aggregates to SQLite database and unlocks achievements."""
        metrics = self.compute_metrics()
        
        db.save_session(
            duration=metrics["duration"],
            score=score_total,  # Save the actual arcade high score
            smoothness=metrics["smoothness"],
            reaction_time=metrics["reaction_time"],
            lane_discipline=metrics["lane_discipline"],
            efficiency=metrics["efficiency"],
            false_gestures=metrics["false_gestures"],
            user_id=user_id
        )
        
        # Check and unlock achievements
        unlocked_list = []
        
        if metrics["duration"] >= 120:
            if db.unlock_achievement("Perfect Driver"):
                unlocked_list.append("Perfect Driver")
                
        if self.throttle_ticks > 0 and self.brake_ticks > 0:
            if db.unlock_achievement("Gesture Master"):
                unlocked_list.append("Gesture Master")
                
        if metrics["smoothness"] >= 90.0:
            if db.unlock_achievement("Smooth Operator"):
                unlocked_list.append("Smooth Operator")
                
        if metrics["efficiency"] >= 95.0:
            if db.unlock_achievement("Safe Driver"):
                unlocked_list.append("Safe Driver")
                
        if current_weather == "night":
            if db.unlock_achievement("Night Rider"):
                unlocked_list.append("Night Rider")
                
        if len(self.dodge_durations) >= 15:
            if db.unlock_achievement("Precision King"):
                unlocked_list.append("Precision King")
                
        metrics["unlocked_achievements"] = unlocked_list
        return metrics

# Global tracker instance
analytics_tracker = SessionAnalyticsTracker()
