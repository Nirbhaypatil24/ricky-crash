"""
SOS System - Manages emergency alerts and responses
Updated: Fixes "Release to Deactivate" bug. Now locks until clicked again.
"""

import threading
import time
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class SOSSystem(QObject):
    sos_status_changed = pyqtSignal(str)
    sos_activated = pyqtSignal(dict)
    sos_deactivated = pyqtSignal()
    
    def __init__(self, gpio_manager, gps_manager=None, gsm_manager=None):
        super().__init__()
        self.gpio_manager = gpio_manager
        self.gps_manager = gps_manager
        self.gsm_manager = gsm_manager
        
        self.sos_active = False
        self.countdown_active = False
        self.countdown_thread = None
        self.ignore_release = False  # <--- NEW: Prevents immediate deactivation
        
        print("🚨 SOS System initialized")

    def start(self):
        self.gpio_manager.sos_button_pressed.connect(self.handle_sos_button_press)
        self.gpio_manager.sos_button_released.connect(self.handle_sos_button_release)
        print("🚨 SOS System started")

    def handle_sos_button_press(self):
        # Only start countdown if not already active and not already counting
        if not self.countdown_active and not self.sos_active:
            self.countdown_active = True
            self.countdown_thread = threading.Thread(
                target=self._countdown_loop, daemon=True
            )
            self.countdown_thread.start()
            print("🚨 SOS button pressed - starting countdown")

    def handle_sos_button_release(self):
        if self.countdown_active:
            # Button released early -> Cancel Countdown
            self.countdown_active = False
            self.sos_status_changed.emit("SOS Cancelled - Normal")
            print("✅ SOS cancelled - button released early")
        
        elif self.sos_active:
            # Button released while active
            if self.ignore_release:
                # If this release is from the initial HOLD, ignore it so we stay locked
                self.ignore_release = False
                print("🔒 SOS Locked (Initial release ignored)")
            else:
                # If this is a NEW click, deactivate
                print("🔘 Button clicked while active -> Deactivating SOS")
                self.deactivate_sos()

    def _countdown_loop(self):
        for i in range(5, 0, -1):
            if not self.countdown_active:
                return
            # Emit countdown status for UI
            self.sos_status_changed.emit(f"SOS COUNTDOWN: {i}")
            print(f"🚨 SOS COUNTDOWN: {i}")
            time.sleep(1)
        
        if self.countdown_active:
            # Countdown finished naturally (user held button)
            self.activate_sos(source="SOS_BUTTON")
            self.countdown_active = False

    def handle_crash_trigger(self):
        """Called immediately when crash is detected (No countdown)"""
        if not self.sos_active:
            print("💥 CRASH SIGNAL RECEIVED - ACTIVATING SOS IMMEDIATELY")
            self.activate_sos(source="CRASH_SENSOR")

    def activate_sos(self, source="SOS_BUTTON"):
        self.sos_active = True
        
        # If activated by button hold, we must ignore the subsequent release
        if source == "SOS_BUTTON":
            self.ignore_release = True
            
        activation_time = datetime.now()
        current_loc = None
        if self.gps_manager:
            current_loc = self.gps_manager.get_location()

        sos_data = {
            'activation_time': activation_time,
            'timestamp': activation_time.isoformat(),
            'location': current_loc,
            'status': 'ACTIVE',
            'type': source
        }
        
        # Update UI text
        if source == "CRASH_SENSOR":
            self.sos_status_changed.emit("💥 CRASH DETECTED! SOS ACTIVE 💥")
        else:
            self.sos_status_changed.emit("🚨 SOS ACTIVATED! 🚨")
            
        self.sos_activated.emit(sos_data)
        
        # Trigger GSM
        if self.gsm_manager:
            self.gsm_manager.send_sos_sms(current_loc, alert_type=source)
        
        print(f"🚨 EMERGENCY ACTIVATED ({source})")

    def deactivate_sos(self):
        if self.sos_active:
            self.sos_active = False
            self.ignore_release = False
            self.sos_status_changed.emit("✅ SOS Deactivated - Normal")
            self.sos_deactivated.emit()
            print("✅ SOS DEACTIVATED")

    def stop(self):
        self.countdown_active = False
        self.deactivate_sos()
