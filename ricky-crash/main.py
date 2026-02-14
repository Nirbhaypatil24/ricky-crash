#!/usr/bin/env python3
"""
Ricky Smart Autometer System
Main entry point for the application
Updated: Enabled MPU6050 Live Monitor
"""

import sys
import os
import signal

# Fix display issues BEFORE importing PyQt5
def setup_display():
    if 'SSH_CONNECTION' in os.environ and 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':10.0'
    elif 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'
    if 'QT_QPA_PLATFORM' not in os.environ:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'

setup_display()

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer, Qt, QUrl, pyqtSignal

try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    from PyQt5.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    print("⚠️ PyQt5.QtMultimedia not found.")
    MULTIMEDIA_AVAILABLE = False

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from frontend.ui_manager import RickyUI
from backend.gpio_manager import GPIOManager
from backend.gps_manager import GPSManager
from backend.fare_calculator import FareCalculator
from backend.mode_controller import ModeController
from backend.sos_system import SOSSystem
from backend.gsm_manager import GSMManager
from backend.crash_detector import CrashDetector

class VideoWindow(QWidget):
    """Fullscreen Video Window"""
    finished = pyqtSignal()
    def __init__(self, video_path):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.video_widget = QVideoWidget()
        layout.addWidget(self.video_widget)
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)
        self.player.mediaStatusChanged.connect(self._check_status)
        self.player.error.connect(self._handle_error)
        if os.path.exists(video_path):
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        else:
            QTimer.singleShot(100, self.finished.emit)
    def start(self): self.player.play()
    def _check_status(self, status):
        if status == QMediaPlayer.EndOfMedia or status == QMediaPlayer.InvalidMedia: self.finished.emit()
    def _handle_error(self): self.finished.emit()

class RickyAutometer:
    def __init__(self):
        try:
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("Ricky Autometer")
        except:
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
            self.app = QApplication(sys.argv)
        
        self.boot_complete = False
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.intro_path = os.path.join(base_path, 'assets', 'intro.mp4')
        self.loading_path = os.path.join(base_path, 'assets', 'load.mp4')

        # --- Initialize Backend ---
        self.gpio_manager = GPIOManager()
        self.gps_manager = GPSManager()
        self.fare_calculator = FareCalculator(self.gps_manager)
        self.mode_controller = ModeController(self.gpio_manager)
        
        # GSM (Check your port!)
        self.gsm_manager = GSMManager(port='/dev/ttyUSB0', emergency_number="+918390600361")
        
        self.sos_system = SOSSystem(self.gpio_manager, self.gps_manager, self.gsm_manager)
        
        # --- CRASH DETECTOR WITH MONITOR ---
        # Enable debug=True to see the live data in terminal
        self.crash_detector = CrashDetector(sensitivity_g=3.0, debug=True) 
        
        # --- Initialize Frontend ---
        self.ui = RickyUI(self.fare_calculator, self.mode_controller, self.sos_system)
        
        self.setup_connections()
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_connections(self):
        self.mode_controller.mode_changed.connect(self.ui.update_mode)
        self.mode_controller.mode_changed.connect(self.play_mode_transition)
        self.gpio_manager.passenger_changed.connect(self.ui.update_passenger)
        self.gpio_manager.passenger_changed.connect(self.fare_calculator.handle_passenger_change)
        self.sos_system.sos_status_changed.connect(self.ui.update_sos_status)
        self.fare_calculator.fare_updated.connect(self.ui.update_fares)
        
        # Connect Crash Detector
        self.crash_detector.crash_detected.connect(self.sos_system.handle_crash_trigger)
       # Connect Live Graph Data
        self.crash_detector.live_data.connect(self.ui.update_graph_data)


    def play_mode_transition(self, mode_name):
        if self.boot_complete and MULTIMEDIA_AVAILABLE and os.path.exists(self.loading_path):
            if hasattr(self, 'loading_window') and self.loading_window.isVisible():
                self.loading_window.close()
            self.loading_window = VideoWindow(self.loading_path)
            self.loading_window.finished.connect(self.loading_window.close)
            self.loading_window.finished.connect(self.loading_window.deleteLater)
            self.loading_window.start()

    def run(self):
        # Start all services
        self.gpio_manager.start()
        self.gps_manager.start()
        self.fare_calculator.start()
        self.mode_controller.start()
        self.sos_system.start()
        self.crash_detector.start() # Start crash monitoring
        
        if MULTIMEDIA_AVAILABLE and os.path.exists(self.intro_path):
            self.boot_window = VideoWindow(self.intro_path)
            self.boot_window.finished.connect(self.finish_boot_sequence)
            self.boot_window.start()
        else:
            self.finish_boot_sequence()
        return self.app.exec_()

    def finish_boot_sequence(self):
        if hasattr(self, 'boot_window'): self.boot_window.close()
        self.ui.showFullScreen()
        QTimer.singleShot(2000, lambda: setattr(self, 'boot_complete', True))

    def signal_handler(self, signum, frame):
        self.shutdown()
        sys.exit(0)

    def shutdown(self):
        try:
            self.fare_calculator.stop()
            self.gps_manager.stop()
            self.sos_system.stop()
            self.mode_controller.stop()
            self.crash_detector.stop() 
            self.gpio_manager.cleanup()
            self.gsm_manager.close()
        except: pass

def main():
    print("🚗 RICKY SMART AUTOMETER SYSTEM")
    autometer = RickyAutometer()
    return autometer.run()

if __name__ == "__main__":
    sys.exit(main())
