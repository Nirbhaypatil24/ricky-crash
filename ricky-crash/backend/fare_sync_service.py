import requests
import threading
import time

class FareSyncService:
    def __init__(self, base_url, driver_id, poll_interval_sec=15):
        self.base_url = base_url.rstrip("/")
        self.driver_id = driver_id
        self.poll_interval_sec = poll_interval_sec
        self.session = requests.Session()

        self.fare_calculator = None
        self.running = False
        self.last_known_rate = None

    def attach(self, fare_calculator):
        """
        Attach FareCalculator and start syncing
        """
        self.fare_calculator = fare_calculator
        fare_calculator.ride_completed.connect(self._on_ride_completed)

        self.running = True
        threading.Thread(
            target=self._fare_rate_poll_loop,
            daemon=True
        ).start()

    # ------------------ FARE RATE SYNC ------------------

    def _fare_rate_poll_loop(self):
        """
        Poll backend for fare rate updates
        """
        while self.running:
            try:
                url = f"{self.base_url}/api/fare/get"
                response = self.session.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    new_rate = float(data.get("fare_rate"))

                    if self.last_known_rate != new_rate:
                        self.last_known_rate = new_rate
                        self.fare_calculator.set_fare_rate(new_rate)
                        print(f"🔄 Fare rate synced from backend: ₹{new_rate}/km")

                else:
                    print(f"⚠️ Fare rate fetch failed: {response.status_code}")

            except Exception as e:
                print(f"❌ Fare rate sync error: {e}")

            time.sleep(self.poll_interval_sec)

    # ------------------ RIDE SYNC ------------------

    def _on_ride_completed(self, passenger_id, ride_data):
        threading.Thread(
            target=self._send_to_backend,
            args=(passenger_id, ride_data),
            daemon=True
        ).start()

    def _send_to_backend(self, passenger_id, ride_data):
      try:
        # ---------------- RIDE TYPE FIX ----------------
        if passenger_id == -1:
            # Private ride
            passenger_id_value = None
            ride_type = "PRIVATE"
        else:
            # Shared ride
            passenger_id_value = str(passenger_id + 1)
            ride_type = "SHARED"

        # ---------- BACKEND NULL SAFETY (MANDATORY) ----------
        start_loc = ride_data.get("start_location")
        end_loc = ride_data.get("end_location")

        if not start_loc or not end_loc:
            print("⚠️ Backend sync skipped: missing GPS data")
            return

        payload = {
            "rideId": ride_data["ride_id"],
            "driver_id": self.driver_id,
            "rideType": ride_type,
            "passengerId": passenger_id_value,

            "startTime": ride_data["start_time"].isoformat(),
            "endTime": ride_data["end_time"].isoformat(),

            "startLatitude": start_loc[0],
            "startLongitude": start_loc[1],
            "endLatitude": end_loc[0],
            "endLongitude": end_loc[1],

            "distanceKm": ride_data["total_distance_km"],
            "fareAmount": ride_data["fare_amount"],
            "fareRate": ride_data["fare_rate_per_km"]
        }

        url = f"{self.base_url}/api/fares/autometer"

        response = self.session.post(url, json=payload, timeout=5)

        if response.status_code != 200:
            print(f"⚠️ Fare sync failed: {response.status_code} {response.text}")
        else:
            print("✅ Fare synced to backend")

      except Exception as e:
        print(f"❌ Backend sync error: {e}")


