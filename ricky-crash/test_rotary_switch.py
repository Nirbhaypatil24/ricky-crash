#!/usr/bin/env python3
"""
Test script for rotary switch with correct GPIO pins
"""

import os
import sys
import time

# Setup display for headless mode
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from backend.gpio_manager import GPIOManager
from backend.mode_controller import ModeController

def main():
    print("🔧 Testing Rotary Switch with Correct GPIO Pins")
    print("=" * 50)
    print("Hardware Configuration:")
    print("  Common pin → GND")
    print("  Position 1 (Private) → GPIO 7")
    print("  Position 2 (Sharing) → GPIO 8")  
    print("  Position 3 (Waiting) → GPIO 18")
    print("  Position 4 (For Hire) → GPIO 23")
    print("  All pins use pull-up resistors (HIGH by default)")
    print("  When position selected → GPIO goes LOW")
    print("=" * 50)

    app = QApplication(sys.argv)

    # Create components
    gpio_manager = GPIOManager()
    mode_controller = ModeController(gpio_manager)

    # Connect debug output
    def on_mode_change(mode):
        print(f"\n🎯 MODE DETECTED: {mode}")
        mode_controller.debug_mode_switch()

    mode_controller.mode_changed.connect(on_mode_change)

    # Start monitoring
    gpio_manager.start()
    mode_controller.start()

    print("\n🔍 Monitoring rotary switch...")
    print("Turn the rotary switch to test different positions")
    print("Press Ctrl+C to stop")

    try:
        # Monitor for 60 seconds or until interrupted
        for i in range(60):
            time.sleep(1)
            if i % 10 == 0:  # Every 10 seconds
                print(f"\n📊 Current status (after {i}s):")
                mode_controller.debug_mode_switch()
                
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")

    finally:
        print("\n🧹 Cleaning up...")
        mode_controller.stop()
        gpio_manager.cleanup()
        print("✅ Test completed")

if __name__ == "__main__":
    main()