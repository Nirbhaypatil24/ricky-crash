"""
GSM Manager - Handles SMS communication via A7670C Module
Updated: Supports sending SMS to MULTIPLE emergency numbers
"""

import serial
import time
import threading
import glob
from PyQt5.QtCore import QObject, pyqtSignal

class GSMManager(QObject):
    sms_sent = pyqtSignal(bool, str)

    # UPDATED: Now accepts a list of numbers (emergency_numbers)
    def __init__(self, port=None, baudrate=115200, emergency_numbers=None):
        super().__init__()
        self.configured_port = port 
        self.baudrate = baudrate
        
        # Ensure it's a list even if a single string is passed
        if emergency_numbers is None:
            self.emergency_numbers = ["+918390600361", "+919014769806"]
        elif isinstance(emergency_numbers, str):
            self.emergency_numbers = [emergency_numbers]
        else:
            self.emergency_numbers = emergency_numbers
            
        self.serial = None
        self.is_connected = False
        
        threading.Thread(target=self.setup_serial, daemon=True).start()

    def setup_serial(self):
        self.is_connected = False
        candidates = []
        if self.configured_port: candidates.append(self.configured_port)
        candidates.extend(glob.glob('/dev/ttyUSB*'))
        candidates.extend(['/dev/ttyS0', '/dev/ttyAMA0'])
        candidates = list(dict.fromkeys(candidates))
        
        print(f"🔍 GSM: Scanning ports: {candidates}")

        for p in candidates:
            try:
                ser = serial.Serial(p, self.baudrate, timeout=1)
                ser.write(b'AT\r\n')
                time.sleep(0.2)
                if "OK" in ser.read_all().decode(errors='ignore'):
                    print(f"✅ GSM Connected on {p}")
                    self.serial = ser
                    self.is_connected = True
                    self._send_at("ATE0")
                    self._send_at("AT+CMGF=1")
                    self._send_at("AT+CSCS=\"GSM\"")
                    return
                else: ser.close()
            except: pass
        print("❌ GSM Module NOT detected.")

    def _send_at(self, command, wait=0.5):
        if not self.is_connected or not self.serial: return ""
        try:
            self.serial.reset_input_buffer()
            self.serial.write((command + "\r\n").encode())
            time.sleep(wait)
            return self.serial.read_all().decode(errors='ignore')
        except: return ""

    def send_sos_sms(self, location_tuple, alert_type="SOS_BUTTON"):
        threading.Thread(target=self._send_sms_thread_safe, args=(location_tuple, alert_type), daemon=True).start()

    def _send_sms_thread_safe(self, location, alert_type):
        if not self.is_connected:
            self.setup_serial()
        
        if self.is_connected:
            self._send_actual_sms(location, alert_type)
        else:
            print("❌ SMS Failed: GSM Disconnected")

    def _send_actual_sms(self, location, alert_type):
        try:
            if not location or location == (0.0, 0.0): lat, lon = 19.8758, 75.3393
            else: lat, lon = location

            maps_link = f"https://maps.google.com/?q={lat:.5f},{lon:.5f}"
            
            header = "🚨 CRASH DETECTED! 🚨" if alert_type == "CRASH_SENSOR" else "🚨 SOS ALERT! 🚨"

            message = (
                f"{header}\n"
                f"Drvr: CHANDU\n"
                f"Ph: 20XXXXXX83\n"
                f"Veh: MH20XX2020\n"
                f"Loc: {lat:.5f},{lon:.5f}\n"
                f"{maps_link}"
            )
            
            self._send_at("AT+CMGF=1") # Ensure Text Mode
            
            # --- UPDATED: Loop through all emergency numbers ---
            all_successful = True
            for number in self.emergency_numbers:
                print(f"📨 Sending '{alert_type}' SMS to {number}...")
                
                self.serial.write(f'AT+CMGS="{number}"\r\n'.encode())
                time.sleep(1.0)
                
                self.serial.write(message.encode())
                time.sleep(0.5)
                
                self.serial.write(bytes([26])) # Send Ctrl+Z
                time.sleep(5) # Wait 5 seconds for the network to process and send
                
                response = self.serial.read_all().decode(errors='ignore')
                if "OK" in response or "+CMGS:" in response:
                    print(f"✅ SMS Sent to {number}!")
                else:
                    print(f"❌ SMS Failed for {number}: {response}")
                    all_successful = False
            
            # Emit final status
            if all_successful:
                self.sms_sent.emit(True, "Sent to all numbers")
            else:
                self.sms_sent.emit(False, "Failed for some/all numbers")
                
        except Exception as e:
            print(f"❌ SMS Error: {e}")

    def close(self):
        if self.serial: self.serial.close()
