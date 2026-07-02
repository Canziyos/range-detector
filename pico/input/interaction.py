# input/interaction.py
from time import ticks_ms, ticks_diff

class MotionDistanceManager:
    def __init__(self, pir_sensor, distance_sensor, active_ms=60000):
        # PIR and distance sensor objects.
        self.pir = pir_sensor
        self.distance = distance_sensor
        self.active_ms = active_ms
        self.state = "IDLE"
        self.last_motion = 0  # last time PIR was HIGH.

    def update(self):
        """
        Returns:
          - active (bool): should fuzzy logic run?
          - distance (mm or None): current distance (if active).
        """
        try:
            now = ticks_ms()

            # --- PIR READ ---
            pir_value = 0
            try:
                pir_value = self.pir.read() if self.pir else 0  # safe PIR read.
            except Exception as e:
                print("PIR read error in manager:", e)
                pir_value = 0

            # --- STATE LOGIC ---
            if self.state == "IDLE":
                if pir_value == 1:  # Motion detected.
                    self.state = "ACTIVE"
                    self.last_motion = now

            elif self.state == "ACTIVE":
                if pir_value == 1:
                    self.last_motion = now  # refresh active window.
                elif ticks_diff(now, self.last_motion) > self.active_ms:
                    self.state = "IDLE"  # 1 min expired.

            # --- OUTPUT ---
            active = self.state == "ACTIVE"
            distance = None
            if active and self.distance:
                try:
                    distance = self.distance.read()  # safe ultrasonic read.
                except Exception as e:
                    print("Distance read error in manager:", e)
                    distance = None

            return active, distance

        except Exception as e:
            # Top-level fallback: system stays safe if manager crashes.
            print("Manager update error:", e)
            return False, None
