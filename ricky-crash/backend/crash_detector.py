"""
Crash Detector - Monitors MPU6050 for sudden impacts
Updated: Emits live data for Graphing
"""

import time
import math
import threading
from PyQt5.QtCore import QObject, pyqtSignal

# Try importing SMBus for I2C communication
try:
    from smbus2 import SMBus
    I2C_AVAILABLE = True
except ImportError:
    try:
        from smbus import SMBus
        I2C_AVAILABLE = True
    except ImportError:
        print("⚠️ SMBus not found. Crash detection running in Simulation Mode.")
        I2C_AVAILABLE = False

class CrashDetector(QObject):
    crash_detected = pyqtSignal()  # Signal emitted on crash
    live_data = pyqtSignal(float)  # NEW: Signal for live graph (G-Force)

    # MPU6050 Registers
    PWR_MGMT_1 = 0x6B
    ACCEL_CONFIG = 0x1C
    ACCEL_XOUT_H = 0x3B
    DEVICE_ADDRESS = 0x68

    def __init__(self, sensitivity_g=3.0, debug=False):
        super().__init__()
        self.bus = None
        self.running = False
        self.sensitivity_threshold = sensitivity_g
        self.debug = debug
        self.interrupt_pin = 4
        
        if I2C_AVAILABLE:
            self.setup_mpu()

    def setup_mpu(self):
        try:
            self.bus = SMBus(1)
            self.bus.write_byte_data(self.DEVICE_ADDRESS, self.PWR_MGMT_1, 0)
            self.bus.write_byte_data(self.DEVICE_ADDRESS, self.ACCEL_CONFIG, 0x18)
            print(f"✅ MPU6050 Initialized (Threshold: {self.sensitivity_threshold}G)")
        except Exception as e:
            print(f"❌ MPU6050 Init Error: {e}")
            self.bus = None

    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _read_raw_data(self, addr):
        high = self.bus.read_byte_data(self.DEVICE_ADDRESS, addr)
        low = self.bus.read_byte_data(self.DEVICE_ADDRESS, addr + 1)
        value = (high << 8) | low
        if value > 32768: value = value - 65536
        return value

    def _monitor_loop(self):
        print("🛡️ Crash Monitor Running...")
        scale_divider = 2048.0 
        
        while self.running:
            try:
                total_g = 1.0 # Default gravity
                
                if self.bus:
                    acc_x = self._read_raw_data(self.ACCEL_XOUT_H)
                    acc_y = self._read_raw_data(self.ACCEL_XOUT_H + 2)
                    acc_z = self._read_raw_data(self.ACCEL_XOUT_H + 4)

                    gx = acc_x / scale_divider
                    gy = acc_y / scale_divider
                    gz = acc_z / scale_divider

                    total_g = math.sqrt(gx**2 + gy**2 + gz**2)

                    # Check for Crash
                    if total_g > self.sensitivity_threshold:
                        print(f"💥 CRASH: {total_g:.2f}G")
                        self.crash_detected.emit()
                        time.sleep(10) # Debounce
                else:
                    # Simulation Mode: Random noise around 1.0G
                    import random
                    total_g = 1.0 + (random.uniform(-0.1, 0.1))

                # Emit Live Data for Graph (Throttle to ~20Hz)
                self.live_data.emit(total_g)
                time.sleep(0.05)

            except Exception as e:
                # print(f"⚠️ MPU Error: {e}") 
                time.sleep(1)
