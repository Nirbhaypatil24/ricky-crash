"""
GPS Manager - Handles GPS data acquisition and processing
Enhanced with real-time distance and speed tracking
"""

import threading
import time
import math
import random
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, pyqtSignal

try:
    import serial
    SERIAL_AVAILABLE = True
    print("✅ Serial module available for GPS")
except ImportError:
    print("⚠️ Serial module not available - GPS simulation mode")
    SERIAL_AVAILABLE = False

class GPSManager(QObject):
    # Signals
    location_updated = pyqtSignal(float, float)  # latitude, longitude
    speed_updated = pyqtSignal(float)  # speed in km/h
    distance_updated = pyqtSignal(float)  # total distance traveled
    
    def __init__(self, port="/dev/serial0", baudrate=9600, force_simulation=False):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.thread = None
        
        # Current state
        self.current_location = None
        self.previous_location = None
        self.current_speed = 0.0
        self.total_distance_traveled = 0.0
        self.trip_start_time = None
        self.simulation_mode = force_simulation or not SERIAL_AVAILABLE

        
        # For realistic simulation
        self.sim_angle = 0
        self.sim_radius = 0.005  # ~500m radius for more realistic movement
        self.sim_speed_base = 15.0  # Base speed 15 km/h
        self.sim_last_update = time.time()
        
        # GPS tracking
        self.gps_fix = False
        self.satellites_count = 0
        self.altitude = 0.0
        self.heading = 0.0

    def start(self):
        """Start GPS monitoring"""
        self.running = True
        self.trip_start_time = datetime.now()
        
        if not self.simulation_mode:
            try:
                self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
                print(f"📡 GPS initialized on {self.port}")
            except Exception as e:
                print(f"⚠️ GPS serial failed, switching to simulation: {e}")
                self.simulation_mode = True
        
        self.thread = threading.Thread(target=self._gps_loop, daemon=True)
        self.thread.start()
        print("📡 GPS manager started with real-time tracking")

    def _gps_loop(self):
        """Main GPS processing loop"""
        if self.simulation_mode:
            self._enhanced_simulation_loop()
        else:
            self._serial_loop()

    def _enhanced_simulation_loop(self):
        """Enhanced GPS simulation with realistic movement patterns"""
        # Mumbai area coordinates for realistic simulation
        base_lat, base_lon = 19.0760, 72.8777  # Mumbai
        
        # Simulate different route patterns
        route_points = [
            (19.0760, 72.8777),  # Starting point
            (19.0800, 72.8800),  # Point 1
            (19.0850, 72.8750),  # Point 2
            (19.0820, 72.8720),  # Point 3
            (19.0790, 72.8760),  # Back towards start
        ]
        
        current_target = 1
        progress_to_target = 0.0
        
        while self.running:
            try:
                current_time = time.time()
                time_delta = current_time - self.sim_last_update
                self.sim_last_update = current_time
                
                # Get current and target positions
                current_pos = route_points[current_target - 1]
                target_pos = route_points[current_target % len(route_points)]
                
                # Calculate movement towards target
                movement_speed = 0.001  # Movement rate
                progress_to_target += movement_speed
                
                if progress_to_target >= 1.0:
                    progress_to_target = 0.0
                    current_target = (current_target + 1) % len(route_points)
                    target_pos = route_points[current_target]
                
                # Interpolate position
                lat = current_pos[0] + (target_pos[0] - current_pos[0]) * progress_to_target
                lon = current_pos[1] + (target_pos[1] - current_pos[1]) * progress_to_target
                
                # Add some random variation to simulate real GPS noise
                lat += random.uniform(-0.0001, 0.0001)
                lon += random.uniform(-0.0001, 0.0001)
                
                # Calculate realistic speed based on movement
                if self.previous_location:
                    distance_moved = self.calculate_distance(
                        self.previous_location[0], self.previous_location[1], lat, lon
                    )
                    
                    if time_delta > 0:
                        # Speed = distance / time, convert to km/h
                        current_speed_ms = (distance_moved * 1000) / time_delta  # m/s
                        self.current_speed = current_speed_ms * 3.6  # Convert to km/h
                        
                        # Add realistic speed variation (10-40 km/h)
                        self.current_speed = max(5, min(45, self.current_speed + random.uniform(-2, 2)))
                    
                    # Update total distance
                    self.total_distance_traveled += distance_moved
                
                # Update location
                self.previous_location = self.current_location
                self.current_location = (lat, lon)
                
                # Emit signals
                self.location_updated.emit(lat, lon)
                self.speed_updated.emit(self.current_speed)
                self.distance_updated.emit(self.total_distance_traveled)
                
                # Update GPS status
                self.gps_fix = True
                self.satellites_count = random.randint(6, 12)
                self.altitude = random.uniform(10, 50)
                self.heading = (self.heading + random.uniform(-5, 5)) % 360
                
                time.sleep(1)  # Update every second for real-time feel
                
            except Exception as e:
                print(f"❌ GPS simulation error: {e}")
                time.sleep(1)

    def _serial_loop(self):
        """Read from actual GPS module"""
        while self.running:
            try:
                line = self.serial.readline().decode("ascii", errors="replace").strip()
                
                if line.startswith("$GPGGA"):
                    location_data = self._parse_gpgga(line)
                    if location_data:
                        lat, lon, altitude, satellites = location_data
                        
                        # Update tracking
                        if self.previous_location:
                            distance = self.calculate_distance(
                                self.previous_location[0], self.previous_location[1], lat, lon
                            )
                            self.total_distance_traveled += distance
                            self.distance_updated.emit(self.total_distance_traveled)
                        
                        self.previous_location = self.current_location
                        self.current_location = (lat, lon)
                        self.altitude = altitude
                        self.satellites_count = satellites
                        self.gps_fix = True
                        
                        self.location_updated.emit(lat, lon)
                
                elif line.startswith("$GPVTG"):
                    speed = self._parse_gpvtg(line)
                    if speed is not None:
                        self.current_speed = speed
                        self.speed_updated.emit(speed)
                
                elif line.startswith("$GPGSA"):
                    fix_data = self._parse_gpgsa(line)
                    if fix_data:
                        self.gps_fix = fix_data
                        
            except Exception as e:
                print(f"❌ GPS serial error: {e}")
                time.sleep(1)

    def _parse_gpgga(self, sentence):
        """Parse GPGGA sentence for location and quality"""
        try:
            parts = sentence.split(",")
            if len(parts) < 15:
                return None
                
            lat_raw, lat_dir, lon_raw, lon_dir = parts[2:6]
            quality = parts[6]
            satellites = parts[7]
            altitude = parts[9]
            
            if not lat_raw or not lon_raw or quality == '0':
                return None

            # Convert ddmm.mmmm to decimal degrees
            lat = float(lat_raw[:2]) + float(lat_raw[2:]) / 60.0
            if lat_dir == "S":
                lat = -lat
                
            lon = float(lon_raw[:3]) + float(lon_raw[3:]) / 60.0
            if lon_dir == "W":
                lon = -lon
            
            alt = float(altitude) if altitude else 0.0
            sats = int(satellites) if satellites else 0
                
            return (lat, lon, alt, sats)
        except Exception:
            return None

    def _parse_gpvtg(self, sentence):
        """Parse GPVTG sentence for speed"""
        try:
            parts = sentence.split(",")
            if len(parts) > 7 and parts[7]:  # Speed in km/h
                return float(parts[7])
            return None
        except Exception:
            return None

    def _parse_gpgsa(self, sentence):
        """Parse GPGSA sentence for fix type"""
        try:
            parts = sentence.split(",")
            if len(parts) > 2:
                fix_type = parts[2]
                return fix_type in ['2', '3']  # 2D or 3D fix
            return False
        except Exception:
            return False

    def get_location(self):
        """Get current location"""
        return self.current_location

    def get_speed(self):
        """Get current speed in km/h"""
        return self.current_speed

    def get_total_distance(self):
        """Get total distance traveled in km"""
        return self.total_distance_traveled

    def get_trip_duration(self):
        """Get trip duration in minutes"""
        if self.trip_start_time:
            duration = datetime.now() - self.trip_start_time
            return duration.total_seconds() / 60
        return 0

    def get_gps_status(self):
        """Get GPS status information"""
        return {
            'fix': self.gps_fix,
            'satellites': self.satellites_count,
            'altitude': self.altitude,
            'speed': self.current_speed,
            'heading': self.heading
        }

    def reset_trip(self):
        """Reset trip counters"""
        self.total_distance_traveled = 0.0
        self.trip_start_time = datetime.now()
        self.previous_location = None
        print("📡 GPS trip counters reset")

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in km"""
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
            
        try:
            # Haversine formula
            R = 6371.0  # Earth radius in km
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
            return 2 * R * math.asin(math.sqrt(a))
        except Exception:
            return 0.0

    def stop(self):
        """Stop GPS monitoring"""
        self.running = False
        
        if hasattr(self, 'serial'):
            try:
                self.serial.close()
            except:
                pass
                
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
            
        print("📡 GPS manager stopped")