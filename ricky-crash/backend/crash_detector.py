"""
Crash Detector - Monitors MPU6050 for sudden impacts
Updated: Integrated Live CSV Logging to Desktop
"""

import time
import math
import threading
import os
import csv
from datetime import datetime
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
    live_data = pyqtSignal(float)  # Signal for live graph (G-Force)

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
        
        # MPU6050 Pins (Automatically mapped by SMBus(1)):
        # SDA -> GPIO 2
        # SCL -> GPIO 3
        self.interrupt_pin = 4  # GPIO 4 for INT (optional)
        
        # Setup CSV Log Path
        self.save_directory = os.path.expanduser("/home/ricky/Desktop/ricky-crash/mpulog")
        self.csv_filename = "mpu6050_log.csv"
        self.file_path = os.path.join(self.save_directory, self.csv_filename)
        
        if I2C_AVAILABLE:
            self.setup_mpu()

    def setup_mpu(self):
        try:
            self.bus = SMBus(1) # Hardware I2C Bus 1 (GPIO 2 & GPIO 3)
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
        if value > 32768: 
            value = value - 65536
        return value

    def _monitor_loop(self):
        print("🛡️ Crash Monitor Running (with CSV Logging)...")
        scale_divider = 2048.0 
        
        # --- Initialize CSV File ---
        csv_file = None
        writer = None
        try:
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)
            
            file_exists = os.path.isfile(self.file_path)
            csv_file = open(self.file_path, mode='a', newline='')
            writer = csv.writer(csv_file)
            
            if not file_exists:
                writer.writerow(["Timestamp", "Accel_X_G", "Accel_Y_G", "Accel_Z_G", "Total_G"])
            print(f"📁 Logging MPU data to: {self.file_path}")
        except Exception as e:
            print(f"❌ Failed to setup CSV logging: {e}")
        # ---------------------------

        while self.running:
            try:
                total_g = 1.0 # Default gravity
                ax, ay, az = 0.0, 0.0, 1.0
                
                if self.bus:
                    # Read Accelerometer Data
                    acc_x = self._read_raw_data(self.ACCEL_XOUT_H)
                    acc_y = self._read_raw_data(self.ACCEL_XOUT_H + 2)
                    acc_z = self._read_raw_data(self.ACCEL_XOUT_H + 4)

                    # Convert to G-Force
                    ax = acc_x / scale_divider
                    ay = acc_y / scale_divider
                    az = acc_z / scale_divider

                    # Calculate total force
                    total_g = math.sqrt(ax**2 + ay**2 + az**2)
                else:
                    # Simulation Mode
                    import random
                    total_g = 1.0 + (random.uniform(-0.1, 0.1))

                # --- LOG TO CSV ---
                if writer and csv_file:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    writer.writerow([timestamp, f"{ax:.4f}", f"{ay:.4f}", f"{az:.4f}", f"{total_g:.4f}"])
                    csv_file.flush() # Force save to disk immediately
                # ------------------

                # Emit Live Data for Graph UI (Throttle to ~20Hz)
                self.live_data.emit(total_g)
                
                # Check for Crash
                if total_g > self.sensitivity_threshold:
                    print(f"💥 CRASH DETECTED: {total_g:.2f}G")
                    self.crash_detected.emit()
                    time.sleep(10) # Pause logging for 10s after crash
                else:
                    time.sleep(0.05) # Normal reading interval

            except Exception as e:
                # Suppress spam if wire wiggles
                time.sleep(1)
        
        # Close file gracefully when app shuts down
        if csv_file:
            csv_file.close()
