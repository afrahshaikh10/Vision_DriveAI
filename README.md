# VisionDrive AI 🏎️👋

VisionDrive AI is a real-time Computer Vision desktop application that turns your webcam into a virtual steering wheel and pedal set. Using your hand gestures, you can control the steering, acceleration, and braking of any racing game.

---

## 🌟 Features

- **Asynchronous Dual Hand Tracking**: Fast, real-time skeletal tracking of both hands via MediaPipe.
- **Dynamic Vector Steering**: Calculates steering angle using the vector connecting your left and right hands.
- **Gesture Control System**:
  - ✊ **Accelerate**: Closed fist on any hand (simulating steering grip), or raise your right hand.
  - 👍 **Nitro Boost**: Thumbs-up gesture (triggers Shift key by default) to keep increasing speed up to 140 MPH.
  - 🖐️ **Brake**: Open palm on any hand (simulating letting go), or bring hands close together.
  - 👎 **Handbrake**: Thumbs-down gesture (triggers spacebar by default).
- **Steering Smoothing**: Multi-frame moving average filter to eliminate hand jitters.
- **Interactive Gaming HUD**:
  - Vector steering wheel overlay that rotates in real-time.
  - Live steering angle trend graph.
  - Session timer and active gesture log.
- **Multi-step Calibration Wizard**: Step-by-step guidance to calibrate neutral hand posture, maximum left turn, and maximum right turn. Saves directly to `config.json`.
- **Keyboard Output Emulation**: Emulates keyboard keystrokes via `pynput` with custom bindings, prevention of duplicate repeat key events, and safety decay releases.

---

## 📁 Project Structure

```text
VisionDriveAI/
├── main.py                # Main application entry point and GUI worker thread loop
├── config.json            # Dynamic configuration profile
├── requirements.txt       # Dependencies list
├── README.md              # Documentation
├── controllers/
│   └── keyboard_controller.py  # Emulates virtual keyboard inputs
├── ui/
│   ├── dashboard.py       # HUD widgets, animated wheel canvas, graph & logs
│   └── settings.py        # Settings sidebar frame containing widgets
├── utils/
│   ├── config.py          # JSON config loader/saver
│   ├── logger.py          # Log utility writing to console and visiondrive.log
│   └── math_utils.py      # Calculations, interpolation and smoothing window
└── vision/
    ├── camera.py          # Threaded camera feed grabber
    ├── hand_tracker.py    # MediaPipe hand tracker parser and drawing utilities
    ├── gesture_detector.py # Gesture classification rules
    ├── steering.py        # Hand vector math and angular states
    └── calibration.py     # Multi-stage wizard sampler
```

---

## 🛠️ Installation & Setup

1. **System Requirements**:
   - Python 3.12+
   - A standard USB or Integrated Webcam.
   - Operating System: Windows (recommended for PyAutoGUI/pynput DirectInput compatibility).

2. **Install Dependencies**:
   Open a terminal in the project directory and run:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage Instructions

1. **Run the Application**:
   ```bash
   python main.py
   ```

2. **Configure Settings**:
   - Select your webcam from the **Active Camera Source** dropdown.
   - Adjust steering sensitivity, dead zone, or maximum frame rates.
   - Select key bindings for accelerate, brake, and steering.

3. **Calibrate (Recommended)**:
   - Click the **Run Calibration** button.
   - **Step 1 (Neutral)**: Place both hands flat, horizontally level, and click when ready. (Wizard automatically samples 15 frames).
   - **Step 2 (Left)**: Rotate your hands fully left (simulating a left turn) and wait.
   - **Step 3 (Right)**: Rotate your hands fully right (simulating a right turn) and wait.
   - Calibration values are saved automatically to `config.json`!

4. **Start Playing**:
   - Click **Start System**.
   - Open your favorite racing game (e.g., TrackMania, Need for Speed, Euro Truck Simulator).
   - *Note: If key presses are not detected in the game, run both the game and `main.py` as Administrator!*
