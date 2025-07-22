import time, gc, network
from machine import Pin, PWM, time_pulse_us
from time import sleep
from socket_client import get_data_client, send_distance
from socket_server import make_cmd_server, poll_command, get_last_ping_time
from secrets import WIFI_SSID, WIFI_PASS 


# Wi-Fi helper
def connect_to_wifi(ssid="ssid",
                    password="password",
                    timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while timeout > 0 and not wlan.isconnected():
        print("Wi-Fi status:", wlan.status(), "...waiting")
        sleep(1)
        timeout -= 1
    if wlan.isconnected():
        print("Pico online @", wlan.ifconfig()[0])
        return True
    print("Wi-Fi failed.")
    return False


 # Setup pins
green_btn = Pin(12, Pin.IN, Pin.PULL_UP)
red_btn = Pin(13, Pin.IN, Pin.PULL_UP)
buz = Pin(14, Pin.OUT)
trig_pin = Pin(15, Pin.OUT)
echo_pin = Pin(16, Pin.IN)
pwm_led = PWM(Pin(17))
ping_led = Pin(18, Pin.OUT)

pwm_led.freq(1000)
#buz.freq(200)
# thresholds
min_dist  = 150 # brightest.
max_dist  = 2000 # led dimmest.

# rolling-average window.
dist_window = []
win_size     = 5

# command server (ONE instance).
cmd_srv = make_cmd_server()       # listens on port 1234.


def get_raw_pulse(trig_pin, echo_pin, timeout_us = 30000):
    trig_pin.value(0)
    time.sleep_us(2)
    trig_pin.value(1)
    time.sleep_us(10)
    trig_pin.value(0)

    try:
        return time_pulse_us(echo_pin, 1, timeout_us)  # blocks IRQ-safe.
    except OSError:
        return None
def buzz():
    buzzer = PWM(buz)
    buzzer.freq(200)
    buzzer.duty_u16(25000)
    time.sleep(1)
    buzzer.duty_u16(0)
    buzzer.deinit()

def distance_to_pwm_u16(dist):
    if dist <= min_dist:
        return 0
    if dist >= max_dist:
        return 1000
    ratio = (dist - min_dist) / (max_dist - min_dist)
    return int((1 - ratio)*65535)

# Main
if not connect_to_wifi():
    raise SystemExit

cli            = None
last_send_ms   = 0
heartbeat_ms   = 2000          # push a sample every 2 s.
gc_tick        = time.ticks_ms()
last_blink_ms = 0
blink_ms = 100
sensing_active = True
last_gp = 0
last_rp = 0
debounce = 300
buzz_last_time = 0
buzz_cooldown = 1000 # 1sec.
while True:
    now = time.ticks_ms()


    if green_btn.value() == 0:
        if time.ticks_diff(now, last_gp) > debounce:
            sensing_active = True
            print("sensing...")
            last_gp = now

    if red_btn.value() == 0:
        if time.ticks_diff(now, last_rp)>debounce:
            sensing_active = False
            print("Not sensing..")
            last_rp = now

    if ping_led.value() and time.ticks_diff(now, last_blink_ms) > blink_ms:
        ping_led.value(0) 

    # GC every second (keeps heap healthy).
    if time.ticks_diff(now, gc_tick) >= 1000:
        gc.collect()
        gc_tick = now

    # Service control socket.
    poll_command(cmd_srv, pwm_led, ping_led)

    if sensing_active:

        # Read sensor
        pulse = get_raw_pulse(trig_pin, echo_pin, timeout_us=30000)
        
        if pulse is None:
            print(pulse)
            pass
        else:
            dist_mm = (pulse*172)/1000
            if dist_mm < min_dist:
                if time.ticks_diff(now, buzz_last_time) > buzz_cooldown:
                    buzz()
                    buzz_last_time = now
                continue

            # update every loop (in-range and too-far)
            br = distance_to_pwm_u16(dist_mm)
            pwm_led.duty_u16(br)
            print(br)

            dist_window.append(dist_mm)
            if len(dist_window) > win_size:
                dist_window.pop(0)

            if len(dist_window) == win_size:
                avg = sum(dist_window) / win_size
                #print("avg pulse:", avg)

                # send to PC every heartbeat_ms while object is IN
                if time.ticks_diff(now, last_send_ms) > heartbeat_ms:
                    if cli is None:                # ask only when necessary.
                        cli = get_data_client()    # non-blocking dial.
                    if cli and send_distance(cli, int(avg)):
                        print(f"Sent avg distance: {int(avg)} mm")
                        last_send_ms = now
                    else:
                        cli = None                 # force new connect next time.

    sleep(0.05)
