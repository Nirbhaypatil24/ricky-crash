import threading
import requests

class SosSyncService:
    def __init__(self, base_url=None):
        self.base_url = (
            base_url
            or "https://ec2-13-220-53-209.compute-1.amazonaws.com/api/sos"
        ).rstrip("/")
        self.session = requests.Session()
        print(f"🔗 SosSyncService initialized with backend URL: {self.base_url}")

    def attach(self, sos_system):
        sos_system.sos_activated.connect(self._on_sos_activated)
        print("✅ SosSyncService attached to SOSSystem signals")

    def _on_sos_activated(self, sos_data):
        threading.Thread(
            target=self._send_to_backend,
            args=(sos_data,),
            daemon=True
        ).start()

    def _send_to_backend(self, sos_data):
        try:
            location = sos_data.get("location")

            # Defensive: ensure valid floats
            lat = float(location[0]) if location else 0.0
            lon = float(location[1]) if location else 0.0

            payload = {
                "type": sos_data.get("type", "SOS_BUTTON"),
                "latitude": lat,
                "longitude": lon
            }

            response = self.session.post(
                self.base_url,
                json=payload,        # ✅ FIX: SEND JSON BODY
                timeout=5
            )

            if response.status_code in (200, 201):
                print(f"✅ SOS synced successfully: {response.text}")
            else:
                print(
                    f"⚠️ SOS sync failed "
                    f"[{response.status_code}]: {response.text}"
                )

        except Exception as e:
            print(f"❌ SOS backend sync error: {e}")
