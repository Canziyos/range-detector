# boot.py – bring Wi-Fi up once, before main.py starts.

import network, time

SSID = "TN_wifi_D6C00D"
PWD  = "7WDFEWGTNM"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

if not wlan.isconnected():
    wlan.connect(SSID, PWD)
    t0 = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), t0) > 15_000:   # 15-s cap.
            print("boot.py Wi-Fi timeout - main.py will retry")
            break
        time.sleep_ms(200)

if wlan.isconnected():
    print("boot.py Wi-Fi up -->", wlan.ifconfig()[0])
