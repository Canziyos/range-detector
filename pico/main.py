# main.py – Pico firmware with Wi-Fi watchdog.
import boot
import gc, network
from time import ticks_ms, ticks_diff, sleep_ms, sleep_us
from machine import time_pulse_us, Pin, PWM
import socket_client as sc
import socket_server as ss
from utils import dbg
import utils
ssid = boot.SSID
pwd = boot.PWD
# ------------------------------------------------------------------ #
# Wi-Fi watchdog: reconnect without blocking main loop.              #
# ------------------------------------------------------------------ #
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

# ------------------------------------------------------------------ #
# data watchdog: reconnect without blocking main loop.              #
# ------------------------------------------------------------------ #
def data_watchdog():
    """ Maintain the data socket conection,
    (none-blocking, uses back-off)"""
    sc._ensure_connection()

# ------------------------------------------------------------------ #
# GPIO configuration.                                                #
# ------------------------------------------------------------------ #
green_btn = Pin(13, Pin.IN, Pin.PULL_UP)
red_btn   = Pin(14, Pin.IN, Pin.PULL_UP)
trig = Pin(15, Pin.OUT)
echo = Pin(16, Pin.IN)
pwm_led = PWM(Pin(17))
pwm_led.freq(1_000)
ping_led = Pin(18, Pin.OUT)

# ------------------------------------------------------------------ #
# Globals and constants.                                             #
# ------------------------------------------------------------------ #
blink_ms  = 100

last_blink_ms = last_green_ms = last_red_ms = ticks_ms()
debounce_ms   = 300


# ------------------------------------------------------------------ #
# Helper: distance --> PWM duty.                                     #
# ------------------------------------------------------------------ #
def distance_to_pwm_u16(dist_mm: int) -> int:
    if dist_mm <= utils.min_dist:
        return 65_535
    if dist_mm >= utils.max_dist:
        return 0
    span = utils.max_dist - utils.min_dist
    pct  = 1.0 - (dist_mm - utils.min_dist) / span
    return int(pct * 65_535)

# ------------------------------------------------------------------ #
# Ultrasonic distance.                                               #
# ------------------------------------------------------------------ #
def measure_distance_mm() -> int:
    trig.low(); sleep_us(2)
    trig.high(); sleep_us(10); trig.low()
    pulse = time_pulse_us(echo, 1, 30_000)
    return utils.max_dist if pulse < 0 else int(pulse * 0.1715)

# ------------------------------------------------------------------ #
# Start command server once.                                         #
# ------------------------------------------------------------------ #
cmd_srv = ss.make_cmd_server()

print("Boot complete. Entering main loop.")

while True:
    now = ticks_ms()

    wifi_watchdog(ssid, pwd)
    data_watchdog()
    ss.poll_command(cmd_srv, pwm_led, ping_led)

    if utils.buttons_enabled:
        if green_btn.value() == 0 and ticks_diff(now, last_green_ms) > debounce_ms:
            utils.sensing_active = True
            dbg("Green button --> sensing_active = True")
            last_green_ms = now
        if red_btn.value() == 0 and ticks_diff(now, last_red_ms) > debounce_ms:
            utils.sensing_active = False
            dbg("Red button --> sensing_active = False")
            last_red_ms = now

    if ping_led.value() and ticks_diff(now, last_blink_ms) > blink_ms:
        ping_led.low()

    if utils.sensing_active:
        dist = measure_distance_mm()
        dbg(f"dist: {dist}")
        pwm_led.duty_u16(distance_to_pwm_u16(dist))
        ok = sc.write_line(f"distance: {dist}")
        if ok:
            dbg("distance sent", dist)
    else:
        pwm_led.duty_u16(0)

    if now % 5_000 < 50:
        gc.collect()

    sleep_ms(100)
