import customtkinter as ctk
import csv
import json
import os
import time
from typing import Any, Dict, List
from utils.db import db
from utils.theme_manager import get_theme_colors

class AnalyticsScreen(ctk.CTkFrame):
    """Renders charts showing driver telemetry histories and exposes DB report exports."""
    def __init__(self, parent: Any, user_data: Dict[str, Any]):
        super().__init__(parent, fg_color="transparent")
        self.user_data = user_data
        
        self.setup_ui()

    def setup_ui(self) -> None:
        theme = self.user_data.get("active_theme", "cyberpunk")
        colors = get_theme_colors(theme)
        
        # Header Title
        header = ctk.CTkLabel(
            self,
            text="📊 TELEMETRY PERFORMANCE ANALYTICS",
            font=ctk.CTkFont(family="Outfit", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        header.pack(anchor="w", padx=20, pady=(20, 5))
        
        desc = ctk.CTkLabel(
            self,
            text="Detailed summaries of your driver lane tracking, gesture reactions, and speeds.",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        # Split pane
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        left_pan = ctk.CTkFrame(main_split, fg_color="transparent")
        left_pan.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_pan = ctk.CTkFrame(main_split, fg_color="transparent")
        right_pan.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Query sessions for user
        sessions = db.get_sessions(self.user_data["id"])
        total_runs = len(sessions)
        avg_score = 0
        max_score = 0
        avg_smoothness = 0.0
        
        if total_runs > 0:
            avg_score = int(sum(s["score"] for s in sessions) / total_runs)
            max_score = max(s["score"] for s in sessions)
            avg_smoothness = sum(s["smoothness"] for s in sessions) / total_runs
            
        left_title = ctk.CTkLabel(
            left_pan, text="📊 STATISTICAL AGGREGATES",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        left_title.pack(anchor="w", pady=(0, 10))
        
        card_grid = ctk.CTkFrame(left_pan, fg_color="transparent")
        card_grid.pack(fill="x", pady=5)
        card_grid.grid_columnconfigure((0, 1), weight=1)
        
        self._add_stat_card(card_grid, "TOTAL SIM RUNS", f"{total_runs}", 0, 0, colors["secondary"])
        self._add_stat_card(card_grid, "AVG ARCADE SCORE", f"{avg_score} pts", 0, 1, "#00FF66")
        self._add_stat_card(card_grid, "HIGH SCORE ACHIEVED", f"{max_score}", 1, 0, colors["accent"])
        self._add_stat_card(card_grid, "AVG STEER SMOOTHNESS", f"{int(avg_smoothness)}%", 1, 1, "#F1C40F")
        
        # EXPORTS panel
        export_box = ctk.CTkFrame(left_pan, fg_color="#0a0a0f", border_width=1, border_color="#1b1836", corner_radius=10)
        export_box.pack(fill="x", pady=(15, 0), ipady=10)
        
        export_lbl = ctk.CTkLabel(export_box, text="EXPORT DATABASE TELEMETRY", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="#888888")
        export_lbl.pack(pady=(8, 4))
        
        btn_frame = ctk.CTkFrame(export_box, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10)
        
        csv_btn = ctk.CTkButton(btn_frame, text="CSV REPORT", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#121216", border_width=1, border_color="#1b1836", hover_color="#00FF66", width=80, command=self.export_csv, cursor="hand2")
        csv_btn.pack(side="left", expand=True, padx=4, pady=5)
        
        json_btn = ctk.CTkButton(btn_frame, text="JSON EXPORT", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#121216", border_width=1, border_color="#1b1836", hover_color=colors["secondary"], width=80, command=self.export_json, cursor="hand2")
        json_btn.pack(side="left", expand=True, padx=4, pady=5)
        
        report_btn = ctk.CTkButton(btn_frame, text="TXT SUMMARY", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#121216", border_width=1, border_color="#1b1836", hover_color=colors["accent"], width=80, command=self.export_report, cursor="hand2")
        report_btn.pack(side="left", expand=True, padx=4, pady=5)
        
        self.status_lbl = ctk.CTkLabel(left_pan, text="", font=ctk.CTkFont(size=10), text_color="#00FF66")
        self.status_lbl.pack(pady=5)
        
        # Dynamic Neon Chart (Score history)
        right_title = ctk.CTkLabel(
            right_pan, text="📈 RUN SCORE HISTORY (NEON CHART)",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        right_title.pack(anchor="w", pady=(0, 10))
        
        chart_canvas = ctk.CTkCanvas(right_pan, bg="#0a0a0f", highlightthickness=1, highlightbackground="#1b1836")
        chart_canvas.pack(fill="both", expand=True)
        
        if total_runs == 0:
            chart_canvas.create_text(160, 100, text="NO telemetry logs found.\n\nComplete driving runs to populate score graph.", font=("Outfit", 10, "bold"), fill="#5a5a66", justify="center")
        else:
            history = list(reversed(sessions[:6]))
            num_bars = len(history)
            cw, ch = 300, 180
            
            chart_canvas.create_line(30, 20, 30, ch - 25, fill="#1b1836")
            chart_canvas.create_line(30, ch - 25, cw - 10, ch - 25, fill="#1b1836")
            
            max_val = max(100.0, max(s["score"] for s in history))
            dx = (cw - 50) / max(1, num_bars)
            
            theme_accent = colors["accent"]
            theme_border = colors["border"]
            
            for i, run in enumerate(history):
                x = 35 + i * dx
                val = run["score"]
                bar_h = (val / max_val) * (ch - 60)
                y1 = ch - 25 - bar_h
                y2 = ch - 25
                
                chart_canvas.create_rectangle(x + 5, y1, x + dx - 5, y2, fill=theme_accent, outline=theme_border, width=1.5)
                chart_canvas.create_text(x + dx/2, y1 - 10, text=f"{val}", font=("Consolas", 8, "bold"), fill="#FFFFFF")
                date_part = run["date_time"].split(" ")[1][:5]
                chart_canvas.create_text(x + dx/2, ch - 12, text=date_part, font=("Consolas", 8), fill="#888888")

    def _add_stat_card(self, parent: Any, title: str, value: str, row: int, col: int, color: str) -> None:
        card = ctk.CTkFrame(parent, fg_color="#0a0a0f", border_width=1, border_color="#1b1836", corner_radius=10, height=75)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        card.grid_propagate(False)
        
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9, weight="bold"), text_color="#5a5a66")
        lbl_title.pack(anchor="w", padx=10, pady=(6, 0))
        
        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(family="Outfit", size=13, weight="bold"), text_color=color)
        lbl_val.pack(anchor="w", padx=10, pady=(2, 6))

    def export_csv(self) -> None:
        sessions = db.get_sessions(self.user_data["id"])
        if not sessions:
            self.status_lbl.configure(text="No sessions to export.", text_color="#FF007F")
            return
        os.makedirs("exports", exist_ok=True)
        filepath = f"exports/driving_report_user_{self.user_data['id']}.csv"
        with open(filepath, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Session ID", "Timestamp", "Duration (sec)", "Arcade Score", "Smoothness", "Reaction Time (sec)", "Lane Discipline", "Efficiency", "False Gestures"])
            for s in sessions:
                writer.writerow([s["id"], s["date_time"], s["duration_sec"], s["score"], s["smoothness"], s["reaction_time_sec"], s["lane_discipline"], s["efficiency"], s["false_gestures_count"]])
        self.status_lbl.configure(text=f"EXPORT: CSV saved to {filepath}", text_color="#00FF66")

    def export_json(self) -> None:
        sessions = db.get_sessions(self.user_data["id"])
        if not sessions:
            self.status_lbl.configure(text="No sessions to export.", text_color="#FF007F")
            return
        os.makedirs("exports", exist_ok=True)
        filepath = f"exports/driving_report_user_{self.user_data['id']}.json"
        with open(filepath, mode="w") as f:
            json.dump(sessions, f, indent=4)
        self.status_lbl.configure(text=f"EXPORT: JSON saved to {filepath}", text_color="#00FF66")

    def export_report(self) -> None:
        sessions = db.get_sessions(self.user_data["id"])
        if not sessions:
            self.status_lbl.configure(text="No sessions to export.", text_color="#FF007F")
            return
        os.makedirs("exports", exist_ok=True)
        filepath = f"exports/driving_report_user_{self.user_data['id']}.txt"
        
        total_runs = len(sessions)
        avg_score = sum(s["score"] for s in sessions) / total_runs if total_runs > 0 else 0
        max_score = max(s["score"] for s in sessions) if total_runs > 0 else 0
        avg_smoothness = sum(s["smoothness"] for s in sessions) / total_runs if total_runs > 0 else 0
        
        with open(filepath, mode="w") as f:
            f.write("==================================================\n")
            f.write(f"           VISIONDRIVE AI USER REPORT             \n")
            f.write("==================================================\n\n")
            f.write(f"Player: {self.user_data.get('name', 'Driver')}\n")
            f.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Simulator Runs: {total_runs}\n")
            f.write(f"Average Driving Score: {avg_score:.1f}/100\n")
            f.write(f"Arcade High Score achieved: {max_score}\n")
            f.write(f"Average Steering Smoothness: {avg_smoothness:.1f}%\n\n")
            f.write("--------------------------------------------------\n")
            f.write("RECENT RUN DETAILS:\n")
            f.write("--------------------------------------------------\n")
            for s in sessions[:10]:
                f.write(f"Run #{s['id']} | Date: {s['date_time']} | Score: {s['score']} | Smoothness: {s['smoothness']:.1f}% | Efficiency: {s['efficiency']:.1f}%\n")
                
        self.status_lbl.configure(text=f"EXPORT: Text report saved to {filepath}", text_color="#00FF66")
