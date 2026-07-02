from machine import Pin, PWM as HW_PWM

class PWM:
    def __init__(self, pin, mode="generic", freq=1000, duty=0):
        """
        Generic PWM controller.
        mode: 'buzzer', 'led', 'servo', or 'generic'
        freq: default frequency in Hz.
        duty: initial duty in % (0-100).
        """
        try:
            self.pin = Pin(pin, Pin.OUT)  # Init pin.
            self.pwm = HW_PWM(self.pin)   # Init hardware PWM.
            self.mode = mode
            self.set_frequency(freq)
            self.set_duty(duty)
        except Exception as e:
            # If PWM init fails, fallback to safe dummy state.
            print("PWM init error:", e)
            self.pwm = None

    def set_frequency(self, freq):
        # Clamp to safe MicroPython range.
        try:
            freq = min(max(int(freq), 1), 20000)  # 1 Hz to 20 kHz.
            if self.pwm:
                self.pwm.freq(freq)
        except Exception as e:
            print("PWM freq error:", e)

    def set_duty(self, duty_percent):
        # Clamp 0-100% and map to 0-65535.
        try:
            duty_percent = min(max(duty_percent, 0), 100)
            if self.pwm:
                self.pwm.duty_u16(int(duty_percent / 100 * 65535))
        except Exception as e:
            print("PWM duty error:", e)

    def update(self, freq=None, duty=None):
        """
        Update both frequency and duty if provided.
        """
        try:
            if freq is not None:
                self.set_frequency(freq)
            if duty is not None:
                self.set_duty(duty)
        except Exception as e:
            print("PWM update error:", e)

    def off(self):
        """Stop output (set duty 0)."""
        try:
            if self.pwm:
                self.pwm.duty_u16(0)
        except Exception as e:
            print("PWM off error:", e)

    def deinit(self):
        # Stop output and free PWM resource.
        try:
            self.off()
            if self.pwm:
                self.pwm.deinit()
        except Exception as e:
            print("PWM deinit error:", e)
