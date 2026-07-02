from machine import Pin, time_pulse_us
from time import sleep_us, ticks_ms, ticks_diff

class Ultrasonic:
    def __init__(self, trig_pin, echo_pin, max_distance_mm=2000, samples=3):
        """
        Ultrasonic distance sensor.
        trig_pin, echo_pin: GPIO numbers
        max_distance_mm: maximum measurable distance (beyond = None)
        samples: number of readings to average for smoothing
        """
        try:
            self.trig = Pin(trig_pin, Pin.OUT)  # Init trigger pin.
            self.echo = Pin(echo_pin, Pin.IN)   # Init echo pin.
        except Exception as e:
            print("Ultrasonic init error:", e)
            self.trig = None
            self.echo = None
        self.max_distance_mm = max_distance_mm
        self.samples = samples

    def _single_read(self):
        """Perform one ultrasonic measurement (raw)."""
        if not self.trig or not self.echo:
            return None  # No hardware init.

        try:
            # Trigger pulse.
            self.trig.low()
            sleep_us(2)
            self.trig.high()
            sleep_us(10)
            self.trig.low()

            # Measure echo.
            pulse = time_pulse_us(self.echo, 1, 30_000)  # timeout 30ms.
            if pulse < 0:
                return None
            dist = int(pulse * 0.1715)  # mm.
            if dist > self.max_distance_mm:
                return None
            return dist
        except Exception as e:
            print("Ultrasonic read error:", e)
            return None

    def read(self):
        """
        Return averaged distance in mm (or None if no valid reading).
        """
        readings = []
        try:
            for _ in range(self.samples):
                d = self._single_read()
                if d is not None:
                    readings.append(d)
                sleep_us(1000)  # small delay between samples.
            return int(sum(readings) / len(readings)) if readings else None
        except Exception as e:
            print("Ultrasonic average read error:", e)
            return None


class PIR:
    def __init__(self, sense_pin, warmup_ms=30000):
        """
        PIR motion sensor (digital).
        sense_pin: GPIO number
        warmup_ms: ignore readings for this duration after power-up
        """
        try:
            self.sense = Pin(sense_pin, Pin.IN)  # Init PIR pin.
        except Exception as e:
            print("PIR init error:", e)
            self.sense = None
        self.warmup_ms = warmup_ms
        self.start_time = ticks_ms()

    def read(self):
        """
        Return 0 or 1 after warm-up period.
        Before warm-up expires, always return 0.
        """
        if not self.sense:
            return 0  # Fallback if no hardware.
        try:
            if ticks_diff(ticks_ms(), self.start_time) < self.warmup_ms:
                return 0
            return self.sense.value()
        except Exception as e:
            print("PIR read error:", e)
            return 0
