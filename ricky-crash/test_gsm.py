"""
Simple GSM Tester - Run this separately to debug connection
"""
import serial
import time
import glob

def test_gsm():
    print("🔍 Scanning for GSM Module...")
    ports = glob.glob('/dev/ttyUSB*') + ['/dev/ttyS0']
    
    found = False
    for port in ports:
        try:
            print(f"👉 Testing {port}...", end="", flush=True)
            ser = serial.Serial(port, 115200, timeout=1)
            
            ser.write(b'AT\r\n')
            time.sleep(0.5)
            response = ser.read_all().decode(errors='ignore')
            ser.close()
            
            if "OK" in response:
                print(" ✅ FOUND! (Responded to AT)")
                found = True
                
                # Test SMS config
                print(f"   [+] Testing SMS capability on {port}...")
                ser = serial.Serial(port, 115200, timeout=1)
                ser.write(b'AT+CMGF=1\r\n')
                time.sleep(0.5)
                resp2 = ser.read_all().decode(errors='ignore')
                if "OK" in resp2:
                    print("   ✅ SMS Text Mode supported")
                else:
                    print("   ⚠️ Could not set SMS mode")
                ser.close()
                break # Stop after finding first working port
            else:
                print(" ❌ No Response")
        except Exception as e:
            print(f" ⚠️ Error opening port: {e}")

    if not found:
        print("\n❌ GSM Module NOT found.")
        print("troubleshooting:")
        print("1. Run: sudo chmod 666 /dev/ttyUSB*")
        print("2. Run: sudo systemctl stop ModemManager")

if __name__ == "__main__":
    test_gsm()
