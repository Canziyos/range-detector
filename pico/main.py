# main.py – Pico firmware with Wi-Fi watchdog.
import boot
import machine
import gc, network
from time import ticks_ms, ticks_diff, sleep_ms
from machine import Pin
import socket_client as sc
import socket_server as ss
from utils import dbg, green_irq, red_irq, pir_irq
import utils

# SenseFuzzPWM imports
from sensefuzzpwm.input.sensors import PIR, Ultrasonic
from sensefuzzpwm.input.interaction import MotionDistanceManager
from sensefuzzpwm.output.pwm import PWM
from sensefuzzpwm.fuzzy_logic.fuzzy_core import FuzzyCore
from sensefuzzpwm.fuzzy_logic.fuzzy_config import input_sets, output_sets, output_ranges, rules

ssid = boot.SSID
pwd = boot.PWD

# ------------------------------------------------------------------ #
# Wi-Fi watchdog: reconnect without blocking main loop.
_last_wifi_try = 0  # ms timestamp of last reconnect attempt.

def wifi_watchdog(ssid: str, pwd: str, retry_ms: int = 10_000):
    """Re-connect if WLAN is down. Non-blocking; call each loop."""
    global _last_wifi_try

    wlan = network.WLAN(network.STA_IF)

    if wlan.isconnected():
        return

    now = ticks_ms()
    if ticks_diff(now, _last_wifi_try) < retry_ms:
        return

    _last_wifi_try = now
    wlan.active(True)
    wlan.connect(ssid, pwd)
    dbg("Wi-Fi watchdog: attempting reconnect")

# Data watchdog: maintain socket connection.
# ------------------------------------------------------------------ #
def data_watchdog():
    """Maintain the data socket connection (non-blocking)."""
    sc._ensure_connection()


# GPIO + IRQ configuration.
# ------------------------------------------------------------------ #
green_btn = Pin(13, Pin.IN, Pin.PULL_UP)
red_btn   = Pin(14, Pin.IN, Pin.PULL_UP)
ping_led  = Pin(18, Pin.OUT)
sys_led   = Pin(17, Pin.OUT)    # Status LED for system ON/OFF.
pir_pin   = Pin(12, Pin.IN)
pir_sensor = PIR(12)

# Attach IRQ handlers from utils
green_btn.irq(trigger=Pin.IRQ_FALLING, handler=green_irq)  # press => system ON.
red_btn.irq(trigger=Pin.IRQ_FALLING, handler=red_irq)      # press => system OFF.
pir_pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=pir_irq)  # PIR detect.


# Hardware components via SenseFuzzPWM.
# ------------------------------------------------------------------ #
ultra = Ultrasonic(15, 16)  # Ultrasonic on GPIO15/16.
manager = MotionDistanceManager(pir_sensor, ultra, active_ms=60000)

controller = FuzzyCore(input_sets, output_sets, rules, output_ranges)
buzzer = PWM(pin=28, mode="buzzer")  # Buzzer output


# Other constants.
# ------------------------------------------------------------------ #
blink_ms = 100
last_blink_ms = ticks_ms()
last_alert_state = False  # track last PIR alert status


# Start command server once.
# ------------------------------------------------------------------ #
cmd_srv = ss.make_cmd_server()

print("Boot complete. Entering main loop.")

while True:
    now = ticks_ms()

    wifi_watchdog(ssid, pwd)
    data_watchdog()
    ss.poll_command(cmd_srv, ping_led)

    # Blink ping LED briefly when PING received.
    if ping_led.value() and ticks_diff(now, last_blink_ms) > blink_ms:
        ping_led.low()

    # Update system status LED (ON/OFF indicator)
    sys_led.value(1 if utils.sys_on else 0)

    # -----------------------------
    # System OFF => disable outputs
    # -----------------------------
    if not utils.sys_on:
        buzzer.off()             # Buzzer silent.
        last_alert_state = False # Reset PIR alert tracking.
        #sleep_ms(100) # used before introducing lightsleep.
        # Enter light sleep until an interrupt occurs (green button press).
        machine.lightsleep()
        continue
    

    # -------------------------------------
    # System ON → handle PIR + fuzzy logic
    # -------------------------------------
    active, distance = manager.update()
    dbg("manager says: ", active, distance)

    # --- Alert message handling ---
    if active != last_alert_state:
        sc.write_line("alert: 1" if active else "alert: 0")
        dbg(f"Sent alert: {'1' if active else '0'}")
        last_alert_state = active

    # --- Distance + buzzer control ---
    if active and distance is not None:
        fuzzy_out = controller.compute({"distance": distance})
        duty = fuzzy_out["duty"]
        freq = min(max(100, fuzzy_out["freq"]), 2000)
        buzzer.update(freq=freq, duty=duty)

        sc.write_line(f"distance: {distance}")
        #dbg(f"distance sent: {distance} mm | duty={duty:.1f} freq={freq} Hz")
        dbg(f"distance sent: {distance} mm")
    else:
        buzzer.off()

    # Garbage collect every 5s.
    if now % 5000 < 50:
        gc.collect()

    sleep_ms(100)
