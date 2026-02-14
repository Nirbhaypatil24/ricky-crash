"""
Mode Controller - Handles different operational modes
Updated to work with corrected GPIO pins
"""

from PyQt5.QtCore import QObject, pyqtSignal
import time

class ModeController(QObject):
    # Signals
    mode_changed = pyqtSignal(str)  # mode_name
    
    # Available modes - CORRECTED TO MATCH HARDWARE
    MODES = {
        'For Hire': 'Available for passengers - GPIO 23',
        'Private': 'Single passenger/group - GPIO 7',
        'Sharing': '3 individual passengers - GPIO 8', 
        'Waiting': 'Driver break/waiting - GPIO 18'
    }
    
    def __init__(self, gpio_manager):
        super().__init__()
        self.gpio_manager = gpio_manager
        self.current_mode = 'For Hire'  # Default mode
        self.is_active = False
        
        print("🔄 Mode Controller initialized with corrected GPIO mapping")

    def start(self):
        """Start mode monitoring"""
        # Connect to GPIO manager signals
        self.gpio_manager.mode_switch_changed.connect(self.handle_mode_change)
        self.is_active = True
        
        # Get initial mode from hardware
        initial_mode = self.gpio_manager.get_current_mode()
        if initial_mode != self.current_mode:
            self.handle_mode_change(initial_mode)
        
        print("🔄 Mode Controller started - monitoring rotary switch")

    def handle_mode_change(self, mode_name):
        """Handle mode switch changes from rotary switch"""
        if mode_name in self.MODES and mode_name != self.current_mode:
            old_mode = self.current_mode
            self.current_mode = mode_name
            
            print(f"🔄 Mode changed: {old_mode} → {mode_name}")
            print(f"📝 {self.MODES[mode_name]}")
            
            # Show GPIO states for debugging
            gpio_states = self.gpio_manager.get_gpio_states()
            if isinstance(gpio_states, dict):
                print("🔧 GPIO States:")
                for pin_name, state in gpio_states.items():
                    if 'mode_' in pin_name:
                        print(f"   {pin_name}: {state}")
            
            # Emit signal for UI update
            self.mode_changed.emit(mode_name)
            
            # Handle mode-specific logic
            self._handle_mode_logic(mode_name, old_mode)

    def _handle_mode_logic(self, new_mode, old_mode):
        """Handle mode-specific business logic"""
        if new_mode == 'Private':
            print("🚖 Private mode activated - GPIO 7 LOW")
            print("   - Single fare calculation enabled")
            print("   - Individual passenger switches ignored")
            
        elif new_mode == 'Sharing':
            print("👥 Sharing mode activated - GPIO 8 LOW")
            print("   - 3 individual passenger tracking enabled")
            print("   - Separate fare calculation for each passenger")
            
        elif new_mode == 'For Hire':
            print("🚕 For Hire mode activated - GPIO 23 LOW")
            print("   - Ready to accept passengers")
            print("   - All fare calculations stopped")
            
        elif new_mode == 'Waiting':
            print("⏸️ Waiting mode activated - GPIO 18 LOW")
            print("   - Driver on break")
            print("   - Not accepting passengers")

    def get_current_mode(self):
        """Get current operational mode"""
        return self.current_mode

    def get_mode_description(self):
        """Get description of current mode"""
        return self.MODES.get(self.current_mode, "Unknown mode")

    def is_fare_mode(self):
        """Check if current mode involves fare calculation"""
        return self.current_mode in ['Private', 'Sharing']

    def is_passenger_mode(self):
        """Check if current mode accepts passengers"""
        return self.current_mode in ['For Hire', 'Private', 'Sharing']

    def force_mode_change(self, mode_name):
        """Force mode change (for testing/manual control)"""
        if mode_name in self.MODES:
            self.handle_mode_change(mode_name)
            return True
        return False

    def debug_mode_switch(self):
        """Debug the rotary switch states"""
        gpio_states = self.gpio_manager.get_gpio_states()
        print("🔧 Rotary Switch Debug:")
        print(f"Current mode: {self.current_mode}")
        
        if isinstance(gpio_states, dict):
            mode_pins = {
                'mode_private (GPIO 7)': 'Private',
                'mode_sharing (GPIO 8)': 'Sharing', 
                'mode_waiting (GPIO 18)': 'Waiting',
                'mode_for_hire (GPIO 23)': 'For Hire'
            }
            
            for pin_name, expected_mode in mode_pins.items():
                state = gpio_states.get(pin_name, 'UNKNOWN')
                active = "🟢 ACTIVE" if state == "LOW" else "⚪ INACTIVE"
                print(f"   {pin_name}: {state} {active}")
        else:
            print(f"   {gpio_states}")

    def stop(self):
        """Stop mode controller"""
        self.is_active = False
        print("🔄 Mode Controller stopped")