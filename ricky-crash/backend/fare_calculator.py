"""
Fare Calculator - Calculates fares based on real GPS data
Updated to use actual GPS coordinates and real-time tracking
"""

import threading
import time
import math
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, pyqtSignal
import uuid

# ✅ ADD THIS IMPORT
from backend.fare_sync_service import FareSyncService


class FareCalculator(QObject):
    # Signals
    fare_updated = pyqtSignal(int, float)  # passenger_id, fare_amount
    total_fare_updated = pyqtSignal(float)  # total_fare for private mode
    ride_completed = pyqtSignal(int, dict)  # passenger_id, ride_data
    distance_updated = pyqtSignal(float)  # total distance
    duration_updated = pyqtSignal(int)  # duration in minutes
    
    def __init__(self, gps_manager, fare_rate_per_km=12.0):
        super().__init__()
        self.gps_manager = gps_manager
        self.fare_rate_per_km = fare_rate_per_km
        self.running = False
        self.thread = None
        
        self.gps_stale_threshold = 60  # seconds
        self.distance_source = "GPS"  # GPS or ROTARY
        # Real-time GPS tracking
        self.last_gps_update = time.time()
        self.last_valid_gps_time = time.time()      # ✅ REAL GPS heartbeat

        self.current_location = None
        
        # Passenger states (3 passengers for sharing mode)
        self.passengers = {}
        for i in range(3):
            self.passengers[i] = {
                'onboard': False,
                'fare': 0.0,
                'start_location': None,
                'last_location': None,
                'start_time': None,
                'total_distance': 0.0,
                'ride_id': None,
                'waiting_time': 0.0  # Time spent stationary
            }
        
        # Private mode state
        self.private_mode_active = False
        self.private_fare = 0.0
        self.private_start_location = None
        self.private_last_location = None
        self.private_start_time = None
        self.private_distance = 0.0
        self.private_waiting_time = 0.0
        
        # Speed-based calculations
        self.minimum_speed_threshold = 2.0  # km/h - below this is considered waiting
        
        self.lock = threading.Lock()
        
        # Connect to GPS signals
        self.gps_manager.location_updated.connect(self._on_location_update)
        self.gps_manager.speed_updated.connect(self._on_speed_update)
        
        print("💰 Fare Calculator initialized with real GPS integration")

        # ---------------- BACKEND SYNC (SELF-CONTAINED) ----------------
        try:
            self._fare_sync = FareSyncService(
                base_url="http://ec2-3-110-29-119.ap-south-1.compute.amazonaws.com:8080",
                driver_id="DRIVER-1"
            )

            # Attach service to THIS calculator
            self._fare_sync.attach(self)

            print("🌐 Fare backend sync enabled")
        except Exception as e:
            print(f"⚠️ Fare backend sync disabled: {e}")

    def start(self):
        """Start fare calculation thread"""
        self.running = True
        self.thread = threading.Thread(target=self._calculation_loop, daemon=True)
        self.thread.start()
        print("💰 Fare Calculator started with GPS tracking")

    def _on_location_update(self, lat, lon):
        """Handle GPS location updates"""
        self.last_valid_gps_time = time.time()
        self.current_location = (lat, lon)

    def _on_speed_update(self, speed):
        """Handle GPS speed updates"""
        # Speed is used to determine if vehicle is moving or waiting
        self.current_speed = speed

    def _calculation_loop(self):
      """Main fare calculation loop using real GPS data"""
      while self.running:
        try:
            current_location = self.gps_manager.get_location()
            current_speed = self.gps_manager.get_speed()
            current_time = time.time()

            # 🔧 CHANGE 3 — GPS STALE / RECOVERY DETECTION (FLAG ONLY)
            gps_stale_duration = current_time - self.last_valid_gps_time

            if gps_stale_duration > self.gps_stale_threshold:
                if self.distance_source != "ROTARY":
                    print("⚠️ GPS stale > 60s. Switching to ROTARY distance calculation")
                    self.distance_source = "ROTARY"
            else:
                if self.distance_source != "GPS":
                    print("✅ GPS signal restored. Switching back to GPS distance calculation")
                    self.distance_source = "GPS"

            time_delta = current_time - self.last_gps_update

            if current_location and time_delta >= 1.0:  # Update every second
                with self.lock:
                    # Update sharing mode passengers
                    for pid, passenger in self.passengers.items():
                        if passenger['onboard']:
                            self._update_passenger_fare(
                                pid, passenger, current_location, current_speed, time_delta
                            )

                    # Update private mode
                    if self.private_mode_active:
                        self._update_private_fare(
                            current_location, current_speed, time_delta
                        )

                self.last_gps_update = current_time

            time.sleep(0.5)  # Check every 500ms for responsive updates

        except Exception as e:
            print(f"❌ Fare calculation error: {e}")
            time.sleep(1)

    def _get_rotary_distance(self, time_delta):
       """
       Rotary encoder fallback distance calculation.
       Hardware integration will be added later.

       Expected future logic:
       - Read pulse count
       - pulses -> wheel rotations
       - rotations -> distance
       """
       return 0.0

    def _update_passenger_fare(self, pid, passenger, current_location, current_speed, time_delta):
      """Update fare for individual passenger using real GPS"""
      if not passenger['last_location']:
        passenger['last_location'] = current_location
        return

      # 🔧 CHANGE 4 — source-based distance selection
      if self.distance_source == "GPS":
        distance_moved = self._calculate_distance(
            passenger['last_location'], current_location
        )
      else:
        distance_moved = self._get_rotary_distance(time_delta)

      # Only count significant movement (> 5 meters)
      if distance_moved > 0.005:  # 5 meters in km
        # Distance-based fare
        distance_fare = distance_moved * self.fare_rate_per_km
        passenger['fare'] += distance_fare
        passenger['total_distance'] += distance_moved

        # Update last location
        passenger['last_location'] = current_location

    # Add waiting time charges if speed is low
      if current_speed < self.minimum_speed_threshold:
        waiting_charge_per_minute = 2.0  # ₹2 per minute waiting
        waiting_charge = (time_delta / 60.0) * waiting_charge_per_minute
        passenger['fare'] += waiting_charge
        passenger['waiting_time'] += time_delta / 60.0

      # Emit fare update
      self.fare_updated.emit(pid, passenger['fare'])

    
    def finalize_all_rides(self):
        """Force complete all active passenger rides and private mode"""
        with self.lock:
            # Finish private mode
            if self.private_mode_active:
                ride_data = self.stop_private_mode()
                if ride_data:
                    # Emit ride_completed for private ride with passenger_id=-1
                    self.ride_completed.emit(-1, ride_data)
                    print("✅ Private ride sent on finalize")

            # Finish all sharing mode rides
            for pid, passenger in self.passengers.items():
                if passenger['onboard']:
                    # Force alight
                    self.handle_passenger_change(pid, onboard=False)
                    print(f"✅ Passenger {pid+1} ride finalized on mode switch")


    def _update_private_fare(self, current_location, current_speed, time_delta):
        """Update private mode fare using real GPS"""
        if not self.private_last_location:
            self.private_last_location = current_location
            return
        
        # Calculate distance moved
        distance_moved = self._calculate_distance(
            self.private_last_location, current_location
        )
        
        # Only count significant movement
        if distance_moved > 0.005:  # 5 meters
            distance_fare = distance_moved * self.fare_rate_per_km
            self.private_fare += distance_fare
            self.private_distance += distance_moved
            
            self.private_last_location = current_location
            
            # Emit updates
            self.total_fare_updated.emit(self.private_fare)
            self.distance_updated.emit(self.private_distance)
        
        # Add waiting charges
        if current_speed < self.minimum_speed_threshold:
            waiting_charge_per_minute = 2.0
            waiting_charge = (time_delta / 60.0) * waiting_charge_per_minute
            self.private_fare += waiting_charge
            self.private_waiting_time += time_delta / 60.0
            
            self.total_fare_updated.emit(self.private_fare)
        
        # Update duration
        if self.private_start_time:
            duration_minutes = (datetime.now() - self.private_start_time).total_seconds() / 60
            self.duration_updated.emit(int(duration_minutes))

    def _calculate_distance(self, loc1, loc2):
        """Calculate distance between two coordinates using GPS manager"""
        if not loc1 or not loc2:
            return 0.0
        
        return self.gps_manager.calculate_distance(loc1[0], loc1[1], loc2[0], loc2[1])

    def handle_passenger_change(self, passenger_id, onboard):
        """Handle passenger boarding/alighting with GPS data"""
        if passenger_id >= len(self.passengers):
            return
            
        with self.lock:
            passenger = self.passengers[passenger_id]
            current_location = self.gps_manager.get_location()
            
            if onboard and not passenger['onboard']:
                # Passenger boarding
                passenger['onboard'] = True
                passenger['fare'] = 0.0
                passenger['start_location'] = current_location
                passenger['last_location'] = current_location
                passenger['start_time'] = datetime.now()
                passenger['total_distance'] = 0.0
                passenger['waiting_time'] = 0.0
                passenger['ride_id'] = f"SHARED1-{uuid.uuid4()}"

                print(f"🟢 Passenger {passenger_id+1} boarded at GPS: {current_location}")
                self.fare_updated.emit(passenger_id, 0.0)
                
            elif not onboard and passenger['onboard']:
                # Passenger alighting
                passenger['onboard'] = False
                end_time = datetime.now()
                duration = (end_time - passenger['start_time']).total_seconds() / 60
                
                # Calculate final distance from GPS
                final_distance = 0.0
                if passenger['start_location'] and current_location:
                    final_distance = self._calculate_distance(
                        passenger['start_location'], current_location
                    )
                
                # Prepare comprehensive ride data
                ride_data = {
                    'ride_id': passenger['ride_id'],
                    'passenger_id': passenger_id + 1,
                    'start_time': passenger['start_time'],
                    'end_time': end_time,
                    'duration_minutes': round(duration, 1),
                    'total_distance_km': round(passenger['total_distance'], 3),
                    'straight_line_distance_km': round(final_distance, 3),
                    'fare_amount': round(passenger['fare'], 2),
                    'fare_rate_per_km': self.fare_rate_per_km,
                    'waiting_time_minutes': round(passenger['waiting_time'], 1),
                    'start_location': passenger['start_location'],
                    'end_location': current_location,
                    'average_speed': round((passenger['total_distance'] / (duration/60)) if duration > 0 else 0, 1)
                }
                
                print(f"🔴 Passenger {passenger_id+1} completed ride:")
                print(f"   💰 Fare: ₹{ride_data['fare_amount']}")
                print(f"   💰 Fare: ₹{ride_data['ride_id']}")
                print(f"   🛣️ Distance: {ride_data['total_distance_km']} km")
                print(f"   ⏱️ Duration: {ride_data['duration_minutes']} min")
                print(f"   🚗 Avg Speed: {ride_data['average_speed']} km/h")
                print(f"   ⏳ Waiting: {ride_data['waiting_time_minutes']} min")
                
                self.ride_completed.emit(passenger_id, ride_data)
                
                # Reset passenger data
                passenger.update({
                    'fare': 0.0,
                    'start_location': None,
                    'last_location': None,
                    'start_time': None,
                    'total_distance': 0.0,
                    'waiting_time': 0.0,
                    'ride_id': None
                })

    def start_private_mode(self):
        """Start private mode fare calculation with GPS reset"""
        with self.lock: 
            self.private_mode_active = True
            self.private_fare = 0.0
            self.private_start_location = self.gps_manager.get_location()
            self.private_last_location = self.private_start_location
            self.private_start_time = datetime.now()
            self.private_distance = 0.0
            self.private_waiting_time = 0.0
            self.private_ride_id = f"PRIVATE1-{uuid.uuid4()}"

            
            # Reset GPS trip tracking
            self.gps_manager.reset_trip()
            
            print("🚖 Private mode started with GPS tracking")
            self.total_fare_updated.emit(0.0)
            self.distance_updated.emit(0.0)
            self.duration_updated.emit(0)

    def stop_private_mode(self):
        """Stop private mode and return comprehensive ride data"""
        with self.lock:
            if self.private_mode_active:
                self.private_mode_active = False
                end_time = datetime.now()
                duration = (end_time - self.private_start_time).total_seconds() / 60
                
                
                # Get final GPS data
                current_location = self.gps_manager.get_location()
                gps_total_distance = self.gps_manager.get_total_distance()
                
                # Calculate straight-line distance
                straight_line_distance = 0.0
                if self.private_start_location and current_location:
                    straight_line_distance = self._calculate_distance(
                        self.private_start_location, current_location
                    )
                
                ride_data = {
                    'ride_id': self.private_ride_id,
                    'start_time': self.private_start_time,
                    'end_time': end_time,
                    'duration_minutes': round(duration, 1),
                    'calculated_distance_km': round(self.private_distance, 3),
                    'gps_total_distance_km': round(gps_total_distance, 3),
                    'straight_line_distance_km': round(straight_line_distance, 3),
                    'fare_amount': round(self.private_fare, 2),
                    'fare_rate_per_km': self.fare_rate_per_km,
                    'waiting_time_minutes': round(self.private_waiting_time, 1),
                    'start_location': self.private_start_location,
                    'end_location': current_location,
                    'average_speed': round((gps_total_distance / (duration/60)) if duration > 0 else 0, 1),
                    'max_speed': round(max(0, self.gps_manager.get_speed()), 1)
                }
                
                print(f"🔴 Private ride completed:")
                print(f"   💰 Total Fare: ₹{ride_data['fare_amount']}")
                print(f"   💰 Total Fare: ₹{ride_data['ride_id']}")
                print(f"   🛣️ GPS Distance: {ride_data['gps_total_distance_km']} km")
                print(f"   📏 Straight Distance: {ride_data['straight_line_distance_km']} km")
                print(f"   ⏱️ Duration: {ride_data['duration_minutes']} min")
                print(f"   🚗 Avg Speed: {ride_data['average_speed']} km/h")
                print(f"   ⏳ Waiting: {ride_data['waiting_time_minutes']} min")
                
                return ride_data
        return None

    def get_passenger_fare(self, passenger_id):
        """Get current fare for a passenger"""
        if passenger_id < len(self.passengers):
            return self.passengers[passenger_id]['fare']
        return 0.0

    def get_total_fare(self):
        """Get total fare (for private mode)"""
        return self.private_fare

    def get_real_time_stats(self):
        """Get real-time GPS-based statistics"""
        gps_status = self.gps_manager.get_gps_status()
        
        return {
            'current_speed': round(self.gps_manager.get_speed(), 1),
            'total_distance': round(self.gps_manager.get_total_distance(), 3),
            'trip_duration': round(self.gps_manager.get_trip_duration(), 1),
            'gps_fix': gps_status['fix'],
            'satellites': gps_status['satellites'],
            'current_location': self.gps_manager.get_location()
        }

    def set_fare_rate(self, rate):
        """Update fare rate"""
        with self.lock:
            self.fare_rate_per_km = rate
            print(f"💰 Fare rate updated to ₹{rate}/km")

    def stop(self):
        """Stop fare calculator"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        print("💰 Fare Calculator stopped")