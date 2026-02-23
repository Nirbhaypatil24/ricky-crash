"""
GPIO Manager - Handles all hardware GPIO operations
Updated with correct rotary switch GPIO pins
"""

import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal

try:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    GPIO_AVAILABLE = True
    print("✅ RPi.GPIO available")
except ImportError:
    print("⚠️ RPi.GPIO not available - simulation mode")
    GPIO_AVAILABLE = False
    
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        IN = "IN"
        PUD_UP = "PUD_UP"
        PUD_DOWN = "PUD_DOWN"
        HIGH = 1
        LOW = 0
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode, **kwargs): pass
        @staticmethod
        def output(pin, state): print(f"GPIO {pin} = {state}")
        @staticmethod
        def input(pin): return MockGPIO.HIGH
        @staticmethod
        def cleanup(): pass
    
    GPIO = MockGPIO()

class GPIOManager(QObject):
    # Signals
    passenger_changed = pyqtSignal(int, bool)  # passenger_id, onboard
    sos_button_pressed = pyqtSignal()
    sos_button_released = pyqtSignal()
    mode_switch_changed = pyqtSignal(str)  # mode name
    
    # GPIO Pin Definitions - CORRECTED ACCORDING TO YOUR SPECIFICATION
    PINS = {
        # SOS System
        'sos_buzzer': 26,
        'sos_button': 12,
        'sos_led': 21,
        
        # Sharing Mode (Passenger Switches) 
        'passenger_1': 6,
        'passenger_2': 13,
        'passenger_3': 19,
        
        # Rotary Mode Switch - CORRECTED PINS
        'mode_private': 7,      # Position 1 (Private Mode) → GPIO 7
        'mode_sharing': 8,      # Position 2 (Sharing Mode) → GPIO 8  
        'mode_waiting': 18,     # Position 3 (Waiting Mode) → GPIO 18
        'mode_for_hire': 23,    # Position 4 (For Hire Mode) → GPIO 23
        
        # MPU6050 (I2C)
        'mpu_scl': 3,
        'mpu_sda': 2,
        'mpu_int': 4
    }
    
    # Mode mapping - CORRECTED
    MODES = {
        'mode_private': 'Private',      # GPIO 7
        'mode_sharing': 'Sharing',      # GPIO 8  
        'mode_waiting': 'Waiting',      # GPIO 18
        'mode_for_hire': 'For Hire'    # GPIO 23
    }

    def __init__(self):
        super().__init__()
        self.running = False
        self.threads = []
        
        # State tracking
        self.passenger_states = {0: False, 1: False, 2: False}  # False = offboard
        self.current_mode = "For Hire"  # Default mode
        self.sos_active = False
        
        if GPIO_AVAILABLE:
            self.setup_gpio()

    def setup_gpio(self):
        """Initialize all GPIO pins with correct configuration"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # SOS System
        GPIO.setup(self.PINS['sos_buzzer'], GPIO.OUT)
        GPIO.setup(self.PINS['sos_button'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PINS['sos_led'], GPIO.OUT)
        
        # Passenger switches (pulled up, goes LOW when pressed)
        for i in range(1, 4):
            GPIO.setup(self.PINS[f'passenger_{i}'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Rotary Mode Switch - CORRECTED WITH PULL-UP RESISTORS
        # Common pin goes to GND, so when position is selected, pin goes LOW
        for mode_pin in ['mode_private', 'mode_sharing', 'mode_waiting', 'mode_for_hire']:
            GPIO.setup(self.PINS[mode_pin], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            print(f"🔧 Setup {mode_pin} on GPIO {self.PINS[mode_pin]} with pull-up")
        
        # Initialize outputs to OFF
        GPIO.output(self.PINS['sos_buzzer'], GPIO.LOW)
        GPIO.output(self.PINS['sos_led'], GPIO.LOW)
        
        print("🔧 GPIO pins initialized with correct rotary switch configuration")

    def start(self):
        """Start monitoring threads"""
        self.running = True
        
        # Start monitoring threads
        threads_config = [
            ('passenger_monitor', self._monitor_passengers),
            ('mode_monitor', self._monitor_mode_switch),
            ('sos_monitor', self._monitor_sos_button)
        ]
        
        for name, target in threads_config:
            thread = threading.Thread(target=target, name=name, daemon=True)
            thread.start()
            self.threads.append(thread)
        
        print("🔧 GPIO monitoring threads started")

    def _monitor_passengers(self):
        """Monitor passenger switches"""
        while self.running:
            try:
                for i in range(3):  # 3 passengers
                    pin = self.PINS[f'passenger_{i+1}']
                    current_state = GPIO.input(pin) == GPIO.LOW  # LOW = onboard
                    
                    if current_state != self.passenger_states[i]:
                        self.passenger_states[i] = current_state
                        self.passenger_changed.emit(i, current_state)
                        status = "ONBOARD" if current_state else "OFFBOARD"
                        print(f"🧑 Passenger {i+1}: {status}")
                
                time.sleep(0.1)  # 100ms polling
            except Exception as e:
                print(f"❌ Passenger monitor error: {e}")
                time.sleep(1)

    def _monitor_mode_switch(self):
        """Monitor rotary mode switch - CORRECTED LOGIC"""
        while self.running:
            try:
                # Check each mode position
                # When rotary switch selects a position, that GPIO pin goes LOW (circuit complete to GND)
                
                selected_mode = None
                
                # Check each mode pin - the one that's LOW is selected
                for mode_key, mode_name in self.MODES.items():
                    pin = self.PINS[mode_key]
                    pin_state = GPIO.input(pin)
                    
                    if pin_state == GPIO.LOW:  # Circuit completed to GND
                        selected_mode = mode_name
                        break
                
                # If no mode is detected as LOW, default to For Hire
                if selected_mode is None:
                    selected_mode = "For Hire"
                
                # Check if mode changed
                if selected_mode != self.current_mode:
                    old_mode = self.current_mode
                    self.current_mode = selected_mode
                    
                    print(f"🔄 Rotary switch: {old_mode} → {selected_mode}")
                    print(f"🔧 GPIO states: Private({self.PINS['mode_private']})={GPIO.input(self.PINS['mode_private'])}, "
                          f"Sharing({self.PINS['mode_sharing']})={GPIO.input(self.PINS['mode_sharing'])}, "
                          f"Waiting({self.PINS['mode_waiting']})={GPIO.input(self.PINS['mode_waiting'])}, "
                          f"For Hire({self.PINS['mode_for_hire']})={GPIO.input(self.PINS['mode_for_hire'])}")
                    
                    self.mode_switch_changed.emit(selected_mode)
                
                time.sleep(0.2)  # 200ms polling
            except Exception as e:
                print(f"❌ Mode monitor error: {e}")
                time.sleep(1)

    def _monitor_sos_button(self):
        """Monitor SOS button with 5-second hold logic"""
        while self.running:
            try:
                if GPIO.input(self.PINS['sos_button']) == GPIO.LOW:  # Button pressed
                    press_start = time.time()
                    self.sos_button_pressed.emit()
                    
                    # Monitor how long button is held
                    while GPIO.input(self.PINS['sos_button']) == GPIO.LOW:
                        hold_time = time.time() - press_start
                        if hold_time >= 5.0:  # 5 seconds
                            if not self.sos_active:
                                self.activate_sos()
                            break
                        time.sleep(0.1)
                    
                    # Button released
                    hold_time = time.time() - press_start
                    if hold_time < 5.0:
                        self.sos_button_released.emit()
                        if self.sos_active:
                            self.deactivate_sos()
                
                time.sleep(0.05)  # 50ms polling for responsive SOS
            except Exception as e:
                print(f"❌ SOS monitor error: {e}")
                time.sleep(1)

    def activate_sos(self):
        """Activate SOS system"""
        self.sos_active = True
        print("🚨 SOS ACTIVATED!")
        
        # Start SOS pattern thread
        sos_thread = threading.Thread(target=self._sos_pattern, daemon=True)
        sos_thread.start()

    def deactivate_sos(self):
        """Deactivate SOS system"""
        self.sos_active = False
        GPIO.output(self.PINS['sos_buzzer'], GPIO.LOW)
        GPIO.output(self.PINS['sos_led'], GPIO.LOW)
        print("✅ SOS deactivated")

    def _sos_pattern(self):
        """Run SOS buzzer and LED pattern"""
        while self.sos_active and self.running:
            try:
                # SOS pattern: ... --- ... (3 short, 3 long, 3 short)
                # Short beeps
                for _ in range(3):
                    GPIO.output(self.PINS['sos_buzzer'], GPIO.HIGH)
                    GPIO.output(self.PINS['sos_led'], GPIO.HIGH)
                    time.sleep(0.2)
                    GPIO.output(self.PINS['sos_buzzer'], GPIO.LOW)
                    GPIO.output(self.PINS['sos_led'], GPIO.LOW)
                    time.sleep(0.2)
                
                time.sleep(0.2)  # Pause
                
                # Long beeps
                for _ in range(3):
                    GPIO.output(self.PINS['sos_buzzer'], GPIO.HIGH)
                    GPIO.output(self.PINS['sos_led'], GPIO.HIGH)
                    time.sleep(0.6)
                    GPIO.output(self.PINS['sos_buzzer'], GPIO.LOW)
                    GPIO.output(self.PINS['sos_led'], GPIO.LOW)
                    time.sleep(0.2)
                
                time.sleep(0.2)  # Pause
                
                # Short beeps
                for _ in range(3):
                    GPIO.output(self.PINS['sos_buzzer'], GPIO.HIGH)
                    GPIO.output(self.PINS['sos_led'], GPIO.HIGH)
                    time.sleep(0.2)
                    GPIO.output(self.PINS['sos_buzzer'], GPIO.LOW)
                    GPIO.output(self.PINS['sos_led'], GPIO.LOW)
                    time.sleep(0.2)
                
                time.sleep(1)  # Pause before repeat
                
            except Exception as e:
                print(f"❌ SOS pattern error: {e}")
                break

    def get_current_mode(self):
        """Get current mode from hardware"""
        return self.current_mode

    def get_gpio_states(self):
        """Get current GPIO states for debugging"""
        if not GPIO_AVAILABLE:
            return "GPIO not available"
            
        states = {}
        for name, pin in self.PINS.items():
            if 'mode_' in name or 'passenger_' in name or name == 'sos_button':
                states[f"{name} (GPIO {pin})"] = "LOW" if GPIO.input(pin) == GPIO.LOW else "HIGH"
        return states

    def cleanup(self):
        """Clean up GPIO resources"""
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1)
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
            print("🧹 GPIO cleanup completed")