#pi@ricky-meter:~/Documents/Rasp $ cat fix_display.py
"""
Test script to fix display issues on Raspberry Pi
"""
import os
import sys

# Fix for headless/SSH connections
def setup_display():
    """Setup display environment for PyQt5"""
    if 'DISPLAY' not in os.environ:
        # Try different display options
        display_options = [':0', ':10.0', ':1']
        for display in display_options:
            os.environ['DISPLAY'] = display
            break
    
    # Set Qt platform for Raspberry Pi
    if 'QT_QPA_PLATFORM' not in os.environ:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
    
    print(f"Display setup: DISPLAY={os.environ.get('DISPLAY', 'None')}")
    print(f"Qt Platform: {os.environ.get('QT_QPA_PLATFORM', 'None')}")

# Test PyQt5 with display fix
if __name__ == "__main__":
    setup_display()
    
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        print("✅ PyQt5 working with display fix!")
    except Exception as e:
        print(f"❌ PyQt5 error: {e}")
        # Try alternative platform
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication(sys.argv)
            print("✅ PyQt5 working with offscreen platform!")
        except Exception as e2:
            print(f"❌ Still failing: {e2}")