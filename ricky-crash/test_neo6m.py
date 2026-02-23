#!/usr/bin/env python3
"""
NEO-6M GPS Tester & Connection Monitor
"""

import serial
import time

# Hardware UART on Raspberry Pi using GPIO 14 & 15
SERIAL_PORT = "/dev/serial0" 
BAUD_RATE = 9600 # Standard baud rate for NEO-6M

def convert_to_degrees(raw_value, direction):
    """Converts NMEA DDMM.MMMMM format to Decimal Degrees"""
    if not raw_value:
        return 0.0
    
    try:
        decimal_point_idx = raw_value.find('.')
        degrees_idx = decimal_point_idx - 2
        
        degrees = float(raw_value[:degrees_idx])
        minutes = float(raw_value[degrees_idx:])
        
        decimal_degrees = degrees + (minutes / 60.0)
        
        if direction in ['S', 'W']:
            decimal_degrees = -decimal_degrees
            
        return decimal_degrees
    except:
        return 0.0

def test_gps():
    print("=" * 55)
    print("🛰️  NEO-6M GPS HARDWARE TESTER")
    print("=" * 55)
    print("Wiring Check:")
    print("  GPS TX -> Pi GPIO 15 (RXD)")
    print("  GPS RX -> Pi GPIO 14 (TXD)")
    print("-" * 55)
    
    try:
        # Timeout set to 2 seconds. If no data arrives in 2s, we know it's disconnected.
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"✅ Serial Port {SERIAL_PORT} opened successfully.\n")
    except serial.SerialException as e:
        print(f"❌ Error: Cannot open {SERIAL_PORT}.")
        print("Make sure Serial Port hardware is enabled in 'sudo raspi-config'")
        return

    print("Monitoring GPS Status... (Press Ctrl+C to stop)\n")

    try:
        while True:
            # Read raw bytes from the UART pins
            raw_line = ser.readline()
            
            # 1. HARDWARE CONNECTION CHECK
            # If the line is empty after the 2-second timeout, the module is not sending data
            if not raw_line:
                print("\r🔴 STATUS: DISCONNECTED (No data received on GPIO 15)       ", end="\033[K")
                continue
            
            try:
                line = raw_line.decode('ascii', errors='replace').strip()
            except UnicodeDecodeError:
                continue

            # 2. DATA CHECK
            # If it starts with $, the hardware is connected and talking to the Pi
            if line.startswith('$GPGGA'):
                parts = line.split(',')
                
                if len(parts) > 7:
                    quality = parts[6]
                    sats = parts[7] if parts[7] else "0"
                    
                    # 3. SATELLITE FIX CHECK
                    if quality == '0' or not parts[2]:
                        # Connected, but no satellites found yet
                        print(f"\r🟠 STATUS: CONNECTED | SEARCHING FOR SATS... (Found: {sats})", end="\033[K")
                    else:
                        # Connected and Location Locked!
                        lat = convert_to_degrees(parts[2], parts[3])
                        lon = convert_to_degrees(parts[4], parts[5])
                        maps_link = f"https://www.google.com/maps?q={lat:.5f},{lon:.5f}"
                        
                        print(f"\r🟢 STATUS: 3D FIX! | Sats: {sats:02s} | Lat: {lat:.5f}, Lon: {lon:.5f}", end="\033[K")

    except KeyboardInterrupt:
        print("\n\n🛑 Test Stopped.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == '__main__':
    test_gps()
