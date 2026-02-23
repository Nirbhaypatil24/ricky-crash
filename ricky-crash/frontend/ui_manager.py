"""
UI Manager - Ricky Theme (Split Screen Layout)
Updated: Added Countdown Animation & SOS Locking Logic
"""

import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QStackedWidget, QLabel, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QColor

from .sharing_mode import SharingModeWidget
from .private_mode import PrivateModeWidget
from .ads_display import AdsDisplayWidget
from .graph_widget import SensorGraphWidget 

# Theme Constants
THEME_BG = "#000000"
THEME_ACCENT = "#FFD700"
THEME_TEXT = "#FFFFFF"
THEME_DANGER = "#FF3B30"
THEME_WARNING = "#FF9500"  # Orange for Countdown
THEME_SUCCESS = "#34C759"
THEME_CARD_BG = "#1C1C1E"

class SOSStatusWidget(QFrame):
    """Compact SOS Status Bar with Countdown Animation"""
    def __init__(self):
        super().__init__()
        self.flash_timer = QTimer()
        self.flash_timer.timeout.connect(self._flash_tick)
        self.flash_state = False
        self.flash_color = THEME_DANGER # Default Red
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedHeight(80)
        self.set_normal_style()
        layout = QHBoxLayout(self)
        
        self.led = QLabel()
        self.led.setFixedSize(24, 24)
        self.led.setStyleSheet(f"background-color: {THEME_SUCCESS}; border-radius: 12px;")
        
        info_layout = QVBoxLayout()
        self.main_lbl = QLabel("SYSTEM NOMINAL")
        self.main_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        self.main_lbl.setStyleSheet(f"color: {THEME_SUCCESS};")
        
        self.sub_lbl = QLabel("SOS READY")
        self.sub_lbl.setStyleSheet("color: #666;")
        
        info_layout.addWidget(self.main_lbl)
        info_layout.addWidget(self.sub_lbl)
        
        layout.addWidget(self.led)
        layout.addLayout(info_layout)
        layout.addStretch()

    def set_normal_style(self):
        self.setStyleSheet(f"background-color: {THEME_CARD_BG}; border-radius: 10px; border: 1px solid #333;")

    def _flash_tick(self):
        self.flash_state = not self.flash_state
        if self.flash_state:
            self.setStyleSheet(f"background-color: {self.flash_color}; border-radius: 10px;")
            self.main_lbl.setStyleSheet("color: white;")
        else:
            self.setStyleSheet(f"background-color: #FFF; border-radius: 10px;")
            self.main_lbl.setStyleSheet(f"color: {self.flash_color};")

    def update_status(self, status):
        status_upper = status.upper()
        
        # 1. CRASH or ACTIVE (Red Flash)
        if "CRASH" in status_upper or "ACTIVATED" in status_upper:
            self.flash_color = THEME_DANGER
            self.flash_timer.start(200 if "CRASH" in status_upper else 500)
            self.main_lbl.setText(status)
            self.sub_lbl.setText("EMERGENCY MODE")
            
        # 2. COUNTDOWN (Orange Flash)
        elif "COUNTDOWN" in status_upper:
            self.flash_color = THEME_WARNING
            self.flash_timer.start(500)
            self.main_lbl.setText(status)
            self.sub_lbl.setText("HOLD TO TRIGGER")
            
        # 3. NORMAL (Reset)
        elif "NORMAL" in status_upper:
            self.flash_timer.stop()
            self.set_normal_style()
            self.main_lbl.setStyleSheet(f"color: {THEME_SUCCESS};")
            self.main_lbl.setText("SYSTEM NOMINAL")
            self.sub_lbl.setText("SOS READY")
            self.led.setStyleSheet(f"background-color: {THEME_SUCCESS}; border-radius: 12px;")
        
        else:
            self.main_lbl.setText(status)

class RickyUI(QMainWindow):
    def __init__(self, fare_calculator, mode_controller, sos_system):
        super().__init__()
        self.fare_calculator = fare_calculator
        self.mode_controller = mode_controller
        self.sos_system = sos_system
        self.gps_manager = fare_calculator.gps_manager
        
        self.current_mode = "For Hire"
        self.setup_ui()
        self.setup_timers()
        self.setup_connections()

    # ... [Keep setup_ui, create_placeholder, update_graph_data, setup_connections as they were] ...
    # (Only repeating essential parts to save space, assuming previous setup_ui is present)
    def setup_ui(self):
        self.setWindowTitle("Ricky Smart Autometer")
        self.setGeometry(0, 0, 1024, 600)
        self.setStyleSheet(f"QMainWindow {{ background-color: {THEME_BG}; }} QLabel {{ color: {THEME_TEXT}; }}")
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        
        # Header
        self.header = QFrame()
        self.header.setFixedHeight(80)
        self.header.setStyleSheet(f"background-color: {THEME_BG}; border-bottom: 2px solid #333;")
        hl = QHBoxLayout(self.header)
        self.mode_lbl = QLabel("FOR HIRE")
        self.mode_lbl.setStyleSheet(f"color: {THEME_ACCENT}; font-size: 32px; font-weight: bold;")
        hl.addStretch(); hl.addWidget(self.mode_lbl)
        
        # Body
        body_container = QWidget()
        split = QHBoxLayout(body_container)
        
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        
        self.mode_stack = QStackedWidget()
        self.sharing_widget = SharingModeWidget()
        self.private_widget = PrivateModeWidget()
        self.for_hire_widget = self.create_placeholder("🚕 FOR HIRE", "Ready")
        self.waiting_widget = self.create_placeholder("⏸️ WAITING", "Break")
        
        self.mode_stack.addWidget(self.sharing_widget)
        self.mode_stack.addWidget(self.private_widget)
        self.mode_stack.addWidget(self.for_hire_widget)
        self.mode_stack.addWidget(self.waiting_widget)
        
        self.sos_widget = SOSStatusWidget()
        
        left_layout.addWidget(self.mode_stack, 1)
        left_layout.addWidget(self.sos_widget, 0)
        
        self.ads_widget = AdsDisplayWidget()
        split.addWidget(self.left_panel, 55)
        split.addWidget(self.ads_widget, 45)
        
        main_layout.addWidget(self.header)
        main_layout.addWidget(body_container)
        self.update_mode("For Hire")

    # ... [Keep keyPressEvent, create_placeholder, update_graph_data etc.] ...
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_1: self.update_mode("Private")
        elif event.key() == Qt.Key_2: self.update_mode("Sharing")
        elif event.key() == Qt.Key_3: self.update_mode("For Hire")
        elif event.key() == Qt.Key_4: self.update_mode("Waiting")
        elif event.key() == Qt.Key_Q: self.close()

    def create_placeholder(self, t, s):
        w = QWidget(); l = QVBoxLayout(w); l.setAlignment(Qt.AlignCenter)
        tl = QLabel(t); tl.setStyleSheet("color: #34C759; font-size: 48px; font-weight: bold;")
        sl = QLabel(s); sl.setStyleSheet("color: #8E8E93; font-size: 20px;")
        l.addWidget(tl); l.addWidget(sl)
        if "HIRE" in t:
            self.for_hire_subtitle = sl
            l.addSpacing(30)
            self.sensor_graph = SensorGraphWidget()
            l.addWidget(self.sensor_graph)
        return w

    @pyqtSlot(float)
    def update_graph_data(self, g):
        if hasattr(self, 'sensor_graph'): self.sensor_graph.update_value(g)

    def setup_connections(self):
        self.gps_manager.speed_updated.connect(lambda s: setattr(self, 'current_speed', s))
        self.fare_calculator.distance_updated.connect(self._on_dist)
        self.gps_manager.location_updated.connect(self.ads_widget.map_widget.update_gps_location)
        self.ads_widget.map_widget.location_resolved.connect(self.private_widget.update_location_text)

    def setup_timers(self):
        self.tmr = QTimer()
        self.tmr.timeout.connect(self.gps_update)
        self.tmr.start(1000)

    @pyqtSlot(str)
    def update_mode(self, mode):
        self.current_mode = mode
        self.mode_lbl.setText(mode.upper())
        m = {"Sharing": 0, "Private": 1, "For Hire": 2, "Waiting": 3}
        if mode in m: self.mode_stack.setCurrentIndex(m[mode])
        if mode == "Private": self.fare_calculator.start_private_mode()
        else: self.fare_calculator.stop_private_mode()

    @pyqtSlot(float)
    def _on_dist(self, d):
        if self.current_mode=="Private": self.private_widget.update_distance(d)

    @pyqtSlot(int, bool)
    def update_passenger(self, p, o):
        if self.current_mode=="Sharing": self.sharing_widget.update_passenger(p, o)
    
    @pyqtSlot(int, float)
    def update_fares(self, p, f):
        if self.current_mode=="Sharing": self.sharing_widget.update_fare(p, f)
        elif self.current_mode=="Private": self.private_widget.update_fare(f)

    # --- UPDATED SOS SLOT ---
    @pyqtSlot(str)
    def update_sos_status(self, s):
        self.sos_widget.update_status(s)
        
        # Only lock map if fully ACTIVATED or CRASH (ignore Countdown)
        is_locked = "ACTIVATED" in s or "CRASH" in s or "ACTIVE" in s
        
        if is_locked:
            self.header.hide()
            self.left_panel.hide()
            self.ads_widget.set_sos_mode(True)
        else:
            # During Countdown or Normal: Show UI normally
            self.header.show()
            self.left_panel.show()
            self.ads_widget.set_sos_mode(False)

    def gps_update(self):
        s = self.fare_calculator.get_real_time_stats()
        if self.current_mode == "Sharing":
            self.sharing_widget.update_total_info(s['total_distance'], int(s['trip_duration']))
            for i in range(3):
                if self.fare_calculator.passengers[i]['onboard']:
                    self.sharing_widget.update_card_live_data(i, self.fare_calculator.passengers[i]['total_distance'])
        elif self.current_mode == "For Hire":
            if hasattr(self, 'for_hire_subtitle'):
                self.for_hire_subtitle.setText(f"GPS Locked • {s['current_speed']:.1f} km/h")
