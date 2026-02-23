#!/usr/bin/env python3
"""
MPU6050 Live Monitor
Run this to visualize sensor data and test crash thresholds.
"""

import time
import math
import os
import sys

# Try importing SMBus
try:
    from smbus2 import SMBus
    I2C_AVAILABLE = True
except ImportError:
    try:
        from smbus import SMBus
        I2C_AVAILABLE = True
    except ImportError:
        I2C_AVAILABLE = False

# MPU6050 Registers
PWR_MGMT_1 = 0x6B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
DEVICE_ADDRESS = 0x68

def setup_mpu(bus):
    try:
        # Wake up
        bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0)
        # Set to +/- 16g range (consistent with main app)
        bus.write_byte_data(DEVICE_ADDRESS, ACCEL_CONFIG, 0x18)
        return True
    except Exception as e:
        print(f"❌ MPU Init Failed: {e}")
        return False

def read_raw_data(bus, addr):
    high = bus.read_byte_data(DEVICE_ADDRESS, addr)
    low = bus.read_byte_data(DEVICE_ADDRESS, addr + 1)
    value = (high << 8) | low
    if value > 32768:
        value = value - 65536
    return value

def main():
    print("="*50)
    print("🛡️  MPU6050 LIVE SENSOR MONITOR")
    print("="*50)

    if not I2C_AVAILABLE:
        print("❌ Error: SMBus library not found.")
        print("   Run: sudo apt-get install python3-smbus i2c-tools")
        return

    try:
        bus = SMBus(1)
        if not setup_mpu(bus):
            return
        
        print("✅ Sensor Connected. Reading data...")
        print("   (Press Ctrl+C to stop)\n")
        
        # Divider for +/- 16g
        scale = 2048.0 
        crash_threshold = 3.0 # G-Force

        while True:
            # Read Accelerometer
            ax_raw = read_raw_data(bus, ACCEL_XOUT_H)
            ay_raw = read_raw_data(bus, ACCEL_XOUT_H + 2)
            az_raw = read_raw_data(bus, ACCEL_XOUT_H + 4)

            # Convert to G
            ax = ax_raw / scale
            ay = ay_raw / scale
            az = az_raw / scale

            # Calculate Total G Vector
            total_g = math.sqrt(ax**2 + ay**2 + az**2)
            
            # Status Indicator
            if total_g > crash_threshold:
                status = "💥 CRASH DETECTED! 💥"
                color = "\033[91m" # Red
            else:
                status = "🟢 NORMAL"
                color = "\033[92m" # Green
            
            reset = "\033[0m"

            # Clear line and print formatted data
            sys.stdout.write(f"\r{color}[{status}]  X: {ax:5.2f}G | Y: {ay:5.2f}G | Z: {az:5.2f}G | TOTAL: {total_g:5.2f}G {reset}")
            sys.stdout.flush()
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n🛑 Monitor Stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
